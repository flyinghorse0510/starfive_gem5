

#include <unordered_map>
#include <cstdlib>
#include <stack>
#include <set>
#include <iterator> 
#include <algorithm>

#include "mem/ruby/structures/SnoopFilter.hh"
#include "base/compiler.hh"
#include "mem/ruby/common/Address.hh"
#include "mem/ruby/protocol/AccessPermission.hh"
#include "debug/RubyCHIDebugStr5.hh"

namespace gem5
{

namespace ruby
{

static inline int get_rand_between(int min, int max) {
  if (min == max) {
    return min;
  }
  return rand()%(max-min + 1) + min;
}


void SnoopFilter::profileMiss() {
  snoopFilterStats.m_snoopfilter_misses++;
}

void SnoopFilter::profileHit() {
  snoopFilterStats.m_snoopfilter_hits++;
}

void SnoopFilter::profileAlloc() {
  snoopFilterStats.m_snoopfilter_alloc++;
}

int SnoopFilter::size() const {
    return m_num_entries;
}

SnoopFilter::~SnoopFilter()
{
    for (int i = 0; i < m_num_sets; i++) {
        // Clear all set contents
        auto &set = m_cache[i];
        if (!set.empty()) {
            std::for_each(set.begin(), set.end(),
                            [](std::pair<Addr,SnoopFilterLineEntry> kv) {
                                auto &sf_entry = kv.second;
                                if (sf_entry.m_entry != nullptr) {
                                    delete sf_entry.m_entry ;
                                }
                            });
            set.clear();
        }
    }
    // Clear all the set
    m_cache.clear();
}

SnoopFilter::SnoopFilter(const Params &p) : SimObject(p),
    m_num_entries(p.size),
    m_assoc(p.assoc),
    m_allow_infinite_entries(p.allow_infinite_entries),
    m_start_index_bit(p.start_index_bit),
    snoopFilterStats(this) {
    
    assert(m_num_entries%m_assoc==0);
    m_num_sets=m_num_entries/m_assoc;
    for (unsigned i = 0; i < m_num_sets; i++) {
      m_cache.push_back(std::unordered_map<Addr,SnoopFilterLineEntry>());
      m_busy_ways.push_back(std::unordered_map<uint64_t,Addr>());
      std::set<uint64_t> avail_ways;
      for (uint64_t way_id=0; way_id < m_assoc; way_id++) {
        avail_ways.insert(way_id);
      }
      m_avail_ways.push_back(avail_ways);
    }
    m_num_set_bits=floorLog2(m_num_sets);
    assert(m_num_set_bits > 0);
}

// tests to see if an address is present in the cache
bool SnoopFilter::isTagPresent(Addr address) const {
    assert(address == makeLineAddress(address));
    int64_t cacheSet = addressToCacheSet(address);
    auto &set = m_cache.at(cacheSet);
    if (set.find(address) != set.end()) {
      return true;
    }
    return false;
}

bool SnoopFilter::cacheAvail(Addr address) const {
  assert(address == makeLineAddress(address));
  int64_t cacheSet = addressToCacheSet(address);
  auto &set = m_cache.at(cacheSet);
  auto &avail_ways = m_avail_ways.at(cacheSet);
  if (set.find(address) != set.end()) {
    return true; // Line already present
  } else if (!avail_ways.empty()) {
    return true; // Line can be allocated. There is space
  } else if (m_allow_infinite_entries) {
    return true; // Line can always be allocated. There no space constraints, but unrealistic
  }
  return false;
}

// find an Invalid or already allocated entry and sets the tag
// appropriate for the address
AbstractCacheEntry* SnoopFilter::allocate(Addr address, AbstractCacheEntry *entry) {
    assert(address == makeLineAddress(address));
    assert(!isTagPresent(address));
    assert(cacheAvail(address));
    int64_t cacheSet = addressToCacheSet(address);
    auto &set = m_cache.at(cacheSet);
    uint64_t way_id = set.size();
    
    // Manage entries if you have finite entries to track
    if (!m_allow_infinite_entries) {
      auto &avail_ways = m_avail_ways.at(cacheSet);
      assert(!avail_ways.empty());
      way_id = *(std::next(std::begin(avail_ways), get_rand_between(0,avail_ways.size()-1)));
      auto &busy_ways = m_busy_ways.at(cacheSet);
      assert(busy_ways.count(way_id) <= 0); // Alloc should not occur for a busy transaction
      avail_ways.erase(way_id);
    }

    // Create an empty entry in Directory
    SnoopFilterLineEntry sf_line;
    sf_line.m_entry = entry;
    sf_line.m_way_id = way_id;
    if (!m_allow_infinite_entries && (set.size() >= m_assoc)) {
      panic("SnoopFilter cannot find an entry to allocate");
    }
    set[address]=sf_line;
    return entry;
}

// deallocate entry
void SnoopFilter::deallocate(Addr address) {
    assert(address == makeLineAddress(address));
    assert(isTagPresent(address));
    int64_t cacheSet = addressToCacheSet(address);
    auto &set = m_cache.at(cacheSet);
    
    // Manage entries if you have finite entries to track
    if (!m_allow_infinite_entries) {
      auto &avail_ways = m_avail_ways.at(cacheSet);
      assert(avail_ways.size() <= m_assoc);
      auto way_id = set[address].m_way_id;
      auto &busy_ways = m_busy_ways.at(cacheSet);
      assert(busy_ways.count(way_id) <= 0); // Dealloc should not occur for a busy transaction
      avail_ways.insert(way_id);
    }

    // Delete the entry pointer
    AbstractCacheEntry* entry = set.at(address).m_entry;
    delete entry;

    // Delete from the cache structure
    [[maybe_unused]] auto num_erased = set.erase(address);
    assert(num_erased == 1);
}

void SnoopFilter::setWayBusy(Addr addr) {
  if (!m_allow_infinite_entries) {
    // addr is undergoing SFRepl
    int64_t cacheSet = addressToCacheSet(addr);
    auto &set = m_cache.at(cacheSet);
    auto &busy_ways = m_busy_ways.at(cacheSet);
    assert(set.count(addr) > 0); // Only an allocated address can undergo SFRepl
    auto &sf_line = set.at(addr);
    auto way_id = sf_line.m_way_id;
    busy_ways[way_id] = addr;

    // Remove it from the set of available ways
    auto &avail_ways = m_avail_ways.at(cacheSet);
    avail_ways.erase(way_id);
  } // else assertion failure ?
}

void SnoopFilter::resetWayBusy(Addr addr) {
  if (!m_allow_infinite_entries) {
    // addr is undergoing SFRepl
    int64_t cacheSet = addressToCacheSet(addr);
    auto &set = m_cache.at(cacheSet);
    auto &busy_ways = m_busy_ways.at(cacheSet);
    assert(set.count(addr) > 0); //Only an allocated address and undergo SFRepl
    auto &sf_line = set.at(addr);
    auto way_id = sf_line.m_way_id;
    busy_ways.erase(way_id);

    // Put it back to the set of available ways
    auto &avail_ways = m_avail_ways.at(cacheSet);
    avail_ways.insert(way_id);
  } // else assertion failure ?
}

bool SnoopFilter::allWaysBusy(Addr addr) const {
  int64_t cacheSet = addressToCacheSet(addr);
  auto &set = m_cache.at(cacheSet);
  auto &busy_ways = m_busy_ways.at(cacheSet);
  if (busy_ways.size() >= m_assoc) {
    return true;
  }
  return false;
}

/**
 * Returns with the physical address of the 
 * conflicting cache line. Will fail if
 * 1. There are free ways available
 * 2. All ways are busy
 */ 
Addr SnoopFilter::cacheProbe(Addr newAddress) const {
    int64_t cacheSet = addressToCacheSet(newAddress);
    auto &set = m_cache.at(cacheSet);
    auto &busy_ways = m_busy_ways.at(cacheSet);
    auto &avail_ways = m_avail_ways.at(cacheSet);
    assert(avail_ways.empty()); // This is only called when all ways are occupied
    assert(!allWaysBusy(newAddress));
    assert(set.size() == m_assoc);

    std::unordered_map<uint64_t, Addr> replaceable_ways_map;
    for (const auto &entry : set) {
      const auto &sf_line = entry.second;
      auto way_id = sf_line.m_way_id;
      if (busy_ways.count(way_id) <= 0) {
        // way_id is not busy
        replaceable_ways_map[way_id] = entry.first;
      }
    }
    assert(!replaceable_ways_map.empty());
    auto random_it = std::next(std::begin(replaceable_ways_map), get_rand_between(0,replaceable_ways_map.size()-1));
    return makeLineAddress(random_it->second);
}

// looks an address up in the cache
AbstractCacheEntry* SnoopFilter::lookup(Addr address) {
  assert(address == makeLineAddress(address));
  int64_t cacheSet = addressToCacheSet(address);
  auto &set = m_cache.at(cacheSet);
  if (set.find(address) == set.end()) {
    return NULL;
  }
//   assert(set.find(address) != set.end());
  return set.at(makeLineAddress(address)).m_entry;
}

// looks an address up in the cache
const AbstractCacheEntry* SnoopFilter::lookup(Addr address) const {
  assert(address == makeLineAddress(address));
  int64_t cacheSet = addressToCacheSet(address);
  auto &set = m_cache.at(cacheSet);
  if (set.find(address) == set.end()) {
    return NULL;
  }
//   assert(set.find(address) != set.end());
  return set.at(makeLineAddress(address)).m_entry;
}

// convert a Address to its location in the cache
int64_t SnoopFilter::addressToCacheSet(Addr address) const {
    assert(address == makeLineAddress(address));
    return bitSelect(address, m_start_index_bit,
                     m_start_index_bit + m_num_set_bits - 1);
}


}
}