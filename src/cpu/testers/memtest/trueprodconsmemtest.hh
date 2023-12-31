/*
 * Copyright (c) 2015, 2021 Arm Limited
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

#ifndef __CPU_ISO_MEMTEST_HH__
#define __CPU_ISO_MEMTEST_HH__

#include <unordered_map>
#include <unordered_set>

#include "base/statistics.hh"
#include "mem/port.hh"
#include "params/TrueProdConsMemTest.hh"
#include "sim/clocked_object.hh"
#include "sim/eventq.hh"
#include "sim/stats.hh"
#include "cpu/testers/memtest/common.hh"

namespace gem5
{

typedef uint16_t writeSyncData_t;

/**
 * The TrueProdConsMemTest class tests a cache coherent memory system.
 * 1. All requests issued by the TrueProdConsMemTest instance are a
 *    single byte. 
 * 2. The addresses are generated sequentially and the same
 *    address is generated again, to remove the effects of cold
 *    misses.
 * 3. The address generation process is controlled to reason about
 *    the performance of cache coherent memory system.
 * In addition to verifying the data, the tester also has timeouts for
 * both requests and responses, thus checking that the memory-system
 * is making progress.
 */
class TrueProdConsMemTest : public ClockedObject
{

  public:

    typedef TrueProdConsMemTestParams Params;
    
    TrueProdConsMemTest(const Params &p);

    Port &getPort(const std::string &if_name,
                  PortID idx=InvalidPortID) override;

  protected:

    uint64_t seqIdx;
    void tick();

    EventFunctionWrapper tickEvent;

    void noRequest();

    EventFunctionWrapper noRequestEvent;

    void noResponse();

    EventFunctionWrapper noResponseEvent;

    class CpuPort : public RequestPort
    {
        TrueProdConsMemTest &seqmemtest;

      public:

        CpuPort(const std::string &_name, TrueProdConsMemTest &_memtest)
            : RequestPort(_name, &_memtest), seqmemtest(_memtest)
        { }

      protected:

        bool recvTimingResp(PacketPtr pkt);

        void recvTimingSnoopReq(PacketPtr pkt) { }

        void recvFunctionalSnoop(PacketPtr pkt) { }

        Tick recvAtomicSnoop(PacketPtr pkt) { return 0; }

        void recvReqRetry();
    };

    CpuPort port;

    PacketPtr retryPkt;

    const unsigned size;

    bool waitResponse;

    const Cycles interval;

    /** Request id for all generated traffic */
    RequestorID requestorId;

   

    std::unordered_set<uint64_t> outstandingAddrs;

    // store the expected value for the addresses we have touched
    std::unordered_map<Addr, writeSyncData_t> referenceData;

    const unsigned blockSize;

    const Addr blockAddrMask;

    /**
     * Get the block aligned address.
     *
     * @param addr Address to align
     * @return The block aligned address
     */
    Addr blockAlign(Addr addr) const
    {
        return (addr & ~blockAddrMask);
    }

    writeSyncData_t writeSyncDataBase;

    const uint64_t workingSet; // Working Set in bytes

    uint64_t numPerCPUWorkingBlocks;

    Addr baseAddr;
    
    std::vector<Addr> perCPUWorkingBlocks;

    bool addrInterleavedOrTiled;

    const unsigned progressInterval;  // frequency of progress reports
    
    const Cycles progressCheck;
    
    Tick nextProgressMessage;   // access # for next progress report

    uint64_t numReadTxnGenerated;

    uint64_t numReadTxnCompleted;

    uint64_t numWriteTxnGenerated;

    uint64_t numWriteTxnCompleted;

    const double maxLoadFactor;

    bool removeConsumedData;

    uint64_t maxLoads;
    
    uint64_t txSeqNum; // requestorID + txSeqNum should be the unique ID

    const bool atomic;

    const bool suppressFuncErrors;

    /*
     * These flags control the stimulus
     * generated by this MemTester
     * @benchmarkC2CBWMode : True
     * Then generate Producer-Consumer 
     * bandwidth benchmarks (i.e. large number
     * of outstanding transactions will be 
     * generated)
     * @benchmarkC2CBWMode : False
     * Then generate Cach-2-Cache Pingpong
     * stimulus to measure the single line
     * "transfer" latencies. The relative
     * placement of the producer consumers
     * become important.
     */
    bool benchmarkC2CBWMode;

    unsigned maxOutStandingTransactions;

    unsigned id; // my_id

    std::set<unsigned> id_producers;

    std::set<unsigned> id_consumers;

    bool isProducer; // Does this MemTester generated write transactions

    bool isIdle;    // Do generate any transactions. An "active" Memtester can become idle if it has generated all the requests and received the corresponding response

    uint64_t num_cpus;

    uint64_t num_producers;

    uint64_t num_consumers;
  protected:
    struct MemTestStats : public statistics::Group
    {
        MemTestStats(statistics::Group *parent);
        statistics::Scalar numReads;
        statistics::Scalar numWrites;
    } stats;

    /**
     * Complete a request by checking the response.
     *
     * @param pkt Response packet
     * @param functional Whether the access was functional or not
     */
    void completeRequest(PacketPtr pkt, bool functional = false);

    bool sendPkt(PacketPtr pkt);

    void recvRetry();

};

} // namespace gem5

#endif // __CPU_ISO_MEMTEST_HH__

