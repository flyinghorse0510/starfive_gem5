# Copyright (c) 2023 Starfive Pvt Limited
# All rights reserved.

import math
import m5
from m5.objects import *
from m5.defines import buildEnv
from m5.util import addToPath, fatal

addToPath('../')

from common import ObjectList
from common import MemConfig
from common import FileSystemConfig

from topologies import *
from network import Network
import pprint as pp

def define_options(parser):
    # By default, ruby uses the simple timing cpu
    parser.set_defaults(cpu_type="TimingSimpleCPU")

    parser.add_argument(
        "--ruby-clock", action="store", type=str,
        default='2GHz',
        help="Clock for blocks running at Ruby system's speed")

    parser.add_argument(
        "--access-backing-store", action="store_true", default=False,
        help="Should ruby maintain a second copy of memory")

    # Options related to cache structure
    parser.add_argument(
        "--ports", action="store", type=int, default=4,
        help="used of transitions per cycle which is a proxy \
            for the number of ports.")

    # network options are in network/Network.py

    # ruby mapping options
    parser.add_argument(
        "--numa-high-bit", type=int, default=0,
        help="high order address bit to use for numa mapping. "
        "0 = highest bit, not specified = lowest bit")
    parser.add_argument(
        "--interleaving-bits", type=int, default=0,
        help="number of bits to specify interleaving " \
           "in directory, memory controllers and caches. "
           "0 = not specified")
    parser.add_argument(
        "--xor-low-bit", type=int, default=20,
        help="hashing bit for channel selection" \
           "see MemConfig for explanation of the default"\
           "parameter. If set to 0, xor_high_bit is also"\
           "set to 0.")

    parser.add_argument(
        "--recycle-latency", type=int, default=10,
        help="Recycle latency for ruby controller input buffers")
    
    parser.add_argument("--d2d-width",type=int,default=256,help="Width of D2D bridge for D2D communication")

    protocol = buildEnv['PROTOCOL']
    exec("from . import %s" % protocol)
    eval("%s.define_options(parser)" % protocol)
    Network.define_options(parser)

def setup_memory_controllers(system, ruby, mem_cntrls, options):
    if (options.numa_high_bit):
        block_size_bits = options.numa_high_bit + 1 - \
                          int(math.log(options.num_dirs, 2))
        ruby.block_size_bytes = 2 ** (block_size_bits)
    else:
        ruby.block_size_bytes = options.cacheline_size

    ruby.memory_size_bits = 48

    index = 0
    mem_ctrls = []
    crossbars = []

    if options.numa_high_bit:
        dir_bits = int(math.log(options.num_dirs, 2))
        intlv_size = 2 ** (options.numa_high_bit - dir_bits + 1)
    else:
        # if the numa_bit is not specified, set the directory bits as the
        # lowest bits above the block offset bits
        intlv_size = options.cacheline_size

    # Sets bits to be used for interleaving.  Creates memory controllers
    # attached to a directory controller.  A separate controller is created
    # for each address range as the abstract memory can handle only one
    # contiguous address range as of now.
    for dir_cntrl in mem_cntrls:
        crossbar = None
        if len(system.mem_ranges) > 1:
            crossbar = IOXBar()
            crossbars.append(crossbar)
            dir_cntrl.memory_out_port = crossbar.cpu_side_ports

        dir_ranges = []
        for r in system.mem_ranges:
            mem_type = ObjectList.mem_list.get(options.mem_type)

            dram_intf = MemConfig.create_mem_intf(mem_type, r, index,
                int(math.log(options.num_dirs, 2)),
                intlv_size, options.xor_low_bit)
            if issubclass(mem_type, DRAMInterface):
                mem_ctrl = m5.objects.MemCtrl(dram = dram_intf)
            else:
                mem_ctrl = dram_intf

            if options.access_backing_store:
                dram_intf.kvm_map=False

            mem_ctrls.append(mem_ctrl)
            dir_ranges.append(dram_intf.range)

            if crossbar != None:
                mem_ctrl.port = crossbar.mem_side_ports
            else:
                mem_ctrl.port = dir_cntrl.memory_out_port

            opt_addr_mapping = getattr(options, "addr_mapping", None)
            opt_disable_ref = getattr(options, "disable_ref", None)

            if (opt_addr_mapping == "RoRaBaBg1CoBg0Co53Dp"):
                mem_ctrl.dram.addr_mapping = 'RoRaBaBg1CoBg0Co53Dp'

            if (opt_disable_ref):
                mem_ctrl.dram.disable_ref = True


            # Enable low-power DRAM states if option is set
            if issubclass(mem_type, DRAMInterface):
                mem_ctrl.dram.enable_dram_powerdown = \
                        options.enable_dram_powerdown

        index += 1
        dir_cntrl.addr_ranges = dir_ranges

    system.mem_ctrls = mem_ctrls

    if len(crossbars) > 0:
        ruby.crossbars = crossbars

