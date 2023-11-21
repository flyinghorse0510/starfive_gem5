# Copyright (c) 2006-2007 The Regents of The University of Michigan
# Copyright (c) 2009 Advanced Micro Devices, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import m5
from m5.objects import *
from m5.defines import buildEnv
from m5.util import addToPath
import os, argparse, sys

addToPath('../')

from common import Options
from ruby import RubyD2D
import ast

# Get paths we might need.  It's expected this file is in m5/configs/example.
config_path = os.path.dirname(os.path.abspath(__file__))
config_root = os.path.dirname(config_path)

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
Options.addNoISAOptions(parser)

parser.add_argument('--maxloads', metavar='N', default=0,help='Stop after N loads')
parser.add_argument('--progress', type=int, default=1000,
                    metavar='NLOADS',
                    help='Progress message interval')
parser.add_argument('--num-dmas', type=int, default=0, help='# of dma testers')
parser.add_argument('--functional', type=int, default=0,
                    help='percentage of accesses that should be functional')
parser.add_argument('--suppress-func-errors', action='store_true',
                    help='suppress panic when functional accesses fail')
parser.add_argument('--mem-test-type',type=str,default='bw_test',help="The type of Memtest stimulus generator to use")
parser.add_argument('--size-ws',type=int,default=1024,help='Working set size in bytes. Must be a multiple of Cacheline size')
parser.add_argument('--enable-DMT', default=False, type=ast.literal_eval, help="enable DMT")
parser.add_argument('--enable-DCT', default=False, type=ast.literal_eval, help="enable DCT")
parser.add_argument('--allow-SD',default=True, type=ast.literal_eval, help="allow SD state") # True for MOESI, False for MESI
parser.add_argument('--num-HNF-TBE', type=int, default=16, help="number of oustanding in HN-F")
parser.add_argument('--ratio-repl-req-TBE', type=str, default='1-1', help="Ratio of req and repl TBE. Valid if --part-TBEs if True")
parser.add_argument('--part-TBEs',default=False,type=ast.literal_eval,help=f'Partition TBEs')
parser.add_argument('--num_trans_per_cycle_llc', default=4, help="number of transitions per cycle in HN-F")
parser.add_argument('--num-SNF-TBE', default=32, help="number of oustanding in HN-F")
parser.add_argument('--num-RNF-TBE', default=32, help="number of oustanding in RN-F")
parser.add_argument('--addr-intrlvd-or-tiled',default=False, type=ast.literal_eval, help="If true the address partitioning across CPUs is interleaved (like [0-N-2N;1-N+1-2N+1;...]). Otherwise Tiled [0:N-1,N:2N-1]")
parser.add_argument('--sequencer-outstanding-requests',type=int,default=32,help="Max outstanding sequencer requests")
parser.add_argument('--inj-interval',default=1,type=int,help="The interval between request packets")
parser.add_argument('--num-snoopfilter-entries', default=4, type=int,help="SnoopFilter: number of entries")
parser.add_argument('--num-snoopfilter-assoc', default=2, type=int,help="SnoopFilter: assoc")
"""
    The (--producers,--num-producers) are mutually exclusive argument specification 
    as are (--consumers,--num-consumers). --producers an --consumers specify the 
    location and the number of producers and consumers respectively. These are mainly
    used in pingpong latency benchmarks. While --num-producers and --num-consumers 
    specify the number of producers and consumer respectively w/o any location information.
    These are used in producer consumer style benchmarks. DO NOT specify both of them
    together. If you do the results are not well-defined
"""
parser.add_argument('--producers',type=str, default='0', help='semicolon separated list of producers')
parser.add_argument('--consumers',type=str, default='1', help='semicolon separated list of consumers')
parser.add_argument('--num-producers',type=int,default=-1,help='number of producers')
parser.add_argument('--num-consumers',type=int,default=-1,help='number of consumers')
parser.add_argument('--chs-1p1c',action='store_true',help='[Test 1] Run isolated 1p 1c coherence sharing benchmarks')
parser.add_argument('--chs-cons-id',type=int,default=0,help='[Test 1] Consumer Id')
parser.add_argument('--chs-prod-id',type=int,default=0,help='[Test 1] Producer Id')
parser.add_argument('--chs-1p1c-num-pairs',default=1,type=int,help='[Test 2] Number of coherence sharing pairs')
parser.add_argument('--chs-1pMc',action='store_true',help='[Test 3] Run 1 producer M > 1 consumers')
parser.add_argument('--chs-1p-MSharers',default=2,type=int,help='[Test 3] Number of sharers')
parser.add_argument('--max-outstanding-requests',default=1,type=int,help='Maximumum number of outstanding requests produced')
parser.add_argument('--id-starter',default=0,type=int,help='Starter id of the migratory sharing patterns')
parser.add_argument('--outstanding-req',default=100,type=int,help='Number of oustanding requests')
parser.add_argument('--allow-infinite-SF-entries',default=True, type=ast.literal_eval, help="Allow infinite SnoopFilter entries.")
parser.add_argument('--xor-addr-bits',default=1,type=int,help='Number of addr bits XORed to obtain the address masks')
parser.add_argument('--block-stride-bits',default=0,type=int,help='Block address strides, 2^(--block-stride-bits)')
parser.add_argument('--randomize-acc',default=False,type=ast.literal_eval,help=f'Randomize access patters')
parser.add_argument('--chi-data-width',default=16,type=int,help=f'CHI Controller data width (in bytes)')
parser.add_argument('--ratio-read-write',type=str, default='1-1', help=f'Read write ratio')
parser.add_argument('--base_addr_1',type=int, default=0, help=f'First address region')
parser.add_argument('--base_addr_2',type=int, default=1073741824, help=f'Second address region')
parser.add_argument('--chi-buffer-depth',type=int,default=16,help=f'CHI buffer depth. Zero implies infinite buffering')
parser.add_argument('--chi-buffer-max-deq-rate',type=int,default=1,help=f'CHI buffer max deq rate. Zero implies infinite deq rate')
parser.add_argument('--snf_allow_retry',type=ast.literal_eval,default=True,help=f'Should SNF send retries')
parser.add_argument('--slots_bocked_by_set',type=ast.literal_eval,default=False,help=f'Is MSHR Blocked on slots')
parser.add_argument('--accepted_buffer_max_deq_rate',type=int,default=0,help=f'Accepted buffer max deq rate. Zero implies infinite deq rate')
parser.add_argument('--decoupled_req_alloc',type=ast.literal_eval,default=False,help=f'Decouple req alloc and MSHR alloc')
parser.add_argument('--num_accepted_entries',type=int,default=0,help=f'Used for decouple accepted req and MSHR allocation. Applicable only when decoupled_req_alloc=True')
parser.add_argument('--num-dies',type=int,default=0,help=f'Number of dies. Each die is modelled as a separate Ruby network')
# parser.add_argument('--simple-link-bw-factor',type=int,default=16,help=f'Link BW factor')

