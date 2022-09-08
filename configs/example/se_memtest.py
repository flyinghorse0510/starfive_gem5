# Copyright (c) 2012-2013 ARM Limited
# All rights reserved.
#
# The license below extends only to copyright in the software and shall
# not be construed as granting a license to any other intellectual
# property including but not limited to intellectual property relating
# to a hardware implementation of the functionality of the software
# licensed hereunder.  You may use the software subject to the license
# terms below provided that you ensure that this notice is replicated
# unmodified and in its entirety in all distributions of the software,
# modified or unmodified, in source code or in binary form.
#
# Copyright (c) 2006-2008 The Regents of The University of Michigan
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

# Simple test script
#
# "m5 test.py"

import argparse
import sys
import os

import m5
from m5.defines import buildEnv
from m5.objects import *
from m5.params import NULL
from m5.util import addToPath, fatal, warn

addToPath('../')

from ruby import Ruby

from common import Options
from common import Simulation
from common import CacheConfig
from common import CpuConfig
from common import ObjectList
from common import MemConfig
from common.FileSystemConfig import config_filesystem
from common.Caches import *
from common.cpu2000 import *

parser = argparse.ArgumentParser()
Options.addCommonOptions(parser)
Options.addSEOptions(parser)

if '--ruby' in sys.argv:
    Ruby.define_options(parser)

parser.add_argument("--maxloads", metavar="N", default=0,
                    help="Stop after N loads")
parser.add_argument("--progress", type=int, default=1000,
                    metavar="NLOADS",
                    help="Progress message interval ")
parser.add_argument("--workingset-size", type=int, default=65536, help="Working set size in bytes")

args = parser.parse_args()

cpus = [MemRandomTest(max_loads = args.maxloads, size=args.workingset_size)]
if args.num_cpus > 0 :
    cpus = [ MemRandomTest(max_loads = args.maxloads, size=args.workingset_size) for _ in range(args.num_cpus) ]

system = System(cpu = cpus,
                clk_domain = SrcClockDomain(clock = args.sys_clock),
                mem_ranges = [AddrRange(args.mem_size)])


# Create a top-level voltage domain
system.voltage_domain = VoltageDomain(voltage = args.sys_voltage)

# Create a source clock for the system and set the clock period
system.clk_domain = SrcClockDomain(clock =  args.sys_clock,
                                   voltage_domain = system.voltage_domain)

if args.ruby:
    # Set the Cache size
    args.l1d_size="1kB"
    args.l1i_size="1kB"
    args.l2_size="32kB"
    args.l3_size="1MB"
    args.l1d_assoc=4
    args.l1i_assoc=4
    args.l2_assoc=8
    args.l3_assoc=16
    args.l1repl = "RandomRP"
    args.l2repl = "RandomRP"
    args.l3repl = "RandomRP"

    Ruby.create_system(args, False, system)
    assert(args.num_cpus == len(system.ruby._cpu_ports))

    system.ruby.clk_domain = SrcClockDomain(clock = args.ruby_clock,
                                        voltage_domain = system.voltage_domain)
    system.ruby.randomization = False
    for (i, cpu) in enumerate(cpus):
        # Connect the cpu's cache ports to Ruby
        cpu.port = system.ruby._cpu_ports[i].in_ports
        system.ruby._cpu_ports[i].deadlock_threshold = 5000000
else:
    print("Can only work with Ruby\n", file=sys.stderr)
    sys.exit(1)

# -----------------------
# run simulation
# -----------------------
root = Root( full_system = False, system = system )
root.system.mem_mode = 'timing'

# Not much point in this being higher than the L1 latency
m5.ticks.setGlobalFrequency('1ns')

# instantiate configuration
m5.instantiate()

# simulate until program terminates
exit_event = m5.simulate(args.abs_max_tick)

print('Exiting @ tick', m5.curTick(), 'because', exit_event.getCause())
