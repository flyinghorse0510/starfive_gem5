# Copyright (c) 2021 ARM Limited
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
from .RubyD2D import create_topology
from common import ObjectList
import pprint as pp

def define_options(parser):
    parser.add_argument("--chi-config", action="store", type=str,
                        default=None,
                        help="NoC config. parameters and bindings. "
                           "Required for CustomMesh topology")
    parser.add_argument("--enable-dvm", default=False, action="store_true")

def read_config_file(file):
    ''' Read file as a module and return it '''
    import types
    import importlib.machinery
    loader = importlib.machinery.SourceFileLoader('chi_configs', file)
    chi_configs = types.ModuleType(loader.name)
    loader.exec_module(chi_configs)
    return chi_configs

def create_system(options, 
                  full_system, 
                  system, 
                  dma_ports, 
                  bootmem,
                  ruby_system, 
                  src_die_id):
    
    """
        Return the following dictionary
        {
            net_id: 
            cpu_sequencers: []
            mem_cntrls:     []
            rnfs:      []
            hnfs:      []
            snfs:      []
            mns:       []
            d2dnodes:  []
            dma_rni:   []
            io_rni:    []
            ha:        object
        }
    """

    ret = dict()
    ret['net_id'] = src_die_id
    
    # Assign the CPUs
    cpus = system.cpu

    if buildEnv['PROTOCOL'] != 'CHID2D':
        m5.panic("This script requires the CHID2D build")

    if options.num_dirs < 1:
        m5.fatal('--num-dirs must be at least 1')

    if options.num_l3caches < 1:
        m5.fatal('--num-l3caches must be at least 1')

    if full_system and options.enable_dvm:
        if len(cpus) <= 1:
            m5.fatal("--enable-dvm can't be used with a single CPU")
        for cpu in cpus:
            for decoder in cpu.decoder:
                decoder.dvm_enabled = True

    # read specialized classes from config file if provided
    if options.chi_config:
        chi_defs = read_config_file(options.chi_config)
    elif options.topology == 'CustomMesh':
        m5.fatal('--chi-config must be provided if topology is CustomMesh')
    else:
        # Use the defaults from CHI_config
        from . import CHI_config as chi_defs

    # NoC params
    params = chi_defs.NoC_Params
    params.data_width = options.chi_data_width
    
    # Node types
    CHI_RNF                = chi_defs.CHI_RNF
    CHI_HNF                = chi_defs.CHI_HNF
    CHI_MN                 = chi_defs.CHI_MN
    CHI_D2DNode            = chi_defs.CHI_D2DNode
    CHI_HA                 = chi_defs.CHI_HA
    CHI_SNF_MainMem        = chi_defs.CHI_SNF_MainMem

    # Distribution objects
    CHI_DieCPUDistribution = chi_defs.DieCPUDistribution
    CHI_DieHADistribution  = chi_defs.DieHADistribution
    CHI_DieD2DDistribution = chi_defs.DieD2DDistribution
    CHI_DieSNFDistribution = chi_defs.DieSNFDistribution

    CHI_DieCPUDistribution.setup_die_map(options.num_dies)
    CHI_DieHADistribution.setup_die_map(options.num_dies)
    CHI_DieD2DDistribution.setup_die_map(options.num_dies)
    CHI_DieSNFDistribution.setup_die_map(options.num_dies)

    # Declare caches and controller types used by the protocol
    # Notice tag and data accesses are not concurrent, so the a cache hit
    # latency = tag + data + response latencies.
    # Default response latencies are 1 cy for all controllers.
    # For L1 controllers the mandatoryQueue enqueue latency is always 1 cy and
    # this is deducted from the initial tag read latency for sequencer requests
    # dataAccessLatency may be set to 0 if one wants to consider parallel
    # data and tag lookups
    class L1ICache(RubyCache):
        dataAccessLatency = 0
        tagAccessLatency = 4
        size = options.l1i_size
        assoc = options.l1i_assoc
        replacement_policy = ObjectList.rp_list.get(options.l1repl)()

    class L1DCache(RubyCache):
        dataAccessLatency = 0
        tagAccessLatency = 4
        size = options.l1d_size
        assoc = options.l1d_assoc
        replacement_policy = ObjectList.rp_list.get(options.l1repl)()

    class L2Cache(RubyCache):
        dataAccessLatency = 12
        tagAccessLatency = 4
        size = options.l2_size
        assoc = options.l2_assoc
        replacement_policy = ObjectList.rp_list.get(options.l2repl)()

    class HNFCache(RubyCache):
        dataAccessLatency = 20
        tagAccessLatency = 6
        size = options.l3_size
        assoc = options.l3_assoc
        replacement_policy = ObjectList.rp_list.get(options.l3repl)()
    
    class HNFRealSnoopFilter(RubySnoopFilter):
        size = options.num_snoopfilter_entries
        assoc = options.num_snoopfilter_assoc
        start_index_bit = 6
        allow_infinite_entries = options.allow_infinite_SF_entries
    
    assert(system.cache_line_size.value == options.cacheline_size)

    cpu_sequencers = []
    mem_cntrls     = []
    mem_dests      = []
    network_nodes  = []
    hnf_dests      = []
    all_cntrls     = []
    rnfs           = [] 
    hnfs           = [] 
    snfs           = []
    mns            = []
    d2dnodes       = []
    dma_rni        = []
    io_rni         = None

    # Creates on RNF per cpu with priv l2 caches
    assert(len(cpus) == options.num_cpus)
    rnfs = [ CHI_RNF(options, 
                     src_die_id,
                     [cpu], 
                     ruby_system, 
                     L1ICache, 
                     L1DCache, 
                     system.cache_line_size.value)
                     for rnf_id, cpu in enumerate(cpus) if src_die_id == CHI_DieCPUDistribution.get_die_id(rnf_id)]
    for rnf in rnfs:
        rnf.addPrivL2Cache(options,L2Cache)
        cpu_sequencers.extend(rnf.getSequencers())
        all_cntrls.extend(rnf.getAllControllers())
        network_nodes.append(rnf)
    ret['cpu_sequencers'] = cpu_sequencers
    ret['rnfs']           = rnfs

    # Creates one Misc Node
    # mns = [ CHI_MN(options, src_die_id, ruby_system, [cpu.l1d for cpu in cpus]) ]
    # for mn in mns:
    #     all_cntrls.extend(mn.getAllControllers())
    #     network_nodes.append(mn)
    #     assert(mn.getAllControllers() == mn.getNetworkSideControllers())
    ret['mns'] = mns

    # Look for other memories
    other_memories = []
    if bootmem:
        other_memories.append(bootmem)
    if getattr(system, 'sram', None):
        other_memories.append(getattr(system, 'sram', None))
    on_chip_mem_ports = getattr(system, '_on_chip_mem_ports', None)
    if on_chip_mem_ports:
        other_memories.extend([p.simobj for p in on_chip_mem_ports])
    
    # Create the HNF cntrls
    sysranges = [] + system.mem_ranges
    for m in other_memories:
        sysranges.append(m.range)
    
    hnf_list = [i for i in range(options.num_l3caches)]
    CHI_HNF.createAddrRanges(options, sysranges, system.cache_line_size.value,
                             hnf_list)
    hnfs = [ CHI_HNF(options, 
                     src_die_id, 
                     hnf_id, 
                     ruby_system, 
                     HNFCache, 
                     HNFRealSnoopFilter, 
                     None) for hnf_id in range(options.num_l3caches) if src_die_id == CHI_DieHADistribution.get_die_id(hnf_id) ]
    for hnf in hnfs:
        network_nodes.append(hnf)
        assert(hnf.getAllControllers() == hnf.getNetworkSideControllers())
        all_cntrls.extend(hnf.getAllControllers())
        hnf_dests.extend(hnf.getAllControllers())
    ret['hnfs'] = hnfs

    # Instantiate the d2d nodes
    num_dies = options.num_dies
    die_list = [i for i in range(num_dies)]
    CHI_D2DNode.createAddrRanges(options, sysranges, system.cache_line_size.value, die_list)
    d2dnodes = [ CHI_D2DNode(options,
                             src_die_id,
                             ruby_system,
                             dst_die_id) for dst_die_id in die_list if (dst_die_id != src_die_id) ]
    d2d_dests = []
    for d2d in d2dnodes:
        network_nodes.append(d2d)
        all_cntrls.extend(d2d.getAllControllers())
        d2d_dests.extend(d2d.getAllControllers())
    ret['d2dnodes'] = d2dnodes

    # Intantiate the HA node
    die_addr_ranges, _ = CHI_D2DNode.getAddrRanges(src_die_id)
    ha = CHI_HA(options, src_die_id, die_addr_ranges, ruby_system) 
    ha_dests = []
    network_nodes.append(ha)
    ha_dests.extend(ha.getAllControllers())
    all_cntrls.extend(ha.getAllControllers())
    ret['ha'] = ha
    
    # Create SNF
    snfs = [ CHI_SNF_MainMem(options, 
                             src_die_id,
                             ruby_system,
                             None,
                             None)
            for snf_id in range(options.num_dirs) if src_die_id == CHI_DieSNFDistribution.get_die_id(snf_id) ]
    
    for snf in snfs:
        snf.setAddrRange(die_addr_ranges)
        network_nodes.append(snf)
        assert(snf.getAllControllers() == snf.getNetworkSideControllers())
        mem_cntrls.extend(snf.getAllControllers())
        all_cntrls.extend(snf.getAllControllers())
        mem_dests.extend(snf.getAllControllers())
    ret['snfs']       = snfs
    ret['mem_cntrls'] = mem_cntrls

    # Create DMA and io
    if len(dma_ports) > 0:
        dma_rni = [ CHI_RNI_DMA(ruby_system, dma_port, None)
                                for dma_port in dma_ports ]
        for rni in dma_rni:
            network_nodes.append(rni)
            all_cntrls.extend(rni.getAllControllers())
        ret['dma_rni'] = dma_rni

    if full_system:
        io_rni = CHI_RNI_IO(ruby_system, None)
        network_nodes.append(io_rni)
        all_cntrls.extend(io_rni.getAllControllers())
        ret['io_rni'] = io_rni
    

    # Assign downstream destinations (RNF/RNI --> HNF)
    for rnf in rnfs:
        rnf.setDownstream(hnf_dests)
    if len(dma_ports) > 0:
        for rni in dma_rni:
            rni.setDownstream(hnf_dests)
    if full_system:
        io_rni.setDownstream(hnf_dests)
    
    # Assign downstream destinations (HNF --> SNF)
    for hnf in hnfs:
        hnf.setDownstream(ha_dests)
        ha.setDownstream(mem_dests)

    # Setup data message size for all controllers
    for cntrl in all_cntrls:
        cntrl.data_channel_size = params.data_width

    # Network configurations
    # virtual networks: 0=request, 1=snoop, 2=response, 3=data
    _network = ruby_system.networks[src_die_id]
    _network.number_of_virtual_networks = 4
    _network.control_msg_size           = params.cntrl_msg_size
    _network.data_msg_size              = params.data_width

    # Incorporate the params into options so it's propagated to
    # makeTopology and create_topology the parent scripts
    for k in dir(params):
        if not k.startswith('__'):
            setattr(options, k, getattr(params, k))

    if options.topology == 'CustomMesh':
        topology = create_topology(network_nodes, options, src_die_id)
        ret['topology'] = topology
    else:
        m5.fatal("%s not supported!" % options.topology)

    return ret