def create_topology(controllers, options, net_idx):
    """ Called from create_system in configs/ruby/<protocol>.py
        Must return an object which is a subclass of BaseTopology
        found in configs/topologies/BaseTopology.py
        This is a wrapper for the legacy topologies.
    """
    exec("import topologies.%s as Topo" % options.topology)
    topology = eval("Topo.%s(controllers, net_idx)" % options.topology)
    return topology

def createDieAddrRanges(options, sys_mem_ranges, die_list):
    _addr_ranges = {}
    phys_mem_addr_bit = int(math.log(AddrRange(options.mem_size).size(),2))
    d2d_bits = int(math.log(len(die_list),2))
    numa_bit = phys_mem_addr_bit-1
    for i, die_id in enumerate(die_list):
        ranges = []
        for r in sys_mem_ranges:
            addr_range = AddrRange(r.start, size = r.size(),
                                    intlvHighBit = numa_bit,
                                    intlvBits = d2d_bits,
                                    intlvMatch = i)
            # Hack to to allow addr_range intersection testing b/w HA nodes and Die addr ranges
            addr_range1 = AddrRange(addr_range.getStartAddr(), end = addr_range.getEndAddr(),
                                    intlvHighBit = numa_bit,
                                    intlvBits = d2d_bits,
                                    intlvMatch = i)
            ranges.append(addr_range1)
        _addr_ranges[die_id] = ranges
        addr_range_str = [a.__str__() for a in ranges]
        print(f'Die@{die_id}, addr_range:{addr_range_str}')
    return _addr_ranges

