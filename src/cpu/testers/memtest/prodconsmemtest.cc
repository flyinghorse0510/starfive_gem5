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

#include "cpu/testers/memtest/prodconsmemtest.hh"

#include "base/compiler.hh"
#include "base/random.hh"
#include "base/statistics.hh"
#include "base/trace.hh"
#include "debug/ProdConsMemLatTest.hh"
#include "sim/sim_exit.hh"
#include "sim/stats.hh"
#include "sim/system.hh"
#include "cpu/testers/memtest/common.hh"

namespace gem5
{

static unsigned int TESTER_ALLOCATOR = 0;

bool
ProdConsMemTest::CpuPort::recvTimingResp(PacketPtr pkt)
{
    seqmemtest.completeRequest(pkt);
    return true;
}

void
ProdConsMemTest::CpuPort::recvReqRetry()
{
    seqmemtest.recvRetry();
}

bool
ProdConsMemTest::sendPkt(PacketPtr pkt) {
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

ProdConsMemTest::ProdConsMemTest(const Params &p)
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
      baseAddr1(p.base_addr_1),
      progressInterval(p.progress_interval),
      progressCheck(p.progress_check),
      nextProgressMessage(p.progress_interval),
      maxLoads(p.max_loads),
      atomic(p.system->isAtomicMode()),
      numIters(p.num_iters),
      seqIdx(0),
      suppressFuncErrors(p.suppress_func_errors), stats(this)
{
    id = TESTER_ALLOCATOR++;
    fatal_if(id >= blockSize, "Too many testers, only %d allowed\n",
             blockSize - 1);

    // set up counters
    numReads = 0;
    numWrites = 0;
    writeSyncData_t writeSyncDataBase = 0x100a; // true: read, false: write
    writeSyncData = { \
                    {0x40000, writeSyncDataBase}, \
                    {0x40040, writeSyncDataBase+1}, \
                    {0x40080, writeSyncDataBase+2}, \
                    {0x400c0, writeSyncDataBase+3}, \
                    {0x40140, writeSyncDataBase+4}, \
                    {0x40180, writeSyncDataBase+5}, \
                    {0x401c0, writeSyncDataBase+6}, \
                    {0x40240, writeSyncDataBase+7}, \
                    {0x40280, writeSyncDataBase+8}, \
                    {0x402c0, writeSyncDataBase+9}, \
                    {0x40340, writeSyncDataBase+10}, \
                    {0x40380, writeSyncDataBase+11}, \
                    {0x403c0, writeSyncDataBase+12}, \
                    {0x40440, writeSyncDataBase+13}, \
                    {0x40480, writeSyncDataBase+14}, \
                    {0x404c0, writeSyncDataBase+15}, \
                    {0x40540, writeSyncDataBase+16}, \
                    {0x40580, writeSyncDataBase+17}, \
                    {0x405c0, writeSyncDataBase+18}, \
                    {0x40640, writeSyncDataBase+19}, \
                    {0x40680, writeSyncDataBase+20}, \
                    {0x406c0, writeSyncDataBase+21}, \
                    {0x40740, writeSyncDataBase+22}, \
                    {0x40780, writeSyncDataBase+23}, \
                    {0x407c0, writeSyncDataBase+24}, \
                    {0x40840, writeSyncDataBase+25}, \
                    {0x40880, writeSyncDataBase+26}, \
                    {0x408c0, writeSyncDataBase+27}, \
                    {0x40940, writeSyncDataBase+28}, \
                    {0x40980, writeSyncDataBase+29}, \
                    {0x409c0, writeSyncDataBase+30}, \
                    {0x40a40, writeSyncDataBase+31}, \
                    {0x40a80, writeSyncDataBase+32}, \
                    {0x40ac0, writeSyncDataBase+33}};
    for (const auto &p : writeSyncData) {
        workingSet.push_back(p.first);
    }

    isProducer = (id == 0)?true:false;

    // kick things into action
    schedule(tickEvent, curTick());
    schedule(noRequestEvent, clockEdge(progressCheck));
}

Port &
ProdConsMemTest::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "port")
        return port;
    else
        return ClockedObject::getPort(if_name, idx);
}

