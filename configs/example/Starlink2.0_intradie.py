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
parser.add_argument("--size-ws",default=False, help="size of array in working set")
parser.add_argument("--rate-style", action="store_true", default=False,help="Replicate a workload across multiple CPUs")
parser.add_argument("--num-iters",default=1000,help="How many iterations to run")
parser.add_argument("--no-roi", action="store_true", default=False,help="Avoid ROI")
parser.add_argument("--use-o3", action="store_true", default=False, help="Use gem5 O3 CPU")

parser.add_argument("--enable-DMT", default=False, help="enable DMT")
parser.add_argument("--num-HNF-TBE", default=16, help="number of oustanding in HN-F")
parser.add_argument("--num_HNF_ReplTBE", default=16, help="number of replacement oustanding in HN-F")

#
# Add the ruby specific and protocol specific options
#
Ruby.define_options(parser)
args = parser.parse_args()

#
# Set the default cache size and associativity to be very small to encourage
# races between requests and writebacks.
#
#args.l1d_size="32KiB"
#args.l1i_size="32KiB"
#args.l2_size="128KiB"
#args.l3_size="2MiB"
#args.l1d_assoc=4
#args.l1i_assoc=4
#args.l2_assoc=8
#args.l3_assoc=16
#args.num_iters = 8
#args.size_ws = 32768 #2048 #4096

block_size = 64

if args.num_cpus < 1 :
     print(f'Requires atleast 1 CPU')
     sys.exit(1)

# Create Workload (Process) list
binaryImg=f'/home/zhiguo.ge/ChipServer/Modeling/Benchmarks/ccbench/band_stream/build/stream.2048_0.GEM5_RV64'
if args.no_roi :
    binaryImg=f'/home/zhiguo.ge/ChipServer/Modeling/Benchmarks/ccbench/band_stream/build_no_roi/stream.2048_0.GEM5_RV64'

#binaryImg=f'/home/zhiguo.ge/ChipServer/Modeling/Benchmarks/ccbench/multi_threads/build/multiThread._.GEM5_RV64'

multiProcess=[]
numThreads=1
if args.rate_style :
    for i in range(args.num_cpus):
        process = Process(pid = 100 + i)
        process.executable = binaryImg
        process.cwd = os.getcwd()
        process.cmd = [binaryImg, f'{i}', f'{args.num_cpus}', f'{args.num_iters}', f'{args.size_ws}']
        multiProcess.append(process)
else :
    process = Process(pid = 100)
    process.executable = binaryImg
    process.cwd = os.getcwd()
    process.cmd = [binaryImg, 0, 1, f'{args.num_iters}']
    multiProcess.append(process)

CPUClass=TimingSimpleCPU
if args.use_o3 :
    CPUClass=DerivO3CPU

CPUClass.numThreads = numThreads
if args.num_cpus > 0 :
    cpus = [ CPUClass(cpu_id=i) for i in range(args.num_cpus) ]

system = System(cpu = cpus,
                clk_domain = SrcClockDomain(clock = args.sys_clock),
                mem_ranges = [AddrRange(args.mem_size)])

if numThreads > 1:
    system.multi_thread = True

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

# Assign workloads to CPUs
for i in range(args.num_cpus) :
    if len(multiProcess) == 1:
        system.cpu[i].workload = multiProcess[0]
    else :
        system.cpu[i].workload = multiProcess[i]
    system.cpu[i].createThreads()

system.workload = SEWorkload.init_compatible(binaryImg)

# Set up the pseudo file system for the threads function above
config_filesystem(system)

# -----------------------
# run simulation
# -----------------------
root = Root(full_system = False, system = system)

# Not much point in this being higher than the L1 latency
m5.ticks.setGlobalFrequency('1ns')

# instantiate configuration
m5.instantiate()

# simulate until program terminates
print("Beginning simulation!")
exit_event = m5.simulate()
print('Exiting @ tick', m5.curTick(), 'because', exit_event.getCause())
