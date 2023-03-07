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

enum MigratoryStructureState {
    READ_GENERATE,
    READ_RECV,
    WRITE_GENERATE,
    WRITE_RECV,
    DONE
};

class MigratoryStructure_t {
    private:
        const Addr addr; // Must be cache line aligned
        const writeSyncData_t data;
        const unsigned start_id;   // The first requestor
        const unsigned iter_count;
        unsigned current_id;
        std::queue<unsigned> subsequent_ids_q; // Where to push next
        MigratoryStructureState state;
        bool isEmpty;
    public:
        MigratoryStructure_t(unsigned j, \
                             unsigned start_id,\
                             Addr addr, \
                             writeSyncData_t data,\
                             unsigned num_sharers)
          : iter_count(j), 
            start_id(start_id),
            addr(addr),
            data(data) {

            state = READ_GENERATE; // Initial state
            current_id = start_id;
            for (unsigned sharer = 0; sharer < num_sharers; sharer++) {
                if (sharer != start_id) {
                    subsequent_ids_q.push(sharer);
                }
            }
            isEmpty = subsequent_ids_q.empty();
            fatal_if(isEmpty,"Inital migratory queue empty. Needs atleast one additional sharer");
        }

        MigratoryStructureState getState() const { return state; }
        Addr getAddr() const { return addr; }
        writeSyncData_t getData() const { return data; }
        void updateState() {
            switch (state) {
                case READ_GENERATE : {
                    state = READ_RECV;
                    break;
                }
                case READ_RECV : {
                    state = WRITE_GENERATE;
                    break;
                }
                case WRITE_GENERATE : {
                    state = WRITE_RECV;
                    break;
                }
                case WRITE_RECV : {
                    state = DONE;
                    break;
                }
                case DONE : {
                    if (subsequent_ids_q.empty()) {
                        isEmpty = true;
                    } else {
                        /* Pop-up the next sharer and restart */
                        current_id = subsequent_ids_q.front();
                        subsequent_ids_q.pop();
                        isEmpty = false;
                        state = READ_GENERATE;
                        // DPRINTF(MigratoryMemLatTest,"Switching to user=%d\n",current_id);
                    }
                    break;
                }
                default : {
                    DPRINTF(MigratoryMemLatTest,"Invalid State=%d\n",state);
                    assert(false);
                }
            }
        }
        bool isDone() const { return (state == DONE); }
        unsigned getCurrentId() const { return current_id; }
        bool allSharersFinished() const { return isEmpty; }
        unsigned getIter() const { return iter_count; }
        std::string to_string() const {
            std::stringstream ss;
            ss << "Addr:" << addr
               << ",Data:" << data
               << ",start_id:" << start_id
               << ",iter_count:" << iter_count
               << ",current_id:" << current_id
               << ",subsequent_ids_q_size:" <<subsequent_ids_q.size()
               << ",state:" << state;
            return ss.str();
        }

};

static unsigned int num_txn_generated=0;
static unsigned int TESTER_ALLOCATOR=0; // Pass Index of the writer. Only written by sole producer
static std::queue<MigratoryStructure_t> migratoryPendRequests;
static bool migStructInitialized=false;

bool MigratoryMemTest::CpuPort::recvTimingResp(PacketPtr pkt)
{
    seqmemtest.completeRequest(pkt);
    return true;
}

void
MigratoryMemTest::CpuPort::recvReqRetry()
{
    seqmemtest.recvRetry();
}

bool
MigratoryMemTest::sendPkt(PacketPtr pkt) {
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

MigratoryMemTest::MigratoryMemTest(const Params &p)
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
      id_starter(p.id_starter),
      atomic(p.system->isAtomicMode()),
      seqIdx(0),
      baseAddr(p.base_addr_1),
      num_cpus(p.num_cpus),
      txSeqNum((static_cast<uint64_t>(p.system->getRequestorId(this))) << 48), // init txSeqNum as RequestorId(16-bit)_0000_0000_0000
      suppressFuncErrors(p.suppress_func_errors), stats(this) {

    id = TESTER_ALLOCATOR++;

    // Initialize the txn counters
    num_txn_generated=0;
    numReadTxnCompleted=0;
    numWriteTxnCompleted=0;
    maxOutStandingTransactions=100;

    /* Initialize the working set. 
     * The same workingSet is shared by everyone.
     * But only the starting requestor initializes
     * the working set array
     */
    bool isStarter = (id == id_starter);
    fatal_if((workingSet%blockSize)!=0,"The working set is not cache line aligned");
    unsigned totalWorkingSetInBlocks=(workingSet/blockSize);
    maxLoads = maxLoadFactor * (totalWorkingSetInBlocks);
    if (isStarter) {
        for (unsigned j = 0; j < maxLoadFactor; j++) {
            for (unsigned i=0; i < totalWorkingSetInBlocks; i++) {
                /* Create the Initial migratory stucture for each block in the working set */
                Addr addr = (baseAddr+i)<<(static_cast<uint64_t>(std::log2(blockSize)));
                writeSyncData_t data = 0x873a; // Append some random data
                migratoryPendRequests.push(MigratoryStructure_t(j,id,addr,data,num_cpus));
                // DPRINTF(MigratoryMemLatTest,"Pushing addr=%x,iter=%d\n",addr,j);
            }
        }
        migStructInitialized=true;
    }
    
    // Generate the initial tick
    schedule(tickEvent, curTick());
    schedule(noRequestEvent, clockEdge(progressCheck));
}

Port &
MigratoryMemTest::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "port")
        return port;
    else
        return ClockedObject::getPort(if_name, idx);
}

