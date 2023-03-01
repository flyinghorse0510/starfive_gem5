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

#include "cpu/testers/memtest/migratorymemtest.hh"

#include "base/compiler.hh"
#include "base/random.hh"
#include "base/statistics.hh"
#include "base/trace.hh"
#include "debug/MigratoryMemLatTest.hh"
#include "sim/sim_exit.hh"
#include "sim/stats.hh"
#include "sim/system.hh"
#include "cpu/testers/memtest/common.hh"
#include <queue>
#include <utility>
#include <tuple>
#include <memory>
#include <algorithm>
#include <iterator>
#include "debug/MsgBufDebug.hh"

namespace gem5
{



static unsigned int TESTER_PRODUCER_IDX; // Pass Index of the writer. Only written by sole producer

bool ParsecMemTest::CpuPort::recvTimingResp(PacketPtr pkt)
{
    seqmemtest.completeRequest(pkt);
    return true;
}

void
ParsecMemTest::CpuPort::recvReqRetry()
{
    seqmemtest.recvRetry();
}

bool
ParsecMemTest::sendPkt(PacketPtr pkt) {
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

ParsecMemTest::ParsecMemTest(const Params &p)
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
      maxLoadFactor(p.max_loads),
      atomic(p.system->isAtomicMode()),
      seqIdx(0),
      baseAddr(p.base_addr_1),
      num_cpus(p.num_cpus),
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48), // init txSeqNum as RequestorId(16-bit)_0000_0000_0000
      suppressFuncErrors(p.suppress_func_errors), stats(this) {

    id = TESTER_ALLOCATOR++;

    // Initialize the txn counters
    numReadTxnGenerated=0;
    numReadTxnCompleted=0;
    numWriteTxnGenerated=0;
    numWriteTxnCompleted=0;
    maxLoads=0;

    // Create the working set
    bool isWarmupPhase;
    bool isIdle;
    std::vector<Addr> sharedWorkingSet;
    std::vector<Addr> privateWorkingSet; // Used to store lock-like variables
    std::set<Addr> totalWorkingSet; // Used for warmup

    state=MemTestStatus::Idle;

    // Generate the initial tick
    schedule(tickEvent, curTick());
    schedule(noRequestEvent, clockEdge(progressCheck));
}

Port &
ParsecMemTest::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "port")
        return port;
    else
        return ClockedObject::getPort(if_name, idx);
}

