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

#include "cpu/testers/memtest/seqmemtest.hh"

#include "base/compiler.hh"
#include "base/random.hh"
#include "base/statistics.hh"
#include "base/trace.hh"
#include "debug/SeqMemTest.hh"
#include "debug/SeqMemLatTest.hh"
#include "sim/sim_exit.hh"
#include "sim/stats.hh"
#include "sim/system.hh"
#include <algorithm>
#include <cmath>
#include "cpu/testers/memtest/common.hh"

namespace gem5
{

static unsigned int TESTER_ALLOCATOR = 0;
static unsigned int TESTER_PRODUCER_IDX; // Pass Index of the writer. Only written by sole producer


bool
SeqMemTest::CpuPort::recvTimingResp(PacketPtr pkt)
{
    seqmemtest.completeRequest(pkt);
    return true;
}

void
SeqMemTest::CpuPort::recvReqRetry()
{
    seqmemtest.recvRetry();
}

bool
SeqMemTest::sendPkt(PacketPtr pkt) {
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

SeqMemTest::SeqMemTest(const Params &p)
    : ClockedObject(p),
      tickEvent([this]{ tick(); }, name()),
      noRequestEvent([this]{ noRequest(); }, name()),
      noResponseEvent([this]{ noResponse(); }, name()),
      port("port", *this),
      retryPkt(nullptr),
      waitResponse(false),
      size(p.size),
      interval(p.interval),
      requestorId(p.system->getRequestorId(this)),
      blockSize(p.system->cacheLineSize()),
      blockAddrMask(blockSize - 1),
      workingSet(p.working_set),
      progressInterval(p.progress_interval),
      progressCheck(p.progress_check),
      nextProgressMessage(p.progress_interval),
      maxLoads(p.max_loads),
      atomic(p.system->isAtomicMode()),
      seqIdx(0),
      num_cpus(p.num_cpus),
      baseAddr(p.base_addr_1),
      addrInterleavedOrTiled(p.addr_intrlvd_or_tiled),
      percentReads(p.percent_reads),
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48),
      suppressFuncErrors(p.suppress_func_errors), stats(this)
{
    id = TESTER_ALLOCATOR++;
    fatal_if(id >= blockSize, "Too many testers, only %d allowed\n",
             blockSize - 1);

    fatal_if(workingSet%(num_cpus*blockSize)!=0,"per CPU working set not block aligned, workingSet=%d,num_cpus=%d,blockSize=%d\n",workingSet,num_cpus,blockSize);
    numPerCPUWorkingBlocks=(workingSet/(num_cpus*blockSize));
    for (unsigned i=0; i < numPerCPUWorkingBlocks; i++) {
        Addr effectiveBlockAddr=(addrInterleavedOrTiled)?(baseAddr+(num_cpus*i)+id):
                                (baseAddr+(numPerCPUWorkingBlocks*id)+i);
        perCPUWorkingBlocks.push_back(effectiveBlockAddr<<(static_cast<uint64_t>(std::log2(blockSize))));
    }
    fatal_if(perCPUWorkingBlocks.size()<=0,"Working Set size is 0\n");

    if (perCPUWorkingBlocks.size() > 1) {
        if (addrInterleavedOrTiled) {
            DPRINTF(SeqMemLatTest,"CPU_%d WorkingSetRange:[%x:%x]\n",id,perCPUWorkingBlocks.at(0),perCPUWorkingBlocks.at(1));
        } else {
            DPRINTF(SeqMemLatTest,"CPU_%d WorkingSetRange:[%x,%x]\n",id,perCPUWorkingBlocks.at(0),perCPUWorkingBlocks.at(numPerCPUWorkingBlocks-1));
        }
    } else if (perCPUWorkingBlocks.size() >= 1) {
        DPRINTF(SeqMemLatTest,"CPU_%d WorkingSetRange:[%x]\n",id,perCPUWorkingBlocks.at(0));
    }

    maxLoads = maxLoads * perCPUWorkingBlocks.size();
    printf("*** CPU%d workingBlocks(numCacheLines) in the CPU: %d, Working set load times:%d, maxLoads:%d  \n", id, perCPUWorkingBlocks.size(),  p.max_loads, maxLoads);

    // set up counters
    numReads = 0;
    numWrites = 0;
    writeSyncDataBase=0x8f1;

    // kick things into action
    schedule(tickEvent, curTick());
    schedule(noRequestEvent, clockEdge(progressCheck));
}

Port &
SeqMemTest::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "port")
        return port;
    else
        return ClockedObject::getPort(if_name, idx);
}

