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

#include "cpu/testers/memtest/trueprodconsmemtest.hh"

#include "base/compiler.hh"
#include "base/random.hh"
#include "base/statistics.hh"
#include "base/trace.hh"
#include "debug/TrueProdConsMemLatTest.hh"
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

class ConsumerReadData_t {
    private:
        Addr addr;
        writeSyncData_t data;
        int iter_count;
    public:
        ConsumerReadData_t() : 
            addr(0xfffffff),
            data(0xffff),
            iter_count(-1)
            {}
        ConsumerReadData_t(Addr addr, \
                           writeSyncData_t data, \
                           int iter_count)
            : addr(addr),
              data(data),
              iter_count(iter_count) {}
        Addr getAddr() const { return addr; }
        writeSyncData_t getData() const { return data; }
        int getIterCount() const { return iter_count; }
};

static std::unordered_map<unsigned, std::unordered_map<Addr,ConsumerReadData_t>> writeValsQ;
static std::unordered_map<Addr,uint32_t> pendingReads;  // Data has not been consumed for these addresses. The mapped value represents the number of consumers
static std::unordered_map<Addr,unsigned> addrIterCountMap; // The number of IterCount
static unsigned int TESTER_PRODUCER_IDX; // Pass Index of the writer. Only written by sole producer
static unsigned int TESTER_ALLOCATOR = 0;
static unsigned int TOTAL_REQ_AGENTS = 0;
static unsigned int producer_peer_id=0;    // Location ind producer peer id
static unsigned int numCPUTransactionsCompleted = 0; // Number of CPUs that have completed their transactions

bool
TrueProdConsMemTest::CpuPort::recvTimingResp(PacketPtr pkt)
{
    seqmemtest.completeRequest(pkt);
    return true;
}

void
TrueProdConsMemTest::CpuPort::recvReqRetry()
{
    seqmemtest.recvRetry();
}

bool
TrueProdConsMemTest::sendPkt(PacketPtr pkt) {
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

TrueProdConsMemTest::TrueProdConsMemTest(const Params &p)
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
      removeConsumedData(p.removed_consumed_data),
      num_cpus(p.num_cpus),
      addrInterleavedOrTiled(p.addr_intrlvd_or_tiled),
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48), // init txSeqNum as RequestorId(16-bit)_0000_0000_0000
      suppressFuncErrors(p.suppress_func_errors), stats(this)
{
    id = TESTER_ALLOCATOR++;
    fatal_if(id >= blockSize, "Too many testers, only %d allowed\n",
             blockSize - 1);
    
    // Compute the producer consumer relations
    std::copy(p.id_producers.begin(),p.id_producers.end(),std::inserter(id_producers,id_producers.end()));
    std::copy(p.id_consumers.begin(),p.id_consumers.end(),std::inserter(id_consumers,id_consumers.end()));
    num_producers=id_producers.size();
    num_consumers=id_consumers.size();
    fatal_if(num_producers > num_cpus, "Number of producers must be less than the number of CPUs");
    fatal_if(num_consumers > num_cpus, "Number of consumers must be less than the number of CPUs");
    fatal_if((num_consumers+num_producers) > num_cpus, "Total active CPUs higher than maximum number of CPUs,(num_producers=%d,num_consumers=%d,num_cpus=%d)\n",num_producers,num_consumers,num_cpus);
    auto itr_producer = std::find(id_producers.begin(),id_producers.end(),id);
    auto itr_consumer = std::find(id_consumers.begin(),id_consumers.end(),id);
    isIdle = true;
    isProducer = false;
    if (itr_producer != id_producers.end()) {
        fatal_if(itr_consumer != id_consumers.end(),"%d cannot be both producer and consumer \n",id);
        isProducer = true;
        isIdle = false;
    } else if (itr_consumer != id_consumers.end()) {
        fatal_if(itr_producer != id_producers.end(),"%d cannot be both producer and consumer \n",id);
        isIdle = false;
    }

    /* Holds the pendinf reads; Initially empty */
    writeValsQ[id]=std::unordered_map<Addr,ConsumerReadData_t>();

    // Initialize the txn counters
    numReadTxnGenerated=0;
    numReadTxnCompleted=0;
    numWriteTxnGenerated=0;
    numWriteTxnCompleted=0;
    TESTER_PRODUCER_IDX = 0;

    maxLoads=0;
    if (!isIdle) {
        printf("CPU_%d(num_producers:%d,num_consumers:%d)\n",id,num_producers,num_consumers);
        fatal_if(workingSet%(num_producers*blockSize)!=0,"per producer working set not block aligned\n");
        unsigned totalWorkingSetInBlocks=(workingSet/blockSize);
        numPerCPUWorkingBlocks=(workingSet/(num_producers*blockSize));
        if (addrInterleavedOrTiled) {
            for (unsigned i=0; i < numPerCPUWorkingBlocks; i++) {
                Addr effectiveBlockAddr=baseAddr+(num_producers*i)+producer_peer_id;
                addrIterCountMap[effectiveBlockAddr]=0;
                perCPUWorkingBlocks.push_back(effectiveBlockAddr<<(static_cast<uint64_t>(std::log2(blockSize))));
            }
        } else {
            for (unsigned i=0; i < numPerCPUWorkingBlocks; i++) {
                Addr effectiveBlockAddr=baseAddr+(numPerCPUWorkingBlocks*(producer_peer_id))+i;
                addrIterCountMap[effectiveBlockAddr]=0;
                perCPUWorkingBlocks.push_back(effectiveBlockAddr<<(static_cast<uint64_t>(std::log2(blockSize))));
            }
        }
        fatal_if(perCPUWorkingBlocks.size()<=0,"Working Set size is 0\n");
        if (isProducer) {
            // Only generate The write data once. The reader can read it multiple times
            maxLoads = static_cast<uint64_t>(std::ceil(maxLoadFactor * static_cast<double>(perCPUWorkingBlocks.size())));
            producer_peer_id++;
        } else {
            /* If you are a consumer. Consume the data generated by all the producers */
            maxLoads = static_cast<uint64_t>(std::ceil(num_producers * maxLoadFactor * (static_cast<double>(perCPUWorkingBlocks.size()))));        
        }
        fatal_if(maxLoads <= 0, "Requires a minimum of 1 Load/Store for non idle MemTesters");
        maxOutStandingTransactions = std::min((int)(perCPUWorkingBlocks.size()),p.outstanding_req);
        DPRINTF(TrueProdConsMemLatTest,"CPU_%d(Producer:%d,Idle:%d) WorkingSetRange:[%x,%x], WorkingSetSize=%d, maxTxn=%d\n",id,isProducer,isIdle,perCPUWorkingBlocks.at(0),perCPUWorkingBlocks.at(numPerCPUWorkingBlocks-1),numPerCPUWorkingBlocks,maxLoads);
    
        // kick things into action
        TOTAL_REQ_AGENTS++;
        schedule(tickEvent, curTick());
        schedule(noRequestEvent, clockEdge(progressCheck));
    }
}

