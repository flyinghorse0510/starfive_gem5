arka.maity@sdc-01:~/Desktop/gem5_jh8100_starlink2.0$ ./cherryPickCHIFromPublic.sh
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp 70d855d783] mem-ruby: Fix handling of stale CleanUnique
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Tue Feb 8 17:34:52 2022 -0600
 4 files changed, 84 insertions(+), 44 deletions(-)
[devTmp 72a1118c7c] mem-ruby: CHI fix for WUs on local+upstream line
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Wed Sep 22 14:05:28 2021 +0100
 1 file changed, 11 insertions(+), 1 deletion(-)
Auto-merging src/mem/ruby/structures/SConscript
Auto-merging src/mem/ruby/slicc_interface/RubySlicc_Util.hh
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
Auto-merging src/mem/ruby/protocol/RubySlicc_Exports.sm
Auto-merging src/mem/ruby/SConscript
Auto-merging configs/topologies/CustomMesh.py
Auto-merging configs/ruby/CHI_config.py
Auto-merging configs/ruby/CHI.py
[devTmp 53c506a9b6] configs, mem-ruby: Implement DVMOps in CHI
 Author: Samuel Stark <samuel.stark2@arm.com>
 Date: Tue Apr 5 14:07:06 2022 +0100
 24 files changed, 3124 insertions(+), 79 deletions(-)
 create mode 100644 src/mem/ruby/protocol/chi/CHI-dvm-misc-node-actions.sm
 create mode 100644 src/mem/ruby/protocol/chi/CHI-dvm-misc-node-funcs.sm
 create mode 100644 src/mem/ruby/protocol/chi/CHI-dvm-misc-node-ports.sm
 create mode 100644 src/mem/ruby/protocol/chi/CHI-dvm-misc-node-transitions.sm
 create mode 100644 src/mem/ruby/protocol/chi/CHI-dvm-misc-node.sm
 create mode 100644 src/mem/ruby/structures/MN_TBEStorage.hh
 create mode 100644 src/mem/ruby/structures/MN_TBETable.cc
 create mode 100644 src/mem/ruby/structures/MN_TBETable.hh
[devTmp 4482bc33a6] arch-arm: Fixed ARM/gem5.fast compilation failures
 Author: Bobby R. Bruce <bbruce@ucdavis.edu>
 Date: Thu May 19 11:33:55 2022 -0700
 2 files changed, 4 insertions(+), 7 deletions(-)
[devTmp 3f3d655028] mem-ruby: add missing response for ReadOnce
 Author: Daecheol You <daecheol.you@samsung.com>
 Date: Mon Mar 14 13:57:04 2022 +0900
 1 file changed, 1 insertion(+), 1 deletion(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp b20da8df2a] mem-ruby: fix sharer update for stale WriteCleanFull
 Author: Daecheol You <daecheol.you@samsung.com>
 Date: Fri Mar 11 12:24:11 2022 +0900
 3 files changed, 17 insertions(+), 6 deletions(-)
[devTmp 25c4613324] mem-ruby: fix the condition for stale WriteCleanFull
 Author: Daecheol You <daecheol.you@samsung.com>
 Date: Fri Mar 11 12:55:34 2022 +0900
 1 file changed, 1 insertion(+), 1 deletion(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp 4a6fc0bb51] mem-ruby: fix CHI wrong response to ReadShared
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Tue Mar 1 18:48:43 2022 -0600
 1 file changed, 15 insertions(+), 22 deletions(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp f8dcc9b94c] mem-ruby: removed check for WriteCleanFull
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Tue Mar 1 19:03:59 2022 -0600
 1 file changed, 1 deletion(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp a7464ffb41] mem-ruby: fix state updates on WriteCleanFull
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Wed Mar 2 15:58:08 2022 -0600
 1 file changed, 9 insertions(+), 3 deletions(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp 43e96b0d20] mem-ruby: fix inconsistent WBs for dirty data
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Wed Mar 2 15:18:29 2022 -0600
 1 file changed, 8 insertions(+), 5 deletions(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp 8ec818ae17] mem-ruby: reuse existing event on CleanUnique
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Wed Mar 2 16:17:43 2022 -0600
 1 file changed, 9 insertions(+), 24 deletions(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp bee3660222] mem-ruby: fix MaintainCoherence typo
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Wed Mar 2 16:18:26 2022 -0600
 2 files changed, 3 insertions(+), 3 deletions(-)
[devTmp fcff539632] mem-ruby: fix functionalRead on pending CU
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Wed Mar 2 17:43:00 2022 -0600
 1 file changed, 10 insertions(+), 3 deletions(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp 41368f1d4b] mem-ruby: fix data state for partial WU
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Fri Apr 8 10:44:03 2022 -0500
 1 file changed, 6 insertions(+), 1 deletion(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp 647f21616d] mem-ruby: fix CHI snoops clearing WU data
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Mon May 16 17:50:18 2022 -0500
 1 file changed, 3 insertions(+), 10 deletions(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp 7f577f4650] mem-ruby: fix Evict request for CHI excl. caches
 Author: Tiago Mück <tiago.muck@arm.com>
 Date: Tue May 17 13:20:48 2022 -0500
 1 file changed, 25 insertions(+), 10 deletions(-)
Auto-merging src/mem/ruby/protocol/chi/CHI-cache-actions.sm
[devTmp 42ac65b325] mem-ruby: modify the TBE data state for ReadOnce_HitUpstream
 Author: Daecheol You <daecheol.you@samsung.com>
 Date: Fri Mar 11 13:23:59 2022 +0900
 1 file changed, 9 insertions(+)