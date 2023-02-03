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

#include "cpu/testers/memtest/isolatedmemtest.hh"

#include "base/compiler.hh"
#include "base/random.hh"
#include "base/statistics.hh"
#include "base/trace.hh"
#include "debug/IsolatedMemTest.hh"
#include "debug/IsolatedMemLatTest.hh"
#include "sim/sim_exit.hh"
#include "sim/stats.hh"
#include "sim/system.hh"
#include "cpu/testers/memtest/common.hh"

namespace gem5
{

static unsigned int TESTER_ALLOCATOR = 0;

bool
IsolatedMemTest::CpuPort::recvTimingResp(PacketPtr pkt)
{
    seqmemtest.completeRequest(pkt);
    return true;
}

void
IsolatedMemTest::CpuPort::recvReqRetry()
{
    seqmemtest.recvRetry();
}

bool
IsolatedMemTest::sendPkt(PacketPtr pkt) {
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

IsolatedMemTest::IsolatedMemTest(const Params &p)
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
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48), // zhiang: init txSeqNum to ReqId(16-bit)_0000_0000_0000
      suppressFuncErrors(p.suppress_func_errors), stats(this)
{
    id = TESTER_ALLOCATOR++;
    fatal_if(id >= blockSize, "Too many testers, only %d allowed\n",
             blockSize - 1);

    // set up counters
    numReads = 0;
    numWrites = 0;
    bool readOrWriteVal = true; // true: read, false: write
    readWriteMap = { \
                    {0x40000, readOrWriteVal}, \
                    {0x40040, readOrWriteVal}, \
                    {0x40080, readOrWriteVal}, \
                    {0x400c0, readOrWriteVal}, \
                    {0x40140, readOrWriteVal}, \
                    {0x40180, readOrWriteVal}, \
                    {0x401c0, readOrWriteVal}, \
                    {0x40240, readOrWriteVal}, \
                    {0x40280, readOrWriteVal}, \
                    {0x402c0, readOrWriteVal}, \
                    {0x40340, readOrWriteVal}, \
                    {0x40380, readOrWriteVal}, \
                    {0x403c0, readOrWriteVal}, \
                    {0x40440, readOrWriteVal}, \
                    {0x40480, readOrWriteVal}, \
                    {0x404c0, readOrWriteVal}, \
                    {0x40540, readOrWriteVal}, \
                    {0x40580, readOrWriteVal}, \
                    {0x405c0, readOrWriteVal}, \
                    {0x40640, readOrWriteVal}, \
                    {0x40680, readOrWriteVal}, \
                    {0x406c0, readOrWriteVal}, \
                    {0x40740, readOrWriteVal}, \
                    {0x40780, readOrWriteVal}, \
                    {0x407c0, readOrWriteVal}, \
                    {0x40840, readOrWriteVal}, \
                    {0x40880, readOrWriteVal}, \
                    {0x408c0, readOrWriteVal}, \
                    {0x40940, readOrWriteVal}, \
                    {0x40980, readOrWriteVal}, \
                    {0x409c0, readOrWriteVal}, \
                    {0x40a40, readOrWriteVal}, \
                    {0x40a80, readOrWriteVal}, \
                    {0x40ac0, readOrWriteVal}};
    for (const auto &p : readWriteMap) {
        workingSet.push_back(p.first);
    }

    // kick things into action
    schedule(tickEvent, curTick());
    schedule(noRequestEvent, clockEdge(progressCheck));
}

Port &
IsolatedMemTest::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "port")
        return port;
    else
        return ClockedObject::getPort(if_name, idx);
}

