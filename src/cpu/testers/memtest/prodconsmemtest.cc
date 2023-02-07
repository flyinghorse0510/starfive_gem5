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
#include <queue>
#include <utility>
#include <tuple>
#include <memory>
#include "debug/MsgBufDebug.hh"

namespace gem5
{

class ConsumerReadData_t {
    private:
        Addr addr;
        writeSyncData_t data;
        uint32_t num_consumers;
    public:
        ConsumerReadData_t(Addr addr, writeSyncData_t data, uint32_t num_consumers)
            : addr(addr),
              data(data),
              num_consumers(num_consumers) {}
        Addr getPaddr() const { return addr; }
        writeSyncData_t getData() const { return data; }
        uint32_t getNumConsumers() const { return num_consumers; }
        void decConsumers() { num_consumers--; }
};

static unsigned int TESTER_ALLOCATOR = 0;
static std::queue<std::shared_ptr<ConsumerReadData_t>> writeValsQ=std::queue<std::shared_ptr<ConsumerReadData_t>>();
static std::unordered_map<Addr,uint32_t> pendingReads;  // Data has not been consumed for these address. The mapped value represents the number of consumers
static unsigned int TESTER_PRODUCER_IDX; // Pass Index of the writer. Only written by sole producer
static unsigned int numCPUTransactionsCompleted = 0; // Number of CPUs that have completed their transactions

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
      workingSet(p.working_set),
      progressInterval(p.progress_interval),
      progressCheck(p.progress_check),
      nextProgressMessage(p.progress_interval),
      maxLoadFactor(p.max_loads),
      atomic(p.system->isAtomicMode()),
      seqIdx(0),
      baseAddr(p.base_addr_1),
      num_cpus(p.num_cpus),
      num_producers(p.num_producers),
      addrInterleavedOrTiled(p.addr_intrlvd_or_tiled),
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48), // init txSeqNum as RequestorId(16-bit)_0000_0000_0000
      suppressFuncErrors(p.suppress_func_errors), stats(this)
{
    id = TESTER_ALLOCATOR++;
    fatal_if(id >= blockSize, "Too many testers, only %d allowed\n",
             blockSize - 1);

    fatal_if(workingSet%(num_producers*blockSize)!=0,"per producer working set not block aligned, workingSet=%d,num_cpus=%d,blockSize=%d\n",workingSet,num_cpus,blockSize);
    numPerCPUWorkingBlocks=(workingSet/(num_producers*blockSize));
    for (unsigned i=0; i < numPerCPUWorkingBlocks; i++) {
        Addr effectiveBlockAddr=(addrInterleavedOrTiled)?(baseAddr+(num_producers*i)+id):
                                (baseAddr+(numPerCPUWorkingBlocks*id)+i);
        perCPUWorkingBlocks.push_back(effectiveBlockAddr<<(static_cast<uint64_t>(std::log2(blockSize))));
    }
    fatal_if(perCPUWorkingBlocks.size()<=0,"Working Set size is 0\n");

    maxLoads = static_cast<uint64_t>(std::ceil(maxLoadFactor * (static_cast<double>(perCPUWorkingBlocks.size()))));
    
    fatal_if(maxLoads <= 0, "Requires a minimum of 1 Load/Store");

    // set up counters
    numReadTxnGenerated=0;
    numReadTxnCompleted=0;
    numWriteTxnGenerated=0;
    numWriteTxnCompleted=0;
    TESTER_PRODUCER_IDX = 0;
    
    isProducer=false;
    if (id < num_producers) {
        isProducer=true;
    }
    fatal_if(num_producers > num_cpus, "Number of producers must be less than the number of CPUs");
    num_consumers=num_cpus-num_producers;
    DPRINTF(ProdConsMemLatTest,"Max Loads/Store=%d\n",maxLoads);
    DPRINTF(ProdConsMemLatTest,"CPU_%d(Producer:%d) WorkingSetRange:[%x,%x]\n",id,isProducer,perCPUWorkingBlocks.at(0),perCPUWorkingBlocks.at(numPerCPUWorkingBlocks-1));
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

    unsigned workingSetSize=perCPUWorkingBlocks.size();

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
                DPRINTF(ProdConsMemLatTest, "Complete,R,%x,%x\n", req->getPaddr(),pkt_data[0]);
                numReadTxnCompleted++;
                stats.numReads++;

                if (numReadTxnCompleted == (uint64_t)nextProgressMessage) {
                    ccprintf(std::cerr,
                            "%s: completed %d read, %d write accesses @%d\n",
                            name(), numReadTxnCompleted, numWriteTxnCompleted, curTick());
                    nextProgressMessage += progressInterval;
                }
            }
            
            auto pendingAddrPtr=pendingReads.find(req->getPaddr());
            assert(pendingAddrPtr != pendingReads.end());
            pendingReads[req->getPaddr()]--;
            if (pendingReads[req->getPaddr()]==0) {
                pendingReads.erase(pendingAddrPtr);
            }
            if (numReadTxnCompleted >= maxLoads) {
                numCPUTransactionsCompleted++;
            }
        } else {
            assert(pkt->isWrite());

            DPRINTF(ProdConsMemLatTest, "Complete,W,%x,%x\n", req->getPaddr(),pkt_data[0]);
            // update the reference data
            referenceData[req->getPaddr()] = pkt_data[0];
            numWriteTxnCompleted++;
            stats.numWrites++;
            writeValsQ.push(std::make_shared<ConsumerReadData_t>(req->getPaddr(),pkt_data[0],num_consumers));
            if (isProducer && (numWriteTxnCompleted > 0) && (numWriteTxnCompleted%workingSetSize==0)) {
                TESTER_PRODUCER_IDX++;
            }
            if (numWriteTxnCompleted >= maxLoads) {
                numCPUTransactionsCompleted++;
            }
        }
        
        if (numCPUTransactionsCompleted >= num_cpus) {
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
    bool readOrWrite = (isProducer)?false:true;  // Only producer can write
    unsigned workingSetSize=perCPUWorkingBlocks.size();

    // Skip if you have outstanding Too many outstanding transactions
    if (outstandingAddrs.size() >= 100) {
        waitResponse = true;
        return;
    }

    writeSyncData_t data;
    if (!isProducer) {
        /* Skip if you generated maxLoads transactions */
        if (numReadTxnGenerated >= maxLoads) {
            DPRINTF(ProdConsMemLatTest,"Reader finished generating %d\n",numReadTxnGenerated);
            waitResponse = true;
            return;
        }

        /* No producer has generated any data. Stall and check again later */
        if (writeValsQ.empty() && (num_producers > 0)) {
            /**
             * There are no writes to the memory yet.
             * And there are active writers
             * Retry in the next interval
             */
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
            return;
        }

        /* Find an address (from the produced data) to generate a Read request */
        auto consumer_data=writeValsQ.front();
        paddr=consumer_data->getPaddr();

        /* A previous Read to same paddr from this consumer is awaiting response. Stall */
        if (outstandingAddrs.find(paddr) != outstandingAddrs.end()) {
            waitResponse = true;
            return;
        }

        data=consumer_data->getData();
        consumer_data->decConsumers();
        if (consumer_data->getNumConsumers() <= 0) {
            writeValsQ.pop();
        }
    } else {
        /* Skip if you generated maxLoads transactions. But keep rescheduling noRequestEvent */
        if (numWriteTxnGenerated >= maxLoads) {
            DPRINTF(ProdConsMemLatTest,"Writer finished generating %d\n",numWriteTxnGenerated);
            waitResponse = true;
            return;
        }
        
        /* No free addresses to generate from this producer. Stall */
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

        /* This address has pending reads. Stall and reschedule this write later*/
        if (num_consumers > 0) {
            if (pendingReads.find(paddr) != pendingReads.end()) {
                schedule(tickEvent, clockEdge(interval));
                reschedule(noRequestEvent, clockEdge(progressCheck), true);
                return;
            }
            pendingReads[paddr]=num_consumers;
        }
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
        DPRINTF(ProdConsMemLatTest,"Start,R,%x,%x\n",req->getPaddr(),data);
    } else {
        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        pkt_data[0] = data;
        DPRINTF(ProdConsMemLatTest,"Start,W,%x,%x\n",req->getPaddr(),data);
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

        if (readOrWrite) {
            numReadTxnGenerated++;
        } else {
            numWriteTxnGenerated++;
        }
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