Port &
TrueProdConsMemTest::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "port")
        return port;
    else
        return ClockedObject::getPort(if_name, idx);
}

void
TrueProdConsMemTest::completeRequest(PacketPtr pkt, bool functional)
{
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
            auto paddr = req->getPaddr();
            assert(writeValsQ.find(id) != writeValsQ.end());
            auto writeValsAddrPtr = writeValsQ[id].find(paddr);
            assert(writeValsAddrPtr != writeValsQ[id].end());
            auto cdata = writeValsQ[id][paddr];
            assert(paddr == cdata.getAddr());
            // writeSyncData_t ref_data = referenceData[req->getPaddr()];
            if (pkt_data[0] != cdata.getData()) {
                // Incorrect data read. Probably due to unhandled race conditions
                panic("Read of %x returns %x, expected %x\n", remove_paddr,pkt_data[0],cdata.getData());
            } else {
                
                DPRINTF(TrueProdConsMemLatTest,"TrPrdCnsLaT|Addr:%x,Iter:%d,ConsId:%d,ReadEnd\n", \
                        paddr, \
                        cdata.getIterCount(), \
                        id);
                numReadTxnCompleted++;
                stats.numReads++;

                if (numReadTxnCompleted == (uint64_t)nextProgressMessage) {
                    ccprintf(std::cerr,
                            "%s: completed %d read, %d write accesses @%d\n",
                            name(), numReadTxnCompleted, numWriteTxnCompleted, curTick());
                    nextProgressMessage += progressInterval;
                }
            }
            
            /* Remove pending reads from this address, so writes to this address can proceed */
            auto pendingAddrPtr = pendingReads.find(paddr);
            assert(pendingAddrPtr != pendingReads.end());
            pendingReads[paddr]--;
            if (pendingReads[paddr]==0) {
                pendingReads.erase(pendingAddrPtr);
            }
            writeValsQ[id].erase(writeValsAddrPtr);

            if (numReadTxnCompleted >= maxLoads) {
                numCPUTransactionsCompleted++;
            }
        } else {
            assert(pkt->isWrite());
            DPRINTF(TrueProdConsMemLatTest,"TrPrdCnsLaT|Addr:%x,Iter:%d,ProdId:%d,WriteEnd\n", \
                        req->getPaddr(), \
                        addrIterCountMap[req->getPaddr()], \
                        id);
            // update the reference data
            referenceData[req->getPaddr()] = pkt_data[0];
            numWriteTxnCompleted++;
            stats.numWrites++;
            Addr pAddr = req->getPaddr();
            /* Write complete, Signal all the readers */
            for (auto cons_id : id_consumers) {
                writeValsQ[cons_id][pAddr] = ConsumerReadData_t(pAddr,pkt_data[0],addrIterCountMap[pAddr]);
            }
            addrIterCountMap[pAddr]++;

            if (isProducer && (numWriteTxnCompleted > 0) && (numWriteTxnCompleted%workingSetSize==0)) {
                TESTER_PRODUCER_IDX++;
            }
            if (numWriteTxnCompleted >= maxLoads) {
                numCPUTransactionsCompleted++;
            }
        }
        
        if (numCPUTransactionsCompleted >= (num_consumers+num_producers)) {
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
        // schedule(tickEvent, clockEdge(interval));
        schedule(tickEvent, curTick());
    }
}

