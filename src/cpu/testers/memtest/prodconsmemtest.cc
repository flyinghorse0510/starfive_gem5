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
#include <algorithm>
#include <iterator>
#include "debug/MsgBufDebug.hh"

namespace gem5
{

class ConsumerReadData_t {
    private:
        std::unordered_map<Addr,writeSyncData_t> addr_and_data;
        std::unordered_set<Addr> all_addr;
        unsigned addrSetSize;
    public:
        ConsumerReadData_t(const std::unordered_map<Addr,writeSyncData_t> &addrData) {
            std::copy(addrData.begin(), addrData.end(), std::inserter(addr_and_data,addr_and_data.end()));
            for (auto it = addrData.begin(); it != addrData.end(); it++) {
                all_addr.insert(it->first);
            }
            addrSetSize=all_addr.size();
        }
        Addr getNextAddr(const std::unordered_set<Addr>&);
        writeSyncData_t getRefData(const Addr addr) const { 
            assert(addr_and_data.find(addr) != addr_and_data.end());
            return addr_and_data.at(addr); 
        }
        unsigned getWorkingSetSize() const { return addr_and_data.size(); }
        bool isAddrSetEmpty() const { return all_addr.empty(); }
        unsigned getAddrSetSize() const { return all_addr.size(); }
        void removeAddr(const Addr& paddr, const std::string& name2) {
            all_addr.erase(paddr);
        }

};

Addr ConsumerReadData_t::getNextAddr(const std::unordered_set<uint64_t>& outstandingAddrs) {
    bool foundAddr=false;
    Addr addr;
    for (auto caddr : all_addr) {
        if (outstandingAddrs.find(caddr) == outstandingAddrs.end()) {
            foundAddr=true;
            addr=caddr;
            break;
        }
    }
    assert(foundAddr);
    return addr;
}


static unsigned int TESTER_ALLOCATOR = 0;
static std::unordered_map<unsigned,std::shared_ptr<ConsumerReadData_t>> writeValsQ;
static unsigned int TESTER_PRODUCER_IDX; // Pass Index of the writer. Only written by sole producer
static unsigned int numProdCompleted = 0;
static unsigned int numConsCompleted = 0;
static unsigned int TOTAL_REQ_AGENTS = 0;  // Used to hold the agents capable of generating Read/Write requests
static unsigned int producer_peer_id=0;    // Location ind producer peer id
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
      numPeerProducers(p.num_peer_producers),
      addrInterleavedOrTiled(p.addr_intrlvd_or_tiled),
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48), // init txSeqNum as RequestorId(16-bit)_0000_0000_0000
      suppressFuncErrors(p.suppress_func_errors), stats(this)
{
    id = TESTER_ALLOCATOR++;
    fatal_if(id >= blockSize, "Too many testers, only %d allowed\n",
             blockSize - 1);
    

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

    // Initialize the txn counters
    numReadTxnGenerated=0;
    numReadTxnCompleted=0;
    numWriteTxnGenerated=0;
    TESTER_PRODUCER_IDX = 0;

    /**
     * If you are producer, the inject interval need NOT to be too large
     * This assumption may not hold for
     * all benchmarks
     */ 
    if (isProducer) {
        interval = Cycles(1);
    }

    maxLoads=0;
    if (!isIdle) {
        fatal_if(workingSet%(numPeerProducers*blockSize)!=0,"per producer working set not block aligned\n");
        unsigned totalWorkingSetInBlocks=(workingSet/blockSize);
        numPerCPUWorkingBlocks=(workingSet/(numPeerProducers*blockSize));
        if (addrInterleavedOrTiled) {
            for (unsigned i=0; i < numPerCPUWorkingBlocks; i++) {
                Addr effectiveBlockAddr=baseAddr+(numPeerProducers*i)+producer_peer_id;
                perCPUWorkingBlocks.push_back(effectiveBlockAddr<<(static_cast<uint64_t>(std::log2(blockSize))));
            }
        } else {
            for (unsigned i=0; i < numPerCPUWorkingBlocks; i++) {
                Addr effectiveBlockAddr=baseAddr+(numPerCPUWorkingBlocks*(producer_peer_id))+i;
                perCPUWorkingBlocks.push_back(effectiveBlockAddr<<(static_cast<uint64_t>(std::log2(blockSize))));
            }
        }
        fatal_if(perCPUWorkingBlocks.size()<=0,"Working Set size is 0\n");
            
        /**
         * In these tests we are interested in Cache transfer latency.
         * So each address is only traversed once.
         */
        if (isProducer) {
            maxLoads = static_cast<uint64_t>(std::ceil(static_cast<double>(perCPUWorkingBlocks.size())));
            producer_peer_id++;
        } else {
            /* If you are a consumer. Consume the data generated by all the producers */
            maxLoads = static_cast<uint64_t>(std::ceil(num_producers * (static_cast<double>(perCPUWorkingBlocks.size()))));        
        }
        fatal_if(maxLoads <= 0, "Requires a minimum of 1 Load/Store for non idle MemTesters");
        writeDataGenerated.clear();
        maxOutStandingTransactions = p.outstanding_req;
        if (isProducer) {
            /* Producers need to wait for all outstanding writes. Set to max value */
            maxOutStandingTransactions = 100;
        }
        DPRINTF(ProdConsMemLatTest,"CPU_%d(Producer:%d,Idle:%d) WorkingSetRange:[%x,%x], WorkingSetSize=%d, maxTxn=%d\n",id,isProducer,isIdle,perCPUWorkingBlocks.at(0),perCPUWorkingBlocks.at(numPerCPUWorkingBlocks-1),numPerCPUWorkingBlocks,maxLoads);
    
        // kick things into action
        TOTAL_REQ_AGENTS++;
        schedule(tickEvent, curTick());
        schedule(noRequestEvent, clockEdge(progressCheck));
    }
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

            if (numReadTxnCompleted >= maxLoads) {
                DPRINTF(ProdConsMemLatTest,"id=(%d/%d) Completed all read resp=%d,%d\n",id,numConsCompleted,numReadTxnCompleted,maxLoads);
                numConsCompleted++;
            }
        } else {
            assert(pkt->isWrite());

            DPRINTF(ProdConsMemLatTest, "Complete,W,%x,%x\n", req->getPaddr(),pkt_data[0]);
            referenceData[req->getPaddr()] = pkt_data[0];
            stats.numWrites++;
            if (isProducer && ((referenceData.size())>=workingSetSize)) {
                DPRINTF(ProdConsMemLatTest,"id=(%d,%d) Completed all writes resp=%d,%d,numProdCompleted=%d\n",id,producer_peer_id,referenceData.size(),workingSetSize,numProdCompleted);
                for (auto c : id_consumers) {
                    writeValsQ[c] = std::make_shared<ConsumerReadData_t>(referenceData);
                }
                TESTER_PRODUCER_IDX++;

                numProdCompleted++;
            }

        }
        
        if ((numConsCompleted+numProdCompleted) >= TOTAL_REQ_AGENTS) {
            DPRINTF(ProdConsMemLatTest, "id=%d,num_consumers=%d,num_producers=%d,numConsCompleted=%d,numProdCompleted=%d,TOTAL_REQ_AGENTS=%d\n", id, num_consumers, num_producers, numConsCompleted,numProdCompleted,TOTAL_REQ_AGENTS);
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
    assert(!isIdle);

    // create a new request
    Request::Flags flags;
    Addr paddr = 0;
    bool readOrWrite = (isProducer)?false:true;  // Only producer can write
    unsigned workingSetSize=perCPUWorkingBlocks.size();
    unsigned readWorkingSetSize=0;

    writeSyncData_t data;
    if (!isProducer) {
        /* Skip if you generated maxLoads transactions */
        if (numProdCompleted < numPeerProducers) {
            /* Wait for all writes to finish before generating a read*/
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
            return;
        }

        assert(writeValsQ.find(id) != writeValsQ.end());
        auto cdata = writeValsQ.at(id);

        /* Wait if you have too many outstanding read transactions */
        readWorkingSetSize = cdata->getWorkingSetSize();
        if (maxOutStandingTransactions > readWorkingSetSize) {
            maxOutStandingTransactions = readWorkingSetSize;
        }
        if (outstandingAddrs.size() >= maxOutStandingTransactions) {
            waitResponse = true;
            return;
        }

        /* If you have generated all addresses in the working set. do not generate any more */
        if (cdata->isAddrSetEmpty()) {
            DPRINTF(ProdConsMemLatTest,"Reader finished generating workingset %d/%d/%d\n",numReadTxnGenerated,maxLoads,cdata->getAddrSetSize());
            waitResponse = true;
            return;
        }

        /* Pick an address to generate a read request */
        paddr = cdata->getNextAddr(outstandingAddrs);
        data = cdata->getRefData(paddr);

    } else {
        /* Skip if you generated workingSetSize write transactions */
        if (writeDataGenerated.size() >= workingSetSize) {
            DPRINTF(ProdConsMemLatTest,"id=(%d,%d) Completed all writes reqs=%d,%d\n",producer_peer_id,id,writeDataGenerated.size(),workingSetSize);
            waitResponse = true;
            return;
        }
        
        /* Too many outstanding writes. For example non of addresses are free. Stall */
        if (maxOutStandingTransactions > workingSetSize) {
            maxOutStandingTransactions = workingSetSize;
        }
        if (outstandingAddrs.size() >= maxOutStandingTransactions) {
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
        numReadTxnGenerated++;
        // Remove the address from the reader's working set
        assert(writeValsQ.find(id) != writeValsQ.end());
        auto cdata = writeValsQ.at(id);
        cdata->removeAddr(paddr,name());
        DPRINTF(ProdConsMemLatTest,"Start,R,%x,%x,%d/%d/%d\n",req->getPaddr(),data,numReadTxnGenerated,readWorkingSetSize,cdata->getAddrSetSize());
    } else {
        pkt = new Packet(req, MemCmd::WriteReq);
        pkt->dataDynamic(pkt_data);
        pkt_data[0] = data;
        DPRINTF(ProdConsMemLatTest,"Start,W,%x,%x,%d\n",req->getPaddr(),data,numWriteTxnGenerated);
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
        DPRINTF(ProdConsMemLatTest, "Waiting for retry\n");
    }

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs.size() != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
}

void
ProdConsMemTest::noRequest()
{
    assert(!isIdle);
    if (isProducer) {
        if (numWriteTxnGenerated < maxLoads) {
            printf("numWriteTxnGenerated=%d,maxLoads=%d\n",numWriteTxnGenerated,maxLoads);
            panic("%s did not send a request for %d cycles", name(), progressCheck);
        }
    } else {
        if (numReadTxnGenerated < maxLoads) {
            printf("numReadTxnGenerated=%d,maxLoads=%d\n",numReadTxnGenerated,maxLoads);
            panic("%s did not send a request for %d cycles", name(), progressCheck);
        }
    }
    
}

void
ProdConsMemTest::noResponse()
{
    assert(!isIdle);
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
