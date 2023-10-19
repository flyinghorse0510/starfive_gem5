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

#include "base/statistics.hh"
#include "mem/port.hh"
#include "params/DirectedMemTest.hh"
#include "sim/clocked_object.hh"
#include "sim/eventq.hh"
#include "sim/stats.hh"
#include "cpu/testers/memtest/common.hh"

#ifdef DIRECTED_MEM_TIMING
#define MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE (14)
#else
#define MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE (6)
#endif

namespace gem5
{

typedef uint16_t writeSyncData_t;


// # 256-Bits Alignment
// #
// # Low <===================== 128 bits (Little Endian) =====================> High
// # |<-------- 64 bits -------->|<- 8 bits ->|<- 8 bits ->|<------ 48 bits ------>|
// #         Address(paddr)        Memcmd(42)    BlockSize   ExtraData(6 x uint8_t)
// #            uint64_t            uint8_t       uint8_t          uint8_t[6]
// # |<------------- 64 bits ------------->|<------------- 64 bits ------------->|
// # 		 ExtraData(8 x uint8_t)					  Global Timestamp
// # 			   uint8_t[8]							  uint64_t
// # vvvvvvvvvvvvvvvvvvvvvvv
struct DirectedMemTestEntry {
    uint64_t paddr;
	uint8_t memCmd;
	uint8_t blkSize;
	uint8_t data[MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE];
	#ifdef DIRECTED_MEM_TIMING
	uint64_t timeCount;
	#endif
};
// # ^^^^^^^^^^^^^^^^^^^^^^^

/**
 * The Seq2MemTest class tests a cache coherent memory system.
 * 1. All requests issued by the Seq2MemTest instance are a
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
class DirectedMemTest : public ClockedObject
{

	public:

		typedef DirectedMemTestParams Params;
		DirectedMemTest(const Params &p);


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
			DirectedMemTest &directedmemtest;

			public:

				CpuPort(const std::string &_name, DirectedMemTest &_memtest)
					: RequestPort(_name, &_memtest), directedmemtest(_memtest)
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

		unsigned int id;

		writeSyncData_t writeSyncDataBase;

		std::unordered_set<Addr> outstandingAddrs;

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

		const unsigned progressInterval;  // frequency of progress reports
		const Cycles progressCheck;
		Tick nextProgressMessage;   // access # for next progress report


		Addr baseAddr;
		
		uint64_t num_peers;
		
		uint64_t numPerCPUWorkingBlocks;
		
		// std::vector<Addr> perCPUWorkingBlocks;

		std::unordered_map<Addr,unsigned> addrIterMap;
		
		bool addrInterleavedOrTiled;

		uint64_t numReadsGenerated;

		uint64_t numReadsCompleted;
		
		uint64_t numWritesGenerated;
		
		uint64_t numWritesCompleted;
		
		uint64_t maxLoads;

		uint64_t maxOutstandingReq;

		bool all_txns_complete;

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
	
	// Directed MemTest Part
	protected:
		const DirectedMemTestEntry* directedMemTestEntryPtr;
		const DirectedMemTestEntry* directedMemTestTableBasePtr;

		std::string memTestFileDir;

		const DirectedMemTestEntry* getMemTestDataTable(unsigned int id);

		const DirectedMemTestEntry* mmapMemTestTable(std::string& path);

		Addr getMemTestReqAddr(const DirectedMemTestEntry* entry);

		MemCmd::Command getMemTestReqCmd(const DirectedMemTestEntry* entry);

		unsigned getMemTestReqBlkSize(const DirectedMemTestEntry* entry);

		template<class T> bool fillMemTestReqData(const DirectedMemTestEntry* entry, T *reqData);

		const DirectedMemTestEntry* getNextMemTestEntryPtr(bool randomizeAcc = false);

		PacketPtr constructTestPacket(const DirectedMemTestEntry* entry, RequestPtr req);



};

} // namespace gem5

#endif // __CPU_MEMTEST_MEMTEST_HH__