def getCPUList(cpuListStr):
    return [int(c) for c in cpuListStr.split(';')]

#
# Add the ruby specific and protocol specific options
#
RubyD2D.define_options(parser)

args = parser.parse_args()

block_size = 64

splitText=args.ratio_read_write.split('-')
k1=int(splitText[0])
k2=int(splitText[1])
percent_read=int((k1/(k1+k2))*100)

MemTestClass=None
if args.mem_test_type=='bw_test':
    MemTestClass=SeqMemTest
elif args.mem_test_type=='bw_test_sf':
    MemTestClass=Seq2MemTest # Testing the SnoopFilter under extreme configs to trigger outstanding SFRepls
elif args.mem_test_type=='falsesharing_test':
    MemTestClass=FalseSharingMemTest
elif args.mem_test_type=='prod_cons_test':
    MemTestClass=ProdConsMemTest
elif args.mem_test_type=='random_test':
    MemTestClass=MemRandomTest
elif args.mem_test_type=='isolated_test':
    MemTestClass=IsolatedMemTest
elif args.mem_test_type=='migratory_test':
    MemTestClass=MigratoryMemTest
elif args.mem_test_type=='true_prod_cons':
    MemTestClass=TrueProdConsMemTest
elif args.mem_test_type=='memcpy_test':
    MemTestClass=MemCpyTest
else:
    raise ValueError(f'MemTest type undefined')

num_cpus=args.num_cpus
cpuProdListMap=dict([(c,[]) for c in range(num_cpus)])
cpuConsListMap=dict([(c,[]) for c in range(num_cpus)])
num_peer_producers=1