void
SeqMemTest::completeRequest(PacketPtr pkt, bool functional)
{
    const RequestPtr &req = pkt->req;
    assert(req->getSize() == 2);

    // this memTxnId is no longer outstanding
    auto remove_paddr = req->getPaddr();
    auto remove_addr = outstandingAddrs.find(req->getPaddr());
    assert(remove_addr != outstandingAddrs.end());
    outstandingAddrs.erase(remove_addr);

    const writeSyncData_t *pkt_data = pkt->getConstPtr<writeSyncData_t>();

    if (!pkt_data) {
        panic("Received packet data ptr is null for %x\n",remove_paddr);
    }

    if (pkt->isError()) {
        if (!functional || !suppressFuncErrors)
            panic( "%s access failed at %#x\n",
                pkt->isWrite() ? "Write" : "Read", req->getPaddr());
    } else {
        if (pkt->isRead()) {
            writeSyncData_t ref_data = referenceData[req->getPaddr()];
            if (pkt_data[0] != ref_data) {
                // Incorrect data read. Probably due to unhandled race conditions

                panic("Read of %x returns %x, expected %x\n", remove_paddr,pkt_data[0], ref_data);
            } else {
                DPRINTF(SeqMemLatTest, "Complete,%x,R,%x\n", req->getPaddr(),pkt_data[0]);
                
                numReads++;
                stats.numReads++;

                if (numReads == (uint64_t)nextProgressMessage) {
                    ccprintf(std::cerr,
                            "%s: completed %d read, %d write accesses @%d\n",
                            name(), numReads, numWrites, curTick());
                    nextProgressMessage += progressInterval;
                }
            }
        } else {
            assert(pkt->isWrite());
            DPRINTF(SeqMemLatTest, "Complete,%x,W,%x\n", req->getPaddr(),pkt_data[0]);
            // update the reference data
            referenceData[req->getPaddr()] = pkt_data[0];
            numWrites++;
            stats.numWrites++;
        }
        if ((numReads+numWrites) >= maxLoads) {
            printf("Reach MaxLoads, maxLoad:%d, numReads:%d numWrites:%d \n", maxLoads, numReads, numWrites);
            exitSimLoop("maximum number of loads/stores reached");
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
SeqMemTest::MemTestStats::MemTestStats(statistics::Group *parent)
      : statistics::Group(parent),
      ADD_STAT(numReads, statistics::units::Count::get(),
               "number of read accesses completed"),
      ADD_STAT(numWrites, statistics::units::Count::get(),
               "number of write accesses completed")
{

}

void
SeqMemTest::tick()
{
    // we should never tick if we are waiting for a retry
    assert(!retryPkt);
    assert(!waitResponse);

    // create a new request
    Request::Flags flags;
    Addr paddr = 0;

    /* Too many outstanding transactions */
    if ((outstandingAddrs.size() >= 100) || (outstandingAddrs.size() >= perCPUWorkingBlocks.size())) {
        waitResponse = true;
        return;
    }
    
    /* Search for an address within perCPUWorkingBlocks */
    do {
        paddr = perCPUWorkingBlocks.at(seqIdx);
        seqIdx = (seqIdx+1)%(perCPUWorkingBlocks.size());
         
    } while (outstandingAddrs.find(paddr) != outstandingAddrs.end());
    writeSyncData_t data = (TESTER_PRODUCER_IDX << 8) + (writeSyncDataBase++);
    
    outstandingAddrs.insert(paddr);
    RequestPtr req = std::make_shared<Request>(paddr, 2, flags, requestorId);
    req->setContext(id);
    req->setReqInstSeqNum(txSeqNum);

    PacketPtr pkt = nullptr;
    writeSyncData_t *pkt_data = new writeSyncData_t[1];

    unsigned cmd = random_mt.random(0, 100);
    bool readOrWrite = (cmd < percentReads)?true:false;
    if (readOrWrite) {
        pkt = new Packet(req, MemCmd::ReadReq);
        auto ref = referenceData.find(req->getPaddr());
        if (ref == referenceData.end()) {
            referenceData[req->getPaddr()] = 0;
        }
        pkt->dataDynamic(pkt_data);

        DPRINTF(SeqMemLatTest,"Start,%x,R,%x\n",req->getPaddr(),data);
    } else {
        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        pkt_data[0] = data;
        DPRINTF(SeqMemLatTest,"Start,%x,W,%x\n",req->getPaddr(),data);
    }

    txSeqNum++; // for each transaction,increate 1 to generate a new txSeqNum

    // there is no point in ticking if we are waiting for a retry
    bool keep_ticking = sendPkt(pkt);
    if (keep_ticking) {
        // schedule the next tick
        schedule(tickEvent, clockEdge(interval));

        // finally shift the timeout for sending of requests forwards
        // as we have successfully sent a packet
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    } else {
        DPRINTF(SeqMemLatTest, "Waiting for retry\n");
    }

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs.size() != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
}

void
SeqMemTest::noRequest()
{
    panic("%s did not send a request for %d cycles", name(), progressCheck);
}

void
SeqMemTest::noResponse()
{
    panic("%s did not see a response for %d cycles", name(), progressCheck);
}

void
SeqMemTest::recvRetry()
{
    assert(retryPkt);
    if (port.sendTimingReq(retryPkt)) {
        DPRINTF(SeqMemLatTest, "Proceeding after successful retry\n");

        retryPkt = nullptr;
        // kick things into action again
        schedule(tickEvent, clockEdge(interval));
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    }
}

} // namespace gem5