void ParsecMemTest::completeRequest(PacketPtr pkt, bool functional) {
    assert(!isIdle); // An idle MemTester cannot receive a response. It has never generated a request
    const RequestPtr &req = pkt->req;
    assert(req->getSize() == 2);

    // this address is no longer outstanding
    auto remove_paddr = req->getPaddr();
    auto remove_addr = outstandingAddrs.find(req->getPaddr());
    assert(remove_addr != outstandingAddrs.end());
    outstandingAddrs.erase(remove_addr);

    const writeSyncData_t *pkt_data = pkt->getConstPtr<writeSyncData_t>();

    unsigned workingSetSize=perCPUWorkingBlocks.size();

    if (pkt->isError()) {
        if (!functional || !suppressFuncErrors)
            panic( "%s access failed at %#x\n",
                pkt->isWrite() ? "Write" : "Read", req->getPaddr());
    } else {
        if (pkt->isRead()) {
            assert(writeValsQ.find(id) != writeValsQ.end());
            auto cdata = writeValsQ.at(id);
            writeSyncData_t ref_data = cdata->getRefData(remove_paddr);
            if (pkt_data[0] != ref_data) {
                // Incorrect data read. Probably due to unhandled race conditions
                panic("Read of %x returns %x, expected %x\n", remove_paddr,pkt_data[0], ref_data);
            } else {
                DPRINTF(MigratoryMemLatTest, "Complete,R,%x,%x\n", req->getPaddr(),pkt_data[0]);
                numReadTxnCompleted++;
                stats.numReads++;

                if (numReadTxnCompleted == (uint64_t)nextProgressMessage) {
                    ccprintf(std::cerr,
                            "%s: completed %d read, %d write accesses @%d\n",
                            name(), numReadTxnCompleted, numWriteTxnCompleted, curTick());
                    nextProgressMessage += progressInterval;
                }
            }

            if (numReadTxnCompleted >= maxLoads) {
                DPRINTF(MigratoryMemLatTest,"id=(%d/%d) Completed all read resp=%d,%d\n",id,numConsCompleted,numReadTxnCompleted,maxLoads);
                numConsCompleted++;
            }
        } else {
            assert(pkt->isWrite());

            DPRINTF(MigratoryMemLatTest, "Complete,W,%x,%x\n", req->getPaddr(),pkt_data[0]);
            referenceData[req->getPaddr()] = pkt_data[0];
            stats.numWrites++;
            if (isProducer && ((referenceData.size())>=workingSetSize)) {
                DPRINTF(MigratoryMemLatTest,"id=(%d,%d) Completed all writes resp=%d,%d,numProdCompleted=%d\n",id,producer_peer_id,referenceData.size(),workingSetSize,numProdCompleted);
                auto consumer_data = std::make_shared<ConsumerReadData_t>(referenceData);
                for (auto c : id_consumers) {
                    writeValsQ[c] = consumer_data;
                }
                TESTER_PRODUCER_IDX++;

                numProdCompleted++;
            }

        }
        
        if ((numConsCompleted+numProdCompleted) >= TOTAL_REQ_AGENTS) {
            DPRINTF(MigratoryMemLatTest, "id=%d,num_consumers=%d,num_producers=%d,numConsCompleted=%d,numProdCompleted=%d,TOTAL_REQ_AGENTS=%d\n", id, num_consumers, num_producers, numConsCompleted,numProdCompleted,TOTAL_REQ_AGENTS);
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

ParsecMemTest::MemTestStats::MemTestStats(statistics::Group *parent)
      : statistics::Group(parent),
      ADD_STAT(numReads, statistics::units::Count::get(),
               "number of read accesses completed"),
      ADD_STAT(numWrites, statistics::units::Count::get(),
               "number of write accesses completed")
{

}

void
ParsecMemTest::tick()
{
    // we should never tick if we are waiting for a retry
    assert(!retryPkt);
    assert(!waitResponse);
    assert(!isIdle);

    // create a new request
    Request::Flags flags;
    Addr paddr = 0;
    bool readOrWrite = (isProducer)?false:true;  // Only producer can write
    unsigned workingSetSize=perCPUWorkingBlocks.size();
    unsigned readWorkingSetSize=0;

    // Skip if you have outstanding Too many outstanding transactions
    if (outstandingAddrs.size() >= maxOutStandingTransactions) {
        waitResponse = true;
        return;
    }

    writeSyncData_t data;
    if (!isProducer) {
        /* Skip if you generated maxLoads transactions */
        if (numReadTxnGenerated >= maxLoads) {
            DPRINTF(MigratoryMemLatTest,"Reader finished generating %d\n",numReadTxnGenerated);
            waitResponse = true;
            return;
        }

        if (numProdCompleted < numPeerProducers) {
            /* Wait for all writes to finish before generating a read*/
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
            // DPRINTF(MigratoryMemLatTest,"Reader waiting for %d/%d\n",numProdCompleted,numPeerProducers);
            return;
        }
        // DPRINTF(MigratoryMemLatTest,"All producers finished generating\n");
        assert(writeValsQ.find(id) != writeValsQ.end());

        /* The entire working set is outstanding*/
        auto cdata = writeValsQ.at(id);
        readWorkingSetSize = cdata->getWorkingSetSize();
        if (outstandingAddrs.size() >= readWorkingSetSize) {
            waitResponse = true;
            return;
        }

        /* Pick an address to generate a read request */
        do {
            paddr = cdata->getNextAddr();
            data = cdata->getRefData(paddr);
        } while (outstandingAddrs.find(paddr) != outstandingAddrs.end());

    } else {
        /* Skip if you generated workingSetSize write transactions */
        if (writeDataGenerated.size() >= workingSetSize) {
            DPRINTF(MigratoryMemLatTest,"id=(%d,%d) Completed all writes reqs=%d,%d\n",producer_peer_id,id,writeDataGenerated.size(),workingSetSize);
            waitResponse = true;
            return;
        }
        
        /* No free addresses to generate from this producer. Stall */
        /* Should have an assertions that? outstandingAddrs.size() <= workingSetSize*/
        if (outstandingAddrs.size() >= workingSetSize) {
            waitResponse = true;
            return;
        }

        /* Search for an address within the workingSetSize cacheline */
        do {
            paddr = perCPUWorkingBlocks.at(seqIdx);
            seqIdx = (seqIdx+1)%(workingSetSize);
        } while (outstandingAddrs.find(paddr) != outstandingAddrs.end());
        data = (TESTER_PRODUCER_IDX << 8) + (writeSyncDataBase++);

        writeDataGenerated.insert(paddr);
    }

    outstandingAddrs.insert(paddr);
    RequestPtr req = std::make_shared<Request>(paddr, 2, flags, requestorId);
    req->setContext(id);
    req->setReqInstSeqNum(txSeqNum);
    
    PacketPtr pkt = nullptr;
    writeSyncData_t *pkt_data = new writeSyncData_t[1];

    if (readOrWrite) {
        pkt = new Packet(req, MemCmd::ReadReq);
        referenceData[req->getPaddr()] = data;
        pkt->dataDynamic(pkt_data);
        DPRINTF(MigratoryMemLatTest,"Start,R,%x,%x,%d/%d\n",req->getPaddr(),data,outstandingAddrs.size(),readWorkingSetSize);
        numReadTxnGenerated++;
    } else {
        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        pkt_data[0] = data;
        DPRINTF(MigratoryMemLatTest,"Start,W,%x,%x,%d\n",req->getPaddr(),data,outstandingAddrs.size());
        numWriteTxnGenerated++;
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
        DPRINTF(MigratoryMemLatTest, "Waiting for retry\n");
    }

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs.size() != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
}

void
ParsecMemTest::noRequest()
{
    assert(!isIdle);
    if (isProducer) {
        if (numWriteTxnGenerated < maxLoads) {
            panic("%s did not send a request for %d cycles", name(), progressCheck);
        }
    } else {
        if (numReadTxnGenerated < maxLoads) {
            panic("%s did not send a request for %d cycles", name(), progressCheck);
        }
    }
    
}

void
ParsecMemTest::noResponse()
{
    assert(!isIdle);
    panic("%s did not see a response for %d cycles", name(), progressCheck);
}

void
ParsecMemTest::recvRetry()
{
    assert(retryPkt);
    if (port.sendTimingReq(retryPkt)) {
        DPRINTF(MigratoryMemLatTest, "Proceeding after successful retry\n");

        retryPkt = nullptr;
        // kick things into action again
        schedule(tickEvent, clockEdge(interval));
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    }
}

} // namespace gem5