if (args.mem_test_type=='prod_cons_test') or (args.mem_test_type=='true_prod_cons'):
    import random
    if (args.chs_1p1c):
        # 1P-1C with controllable prod_id and cons_id locations
        assert(args.chs_prod_id != args.chs_cons_id)
        assert(args.chs_prod_id < num_cpus)
        assert(args.chs_cons_id < num_cpus)
        cpuProdListMap[args.chs_prod_id]=[args.chs_prod_id]
        cpuConsListMap[args.chs_prod_id]=[args.chs_cons_id]
        cpuProdListMap[args.chs_cons_id]=[args.chs_prod_id]
        cpuConsListMap[args.chs_cons_id]=[args.chs_cons_id]
    elif (args.chs_1pMc) :
        assert(not (args.chs_1p1c)) # Do not set it to true
        assert(args.chs_prod_id < num_cpus)
        cpuProdListMap[args.chs_prod_id]=[args.chs_prod_id]
        assert(args.chs_1p_MSharers > 1)
        num_cons=0
        for cons_id in range(num_cpus):
            if num_cons >= args.chs_1p_MSharers:
                break
            if cons_id == args.chs_prod_id:
                continue
            else :
                cpuConsListMap[cons_id].append(cons_id)
                cpuProdListMap[cons_id].append(args.chs_prod_id)
                cpuConsListMap[args.chs_prod_id].append(cons_id)
                num_cons+=1
    else :
        # M x (1P-1C) with controllable prod_id and cons_id locations
        npairs = args.chs_1p1c_num_pairs
        assert((2*npairs) <= num_cpus)
        available_cpus = list(range(num_cpus))
        producer_cpus=available_cpus[:num_cpus//2]
        consumer_cpus=available_cpus[num_cpus//2:]
        num_peer_producers=npairs
        for n in range(npairs) :
            producer=producer_cpus[n] #random.sample(available_cpus,1)[0]
            consumer=consumer_cpus[n] #random.sample(available_cpus,1)[0]
            cpuProdListMap[producer]=[producer]
            cpuConsListMap[producer]=[consumer]
            cpuProdListMap[consumer]=[producer]
            cpuConsListMap[consumer]=[consumer]
else :
    # Dont care. Store the default values
    cpuProdListMap[args.chs_prod_id]=[args.chs_prod_id]
    cpuConsListMap[args.chs_prod_id]=[args.chs_cons_id]
    cpuProdListMap[args.chs_cons_id]=[args.chs_prod_id]
    cpuConsListMap[args.chs_cons_id]=[args.chs_cons_id]

if num_cpus > block_size:
     print("Error: Number of testers %d limited to %d because of false sharing"
           % (num_cpus, block_size))
     sys.exit(1)

cpus = []
num_dmas=args.num_dmas

if num_cpus > 0 :
    cpus = [ MemTestClass(max_loads = args.maxloads,
                     working_set = args.size_ws,
                     interval = args.inj_interval,
                     num_peers = num_cpus+num_dmas,
                     addr_intrlvd_or_tiled = args.addr_intrlvd_or_tiled,
                     id_producers = cpuProdListMap[i],
                     id_consumers = cpuConsListMap[i],
                     outstanding_req = args.outstanding_req,
                     id_starter = args.id_starter,
                     num_peer_producers = num_peer_producers,
                     block_stride_bits = args.block_stride_bits,
                     randomize_acc = args.randomize_acc,
                     percent_reads = percent_read,
                     base_addr_1=args.base_addr_1,
                     base_addr_2=args.base_addr_2,
                     no_gen=False if i == (num_cpus-1) else True,
                     suppress_func_errors = args.suppress_func_errors) \
             for i in range(num_cpus) ]

system = System(cpu = cpus,
                clk_domain = SrcClockDomain(clock = args.sys_clock),
                mem_ranges = [AddrRange(args.mem_size)])


if num_dmas > 0:
    dmas = [ MemTestClass(max_loads = args.maxloads,
                     progress_interval = args.progress,
                     interval = args.inj_interval,
                     working_set = args.size_ws,
                     num_peers = num_cpus+num_dmas,
                     id_producers = cpuProdListMap[i],
                     id_consumers = cpuConsListMap[i],
                     outstanding_req = args.outstanding_req,
                     id_starter = args.id_starter,
                     num_peer_producers = num_peer_producers,
                     addr_intrlvd_or_tiled = args.addr_intrlvd_or_tiled,
                     block_stride_bits = args.block_stride_bits,
                     randomize_acc = args.randomize_acc,
                     percent_reads = percent_read,
                     no_gen=False if i == (num_cpus-1) else True,
                     suppress_func_errors = not args.suppress_func_errors) \
             for i in range(args.num_dmas) ]
    system.dma_devices = dmas
else:
    dmas = []

dma_ports = []
for (i, dma) in enumerate(dmas):
    dma_ports.append(dma.port)

RubyD2D.create_system(args, False, system, dma_ports = dma_ports)

# Create a top-level voltage domain and clock domain
system.voltage_domain = VoltageDomain(voltage = args.sys_voltage)
system.clk_domain = SrcClockDomain(clock = args.sys_clock,
                                   voltage_domain = system.voltage_domain)
# Create a seperate clock domain for RubyD2D
system.ruby.clk_domain = SrcClockDomain(clock = args.ruby_clock,
                                        voltage_domain = system.voltage_domain)

#
# The tester is most effective when randomization is turned on and
# artifical delay is randomly inserted on messages
#
system.ruby.randomization = False

assert(len(cpus) == len(system.ruby._cpu_ports))

for (i, cpu) in enumerate(cpus):
    #
    # Tie the cpu memtester ports to the correct system ports
    #
    cpu.port = system.ruby._cpu_ports[i].in_ports

    #
    # Since the memtester is incredibly bursty, increase the deadlock
    # threshold to 5 million cycles
    #
    system.ruby._cpu_ports[i].deadlock_threshold = 5000000

# -----------------------
# run simulation
# -----------------------

root = Root( full_system = False, system = system )
root.system.mem_mode = 'timing'

# Not much point in this being higher than the L1 latency
if (args.disable_gclk_set):
    print ("No setGlobalFrequency\n")
else:
    m5.ticks.setGlobalFrequency('1ns')

# instantiate configuration
m5.instantiate()
sys.exit(-1)

# simulate until program terminates
exit_event = m5.simulate(args.abs_max_tick)

print('Exiting @ tick', m5.curTick(), 'because', exit_event.getCause())