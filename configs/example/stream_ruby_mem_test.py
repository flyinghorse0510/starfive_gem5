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
import re

import logging
logging.basicConfig(level=logging.INFO)

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
parser.add_argument("--num-producers",type=int,default=1,help='Number of producer')
parser.add_argument("--enable-DMT", default=False, help="enable DMT")
parser.add_argument("--num-HNF-TBE", default=16, help="number of oustanding in HN-F")
parser.add_argument("--num_HNF_ReplTBE", default=16, help="number of replacement oustanding in HN-F")
parser.add_argument("--num_trans_per_cycle_llc", default=4, help="number of transitions per cycle in HN-F")
parser.add_argument("--num-SNF-TBE", default=32, help="number of oustanding in HN-F")
parser.add_argument("--addr-intrlvd-or-tiled",default=False,help="If true the address partitioning across CPUs is interleaved (like [0-N-2N;1-N+1-2N+1;...]). Otherwise Tiled [0:N-1,N:2N-1]")
parser.add_argument("--sequencer-outstanding-requests",type=int,default=32,help="Max outstanding sequencer requests")

#
# Add the ruby specific and protocol specific options
#
Ruby.define_options(parser)

args = parser.parse_args()

#
# Set the default cache size and associativity to be very small to encourage
# races between requests and writebacks.
#
# args.l1d_size="256B"
# args.l1i_size="256B"
# args.l2_size="512B"
# args.l3_size="1kB"
# args.l1d_assoc=2
# args.l1i_assoc=2
# args.l2_assoc=2
# args.l3_assoc=2

block_size = 64
offset = 0x0
max_outstanding = 100
scale = 3.0

arbi_policy = {'round_robin':0, 'st_first':1}

if args.num_cpus > block_size:
     print("Error: Number of testers %d limited to %d because of false sharing"
           % (args.num_cpus, block_size))
     sys.exit(1)

#
# Currently ruby does not support atomic or uncacheable accesses
#

sz_pat = re.compile('^(\d+)([K|k|M|m|G|g])i*B$')
def parse_size(sz:str):
    sz_srch = re.search(sz_pat,sz)
    try:
        assert sz_srch != None
    except:
        logging.debug(f'sz_pat not found in {sz}.')
    multiplier = {'K':2**10, 'k':2**10, 'M':2**20, 'm':2**20, 'G':2**30, 'g':2**30}
    base = int(sz_srch.group(1))
    unit = sz_srch.group(2)
    return int(base*multiplier[unit])

# later may support scale, copy, add
MemTestClass = None
if args.mem_test_type=='stream_test':
    l3_size = parse_size(args.l3_size) # l3 size read from console
    mem_size = parse_size(args.mem_size) # mem size read from console
    ws_size = args.size_ws # ws size read from console

    min_ws_size = 4*args.num_l3caches*l3_size # at least 4x sizeof(avail llc)

    min_mem_size = 3*min_ws_size # A,B,C three arrays
    logging.info(f'Stream Test: num_cpus:{args.num_cpus}, num_llc:{args.num_l3caches}, l3_size:{l3_size}, '+
                  f'min_ws_size(4*num_llc*l3_size):{min_ws_size}, min_mem_size(3*min_ws_size):{min_mem_size}')
    logging.info(f'ws_size read from console:{ws_size}, mem_size read from console:{mem_size}')
    assert ws_size >= min_ws_size, f'working set is too small, should be larger than 4*num_llc*l3size:{min_ws_size}!'
    req_mem_size = 3*ws_size
    assert mem_size >= req_mem_size, "mem size is too small!"
    
    logging.info(f'eventual ws_size:{ws_size}')
    MemTestClass=StreamMemTest

else:
    logging.critical(f'Test name not found: {args.mem_test_type}! Current support tests: triad_test')

if args.num_cpus > 0 :
    cpus = [ MemTestClass(id = i, num_cpus = args.num_cpus, maxloads = args.maxloads, 
                          max_outstanding = max_outstanding, ws_size = ws_size, arbi_policy = arbi_policy['round_robin'], 
                          addr_a = offset, addr_b = ws_size+offset, addr_c = ws_size*2+offset, scale=scale,
                          suppress_func_errors = args.suppress_func_errors) \
             for i in range(args.num_cpus) ]

system = System(cpu = cpus,
                clk_domain = SrcClockDomain(clock = args.sys_clock),
                mem_ranges = [AddrRange(args.mem_size)])

if args.num_dmas > 0:
    dmas = [ MemTestClass(id = i, num_cpus = args.num_cpus, maxloads = args.maxloads, 
                          max_outstanding = max_outstanding, ws_size = ws_size, arbi_policy = arbi_policy['round_robin'], 
                          addr_a = offset, addr_b = ws_size+offset, addr_c = ws_size*2+offset, scale=scale,
                          suppress_func_errors = args.suppress_func_errors) \
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
