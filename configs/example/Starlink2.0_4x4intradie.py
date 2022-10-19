import m5
from m5.objects import *
from m5.defines import buildEnv
from m5.util import addToPath
import os, argparse, sys

addToPath('../')
from common.FileSystemConfig import config_filesystem

from common import Options
from ruby import Ruby

# Get paths we might need.  It's expected this file is in m5/configs/example.
config_path = os.path.dirname(os.path.abspath(__file__))
config_root = os.path.dirname(config_path)

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
Options.addNoISAOptions(parser)

#
# Add the ruby specific and protocol specific options
#
Ruby.define_options(parser)
parser.add_argument("--size",help="size of array in working set")
args = parser.parse_args()

#
# Set the default cache size and associativity to be very small to encourage
# races between requests and writebacks.
#
args.l1d_size="32KiB"
args.l1i_size="32KiB"
args.l2_size="128KiB"
args.l3_size="2MiB"
args.l1d_assoc=4
args.l1i_assoc=4
args.l2_assoc=4
args.l3_assoc=4

block_size = 64

if args.num_cpus < 1 :
     print(f'Requires atleast 1 CPU')
     sys.exit(1)

#
# Currently ruby does not support atomic or uncacheable accesses
#

if args.num_cpus > 0 :
    cpus = [ TimingSimpleCPU(cpu_id=i) for i in range(args.num_cpus) ]

system = System(cpu = cpus,
                clk_domain = SrcClockDomain(clock = args.sys_clock),
                mem_ranges = [AddrRange(args.mem_size)])

system.mem_mode = 'timing'

# create the interrupt controller for the CPU and connect to the membus
for cpu in system.cpu:
    cpu.createInterruptController()

Ruby.create_system(args, False, system, dma_ports = [])

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
    system.ruby._cpu_ports[i].connectCpuPorts(cpu)
    system.ruby._cpu_ports[i].deadlock_threshold = 5000000

isa = str(m5.defines.buildEnv['TARGET_ISA']).lower()
# GEM5DIR = '/home/arka.maity/Desktop/gem5_starlink2.0'
# binary = f'{GEM5DIR}/tests/test-progs/hello/bin/{isa}/linux/hello'
binary = '/home/lester.leong/Desktop/gem5_starlink2.0/benchmarks/starlink2/caches.GEM5_RV64'
# Create a process for a simple "multi-threaded" application
process = Process()
# Set the command
# cmd is a list which begins with the executable (like argv)
process.cmd = [binary,args.size,'10000','16'] #workingset, numiters, stride size
# Set the cpu to use the process as its workload and create thread contexts
for cpu in system.cpu:
    cpu.workload = process
    cpu.createThreads()

system.workload = SEWorkload.init_compatible(binary)

# Set up the pseudo file system for the threads function above
config_filesystem(system)

# -----------------------
# run simulation
# -----------------------
root = Root( full_system = False, system = system )


# Not much point in this being higher than the L1 latency
m5.ticks.setGlobalFrequency('1ns')

# instantiate configuration
m5.instantiate()

# simulate until program terminates
print("Beginning simulation!")
exit_event = m5.simulate()
print('Exiting @ tick', m5.curTick(), 'because', exit_event.getCause())