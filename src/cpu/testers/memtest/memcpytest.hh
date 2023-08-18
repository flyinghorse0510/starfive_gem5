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

#ifndef __CPU_MEMTEST_MEMTEST_HH__
#define __CPU_MEMTEST_MEMTEST_HH__

#include <unordered_map>
#include <unordered_set>
#include <sstream>
#include <queue>

#include "base/statistics.hh"
#include "mem/port.hh"
#include "params/MemCpyTest.hh"
#include "sim/clocked_object.hh"
#include "sim/eventq.hh"
#include "sim/stats.hh"
#include "cpu/testers/memtest/common.hh"

namespace gem5
{


enum MemCpyAddrState {
  // WRITE_RESP_RECVD is also free, as we can re-issue a fresh request
  FREE,
  READ_ISSUED,
  READ_RESP_RECVD,
  WRITE_ISSUED
};

class MemCpyAddr_t {
  public:
    MemCpyAddr_t(Addr _addr, MemCpyAddrState _state)
        : addr(_addr), state(_state)
    { }
    Addr getAddr() const { return addr; }
    bool isFree() const { return state == FREE; }
    MemCpyAddrState getState() const { return state; }
    void setState(MemCpyAddrState _state) { state = _state; }
    std::string getStr() const {
        std::stringstream ss;
        ss << "Addr: 0x" << std::hex << addr << " State: ";
        switch (state) {
            case FREE:
                ss << "FREE";
                break;
            case READ_ISSUED:
                ss << "READ_ISSUED";
                break;
            case READ_RESP_RECVD:
                ss << "READ_RESP_RECVD";
                break;
            case WRITE_ISSUED:
                ss << "WRITE_ISSUED";
                break;
        }
        return ss.str();
    }

  private:
    Addr addr;
    MemCpyAddrState state;
};

typedef uint16_t writeSyncData_t;

/**
 * The MemCpyTest class tests a cache coherent memory system.
 * 1. All requests issued by the MemCpyTest instance are a
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
class MemCpyTest : public ClockedObject
{

  public:

    typedef MemCpyTestParams Params;
    MemCpyTest(const Params &p);


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
        MemCpyTest &seqmemtest;

      public:

        CpuPort(const std::string &_name, MemCpyTest &_memtest)
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

    bool waitResponse;

    const Cycles interval;

    /** Request id for all generated traffic */
    RequestorID requestorId;

    unsigned int id;

    const uint64_t workingSet; // Working Set in bytes

    uint64_t workingSetSize; // Number of unique cache lines in thw Working set

    writeSyncData_t writeSyncDataBase;

    std::unordered_set<Addr> outstandingAddrs;

    // store the expected value for the addresses we have touched
    std::unordered_map<Addr, writeSyncData_t> referenceData;

    const unsigned blockSize;

    const Addr blockAddrMask;

    const unsigned percentReads;

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

    const unsigned progressInterval;  // frequency of progress reports
    const Cycles progressCheck;
    Tick nextProgressMessage;   // access # for next progress report

    Addr readBaseAddr;

    Addr writeBaseAddr;
    
    uint64_t num_peers;
    
    uint64_t numPerCPUWorkingBlocks;
    
    std::queue<std::shared_ptr<MemCpyAddr_t>> freeAddrQueue;

    std::queue<std::shared_ptr<MemCpyAddr_t>> readRespRecvQueue;

    std::unordered_map<Addr,std::shared_ptr<MemCpyAddr_t>> transientAddrMap;

    std::unordered_map<Addr,unsigned> addrIterMap;

    // std::unordered_set<Addr> completedAddr;

    uint64_t numAddrTxnsGenerated;

    uint64_t numAddrTxnsCompleted;

    bool all_txns_complete;
    
    bool addrInterleavedOrTiled;

    uint64_t maxAccessFactor;

    uint64_t maxOutstandingReq;

    uint64_t txSeqNum; // requestorID + txSeqNum should be the unique ID

    uint64_t blockStrideBits;

    const bool randomizeAcc;

    const bool atomic;

    const bool suppressFuncErrors;
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

#endif // __CPU_MEMTEST_MEMTEST_HH__

