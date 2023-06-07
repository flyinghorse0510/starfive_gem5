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

#include <mem/ruby/structures/TBEStorage.hh>

namespace gem5
{

namespace ruby
{

// m_start_index_bit is set to default value of 6 assuming a block size of 64Bytes
TBEStorage::TBEStorage(statistics::Group *parent, std::string tbeDesc, int number_of_TBEs)
    : m_reserved(0), m_stats(parent, tbeDesc), m_block_on_set(false),
      m_start_index_bit(6),
      m_num_set_bits(3)
{
    for (int i = 0; i < number_of_TBEs; ++i)
        m_slots_avail.push(i);
}

TBEStorage::TBEStorage(statistics::Group *parent, int number_of_TBEs)
    : m_reserved(0), m_stats(parent), m_block_on_set(false),
      m_start_index_bit(6),
      m_num_set_bits(3)
{
    for (int i = 0; i < number_of_TBEs; ++i)
        m_slots_avail.push(i);
}

TBEStorage::TBEStorage(statistics::Group *parent, std::string tbeDesc, int number_of_TBEs, bool block_on_set)
    : m_reserved(0), m_stats(parent, tbeDesc), m_block_on_set(block_on_set), 
      m_start_index_bit(6),
      m_num_set_bits(3)
{
    for (int i = 0; i < number_of_TBEs; ++i)
        m_slots_avail.push(i);
}

TBEStorage::TBEStorage(statistics::Group *parent, \
                       std::string tbeDesc, \
                       int number_of_TBEs, \
                       bool block_on_set, \
                       int start_index_bit, \
                       int num_set_bits)
    : m_reserved(0), 
      m_stats(parent, tbeDesc), 
      m_block_on_set(block_on_set),
      m_start_index_bit(start_index_bit),
      m_num_set_bits(num_set_bits)
{
    for (int i = 0; i < number_of_TBEs; ++i)
        m_slots_avail.push(i);
}

TBEStorage::TBEStorageStats::TBEStorageStats(statistics::Group *parent, std::string tbeDesc)
    : statistics::Group(parent),
      ADD_STAT(avg_size, std::string("TBE "+tbeDesc+" Occupancy").c_str()),
      ADD_STAT(avg_util, std::string("TBE "+tbeDesc+" Utilization").c_str()),
      ADD_STAT(avg_reserved, std::string("TBE "+tbeDesc+" Reserved").c_str())
{
}

TBEStorage::TBEStorageStats::TBEStorageStats(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(avg_size, "Avg. number of slots allocated"),
      ADD_STAT(avg_util, "Avg. utilization"),
      ADD_STAT(avg_reserved, "Avg. number of slots reserved")
{
}

void TBEStorage::addReserveSlot(Addr addr) {
    if(m_block_on_set) {
        auto cacheSet = addressToCacheSet(addr);
        if (m_slots_reserved_by_set.count(cacheSet) > 0) {
            m_slots_reserved_by_set[cacheSet]++;
        } else {
            m_slots_reserved_by_set[cacheSet] = 1;
        }
    }
    incrementReserved();
}

void TBEStorage::removeReserveSlot(Addr addr) {
    if(m_block_on_set) {
        auto cacheSet = addressToCacheSet(addr);
        assert(m_slots_reserved_by_set.count(cacheSet) > 0);
        m_slots_reserved_by_set[cacheSet]--;
        if (m_slots_reserved_by_set[cacheSet] == 0) {
            m_slots_reserved_by_set.erase(cacheSet);
        }
    }
    decrementReserved();
}

int TBEStorage::getTopSlot() const {
    assert(m_slots_avail.size() > 0);
    return m_slots_avail.top();
}

int TBEStorage::getReserveSlot(Addr addr) const  {
    auto cacheSet = addressToCacheSet(addr);
    if (m_slots_reserved_by_set.count(cacheSet) > 0) {
        return m_slots_reserved_by_set.at(cacheSet);
    } else {
        return -1;
    }
}

int TBEStorage::getAllocSlot(Addr addr) const {
    auto cacheSet = addressToCacheSet(addr);
    if (m_slots_bocked_by_set.count(cacheSet) > 0) {
        return m_slots_bocked_by_set.at(cacheSet);
    } else {
        return -1;
    }
}

Addr TBEStorage::getOccupySlotAddr(int slot) const {
    if (m_slots_occupied_by_addr.count(slot) > 0) {
        return m_slots_occupied_by_addr.at(slot);
    } else {
        return 0xffffffffffffffff;
    }
}

} // namespace ruby
} // namespace gem5
