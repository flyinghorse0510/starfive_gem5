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

enum TrueProdState {
    WRITE_GENERATE,
    WRITE_RECV,
    WRITE_DONE,
    ALL_READS_DONE,
    POP_WRITE_QUEUE
};

enum TrueConsState {
    READ_INACTIVE,
    READ_GENERATE,
    READ_RECV,
    READ_DONE
};

class TrueProdConsStruct_t {
    private:
        const Addr addr;
        const writeSyncData_t data;
        const unsigned max_iter_count;
        const unsigned iter_count;
        const unsigned prod_id;
        TrueProdState prod_state;   
        std::unordered_map<unsigned,TrueConsState> cons_id_states_map; // This should also be const. But not sure how to initialize a const vector
    public:
        TrueProdConsStruct_t(Addr addr, \
                             writeSyncData_t data, \
                             unsigned max_iter_count, \
                             unsigned iter_count, \
                             unsigned producer_id, \
                             const std::unordered_set<unsigned>& cons_list)
            : addr(addr), 
              data(data),
              max_iter_count(max_iter_count),
              iter_count(iter_count),
              prod_id(producer_id) {
                prod_state = WRITE_GENERATE;
                for (auto cons : cons_list) {
                    cons_id_states_map[cons] = READ_INACTIVE;
                }
            }
        void updateProdState() {
            switch(prod_state) {
                case WRITE_GENERATE : {
                    prod_state = WRITE_RECV;
                    break;
                }
                case WRITE_RECV : {
                    prod_state = WRITE_DONE;
                    break;
                }
                case WRITE_DONE :
                case ALL_READS_DONE : {
                    prod_state = POP_WRITE_QUEUE;
                }
            }
        }
        void updateConsState(unsigned cons_id) {
            assert(cons_id_states_map.find(cons_id) != cons_id_states_map.end());
            auto cons_state = cons_id_states_map[cons_id];
            switch(cons_state) {
                case READ_GENERATE : {
                    cons_state = READ_RECV;
                    break;
                }
                case READ_RECV : {
                    cons_state = READ_DONE;
                    break;
                }
                case READ_DONE : {
                    cons_id_states_map.erase(cons_id);
                    if (cons_id_states_map.empty()) {
                        prod_state = ALL_READS_DONE;
                    }
                    break;
                }
                default : {
                    DPRINTF(TrueProdConsMemLatTest,"Illegal States encountered\n");
                }
            }
        }
        bool isWriteDone() const { return (prod_state == WRITE_DONE); }
        bool isAllWritesDone() const { return (iter_count >= max_iter_count); }
        bool isAllReadsDone() const { return (prod_state == ALL_READS_DONE); }
        bool canPopWriteQueue() const { return (prod_state == POP_WRITE_QUEUE); }
        void setForRead() {
            assert(isWriteDone());
            for (auto& entry : cons_id_states_map) {
                entry.second = READ_GENERATE;
            }
        }
        Addr getAddr() const { return addr; }
        writeSyncData_t getData() const { return data; }
        unsigned getIterCount() const { return iter_count; }
        unsigned getProdId() const { return prod_id; }
        bool isConsPresent(unsigned id) const {
            if (cons_id_states_map.find(id) != cons_id_states_map.end()) {
                return true;
            }
            return false;
        }
        TrueProdState getProdState() const { return prod_state; }
        TrueConsState getConsState(unsigned cons_id) const {
            assert(cons_id_states_map.find(cons_id) != cons_id_states_map.end());
            return cons_id_states_map.at(cons_id);
        }
};

static unsigned int num_txn_generated=0;
static unsigned int TESTER_ALLOCATOR=0; // Pass Index of the writer. Only written by sole producer
static std::queue<TrueProdConsStruct_t> prodAddrQ;
static std::unordered_map<Addr,TrueProdConsStruct_t> prodAddrMap;
static std::queue<TrueProdConsStruct_t> consAddrQ;
static std::unordered_map<Addr,TrueProdConsStruct_t> consAddrMap;

