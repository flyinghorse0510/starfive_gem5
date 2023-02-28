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
      maxLoads(p.maxloads),
      wsSize(p.ws_size),
      maxOutstanding(p.max_outstanding),
      arbiPolicy(static_cast<ArbiPolicy>(p.arbi_policy)),
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

    // generate the cmd list
    for (uint64_t it=0; it<maxIters; it++){
        uint64_t offset = (id+numCpus*it)*blockSize%wsSize;
        assert(blockAlign(b+offset) == b+offset);
        STReq* streq = new STReq(it, 0, a+offset, b, c, wsSize, STState::INIT); // must use shared_ptr, otherwise LDReq cannot ref to this obj
        STList.push_back(streq); // STReq(uint64_t iter, double val, Addr addr, Addr addr_b, Addr addr_c, uint64_t wsSize, STState state)

        // TODO: hardcoded val = 1 for b and val = 2 for c
        LDReq* ldreq = new LDReq(it, 1, b+offset, LDState::PREP, streq);
        LDList.push_back(ldreq); // LDReq(uint64_t iter, double val, Addr addr, LDState state, STReq* streq)
        ldreq = new LDReq(it, 2, c+offset, LDState::PREP, streq);
        LDList.push_back(ldreq); // LDReq(uint64_t iter, double val, Addr addr, LDState state, STReq* streq)
    }
    
    printf("StreamMemTest(%p) ctor: id:%u, numCpus:%u, blkSize: %u, maxLoads:%lu, maxiter:%lu, maxOutstanding:%lu, wsSize:%lu, a:%#lx, b:%#lx, c:%#lx, arbiPolicy:%d\n", 
            this, id, numCpus, blockSize, maxLoads, maxIters, maxOutstanding, wsSize, a, b, c, int(arbiPolicy));

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
    assert(req->getSize() == 8); // TODO: what does this check?

    // this memTxnId is no longer outstanding
    auto rspAddr = req->getPaddr();

    const double *pkt_data = pkt->getConstPtr<double>();

    if (pkt->isError()) {
        if (!functional || !suppressFuncErrors)
            panic( "%s access failed at %#lx\n",
                pkt->isWrite() ? "Write" : "Read", req->getPaddr());
    } else {
        if (pkt->isRead()) { // must be LDReq
            auto remove_addr = outstandingLDAddrs.find(req->getPaddr());
            assert(remove_addr != outstandingLDAddrs.end());
            assert((rspAddr >=b && rspAddr < b+wsSize) || (rspAddr >=c && rspAddr < c+wsSize)); // boundary check, [b,b+wsSize) or [c,c+wsSize)

            std::list<LDReq*>::iterator ldReqIt = remove_addr->second;

            printf("In tick %lu: Recv response for LDReq[%lu](addr:%#lx, state:%d), updated outstandingLDAddrs:\n", curTick(), (*ldReqIt)->iter, (*ldReqIt)->addr, int((*ldReqIt)->state));
            outstandingLDAddrs.erase(remove_addr);

            for(auto it = outstandingLDAddrs.begin(); it != outstandingLDAddrs.end(); it++){
                LDReq* req = (*(*it).second);
                printf("outstandingLDAddrs[%#lx] = LDReq[%lu](addr:%#lx, state:%d)\n", (*it).first, req->iter, req->addr, int(req->state));
            }
            
            (*ldReqIt)->wakeupST(*pkt_data);
            LDList.erase(ldReqIt); // TODO: here we directly copy data to ST and thus can delete LD. Otherwise need to wait for ST to delete LD
            delete (*ldReqIt);

            DPRINTF(StreamTest, "Complete,%#lx,R,%lu\n", req->getPaddr(), *pkt_data);

            numReads++;
            stats.numReads++;

        } else { // must be STReq
            assert(pkt->isWrite());
            
            auto remove_addr = outstandingSTAddrs.find(req->getPaddr());
            assert(remove_addr != outstandingSTAddrs.end());
            assert(rspAddr >=a && rspAddr <a+wsSize); // boundary check, [a,a+wsSize)

            std::list<STReq*>::iterator stReqIt = remove_addr->second;

            printf("In tick %lu: Recv response for STReq[%lu](addr:%#lx, state:%d), updated outstandingSTAddrs:\n", curTick(), (*stReqIt)->iter, (*stReqIt)->addr, int((*stReqIt)->state));
            outstandingSTAddrs.erase(remove_addr);
            

            for(auto it = outstandingSTAddrs.begin(); it != outstandingSTAddrs.end(); it++){
                STReq* req = (*(*it).second);
                printf("outstandingSTAddrs[%#lx] = STReq[%lu](addr:%#lx, state:%d)\n", (*it).first, req->iter, req->addr, int(req->state));
            }
            
            STList.erase(stReqIt); // TODO: here we directly copy data to ST and thus can delete LD. Otherwise need to wait for ST to delete LD
            delete (*stReqIt);

            DPRINTF(StreamTest, "Complete,%#lx,W,%lu\n", req->getPaddr(), *pkt_data);

            numWrites++;
            stats.numWrites++;

            numIters++; // here we actually complete the iteration
            if (numIters >= maxIters) {
                // sanity check
                assert(STList.empty() && LDList.empty());
                printf("in tick %lu: Reach MaxLoads, maxLoad:%lu, numReads:%lu numWrites:%lu \n", curTick(), maxIters, numReads, numWrites);
                exitSimLoop("maximum number of loads/stores reached");
            }
        }
    }

    // the packet will delete the data
    delete pkt;

    // finally shift the response timeout forward if we are still
    // expecting responses; deschedule it otherwise
    std::size_t outstandingAddrs = outstandingLDAddrs.size() + outstandingSTAddrs.size();
    if (outstandingAddrs != 0)
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