TrueProdConsMemTest::MemTestStats::MemTestStats(statistics::Group *parent)
      : statistics::Group(parent),
      ADD_STAT(numReads, statistics::units::Count::get(),
               "number of read accesses completed"),
      ADD_STAT(numWrites, statistics::units::Count::get(),
               "number of write accesses completed")
{

}

void
TrueProdConsMemTest::tick()
{
    // we should never tick if we are waiting for a retry
    assert(!retryPkt);
    assert(!waitResponse);
    assert(!isIdle);

    // create a new request
    unsigned offset=0;
    Request::Flags flags;
    Addr paddr = 0;
    bool readOrWrite = (isProducer)?false:true;  // Only producer can write
    unsigned workingSetSize=perCPUWorkingBlocks.size();

    // Skip if you have outstanding Too many outstanding transactions
    if (outstandingAddrs.size() >= maxOutStandingTransactions) {
        waitResponse = true;
        return;
    }

    writeSyncData_t data;
    if (!isProducer) {
        /* Skip if you generated maxLoads transactions */
        if (numReadTxnGenerated >= maxLoads) {
            DPRINTF(TrueProdConsMemLatTest,"Reader finished generating %d\n",numReadTxnGenerated);
            waitResponse = true;
            return;
        }

        assert(writeValsQ.find(id) != writeValsQ.end());

        /* No producer has generated any data. Stall and check again later */
        if ((writeValsQ[id].empty()) && (num_producers > 0)) {
            /**
             * There are no writes to the memory yet.
             * And there are active writers
             * Retry in the next interval
             */
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
            return;
        }

        ConsumerReadData_t cons_data;
        bool addrFound = false;
        for (const auto &elem : writeValsQ[id]) {
            paddr = elem.first;
            cons_data = elem.second;
            assert(paddr == cons_data.getAddr());
            if (outstandingAddrs.find(paddr) != outstandingAddrs.end()) {
                continue;
            } else {
                addrFound = true;
                break;
            }
        }
        if (!addrFound) {
            /* No addresses with pending reads. Keep Polling */
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
            return;
        }
        
        DPRINTF(TrueProdConsMemLatTest,"TrPrdCnsLaT|Addr:%x,Iter:%d,ConsId:%d,ReadStart\n", \
                cons_data.getAddr(), \
                cons_data.getIterCount(), \
                id);
    } else {
        /* Skip if you generated maxLoads transactions. But keep rescheduling noRequestEvent */
        if (numWriteTxnGenerated >= maxLoads) {
            DPRINTF(TrueProdConsMemLatTest,"Writer finished generating %d\n",numWriteTxnGenerated);
            waitResponse = true;
            return;
        }
        
        /* Search for an address within the workingSet */
        bool addrFound = false;
        for (const auto waddr : perCPUWorkingBlocks) {
            paddr = waddr;
            if (outstandingAddrs.find(paddr) != outstandingAddrs.end()) {
                continue; // Outstanding writes
            } else if (pendingReads.find(paddr) != pendingReads.end()) {
                continue; // pending reads
            } else {
                addrFound = true;
                break;
            }
        }
        if (!addrFound) {
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
            return;
        }
        data = (TESTER_PRODUCER_IDX << 8) + (writeSyncDataBase++);
        pendingReads[paddr]=num_consumers;
        DPRINTF(TrueProdConsMemLatTest,"TrPrdCnsLaT|Addr:%x,Iter:%d,ProdId:%d,WriteStart\n", \
                paddr, \
                addrIterCountMap[paddr], \
                id);
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
        numReadTxnGenerated++;
    } else {
        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        pkt_data[0] = data;
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
        DPRINTF(TrueProdConsMemLatTest, "Waiting for retry\n");
    }

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs.size() != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
}

void
TrueProdConsMemTest::noRequest()
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
TrueProdConsMemTest::noResponse()
{
    assert(!isIdle);
    panic("%s did not see a response for %d cycles", name(), progressCheck);
}

void
TrueProdConsMemTest::recvRetry()
{
    assert(retryPkt);
    if (port.sendTimingReq(retryPkt)) {
        DPRINTF(TrueProdConsMemLatTest, "Proceeding after successful retry\n");

        retryPkt = nullptr;
        // kick things into action again
        schedule(tickEvent, clockEdge(interval));
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    }
}

} // namespace gem5