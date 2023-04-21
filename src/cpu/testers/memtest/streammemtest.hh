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
#include <list>
#include "base/trace.hh"
#include "debug/StreamDBG.hh"
#include "base/statistics.hh"
#include "mem/port.hh"
#include "params/StreamMemTest.hh"
#include "sim/clocked_object.hh"
#include "sim/eventq.hh"
#include "sim/stats.hh"
#include "cpu/testers/memtest/common.hh"

namespace gem5
{


/**
 * TODO: update the comment here
 * The StreamMemTest class tests a cache coherent memory system.
 * 1. All requests issued by the StreamMemTest instance are a
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

enum class STState {INIT, WAIT_B, WAIT_C, PREP, SENT, CMPL};
enum class LDState {INIT, PREP, SENT, CMPL};

class STMReq {
public:
  uint64_t iter;
  double val;
  Addr addr;
  STMReq(uint64_t iter, double val, Addr addr):iter(iter), val(val), addr(addr) {}
  virtual ~STMReq(){}
};

class STReq: public STMReq{
public:
  double b;
  double c;
  Addr addr_b;
  Addr addr_c;
  uint64_t wsSize;
  STState state;

  void wakeup(Addr addr, double data){
    DPRINTF(StreamDBG, "In ST[%lu].wakeup: state:%d, addr:%lu, data:%f\n", iter, int(state), addr, data);
    if(addr>=addr_b && addr<addr_b+wsSize)
    {
      b = data;
      switch(state){
        case STState::INIT : state = STState::WAIT_C; break;
        case STState::WAIT_B : state = STState::PREP; break;
        default: 
          panic("STReq[%lu](addr:%lu) woke up by LD B in state %d\n", iter, this->addr, int(state));
      }
    }
    else if(addr>=addr_c && addr<addr_c+wsSize)
    {
      c = data;
      switch(state){
        case STState::INIT : state = STState::WAIT_B; break;
        case STState::WAIT_C : state = STState::PREP; break;
        default: 
          panic("STReq[%lu](addr:%#lx) woke up by in state %d\n", iter, this->addr, int(state));
      }
    }
    else
    {
      panic("STReq[%lu](addr:%#lx) recv wired addr %#lx\n", iter, this->addr, addr);
    }
    // TODO: here prepare to send out st req
    if(state == STState::PREP){
      val = b + c*1.0;
      DPRINTF(StreamDBG, "In ST[%lu].wakeup: PREP to send, val:%f\n", iter, val);
    }
  }

  STReq(uint64_t iter, double val, Addr addr, Addr addr_b, Addr addr_c, uint64_t wsSize, STState state)
      :STMReq(iter, val, addr), state(state), b(0), c(0), addr_b(addr_b), addr_c(addr_c), wsSize(wsSize)
  {
    DPRINTF(StreamDBG, "STReq[%lu](%p) ctor, val:%f, addr:%#lx, state:%d\n", iter, this, val, addr, int(state));
  }
};

class LDReq : public STMReq {
public:
    LDState state;
    STReq* streq; // observer
    
    void wakeupST(double data){
      streq->wakeup(addr, data);
    }
    
    LDReq(uint64_t iter, double val, Addr addr, LDState state, STReq* streq)
        :STMReq(iter, val, addr), state(state), streq(streq)
    {
      DPRINTF(StreamDBG, "LDReq[%lu](%p) ctor, val:%f, addr:%#lx, state:%d, streq:%p\n", iter, this, val, addr, int(state), streq);
    }
};

enum class ArbiPolicy {RoundRobin=0, StoreFirst};


class StreamMemTest : public ClockedObject
{

  public:

    typedef StreamMemTestParams Params;
    StreamMemTest(const Params &p);


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
        StreamMemTest &streammemtest;

      public:

        CpuPort(const std::string &_name, StreamMemTest &_memtest)
            : RequestPort(_name, &_memtest), streammemtest(_memtest)
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

    const uint64_t maxOutstanding;

    const unsigned progressInterval;  // frequency of progress reports
    const Cycles progressCheck;
    Tick nextProgressMessage;   // access # for next progress report


    /**
     * data structures related to stream test
    */
  public:
    const uint64_t wsSize;
    const Addr a,b,c; // address for stream arr
    const double scale;
    const uint32_t id;
    const uint32_t numCpus;
    const uint32_t blockSize;
    const Addr blockAddrMask;
    const uint64_t maxLoads;
    uint64_t maxIters;
    uint64_t numIters;

    ArbiPolicy arbiPolicy;
    std::unordered_map<Addr, std::list<STReq*>::iterator> outstandingSTAddrs;
    std::unordered_map<Addr, std::list<LDReq*>::iterator> outstandingLDAddrs;

    std::list<LDReq*> LDList; // list for LD reqs
    std::list<STReq*> STList; // list for ST reqs

    uint64_t numReads;
    uint64_t numWrites;

    uint64_t txSeqNum; // requestorID + txSeqNum should be the unique ID

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