void
StreamMemTest::tick()
{
    printf("Enter tick %lu\n", curTick());
    // we should never tick if we are waiting for a retry
    assert(!retryPkt);
    assert(!waitResponse);

    /* Too many outstanding transactions */
    size_t outstandingAddrs = outstandingLDAddrs.size() + outstandingSTAddrs.size();
    // LD+ST >= maxOutstanding, TODO: do we need another maxOutstanding check like seqmemtest
    // the reason for seqmemtest to check if outstandingAddrs exceed the address map is if it does,
    // further sending is meaningless and can cause deadlock.
    // sendLD and sendST is to avoid deadlock. LD can have twice the size of numIters in one wkset since we have B and C
    bool sendLD = outstandingLDAddrs.size() < wsSize*2/numCpus/blockSize;
    bool sendST = outstandingSTAddrs.size() < wsSize/numCpus/blockSize;

    if ((outstandingAddrs >= maxOutstanding) || (!sendST && !sendLD)) {
        waitResponse = true;
        printf("Exit tick %lu with too many outstanding\n", curTick());
        return;
    }

    
    // first choose an available req from both LDList and STList
    std::list<STReq*>::iterator stReqIt = STList.end();
    std::list<LDReq*>::iterator ldReqIt = LDList.end();

    printf("In tick %lu: sendLD=%d sendST=%d\n",curTick(), sendLD, sendST);
    
    if(sendLD){
        for(auto it=LDList.begin(); it != LDList.end(); it++){
            printf("LDList[%lu]: addr:%#lx, state:%d\n", (*it)->iter, (*it)->addr, int((*it)->state));
            if((*it)->state == LDState::PREP){
                if(outstandingLDAddrs.find((*it)->addr) == outstandingLDAddrs.end())
                {
                    ldReqIt = it;
                    break;
                } // if addr not appears in outstaningLDAddrs, break the loop
            } // if not PREP, we need to skip this
        }
        if(ldReqIt != LDList.end()){
            printf("LDList[%lu] is chosen.\n", (*ldReqIt)->iter);
        }
        else{
            printf("No LD chosen\n");
        }
    }
    
    if(sendST){
        for(auto it=STList.begin(); it != STList.end(); it++){
            printf("STList[%lu]: addr:%#lx, state:%d\n", (*it)->iter, (*it)->addr, int((*it)->state));
            if((*it)->state == STState::PREP){
                if(outstandingSTAddrs.find((*it)->addr) == outstandingSTAddrs.end())
                {
                    stReqIt = it;
                    break;
                } // if addr not appears in outstaningSTAddrs, break the loop
            } // if not PREP, we need to skip this
        }
        if(stReqIt != STList.end()){
            printf("STList[%lu] is chosen.\n", (*stReqIt)->iter);
        }
        else{
            printf("No ST chosen\n");
        }
    }

    // meaning in this loop we cannot select an addr
    if(stReqIt == STList.end() && ldReqIt == LDList.end()){
        for(auto it = outstandingLDAddrs.begin(); it != outstandingLDAddrs.end(); it++){
            LDReq* req = (*(*it).second);
            printf("outstandingLDAddrs[%#lx] = LDReq[%lu](addr:%#lx, state:%d)\n", (*it).first, req->iter, req->addr, int(req->state));
        }
        for(auto it = outstandingSTAddrs.begin(); it != outstandingSTAddrs.end(); it++){
            STReq* req = (*(*it).second);
            printf("outstandingSTAddrs[%#lx] = STReq[%lu](addr:%#lx, state:%d)\n", (*it).first, req->iter, req->addr, int(req->state));
        }
        printf("In tick %lu: Cannot find an available request\n", curTick());

        std::size_t outstandingAddrs = outstandingLDAddrs.size() + outstandingSTAddrs.size();

        // 1) oustandingAddrs is not empty, meaning all PREP requests's addrs are outstanding
        //    need to wait for response, thus we need to rerun pickCmd until we pick a cmd
        if(outstandingAddrs != 0){
            // DPRINTF(StreamTest, "All PREP requests' addrs are outstanding.\n");
        }
        // 2) outstandingAddrs is empty, meaning all PREP requests are sent
        // (a). the last request is sent.  (b). all requests are not PREP.but ld is always PREP.
        // just wait for response to end this simulation
        // both situations need us to wait.
        else{
            // DPRINTF(StreamTest, "No available requests in PREP state. LDList are all PREP, meaning LDList all sent out and STList wait for LDs.\n");
        }
        waitResponse = true;
        printf("Exit tick %lu with no available addr\n", curTick());
        return;
    }

    // create a new request
    Request::Flags flags;
    PacketPtr pkt = nullptr;
    double *pkt_data = new double;

    // second choose a req
    // current only implement ST goes first
    if(stReqIt != STList.end()){ // ST goes first

        Addr addr = (*stReqIt)->addr;
        assert(outstandingSTAddrs.find(addr) == outstandingSTAddrs.end());
        outstandingSTAddrs[addr] = stReqIt;

        RequestPtr req = std::make_shared<Request>(addr, 8, flags, requestorId);
        assert(req->getPaddr() == addr);

        req->setContext(id);
        req->setReqInstSeqNum(txSeqNum); // zhiang: TODO: here we test InstSeqNum, maybe changed by controllers downstream, let's see

        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        *pkt_data = (*stReqIt)->val;
        DPRINTF(StreamTest,"Start,%#lx,W,%lu\n",req->getPaddr(),(*stReqIt)->val);
        printf("In tick %lu: send ST[%lu](addr: %#lx, val: %f)\n", curTick(), (*stReqIt)->iter, addr, (*stReqIt)->val);
    }
    else {
        assert(ldReqIt != LDList.end());
        Addr addr = (*ldReqIt)->addr;
        assert(outstandingLDAddrs.find(addr) == outstandingLDAddrs.end());
        outstandingLDAddrs[addr] = ldReqIt;

        RequestPtr req = std::make_shared<Request>(addr, 8, flags, requestorId);
        assert(req->getPaddr() == addr);

        req->setContext(id);
        req->setReqInstSeqNum(txSeqNum); // zhiang: TODO: here we test InstSeqNum, maybe changed by controllers downstream, let's see

        pkt = new Packet(req, MemCmd::ReadReq);
        pkt->dataDynamic(pkt_data);
        DPRINTF(StreamTest,"Start,%#lx,R,%lu\n",req->getPaddr(), (*ldReqIt)->val);
        printf("In tick %lu: send LD[%lu](addr: %#lx, val: %f)\n", curTick(), (*ldReqIt)->iter, addr, (*ldReqIt)->val);
    }
    
    // there is no point in ticking if we are waiting for a retry
    bool keep_ticking = sendPkt(pkt);
    if (keep_ticking) {
        printf("In tick %lu: Scheduled next tick at %lu\n", curTick(), clockEdge(interval));
        // schedule the next tick
        schedule(tickEvent, clockEdge(interval));

        // finally shift the timeout for sending of requests forwards
        // as we have successfully sent a packet
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    } else {
        printf("In tick %lu: waiting for retry\n", curTick());
        DPRINTF(StreamTest, "Waiting for retry\n");
    }

    txSeqNum++; // for each transaction,increase 1 to generate a new txSeqNum

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
    
    printf("Exit tick %lu normally\n", curTick());
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
