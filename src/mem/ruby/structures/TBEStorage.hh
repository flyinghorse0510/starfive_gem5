/*
 * Copyright (c) 2021 ARM Limited
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

#ifndef __MEM_RUBY_STRUCTURES_TBESTORAGE_HH__
#define __MEM_RUBY_STRUCTURES_TBESTORAGE_HH__

#include <cassert>
#include <stack>
#include <unordered_map>
#include <set>

#include <base/statistics.hh>
#include "mem/ruby/common/Address.hh"
#include "debug/RubyCHIDebugStr5.hh"
#include "base/trace.hh"

namespace gem5
{

namespace ruby
{

// The TBEStorage is used to track the resources consumed by the TBETable,
// i.e. the number of available TBE slots.
//
// TBEStorage resource tracking has two main differences from TBETable:
//
// 1) Allows slot reservation. This is useful to implement protocols that
// employ retry/credit messages instead of stall when the controller runs
// out of TBEs to accept new request.
//
// 2) Can also assign multiple entries to the same slot. This is useful to
// more easily model cases where multiple transactions share the same TBE
// resource (i.e. the slot).
// E.g: a request that triggers a replacement in a system without
// dedicated WB/Eviction buffer; both transactions can can have separate
// logical TBEs associated to the same slot.
//
// The motivation for having a separate structures for tracking TBEs
// availability are twofold:
//
// - Keeps TBETable simple and without the additional overhead for
// protocols that do not need these additional features.
//
// - Having two separate transactions sharing the same TBE resource using
// the current TBETable would be cumbersome since the TBETable is indexed
// by the transaction address.

class TBEStorage
{
  public:
    TBEStorage(statistics::Group *parent, int number_of_TBEs);

    TBEStorage(statistics::Group *parent, std::string tbeDesc, int number_of_TBEs);
    
    TBEStorage(statistics::Group *parent, std::string tbeDesc, int number_of_TBEs, bool block_on_set);

    // Returns the current number of slots allocated
    int size() const { return m_slots_used.size(); }

    // Returns the total capacity of this TBEStorage table
    int capacity() const { return m_slots_used.size() + m_slots_avail.size(); }

    // Returns number of slots currently reserved
    int reserved() const { return m_reserved; }

    // Returns the number of slots available
    int slotsAvailable() const;

    // Returns the TBEStorage utilization
    float utilization() const { return size() / (float)capacity(); }

    // Returns true if slotsAvailable() >= n; current_time is always ignored
    // This allows this class to be used with check_allocate in SLICC to
    // trigger resource stalls when there are no slots available
    bool areNSlotsAvailable(int n, Tick current_time = 0) const;

    // Increase/decrease the number of reserved slots. Having reserved slots
    // reduces the number of slots available for allocation
    void incrementReserved();
    void decrementReserved();

    // Assign a TBETable entry to a free slot and returns the slot number.
    // Notice we don't need any info from TBETable and just track the number
    // of entries assigned to each slot.
    // This funcion requires slotsAvailable() > 0
    int addEntryToNewSlot();

    // Assign an entry to an existing non-empty slot
    void addEntryToSlot(int slot);

    // Remove an entry from an existing non-empty slot. The slot becomes
    // available again when the number of assigned entries == 0
    void removeEntryFromSlot(int slot);

    // The following are used only when
    // block_on_set is set to true.
    // This is used to simulate the scenerios
    // when slots are allocated based on the
    // address sets. Different address with same
    // sets will conflict and not be allocated
    // simultaneously.
    // [Arka]: Note SLICC interface does not
    // support method overloading so the following
    // methods are suffixed with 2.
    bool areNSlotsAvailable2(Addr addr, int n, Tick current_time = 0) const;

    int addEntryToNewSlot2(Addr addr);

    void addEntryToSlot2(Addr addr, int slot);

    void removeEntryFromSlot2(Addr addr, int slot);

  private:
    int m_reserved;
    std::stack<int> m_slots_avail;
    std::unordered_map<int, int> m_slots_used;

    // The following are used only when
    // block_on_set is set to true.
    
    bool m_block_on_set;
    int m_num_set_bits;
    int m_start_index_bit;
    std::unordered_map<int64_t, int> m_slots_bocked_by_set; // set -> slot map
    int64_t addressToCacheSet(Addr address) const;

    struct TBEStorageStats : public statistics::Group
    {
        TBEStorageStats(statistics::Group *parent);
        TBEStorageStats(statistics::Group *parent, std::string tbeDesc);

        // Statistical variables
        statistics::Average avg_size;
        statistics::Average avg_util;
        statistics::Average avg_reserved;
    } m_stats;
};

// Returns the number of slots available
inline int 
TBEStorage::slotsAvailable() const { 
    return m_slots_avail.size() - m_reserved;
}

inline int64_t 
TBEStorage::addressToCacheSet(Addr address) const {
    assert(address == makeLineAddress(address));
    return bitSelect(address, m_start_index_bit, 
            m_start_index_bit + m_num_set_bits - 1);
}

inline bool
TBEStorage::areNSlotsAvailable(int n, Tick current_time) const
{
    assert(!m_block_on_set);
    return slotsAvailable() >= n;
}

inline bool 
TBEStorage::areNSlotsAvailable2(Addr addr, int n, Tick current_time) const {
    if (m_block_on_set) {
        auto cacheSet = addressToCacheSet(addr);
        if (m_slots_bocked_by_set.count(cacheSet) > 0) {
            // The set is already present
            DPRINTF(RubyCHIDebugStr5,"addr: %#x blocked on set %d\n",addr,cacheSet);
            return false;
        } else {
            return slotsAvailable() >= n;
        }
    } else {
        return slotsAvailable() >= n;
    }
}

inline void
TBEStorage::incrementReserved()
{
    ++m_reserved;
    m_stats.avg_reserved = m_reserved;
}

inline void
TBEStorage::decrementReserved()
{
    assert(m_reserved > 0);
    --m_reserved;
    m_stats.avg_reserved = m_reserved;
}

inline int
TBEStorage::addEntryToNewSlot()
{
    assert(!m_block_on_set); // Must be called only when MSHRs are not blocked on set
    assert(slotsAvailable() > 0);
    assert(m_slots_avail.size() > 0);
    int slot = m_slots_avail.top();
    m_slots_used[slot] = 1;
    m_slots_avail.pop();
    m_stats.avg_size = size();
    m_stats.avg_util = utilization();
    return slot;
}

inline int
TBEStorage::addEntryToNewSlot2(Addr addr) {
    auto cacheSet = addressToCacheSet(addr);
    assert(m_slots_bocked_by_set.count(cacheSet) <= 0);
    assert(slotsAvailable() > 0);
    assert(m_slots_avail.size() > 0);
    int slot = m_slots_avail.top();
    m_slots_used[slot] = 1;
    m_slots_avail.pop();
    if (m_block_on_set) {
        m_slots_bocked_by_set[cacheSet] = slot;
    }
    m_stats.avg_size = size();
    m_stats.avg_util = utilization();
    return slot;
}

inline void
TBEStorage::addEntryToSlot(int slot)
{
    auto iter = m_slots_used.find(slot);
    assert(iter != m_slots_used.end());
    iter->second += 1;
}

inline void
TBEStorage::addEntryToSlot2(Addr addr, int slot)
{
    addEntryToSlot(slot);
}

inline void
TBEStorage::removeEntryFromSlot(int slot)
{
    assert(!m_block_on_set);
    auto iter = m_slots_used.find(slot);
    assert(iter != m_slots_used.end());
    assert(iter->second > 0);
    iter->second -= 1;
    if (iter->second == 0) {
        m_slots_used.erase(iter);
        m_slots_avail.push(slot);
    }
    m_stats.avg_size = size();
    m_stats.avg_util = utilization();
}

inline void
TBEStorage::removeEntryFromSlot2(Addr addr, int slot)
{
    auto iter = m_slots_used.find(slot);
    assert(iter != m_slots_used.end());
    assert(iter->second > 0);
    iter->second -= 1;
    if (iter->second == 0) {
        m_slots_used.erase(iter);
        m_slots_avail.push(slot);
        if (m_block_on_set) {
            auto cacheSet = addressToCacheSet(addr);
            assert(m_slots_bocked_by_set.count(cacheSet) > 0);
            m_slots_bocked_by_set.erase(cacheSet);
        }
    }
    m_stats.avg_size = size();
    m_stats.avg_util = utilization();
}

} // namespace ruby
} // namespace gem5

#endif
