/*
 * Copyright (c) 2023 StarFive Limited
 * All rights reserved.
 */

#ifndef __MEM_RUBY_STRUCTURES_SNOOPFILTER_HH__
#define __MEM_RUBY_STRUCTURES_SNOOPFILTER_HH__

#include <unordered_map>
#include <iterator>
#include <cstdlib>
#include <stack>
#include <set>

#include "base/statistics.hh"
#include "base/compiler.hh"
#include "mem/ruby/common/Address.hh"
#include "mem/ruby/protocol/AccessPermission.hh"
#include "mem/ruby/slicc_interface/AbstractCacheEntry.hh"
#include "debug/RubyCHIDebugStr5.hh"
#include "sim/sim_object.hh"
#include "params/RubySnoopFilter.hh"

namespace gem5
{

namespace ruby
{


struct SnoopFilterLineEntry {
    AbstractCacheEntry* m_entry;
    uint64_t m_way_id;
    SnoopFilterLineEntry() : m_entry(nullptr), m_way_id(0) {}
};


class SnoopFilter : public SimObject {
  public:
    typedef RubySnoopFilterParams Params;

    SnoopFilter(const Params &p);

    ~SnoopFilter();

    // tests to see if an address is present in the cache
    bool isTagPresent(Addr address) const;

    // Returns true if there is:
    //   a) a tag match on this address or there is
    //   b) an Invalid line in the same cache "way"
    bool cacheAvail(Addr address) const;

    /**
     * Allocate a way to an address.
     * Must fail if no ways are avail
     * for allocation. Its the client
     * (CCU's) responsibility 
     * to ensure that there are 
     * free ways available 
     * if m_allow_infinite_entries is false.
     */
    AbstractCacheEntry* allocate(Addr address, AbstractCacheEntry *entry);

    void deallocate(Addr address);

    void setWayBusy(Addr addr);

    void resetWayBusy(Addr addr);

    /**
     * The client (CCU) must test this
     * condition before proceeding with
     * SFRepl. 
     */
    bool allWaysBusy(Addr addr) const;

    /**
     * Returns with the physical address of the 
     * conflicting cache line. Will fail if
     * 1. There are free ways available
     * 2. All ways are busy
     */ 
    Addr cacheProbe(Addr newAddress) const;

    int size() const;

    // looks an address up in the cache
    AbstractCacheEntry* lookup(Addr address);

    const AbstractCacheEntry* lookup(Addr address) const;

    void profileMiss();

    void profileHit();

    void profileAlloc();

  private:
    // Private copy constructor and assignment operator
    SnoopFilter(const SnoopFilter& obj);

    SnoopFilter& operator=(const SnoopFilter& obj);

    /** 
     * Cache Structure. This also includes
     * busy entries that might be 
     * undergoing SFRepl
     */ 
    std::vector<std::unordered_map<Addr,SnoopFilterLineEntry>> m_cache;

    /**
     * Ways that are busy (transient). 
     * Currently undergoing SFRepl for the mapped address
     * They are not avail for allocation.
     * [Arka]: Should lookup fail for these ways  
     */
    std::vector<std::unordered_map<uint64_t,Addr>> m_busy_ways;

    /**
     * Ways that are available for allocation.
     * These ways must not undergo SFRepl.
     */ 
    std::vector<std::set<uint64_t>> m_avail_ways;

    int m_assoc;
    int m_num_sets;
    int m_num_entries;
    int m_num_set_bits;
    int m_start_index_bit;
    bool m_allow_infinite_entries;

    int64_t addressToCacheSet(Addr address) const;

    // Count the Number of SnoopFilter evictions
    struct SnoopFilterStats : public statistics::Group {
      SnoopFilterStats(statistics::Group *parent) : statistics::Group(parent),
       ADD_STAT(m_snoopfilter_misses, "Number of SnoopFilter misses"),
       ADD_STAT(m_snoopfilter_hits, "Number of SnoopFilter hits"),
       ADD_STAT(m_snoopfilter_alloc,"Number of SnoopFilter alloc"),
       ADD_STAT(m_snoopfilter_accesses, "Number of SnoopFilter accesses", m_snoopfilter_hits+m_snoopfilter_alloc) {}
      
      statistics::Scalar m_snoopfilter_misses;
      statistics::Scalar m_snoopfilter_hits;
      statistics::Scalar m_snoopfilter_alloc;
      statistics::Formula m_snoopfilter_accesses;

    } snoopFilterStats;
};

} // namespace ruby
} // namespace gem5

#endif // __MEM_RUBY_STRUCTURES_SNOOPFILTER_HH__