def create_system(options, full_system, system, piobus = None, dma_ports = [],
                  bootmem=None, cpus=None):

    system.ruby = RubySystem()
    ruby = system.ruby

    # Generate pseudo filesystem
    FileSystemConfig.config_filesystem(system, options)

    networks       = []
    mem_cntrls     = []
    cpu_sequencers = []
    rnfs           = []
    hnfs           = []
    snfs           = []
    mns            = []
    hAs            = []
    d2dnodes       = []
    dma_rni        = []
    io_rni         = []
    d2dbridgemap   = dict()

    # Memory map
    other_memories = []
    if bootmem:
        other_memories.append(bootmem)
    if getattr(system, 'sram', None):
        other_memories.append(getattr(system, 'sram', None))
    on_chip_mem_ports = getattr(system, '_on_chip_mem_ports', None)
    if on_chip_mem_ports:
        other_memories.extend([p.simobj for p in on_chip_mem_ports])
    
    # System addr ranges
    sysranges = [] + system.mem_ranges
    for m in other_memories:
        sysranges.append(m.range)
    
    # Die addr ranges
    num_dies = options.num_dies
    die_list = [i for i in range(num_dies)]
    dieAddrRangeMap = createDieAddrRanges(options, 
                        sysranges, 
                        die_list)
    

    # Create the networks object (1 network for each die)
    for src_die_id in range(options.num_dies) :
        (network, IntLinkClass, ExtLinkClass, RouterClass, InterfaceClass) = \
            Network.create_network(options, ruby)
        networks.append(network)
    ruby.networks = networks
    
    for src_die_id in range(options.num_dies) :
        network = networks[src_die_id]

        protocol = buildEnv['PROTOCOL']
        if protocol != 'CHID2D':
            m5.panic("This script requires the CHID2D build")

        from . import CHID2D
        
        try:
            ret = \
            CHID2D.create_system(options, 
                                 full_system,
                                 system,
                                 dma_ports,
                                 dieAddrRangeMap,
                                 sysranges,
                                 ruby,
                                 src_die_id)
            rnfs.extend(ret['rnfs'])
            hnfs.extend(ret['hnfs'])
            snfs.extend(ret['snfs'])
            if 'mns' in ret:
                if len(ret['mns']) > 0:
                    mns.extend(ret['mns'])
            hAs.extend(ret['hAs'])
            d2dnodes.extend(ret['d2dnodes'])
            d2dbridgemap.update(ret['d2dbridgemap'])
            if 'dma_rni' in ret:
                dma_rni.extend(ret['dma_rni'])
            if 'io_rni' in ret:
                io_rni.extend(ret['io_rni'])
            mem_cntrls.extend(ret['mem_cntrls'])
            cpu_sequencers.extend(ret['cpu_sequencers'])
        except:
            print("Error: could not create sytem for ruby protocol %s" % protocol)
            raise

        # Create the network topology
        topology = ret['topology']
        topology.makeTopology(options, network, IntLinkClass, ExtLinkClass,
                RouterClass)

        # Register the topology elements with faux filesystem (SE mode only)
        if not full_system:
            topology.registerTopology(options)

        # Initialize network based on topology
        Network.init_network(options, network, InterfaceClass)

    # Make all the CHI controllers as children of system.ruby
    if len(rnfs) > 0 :
        ruby.rnfs     = rnfs
    if len(hnfs) > 0 :
        ruby.hnfs     = hnfs
    if len(mns) > 0:
        ruby.mns      = mns
    if len(hAs) > 0:
        ruby.hAs      = hAs
    if len(d2dnodes) > 0:
        ruby.d2dnodes = d2dnodes
    if len(snfs) > 0:
        ruby.snfs     = snfs
    if len(dma_rni) > 0:
        ruby.dma_rni  = dma_rni
    if len(io_rni) > 0:
        ruby.io_rni   = io_rni
    ruby.d2dbridges = list(d2dbridgemap.values())

    # Connect the D2DBridges to each other. 1-to-1 connection
    Network.create_d2d_p2p(options,d2dbridgemap)

    # Create a port proxy for connecting the system port. This is
    # independent of the protocol and kept in the protocol-agnostic
    # part (i.e. here).
    sys_port_proxy = RubyPortProxy(ruby_system = ruby)
    if piobus is not None:
        sys_port_proxy.pio_request_port = piobus.cpu_side_ports

    # Give the system port proxy a SimObject parent without creating a
    # full-fledged controller
    system.sys_port_proxy = sys_port_proxy

    # Connect the system port for loading of binaries etc
    system.system_port = system.sys_port_proxy.in_ports

    setup_memory_controllers(system, ruby, mem_cntrls, options)

    # Connect the cpu sequencers and the piobus
    if piobus != None:
        for cpu_seq in cpu_sequencers:
            cpu_seq.connectIOPorts(piobus)

    ruby.number_of_virtual_networks = ruby.networks[0].number_of_virtual_networks
    ruby._cpu_ports = cpu_sequencers
    ruby.num_of_sequencers = len(cpu_sequencers)

    # Create a backing copy of physical memory in case required
    if options.access_backing_store:
        ruby.access_backing_store = True
        ruby.phys_mem = SimpleMemory(range=system.mem_ranges[0],
                                     in_addr_map=False)

def send_evicts(options):
    # currently, 2 scenarios warrant forwarding evictions to the CPU:
    # 1. The O3 model must keep the LSQ coherent with the caches
    # 2. The x86 mwait instruction is built on top of coherence invalidations
    # 3. The local exclusive monitor in ARM systems
    if options.cpu_type == "DerivO3CPU" or \
       buildEnv['TARGET_ISA'] in ('x86', 'arm'):
        return True
    return False
