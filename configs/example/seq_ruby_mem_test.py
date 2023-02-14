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
from ruby import Ruby

# Get paths we might need.  It's expected this file is in m5/configs/example.
config_path = os.path.dirname(os.path.abspath(__file__))
config_root = os.path.dirname(config_path)

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
Options.addNoISAOptions(parser)

parser.add_argument("--maxloads", metavar="N", default=0,
                    help="Stop after N loads")
parser.add_argument("--progress", type=int, default=1000,
                    metavar="NLOADS",
                    help="Progress message interval ")
parser.add_argument("--num-dmas", type=int, default=0, help="# of dma testers")
parser.add_argument("--functional", type=int, default=0,
                    help="percentage of accesses that should be functional")
parser.add_argument("--suppress-func-errors", action="store_true",
                    help="suppress panic when functional accesses fail")
parser.add_argument("--mem-test-type",type=str,default='bw_test',help="The type of Memtest stimulus generator to use")
parser.add_argument("--size-ws",type=int,default=1024,help='Working set size in bytes. Must be a multiple of Cacheline size')
parser.add_argument("--enable-DMT", default=False, help="enable DMT")
parser.add_argument("--enable-DCT", default=False, help="enable DCT")
parser.add_argument("--num-HNF-TBE", default=16, help="number of oustanding in HN-F")
parser.add_argument("--num_HNF_ReplTBE", default=16, help="number of replacement oustanding in HN-F")
parser.add_argument("--num_trans_per_cycle_llc", default=4, help="number of transitions per cycle in HN-F")
parser.add_argument("--num-SNF-TBE", default=32, help="number of oustanding in HN-F")
parser.add_argument("--addr-intrlvd-or-tiled",default=False,help="If true the address partitioning across CPUs is interleaved (like [0-N-2N;1-N+1-2N+1;...]). Otherwise Tiled [0:N-1,N:2N-1]")
parser.add_argument("--sequencer-outstanding-requests",type=int,default=32,help="Max outstanding sequencer requests")
parser.add_argument("--bench-c2cbw-mode",default=True,help="[True] Producer Consumer BW or [False] C2C Latency Test")

"""
    The (--producers,--num-producers) are mutually exclusive argument specification 
    as are (--consumers,--num-consumers). --producers an --consumers specify the 
    location and the number of producers and consumers respectively. These are mainly
    used in pingpong latency benchmarks. While --num-producers and --num-consumers 
    specify the number of producers and consumer respectively w/o any location information.
    These are used in producer consumer style benchmarks. DO NOT specify both of them
    together. If you do the results are not well-defined
"""
parser.add_argument("--producers",type=str, default="0", help="semicolon separated list of producers")
parser.add_argument("--consumers",type=str, default="1", help="semicolon separated list of consumers")
parser.add_argument("--num-producers",type=int,default=-1,help="number of producers")
parser.add_argument("--num-consumers",type=int,default=-1,help="number of consumers")

def getCPUList(cpuListStr):
    return [int(c) for c in cpuListStr.split(';')]

#
# Add the ruby specific and protocol specific options
#
Ruby.define_options(parser)

args = parser.parse_args()

block_size = 64
producers_list=getCPUList(args.producers)
consumers_list=getCPUList(args.consumers)
num_cpus=args.num_cpus
if args.bench_c2cbw_mode:
    producers_list=[i for i in range(args.num_producers)]
    cpu_offset=len(producers_list)
    consumers_list=[(cpu_offset+i) for i in range(args.num_consumers)]

if num_cpus > block_size:
     print("Error: Number of testers %d limited to %d because of false sharing"
           % (num_cpus, block_size))
     sys.exit(1)

#
# Currently ruby does not support atomic or uncacheable accesses
#

MemTestClass=None
if args.mem_test_type=='bw_test':
    MemTestClass=SeqMemTest
elif args.mem_test_type=='prod_cons_test':
    MemTestClass=ProdConsMemTest
elif args.mem_test_type=='random_test':
    MemTestClass=MemRandomTest

if num_cpus > 0 :
    cpus = [ MemTestClass(max_loads = args.maxloads,
                     working_set = args.size_ws,
                     num_cpus = num_cpus,
                     addr_intrlvd_or_tiled = args.addr_intrlvd_or_tiled,
                     bench_c2cbw_mode = args.bench_c2cbw_mode,
                     id_producers = producers_list,
                     id_consumers = consumers_list,
                     suppress_func_errors = args.suppress_func_errors) \
             for i in range(args.num_cpus) ]

system = System(cpu = cpus,
                clk_domain = SrcClockDomain(clock = args.sys_clock),
                mem_ranges = [AddrRange(args.mem_size)])

if args.num_dmas > 0:
    dmas = [ MemTestClass(max_loads = args.maxloads,
                     progress_interval = args.progress,
                     working_set = args.size_ws,
                     num_cpus = num_cpus,
                     bench_c2cbw_mode = args.bench_c2cbw_mode,
                     id_producers = producers_list,
                     id_consumers = consumers_list,
                     addr_intrlvd_or_tiled = args.addr_intrlvd_or_tiled,
                     suppress_func_errors = not args.suppress_func_errors) \
             for i in range(args.num_dmas) ]
    system.dma_devices = dmas
else:
    dmas = []

dma_ports = []
for (i, dma) in enumerate(dmas):
    dma_ports.append(dma.test)
Ruby.create_system(args, False, system, dma_ports = dma_ports)

# Create a top-level voltage domain and clock domain
system.voltage_domain = VoltageDomain(voltage = args.sys_voltage)
system.clk_domain = SrcClockDomain(clock = args.sys_clock,
                                   voltage_domain = system.voltage_domain)
# Create a seperate clock domain for Ruby
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

# simulate until program terminates
exit_event = m5.simulate(args.abs_max_tick)

print('Exiting @ tick', m5.curTick(), 'because', exit_event.getCause())