bool TrueProdConsMemTest::CpuPort::recvTimingResp(PacketPtr pkt)
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
      id_producer(p.id_starter),
      baseAddr(p.base_addr_1),
      num_cpus(p.num_cpus),
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48), // init txSeqNum as RequestorId(16-bit)_0000_0000_0000
      suppressFuncErrors(p.suppress_func_errors), stats(this) {

    id = TESTER_ALLOCATOR++;
    maxOutStandingTransactions = 100;
    bool isProducer = (id == id_producer);
    bool isIdle = (id != id_producer);
    std::copy(p.id_consumers.begin(),p.id_consumers.end(),std::inserter(id_consumers,id_consumers.end()));

    if (id_consumers.find(id) != id_consumers.end()) {
        isIdle = false;
    }

    unsigned totalWorkingSetInBlocks=(workingSet/blockSize);
    if (isProducer) {
        for (unsigned i=0; i < totalWorkingSetInBlocks; i++) {
            Addr addr = (baseAddr+i)<<(static_cast<uint64_t>(std::log2(blockSize)));
            writeSyncData_t data = 0x873a; // Append some random data
            prodAddrQ.push(TrueProdConsStruct_t(\
                addr, \
                data, \
                maxLoadFactor, \
                0, \
                id, \
                id_consumers));
        }
    }

    if (isIdle) {
        // Generate the initial tick
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

void TrueProdConsMemTest::completeRequest(PacketPtr pkt, bool functional) {
 
}

TrueProdConsMemTest::MemTestStats::MemTestStats(statistics::Group *parent)
      : statistics::Group(parent),
      ADD_STAT(numReads, statistics::units::Count::get(),
               "number of read accesses completed"),
      ADD_STAT(numWrites, statistics::units::Count::get(),
               "number of write accesses completed")
{

}

void TrueProdConsMemTest::tick() {
    // we should never tick if we are waiting for a retry
    assert(!isIdle);
    assert(!retryPkt);
    assert(!waitResponse);

    // create a new request
    Request::Flags flags;
    Addr paddr = 0;
    bool readOrWrite = false;
    bool generateRequest = false;
    writeSyncData_t data = 0x0;

    // Skip if you have outstanding Too many outstanding transactions
    if (outstandingAddrs.size() >= maxOutStandingTransactions) {
        waitResponse = true;
        return;
    }

    /* Appropriate addr objects not prepared */
    if (prodAddrQ.empty() && consAddrQ.empty()) {
        /* All transactions completed. Exit ? */
        exitSimLoop("All migratory transactions completed");
        return;
    } else if (prodAddrQ.empty()) {
        if (isProducer) {
            /* Keep 'polling' */
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
        }
    } else {
        if (!isProducer) {
            /* Keep 'polling' */
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
        }
    }

    if (isProducer) {
        /* Handle Write objects */
        assert(!prodAddrQ.empty());
        TrueProdConsStruct_t& writeAddrObj = prodAddrQ.front();
        assert(id == writeAddrObj.getProdId());
        auto writeState = writeAddrObj.getProdState();
        switch(writeState) {
            case WRITE_GENERATE : {
                generateRequest = true;
                readOrWrite = false;
                paddr = writeAddrObj.getAddr();
                data = writeAddrObj.getData();
                break;
            }
            // The following cases must be handled during write response
            case WRITE_RECV : {
                /* 
                 * Nothing new to generate. Waiting on write response. 
                 * Will be handled while completing request. Remember
                 * to schedule a tick, so that this can fire again.
                 */
                waitResponse = true;
                return;
            }
            case WRITE_DONE : {
                paddr = writeAddrObj.getAddr();
                data = writeAddrObj.getData();
                auto iter_count = writeAddrObj.getIterCount();
                if (iter_count < maxLoadFactor) {
                    // Construct and Enqueue a readAddr object into consAddrQ
                    TrueProdConsStruct_t genReadAddrObj(paddr, \
                                                    data, \
                                                    maxLoadFactor, \
                                                    iter_count, \
                                                    id, \
                                                    id_consumers);
                    genReadAddrObj.setForRead(); // Mark this for read
                    consAddrQ.push(genReadAddrObj);
                }
                break;
            }
            case ALL_READS_DONE : {
                paddr = writeAddrObj.getAddr();
                auto iter_count = writeAddrObj.getIterCount();
                if (!writeAddrObj.isAllWritesDone()) {
                    /* Create fresh new write transaction with a different iter_count */
                    TrueProdConsStruct_t genNewWriteAddrObj(paddr, \
                                                    data, \
                                                    maxLoadFactor, \
                                                    iter_count+1, \
                                                    id, \
                                                    id_consumers);
                    prodAddrQ.push(genNewWriteAddrObj);
                }
                break;
            }
        }
        
        if (writeAddrObj.canPopWriteQueue()) {
            prodAddrQ.pop(); // This will allow other writes to proceed
        }
        writeAddrObj.updateProdState();
    } else {
        /* Handle Read objects */
        assert(!consAddrQ.empty());
        TrueProdConsStruct_t& readAddrObj = consAddrQ.front();
        if (!readAddrObj.isConsPresent(id)) {
            /* Poll */
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
            return; // [ARKA]: Do you want to return
        }
        auto readState = readAddrObj.getConsState(id);
        assert(readState != READ_INACTIVE);
        switch(readState) {
            case READ_GENERATE : {
                generateRequest = true;
                readOrWrite = true;
                paddr = readAddrObj.getAddr();
                data = readAddrObj.getData();
                break;
            }
            case READ_RECV : {
                waitResponse = true;
                return;
            }
            case READ_DONE : {
                /* [ARKA]: Add DPRINTF */
            }
        }
        readAddrObj.updateConsState(id);
        if (readAddrObj.isAllReadsDone()) {
            consAddrQ.pop();
        }
    }

    if (generateRequest) {
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
        } else {
            pkt = new Packet(req, MemCmd::WriteReq);
            pkt->dataDynamic(pkt_data);
            pkt_data[0] = data;
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
    } else {
        /* Just schedule a tick */
        schedule(tickEvent, clockEdge(interval));
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
    }

}

void
TrueProdConsMemTest::noRequest()
{
    panic("%s did not send a request for %d cycles", name(), progressCheck);
}

void
TrueProdConsMemTest::noResponse()
{
    // assert(!isIdle);
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