void
IsolatedMemTest::completeRequest(PacketPtr pkt, bool functional)
{
    const RequestPtr &req = pkt->req;
    assert(req->getSize() == 1);

    // this address is no longer outstanding
    auto remove_addr = outstandingAddrs.find(req->getPaddr());
    assert(remove_addr != outstandingAddrs.end());
    outstandingAddrs.erase(remove_addr);

    DPRINTF(IsolatedMemLatTest, "TxSeqNum: %#018x, Completing %s at address %x (blk %x) %s\n",
            pkt->req->getReqInstSeqNum(),
            pkt->isWrite() ? "write" : "read",
            req->getPaddr(), blockAlign(req->getPaddr()),
            pkt->isError() ? "error" : "success");

    const uint8_t *pkt_data = pkt->getConstPtr<uint8_t>();

    if (pkt->isError()) {
        if (!functional || !suppressFuncErrors)
            panic( "%s access failed at %#x\n",
                pkt->isWrite() ? "Write" : "Read", req->getPaddr());
    } else {
        if (pkt->isRead()) {
            uint8_t ref_data = referenceData[req->getPaddr()];
            if (pkt_data[0] != ref_data) {
                panic("%s: read of %x (blk %x) @ cycle %d "
                      "returns %x, expected %x\n", name(),
                      req->getPaddr(), blockAlign(req->getPaddr()), curTick(),
                      pkt_data[0], ref_data);
            }

            numReads++;
            stats.numReads++;

            if (numReads == (uint64_t)nextProgressMessage) {
                ccprintf(std::cerr,
                        "%s: completed %d read, %d write accesses @%d\n",
                        name(), numReads, numWrites, curTick());
                nextProgressMessage += progressInterval;
            }
        } else {
            assert(pkt->isWrite());

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
IsolatedMemTest::MemTestStats::MemTestStats(statistics::Group *parent)
      : statistics::Group(parent),
      ADD_STAT(numReads, statistics::units::Count::get(),
               "number of read accesses completed"),
      ADD_STAT(numWrites, statistics::units::Count::get(),
               "number of write accesses completed")
{

}

void
IsolatedMemTest::tick()
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

    bool readOrWrite = true;  // true: read, false: write
    uint8_t data = random_mt.random<uint8_t>(); // random write data
    do {
        paddr = workingSet.at(seqIdx);
        readOrWrite = readWriteMap[paddr];
        seqIdx = (seqIdx+1)%(workingSet.size());
    } while (outstandingAddrs.find(paddr) != outstandingAddrs.end());
    
    RequestPtr req = std::make_shared<Request>(paddr, 1, flags, requestorId);
    req->setContext(id);
    req->setReqInstSeqNum(txSeqNum); // zhiang: TODO: here we test InstSeqNum, maybe changed by controllers downstream, let's see

    outstandingAddrs.insert(paddr);
    
    PacketPtr pkt = nullptr;
    uint8_t *pkt_data = new uint8_t[1];

    if (readOrWrite) {
        // start by ensuring there is a reference value if we have not
        // seen this address before
        [[maybe_unused]] uint8_t ref_data = 0;
        auto ref = referenceData.find(req->getPaddr());
        if (ref == referenceData.end()) {
            referenceData[req->getPaddr()] = 0;
        } else {
            ref_data = ref->second;
        }

        DPRINTF(IsolatedMemLatTest,"TxSeqNum: %#018x, Initiating at addr %x read\n", req->getReqInstSeqNum(), req->getPaddr());

        pkt = new Packet(req, MemCmd::ReadReq);
        pkt->dataDynamic(pkt_data);
        
    } else {
        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        pkt_data[0] = data;

        DPRINTF(IsolatedMemLatTest,"TxSeqNum: %#018x, Initiating at addr %x write\n", req->getReqInstSeqNum(), req->getPaddr());
    }
    
    txSeqNum++; // for each transaction, we increate 1 to generate a new txSeqNum

    // there is no point in ticking if we are waiting for a retry
    bool keep_ticking = sendPkt(pkt);
    if (keep_ticking) {
        // schedule the next tick
        schedule(tickEvent, clockEdge(interval));

        // finally shift the timeout for sending of requests forwards
        // as we have successfully sent a packet
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    } else {
        DPRINTF(IsolatedMemTest, "Waiting for retry\n");
    }

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs.size() != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
}

void
IsolatedMemTest::noRequest()
{
    panic("%s did not send a request for %d cycles", name(), progressCheck);
}

void
IsolatedMemTest::noResponse()
{
    panic("%s did not see a response for %d cycles", name(), progressCheck);
}

void
IsolatedMemTest::recvRetry()
{
    assert(retryPkt);
    if (port.sendTimingReq(retryPkt)) {
        DPRINTF(IsolatedMemTest, "Proceeding after successful retry\n");

        retryPkt = nullptr;
        // kick things into action again
        schedule(tickEvent, clockEdge(interval));
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    }
}

} // namespace gem5
