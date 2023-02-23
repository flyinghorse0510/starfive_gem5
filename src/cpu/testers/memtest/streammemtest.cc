/*
 * Copyright (c) 2015, 2019, 2021 Arm Limited
 * All rights reserved
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 2002-2005 The Regents of The University of Michigan
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "cpu/testers/memtest/streammemtest.hh"

#include "base/compiler.hh"
#include "base/random.hh"
#include "base/statistics.hh"
#include "base/trace.hh"
#include "debug/StreamTest.hh"
#include "sim/sim_exit.hh"
#include "sim/stats.hh"
#include "sim/system.hh"
#include <algorithm>
#include <cmath>
#include "cpu/testers/memtest/common.hh"

namespace gem5
{

bool
StreamMemTest::CpuPort::recvTimingResp(PacketPtr pkt)
{
    streammemtest.completeRequest(pkt);
    return true;
}

void
StreamMemTest::CpuPort::recvReqRetry()
{
    streammemtest.recvRetry();
}

bool
StreamMemTest::sendPkt(PacketPtr pkt) {
    if (atomic) {
        port.sendAtomic(pkt);
        completeRequest(pkt);
    } else {
        if (!port.sendTimingReq(pkt)) {
            retryPkt = pkt;
            return false;
        }
    }
    return true;
}

StreamMemTest::StreamMemTest(const Params &p)
    : ClockedObject(p),
      id(p.id), // pass from python
      numCpus(p.num_cpus),
      tickEvent([this]{ tick(); }, name()),
      noRequestEvent([this]{ noRequest(); }, name()),
      noResponseEvent([this]{ noResponse(); }, name()),
      port("port", *this),
      retryPkt(nullptr),
      waitResponse(false),
      a(p.addr_a),
      b(p.addr_b),
      c(p.addr_c),
      scale(p.scale),
      maxLoads(p.max_loads),
      wsSize(p.ws_size),
      maxOutstanding(p.max_outstanding),
      lsqPolicy(static_cast<LSQPolicy>(p.lsq_policy)),
      interval(p.interval),
      requestorId(p.system->getRequestorId(this)),
      blockSize(p.system->cacheLineSize()), // 64 byte
      blockAddrMask(blockSize-1),
      progressInterval(p.progress_interval),
      progressCheck(p.progress_check),
      nextProgressMessage(p.progress_interval),
      atomic(p.system->isAtomicMode()),
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48),
      suppressFuncErrors(p.suppress_func_errors), stats(this)
{
    // set up counters
    numReads = 0;
    numWrites = 0;
    numIters = 0;
    maxIters = wsSize*maxLoads/numCpus/blockSize;

    // generate the LSQ
    for (uint64_t it=0; it<maxIters; it++){
        offset_t offset = (id+numCpus*it)*blockSize%wsSize;
        assert(blockAlign(b+offset) == b+offset);
        loadq.emplace(it, offset, LSType::LD, 1, b+offset); // TODO: hardcoded data to be 1 in b
        loadq.emplace(it, offset, LSType::LD, 2, c+offset); // TODO: hardcoded data to be 2 in c
    }
    
    DPRINTF(StreamTest, "id:%u, numCpus:%u, blkSize: %u, maxiter:%lu, maxOutstanding:%lu, wsSize:%lu, a:%s, b:%s, c:%s, lsqPolicy:%d\n", 
            id, numCpus, blockSize, maxIter, maxOutstanding, wsSize, a, b, c, lsqPolicy);

    // kick things into action
    schedule(tickEvent, curTick());
    schedule(noRequestEvent, clockEdge(progressCheck));
}

Port &
StreamMemTest::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "port")
        return port;
    else
        return ClockedObject::getPort(if_name, idx);
}

void
StreamMemTest::completeRequest(PacketPtr pkt, bool functional)
{
    const RequestPtr &req = pkt->req;
    assert(req->getSize() == 2); // TODO: what does this check?

    // this memTxnId is no longer outstanding
    auto remove_paddr = req->getPaddr();
    auto remove_addr = outstandingAddrs.find(req->getPaddr());
    assert(remove_addr != outstandingAddrs.end());
    outstandingAddrs.erase(remove_addr);

    const double *pkt_data = pkt->getConstPtr<double>();

    if (pkt->isError()) {
        if (!functional || !suppressFuncErrors)
            panic( "%s access failed at %#x\n",
                pkt->isWrite() ? "Write" : "Read", req->getPaddr());
    } else {
        if (pkt->isRead()) {
            Addr addr = req->getPaddr();
            if(addr>=b && addr<c){
                offset_t offset = addr-b;
                assert(waitTable.find(offset) != waitTable.end());
                assert(!(uint32_t(waitTable[offset].state) & (1<<0))); // 00:None, 01:RecvB, 10:RecvC, 11:Ready; cannot be RecvB or Ready
                waitTable[offset].state = WaitState(uint32_t(waitTable[offset].state) | WaitState::RecvB);
                waitTable[offset].b = *pkt_data;
            }
            else if(addr>=c && addr<c+wsSize){
                offset_t offset = addr-c;
                assert(waitTable.find(offset) != waitTable.end());
                assert(!(uint32_t(waitTable[offset].state) & (1<<1))); // 00:None, 01:RecvB, 10:RecvC, 11:Ready; cannot be RecvC or Ready
                waitTable[offset].state = WaitState(uint32_t(waitTable[offset].state) | WaitState::RecvC);
                waitTable[offset].c = *pkt_data;
            }
            else{
                panic("Recv addr out of range: %u\n", addr);
            }

            DPRINTF(StreamTest, "Complete,%x,R,%x\n", req->getPaddr(), *pkt_data);
            
            numReads++;
            stats.numReads++;

            if (numReads == (uint64_t)nextProgressMessage) {
                ccprintf(std::cerr,
                        "%s: completed %lu read, %lu write accesses @%d\n",
                        name(), numReads, numWrites, curTick());
                nextProgressMessage += progressInterval;
            }
        } else {
            assert(pkt->isWrite());
            DPRINTF(StreamTest, "Complete,%x,W,%x\n", req->getPaddr(), *pkt_data);

            numWrites++;
            stats.numWrites++;

            numIter++;
            if (numIter >= maxIter) {
                printf("Reach MaxLoads, maxLoad:%lu, numReads:%lu numWrites:%lu \n", maxIter, numReads, numWrites);
                exitSimLoop("maximum number of loads/stores reached");
            }
        }
    }

    // the packet will delete the data
    delete pkt;

    // finally shift the response timeout forward if we are still
    // expecting responses; deschedule it otherwise
    if (outstandingAddrs.size() != 0)
        reschedule(noResponseEvent, clockEdge(progressCheck));
    else if (noResponseEvent.scheduled())
        deschedule(noResponseEvent);
    
    // schedule the next tick
    if (waitResponse) {
        waitResponse = false;
        schedule(tickEvent, clockEdge(interval));
    }
}
StreamMemTest::MemTestStats::MemTestStats(statistics::Group *parent)
      : statistics::Group(parent),
      ADD_STAT(numReads, statistics::units::Count::get(),
               "number of read accesses completed"),
      ADD_STAT(numWrites, statistics::units::Count::get(),
               "number of write accesses completed")
{

}

double
StreamMemTest::triad(double data_b, double data_c)
{
    return data_b + scale*data_c;
}

void
StreamMemTest::checkRdy()
{
    for(auto it=waitTable.begin(); it != waitTable.end(); it++){
        double data = triad(it->second.b, it->second.c);
        Addr addr = a + it->second.offset;
        storeq.emplace(it->second.iter, it->second.offset, LSType::ST, data, addr);
        it = waitTable.erase(it); // must update it to the next it
    }
}


StreamMemTest::StreamReq
StreamMemTest::arbitration(std::queue<StreamReq> loadq, std::queue<StreamReq> storeq)
{
    StreamReq stmReq;
    switch(lsqPolicy){
    case LSQPolicy::RoundRobin:
        if(storeq.empty()){
            assert(!loadq.empty()); // if loadq is also empty, need to check
            stmReq = loadq.front();
            loadq.pop();
        }
        else{
            stmReq = storeq.front();
            storeq.pop();
        }
        break;
    case LSQPolicy::StoreFirst:
        if(storeq.empty()){
            assert(!loadq.empty()); // if loadq is also empty, need to check
            stmReq = loadq.front();
            loadq.pop();
        }
        else{
            stmReq = storeq.front();
            storeq.pop();
        }
        break;
    default:
        panic("Current LSQ arbitration only supports RoundRobin and StoreFirst\n");
        break;
    }
}

void
StreamMemTest::issueCmd()
{
    // create a new request
    Request::Flags flags;

    StreamReq stmreq = arbitration(loadq, storeq);
    
    RequestPtr req = std::make_shared<Request>(stmreq.addr, 8, flags, requestorId);

    assert(req->getPaddr() == stmreq.addr);

    req->setContext(id);
    req->setReqInstSeqNum(txSeqNum); // zhiang: TODO: here we test InstSeqNum, maybe changed by controllers downstream, let's see

    outstandingAddrs.insert(stmreq.addr);
    
    PacketPtr pkt = nullptr;
    double *pkt_data = new double;

    if (stmreq.typ == LSType::LD) {
        pkt = new Packet(req, MemCmd::ReadReq);
        pkt->dataDynamic(pkt_data);
        WaitData waitData = WaitData(it, offset, WaitState::None);
        waitTable[offset] = waitData; // we choose offset as key since when we receive response we can get offset easily
        DPRINTF(StreamTest,"Start,%x,R,%x\n",req->getPaddr(), stmreq.data);
    } else {
        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        *pkt_data = stmreq.data;
        DPRINTF(StreamTest,"Start,%x,W,%x\n",req->getPaddr(),stmreq.data);
    }
    
    // there is no point in ticking if we are waiting for a retry
    bool keep_ticking = sendPkt(pkt);
    if (keep_ticking) {
        // schedule the next tick
        schedule(tickEvent, clockEdge(interval));

        // finally shift the timeout for sending of requests forwards
        // as we have successfully sent a packet
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    } else {
        DPRINTF(StreamTest, "Waiting for retry\n");
    }

    txSeqNum++; // for each transaction,increase 1 to generate a new txSeqNum
}

void
StreamMemTest::tick()
{
    // we should never tick if we are waiting for a retry
    assert(!retryPkt);
    assert(!waitResponse);

    /* Too many outstanding transactions */
    if ((outstandingAddrs.size() >= maxOutstanding) || (outstandingAddrs.size() >= maxIter)) {
        waitResponse = true;
        return;
    }

    checkRdy();
    issueCmd();

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs.size() != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
}

void
StreamMemTest::noRequest()
{
    panic("%s did not send a request for %d cycles", name(), progressCheck);
}

void
StreamMemTest::noResponse()
{
    panic("%s did not see a response for %d cycles", name(), progressCheck);
}

void
StreamMemTest::recvRetry()
{
    assert(retryPkt);
    if (port.sendTimingReq(retryPkt)) {
        DPRINTF(StreamTest, "Proceeding after successful retry\n");

        retryPkt = nullptr;
        // kick things into action again
        schedule(tickEvent, clockEdge(interval));
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    }
}

} // namespace gem5
