#ifndef __CPU_COMMON_MEMTEST_HH__
#define __CPU_COMMON_MEMTEST_HH__

#include <unordered_map>
#include <unordered_set>

#include "base/statistics.hh"
#include "mem/port.hh"
#include "sim/clocked_object.hh"
#include "sim/eventq.hh"
#include "sim/stats.hh"

namespace gem5
{

struct MemTestTxnAttr_t {
  Tick reqStartTime;
  uint64_t reqId;             /* Request Ordering. Also serves as the TxnId */
  uint64_t respId;            /* Response Ordering */
  Addr pAddr;                 /* physical (byte) address */
  std::string readOrWrite;
};

}
#endif /* __CPU_COMMON_MEMTEST_HH__*/