void
ProdConsMemTest::completeRequest(PacketPtr pkt, bool functional)
{
    const RequestPtr &req = pkt->req;
    assert(req->getSize() == 2);

    // this address is no longer outstanding
    auto remove_paddr = req->getPaddr();
    auto remove_addr = outstandingAddrs.find(req->getPaddr());
    assert(remove_addr != outstandingAddrs.end());
    outstandingAddrs.erase(remove_addr);

    
    const writeSyncData_t *pkt_data = pkt->getConstPtr<writeSyncData_t>();

    if (pkt->isError()) {
        if (!functional || !suppressFuncErrors)
            panic( "%s access failed at %#x\n",
                pkt->isWrite() ? "Write" : "Read", req->getPaddr());
    } else {
        if (pkt->isRead()) {
            writeSyncData_t ref_data = referenceData[req->getPaddr()];
            if (pkt_data[0] != ref_data) {
                // panic("%s: read of %x (blk %x) @ cycle %d "
                //       "returns %x, expected %x\n", name(),
                //       req->getPaddr(), blockAlign(req->getPaddr()), curTick(),
                //       pkt_data[0], ref_data);

                // put back the address because you haven't received the "correct" response
                DPRINTF(ProdConsMemLatTest, "Read of %x returns %x, expected %x\n", remove_paddr,pkt_data[0], ref_data);
                outstandingAddrs.insert(remove_paddr);
            } else {
                DPRINTF(ProdConsMemLatTest, "Completing read at address %x, data %x\n", req->getPaddr(),pkt_data[0]);
                
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

             DPRINTF(ProdConsMemLatTest, "Completing write at address %x\n", req->getPaddr());
            // update the reference data
            referenceData[req->getPaddr()] = pkt_data[0];
            numWrites++;
            stats.numWrites++;
        }
        if (maxLoads != 0 && (numWrites+numReads) >= maxLoads)
            exitSimLoop("maximum number of loads/stores reached");
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
ProdConsMemTest::MemTestStats::MemTestStats(statistics::Group *parent)
      : statistics::Group(parent),
      ADD_STAT(numReads, statistics::units::Count::get(),
               "number of read accesses completed"),
      ADD_STAT(numWrites, statistics::units::Count::get(),
               "number of write accesses completed")
{

}

void
ProdConsMemTest::tick()
{
    // we should never tick if we are waiting for a retry
    assert(!retryPkt);
    assert(!waitResponse);

    // create a new request
    unsigned offset=0;
    Request::Flags flags;
    Addr paddr = 0;

    // Skip if you have outstanding transactions
    if (outstandingAddrs.size() >= 1) {
        waitResponse = true;
        return;
    }

    bool readOrWrite = (isProducer)?false:true;  // Only producer can write
    do {
        paddr = workingSet.at(seqIdx);
        seqIdx = (seqIdx+1)%(workingSet.size());
    } while (outstandingAddrs.find(paddr) != outstandingAddrs.end());
    
    RequestPtr req = std::make_shared<Request>(paddr, 2, flags, requestorId);
    req->setContext(id);
    outstandingAddrs.insert(paddr);
    writeSyncData_t data = writeSyncData[paddr];
    
    PacketPtr pkt = nullptr;
    writeSyncData_t *pkt_data = new writeSyncData_t[1];

    if (readOrWrite) {
        // start by ensuring there is a reference value if we have not
        // seen this address before
        [[maybe_unused]] writeSyncData_t ref_data = data;
        auto ref = referenceData.find(req->getPaddr());
        if (ref == referenceData.end()) {
            referenceData[req->getPaddr()] = data;
        } else {
            ref_data = ref->second;
        }

        DPRINTF(ProdConsMemLatTest,"Initiating at addr %x read\n",req->getPaddr());

        pkt = new Packet(req, MemCmd::ReadReq);
        pkt->dataDynamic(pkt_data);
        
    } else {
        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        pkt_data[0] = data;

        DPRINTF(ProdConsMemLatTest,"Initiating at addr %x write\n",req->getPaddr());
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
        DPRINTF(ProdConsMemLatTest, "Waiting for retry\n");
    }

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs.size() != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
}

void
ProdConsMemTest::noRequest()
{
    panic("%s did not send a request for %d cycles", name(), progressCheck);
}

void
ProdConsMemTest::noResponse()
{
    panic("%s did not see a response for %d cycles", name(), progressCheck);
}

void
ProdConsMemTest::recvRetry()
{
    assert(retryPkt);
    if (port.sendTimingReq(retryPkt)) {
        DPRINTF(ProdConsMemLatTest, "Proceeding after successful retry\n");

        retryPkt = nullptr;
        // kick things into action again
        schedule(tickEvent, clockEdge(interval));
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    }
}

} // namespace gem5