void MigratoryMemTest::completeRequest(PacketPtr pkt, bool functional) {
    const RequestPtr &req = pkt->req;
    assert(req->getSize() == 2);

    // Obtain the migratory object
    assert(!migratoryPendRequests.empty());
    MigratoryStructure_t& migratoryObject = migratoryPendRequests.front();
    assert(id == migratoryObject.getCurrentId()); // Id mismatch

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
            assert(migratoryObject.getState() == READ_RECV);
            writeSyncData_t ref_data = migratoryObject.getData();
            DPRINTF(MigratoryMemLatTest,"MiGMemLaT|Addr:%x,Iter:%d,Reqtor:%d,isStarter:%d,Complete:R,misMatch:%d\n",\
                remove_paddr,\
                migratoryObject.getIter(), \
                id,isStarter,(pkt_data[0] != ref_data));
            numReadTxnCompleted++;
            stats.numReads++;

            if (numReadTxnCompleted == (uint64_t)nextProgressMessage) {
                ccprintf(std::cerr,
                        "%s: completed %d read, %d write accesses @%d\n",
                        name(), numReadTxnCompleted, numWriteTxnCompleted, curTick());
                nextProgressMessage += progressInterval;
            }
            migratoryObject.updateState();

        } else {
            assert(pkt->isWrite());
            assert(migratoryObject.getState() == WRITE_RECV);
            DPRINTF(MigratoryMemLatTest,"MiGMemLaT|Addr:%x,Iter:%d,Reqtor:%d,isStarter:%d,Complete:W,misMatch:0\n",\
                    remove_paddr,\
                    migratoryObject.getIter(), \
                    id,isStarter);
            
            referenceData[req->getPaddr()] = pkt_data[0];
            stats.numWrites++;
            migratoryObject.updateState();
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

MigratoryMemTest::MemTestStats::MemTestStats(statistics::Group *parent)
      : statistics::Group(parent),
      ADD_STAT(numReads, statistics::units::Count::get(),
               "number of read accesses completed"),
      ADD_STAT(numWrites, statistics::units::Count::get(),
               "number of write accesses completed")
{

}

void MigratoryMemTest::tick() {
    // we should never tick if we are waiting for a retry
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

    if (migratoryPendRequests.empty()) {
        if (migStructInitialized) {
            /* All transactions completed. Exit ? */
            exitSimLoop("All migratory transactions completed");
            return;
        } else {
            /* No mig transaction created. Keep 'polling' */
            schedule(tickEvent, clockEdge(interval));
            reschedule(noRequestEvent, clockEdge(progressCheck), true);
            DPRINTF(MigratoryMemLatTest,"Queue Empty: Polling\n");
            return;
        }
    }
    MigratoryStructure_t& migratoryObject = migratoryPendRequests.front();
    
    /* You are not the requestor yet. Keep 'polling' */
    if (id != migratoryObject.getCurrentId()) {
        schedule(tickEvent, clockEdge(interval));
        reschedule(noRequestEvent, clockEdge(progressCheck), true);
        return;
    }

    auto state = migratoryObject.getState();
    switch (state) {
        case READ_GENERATE: {
            readOrWrite = true;
            generateRequest = true;
            paddr = migratoryObject.getAddr();
            data = migratoryObject.getData();
            DPRINTF(MigratoryMemLatTest,"MiGMemLaT|Addr:%x,Iter:%d,Reqtor:%d,isStarter:%d,Start:R\n",\
                    paddr,\
                    migratoryObject.getIter(), \
                    id,isStarter);
            break;
        }
        case WRITE_GENERATE: {
            readOrWrite = false;
            generateRequest = true;
            paddr = migratoryObject.getAddr();
            data = migratoryObject.getData();
            DPRINTF(MigratoryMemLatTest,"MiGMemLaT|Addr:%x,Iter:%d,Reqtor:%d,isStarter:%d,Start:W\n",\
                    paddr,\
                    migratoryObject.getIter(), \
                    id,isStarter);
            break;
        }
        case READ_RECV:
        case WRITE_RECV: {
            /* 
             * Nothing new to generate. Waiting on response. 
             * Will be handled while completing request. Remember
             * to schedule a tick, so that this can fire again.
             */
            waitResponse = true;
            return;
        }
        case DONE: {
            num_txn_generated++;
            DPRINTF(MigratoryMemLatTest,"MiGMemLaT|id(%d) %d Transactions completed\n",id,num_txn_generated);
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

    // Schedule noResponseEvent now if we are not expecting a response
    if (!noResponseEvent.scheduled() && (outstandingAddrs.size() != 0))
        schedule(noResponseEvent, clockEdge(progressCheck));
    
    /* 
     * Update the internal state of the migratory object 
     * and signal the next CPU to initiate the transactions
     * Find subsequent_ids_q becomes empty, pop this object
     * Remember to call this after receiving response.
     */
    migratoryObject.updateState();
    bool completeAllTxnsForthisObj = migratoryObject.allSharersFinished();
    if (completeAllTxnsForthisObj) {
        migratoryPendRequests.pop();
    }
}

void
MigratoryMemTest::noRequest()
{
    // assert(!isIdle);
    // if (isProducer) {
    //     if (numWriteTxnGenerated < maxLoads) {
    //         panic("%s did not send a request for %d cycles", name(), progressCheck);
    //     }
    // } else {
    //     if (numReadTxnGenerated < maxLoads) {
    //         panic("%s did not send a request for %d cycles", name(), progressCheck);
    //     }
    // }
    panic("%s did not send a request for %d cycles", name(), progressCheck);
}

void
MigratoryMemTest::noResponse()
{
    // assert(!isIdle);
    panic("%s did not see a response for %d cycles", name(), progressCheck);
}

void
MigratoryMemTest::recvRetry()
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
