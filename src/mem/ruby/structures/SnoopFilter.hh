/*
 * Copyright (c) 2019 ARM Limited
 * All rights reserved.
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
 * Copyright (c) 1999-2008 Mark D. Hill and David A. Wood
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

#ifndef __MEM_RUBY_STRUCTURES_SNOOPFILTER_HH__
#define __MEM_RUBY_STRUCTURES_SNOOPFILTER_HH__

#include <unordered_map>
#include <iterator>
#include <cstdlib>

#include "base/compiler.hh"
#include "mem/ruby/common/Address.hh"
#include "mem/ruby/protocol/AccessPermission.hh"

namespace gem5
{

namespace ruby
{

template<class ENTRY>
struct SnoopFilterLineState
{
    SnoopFilterLineState() { m_permission = AccessPermission_NUM; }
    AccessPermission m_permission;
    ENTRY m_entry;
};

template<class ENTRY>
inline std::ostream&
operator<<(std::ostream& out, const SnoopFilterLineState<ENTRY>& obj)
{
    return out;
}

template<class ENTRY>
class SnoopFilter
{
  public:
    SnoopFilter(statistics::Group *parent);

    SnoopFilter(unsigned num_entries,\
                unsigned assoc,\
                bool allow_infinite_entries, \
                statistics::Group *parent);

    // tests to see if an address is present in the cache
    bool isTagPresent(Addr address) const;

    // Returns true if there is:
    //   a) a tag match on this address or there is
    //   b) an Invalid line in the same cache "way"
    bool cacheAvail(Addr address) const;

    // find an Invalid entry and sets the tag appropriate for the address
    void allocate(Addr address);

    void deallocate(Addr address);

    // Returns with the physical address of the conflicting cache line
    Addr cacheProbe(Addr newAddress) const;

    int size() const;

    // looks an address up in the cache
    ENTRY* lookup(Addr address);
    const ENTRY* lookup(Addr address) const;

    // Get/Set permission of cache block
    AccessPermission getPermission(Addr address) const;
    void changePermission(Addr address, AccessPermission new_perm);

    // Print cache contents
    void print(std::ostream& out) const;

    void profileMiss();
    void profileHit();

    int getCacheSet(Addr address) const;

  private:
    // Private copy constructor and assignment operator
    SnoopFilter(const SnoopFilter& obj);
    SnoopFilter& operator=(const SnoopFilter& obj);

    // Data Members (m_prefix)
    std::vector<std::unordered_map<Addr,SnoopFilterLineState<ENTRY>>> m_cache;

    int m_assoc;
    int m_num_sets;
    int m_num_entries;
    int m_num_set_bits;
    int m_start_index_bit;
    bool m_allow_infinite_entries;
    int64_t addressToCacheSet(Addr address) const;

    // Count the Number of SnoopFilter evictions
    struct SnoopFilterStats : public statistics::Group
    {
      SnoopFilterStats(statistics::Group *parent) : statistics::Group(parent),
       ADD_STAT(m_snoopfilter_misses, "Number of SnoopFilter misses"),
       ADD_STAT(m_snoopfilter_hits, "Number of SnoopFilter hits"),
       ADD_STAT(m_snoopfilter_accesses, "Number of SnoopFilter accesses", m_snoopfilter_hits+m_snoopfilter_misses) {}
      
      statistics::Scalar m_snoopfilter_misses;
      statistics::Scalar m_snoopfilter_hits;
      statistics::Formula m_snoopfilter_accesses;

    } snoopFilterStats;
};

template<class ENTRY>
void SnoopFilter<ENTRY>::profileMiss() {
  snoopFilterStats.m_snoopfilter_misses++;
}

template<class ENTRY>
void SnoopFilter<ENTRY>::profileHit() {
  snoopFilterStats.m_snoopfilter_hits++;
}

template<class ENTRY>
inline int SnoopFilter<ENTRY>::size() const {
    return m_num_entries;
}

template<class ENTRY>
inline std::ostream&
operator<<(std::ostream& out, const SnoopFilter<ENTRY>& obj)
{
    obj.print(out);
    out << std::flush;
    return out;
}


template<class ENTRY>
inline SnoopFilter<ENTRY>::SnoopFilter(statistics::Group *parent) : 
    m_num_entries(0),
    m_num_sets(0),
    m_assoc(0),
    m_allow_infinite_entries(false),
    m_start_index_bit(6),
    snoopFilterStats(parent) {
  m_cache.clear();
}


template<class ENTRY>
inline SnoopFilter<ENTRY>::SnoopFilter(unsigned num_entries,\
                unsigned assoc,\
                bool allow_infinite_entries, \
                statistics::Group *parent) :
    m_num_entries(num_entries),
    m_assoc(assoc),
    m_allow_infinite_entries(allow_infinite_entries),
    m_start_index_bit(6),
    snoopFilterStats(parent) {
    
    assert(m_num_entries%m_assoc==0);
    m_num_sets=m_num_entries/m_assoc;
    for (unsigned i = 0; i < m_num_sets; i++) {
      m_cache.push_back(std::unordered_map<Addr,SnoopFilterLineState<ENTRY>>());
    }
    m_num_set_bits=floorLog2(m_num_sets);
    assert(m_num_set_bits > 0);
}

// tests to see if an address is present in the cache
template<class ENTRY>
inline bool SnoopFilter<ENTRY>::isTagPresent(Addr address) const {
    assert(address == makeLineAddress(address));
    int64_t cacheSet = addressToCacheSet(address);
    auto &set = m_cache.at(cacheSet);
    if (set.find(address) != set.end()) {
      return true;
    }
    return false;
}

template<class ENTRY>
inline bool SnoopFilter<ENTRY>::cacheAvail(Addr address) const {
  assert(address == makeLineAddress(address));
  int64_t cacheSet = addressToCacheSet(address);
  auto &set = m_cache.at(cacheSet);
  if (set.find(address) != set.end()) {
    return true; // Line already present
  } else if (set.size() < m_assoc) {
    return true; // Line can be allocated. There is space
  } else if (m_allow_infinite_entries) {
    return true; // Line can always be allocated. There no space constraints, but unrealistic
  }
  return false;
}

// find an Invalid or already allocated entry and sets the tag
// appropriate for the address
template<class ENTRY>
inline void SnoopFilter<ENTRY>::allocate(Addr address) {
    assert(address == makeLineAddress(address));
    assert(!isTagPresent(address));
    assert(cacheAvail(address));
    // Create an empty entry in Directory
    SnoopFilterLineState<ENTRY> line_state;
    line_state.m_permission = AccessPermission_Invalid;
    line_state.m_entry = ENTRY();
    int64_t cacheSet = addressToCacheSet(address);
    auto &set = m_cache.at(cacheSet);
    if (!m_allow_infinite_entries && (set.size() >= m_assoc)) {
      panic("SnoopFilter cannot find an entry to allocate");
    }
    set[address]=line_state;
}

// deallocate entry
template<class ENTRY>
inline void SnoopFilter<ENTRY>::deallocate(Addr address) {
    assert(address == makeLineAddress(address));
    assert(isTagPresent(address));
    int64_t cacheSet = addressToCacheSet(address);
    auto &set = m_cache.at(cacheSet);
    [[maybe_unused]] auto num_erased = set.erase(address);
    assert(num_erased == 1);
}

template<class ENTRY>
int SnoopFilter<ENTRY>::getCacheSet(Addr address) const {
  return addressToCacheSet(address);
}

static inline int get_rand_between(int min, int max) {
    return rand()%(max-min + 1) + min;
}

// Returns with the physical address of the conflicting cache line
template<class ENTRY>
inline Addr SnoopFilter<ENTRY>::cacheProbe(Addr newAddress) const {
    int64_t cacheSet = addressToCacheSet(newAddress);
    auto &set = m_cache.at(cacheSet);
    assert(m_assoc==set.size());
    auto random_it = std::next(std::begin(set), get_rand_between(0,set.size()-1));
    return makeLineAddress(random_it->first);
}

// looks an address up in the cache
template<class ENTRY>
inline ENTRY* SnoopFilter<ENTRY>::lookup(Addr address) {
  assert(address == makeLineAddress(address));
  int64_t cacheSet = addressToCacheSet(address);
  auto &set = m_cache.at(cacheSet);
  assert(set.find(address) != set.end());
  return &set[makeLineAddress(address)].m_entry;
}

// looks an address up in the cache
template<class ENTRY>
inline const ENTRY* SnoopFilter<ENTRY>::lookup(Addr address) const {
  assert(address == makeLineAddress(address));
  int64_t cacheSet = addressToCacheSet(address);
  auto &set = m_cache.at(cacheSet);
  assert(set.find(address) != set.end());
  return &set[makeLineAddress(address)].m_entry;
}

// convert a Address to its location in the cache
template<class ENTRY>
int64_t SnoopFilter<ENTRY>::addressToCacheSet(Addr address) const {
    assert(address == makeLineAddress(address));
    return bitSelect(address, m_start_index_bit,
                     m_start_index_bit + m_num_set_bits - 1);
}


template<class ENTRY>
inline AccessPermission
SnoopFilter<ENTRY>::getPermission(Addr address) const {
    assert(address == makeLineAddress(address));
    int64_t cacheSet = addressToCacheSet(address);
    auto &set = m_cache.at(cacheSet);
    assert(set.find(address) != set.end());
    return set[makeLineAddress(address)].m_permission;
}

template<class ENTRY>
inline void
SnoopFilter<ENTRY>::print(std::ostream& out) const
{
}

} // namespace ruby
} // namespace gem5

#endif // __MEM_RUBY_STRUCTURES_SNOOPFILTER_HH__