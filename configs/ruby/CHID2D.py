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
                  dieAddrRangeMap,
                  sysranges,
                  ruby_system, 
                  src_die_id):
    
    """
        Return the following dictionary
        {
            net_id: 
            cpu_sequencers: []
            mem_cntrls:     []
            rnfs:           []
            hnfs:           []
            snfs:           []
            mns:            []
            d2dnodes:       []
            d2dbridgemap:   dict()
            dma_rni:        []
            io_rni:         []
            ha:             object
        }

        The d2dbridgemap is dict of the
        form (src,dst) --> D2DBridge node
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
    CHI_D2DNode            = chi_defs.CHI_D2DNode
    CHI_HA                 = chi_defs.CHI_HA
    CHI_SNF_MainMem        = chi_defs.CHI_SNF_MainMem
    CHI_HNF_Snoopable      = chi_defs.CHI_HNF_Snoopable

    # Distribution objects
    CHI_DieCPUDistribution = chi_defs.DieCPUDistribution
    CHI_DieD2DDistribution = chi_defs.DieD2DDistribution
    CHI_DieSNFDistribution = chi_defs.DieSNFDistribution
    CHI_DieHNFDistribution = chi_defs.DieHNFDistribution
    CHI_DieHADistribution  = chi_defs.DieHADistribution

    CHI_DieCPUDistribution.setup_die_map(options.num_dies)
    CHI_DieD2DDistribution.setup_die_map(options.num_dies)
    CHI_DieSNFDistribution.setup_die_map(options.num_dies)
    CHI_DieHNFDistribution.setup_die_map(options.num_dies)
    CHI_DieHADistribution.setup_die_map(options.num_dies)

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
    
    class HNFSnoopFilter(RubySnoopFilter):
        size = options.num_snoopfilter_entries
        assoc = options.num_snoopfilter_assoc
        start_index_bit = 6
        allow_infinite_entries = True
    
    class HASnoopFilter(RubySnoopFilter):
        size = 2
        assoc = 1
        start_index_bit = 6
        allow_infinite_entries = options.allow_infinite_SF_entries
    
    assert(system.cache_line_size.value == options.cacheline_size)

    cpu_sequencers = []
    mem_cntrls     = []
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
    die_list       = list(dieAddrRangeMap.keys())

    # Instantiate HNF (add priv L2 cache)
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

    # Instantiate MiscNode
    ret['mns'] = mns

    # Instantiate HNF
    hnf_list = [ hnf_id for hnf_id in range(options.num_l3caches) if src_die_id == CHI_DieHNFDistribution.get_die_id(hnf_id) ]
    CHI_HNF_Snoopable.createAddrRanges(options, 
                             sysranges, 
                             system.cache_line_size.value,
                             hnf_list)
    hnfs = [ CHI_HNF_Snoopable(options, 
                     src_die_id, 
                     hnf_idx, 
                     ruby_system, 
                     HNFCache, 
                     HNFSnoopFilter, 
                     None) for _, hnf_idx in enumerate(hnf_list) ]
    for hnf in hnfs:
        network_nodes.append(hnf)
        assert(hnf.getAllControllers() == hnf.getNetworkSideControllers())
        all_cntrls.extend(hnf.getAllControllers())
        hnf_dests.extend(hnf.getAllControllers())
    ret['hnfs'] = hnfs

    # Instantiate d2d
    d2dnodes = [ CHI_D2DNode(options,
                             src_die_id,
                             dst_die_id,
                             dieAddrRangeMap,
                             ruby_system) for dst_die_id in die_list if (dst_die_id != src_die_id) ]
    d2d_dests = []
    d2d_bridge_map = dict()
    for d2d in d2dnodes:
        network_nodes.append(d2d)
        all_cntrls.extend(d2d.getAllControllers())
        d2d_dests.extend(d2d.getAllControllers())
        d2d_bridge_map[d2d.getSrcDstPair()] = d2d.getD2DBridge()

    ret['d2dnodes']     = d2dnodes
    ret['d2dbridgemap'] = d2d_bridge_map

    # Intantiate HA
    """
        HAs and SNF are closely tied.
        In each die for every SNF, 
        there is exactly one HA
        What does CustomMesh._autoPairHNFandSNF
        do? Sound like its similar
        to what we are trying to achieve
    """
    hAList = [haId for haId in range(options.num_dirs) if src_die_id == CHI_DieHADistribution.get_die_id(haId)]
    die_addr_ranges = dieAddrRangeMap[src_die_id]
    CHI_HA.createHAAddrRanges(options,
                              die_addr_ranges,
                              system.cache_line_size.value,
                              src_die_id,
                              hAList)
    hAs = [CHI_HA(options,src_die_id,haId,HASnoopFilter,ruby_system) for haId in hAList]
    ha_dests = []
    hAaddrRangeMap = dict()
    for ha in hAs:
        network_nodes.append(ha)
        assert(ha.getAllControllers() == ha.getNetworkSideControllers())
        ha_dests.extend(ha.getAllControllers())
        all_cntrls.extend(ha.getAllControllers())
        hAaddrRangeMap[ha.getHAId()] = ha.getHAAddrRanges()
    
    # Intantiate SNF
    snfs = [ CHI_SNF_MainMem(
        options,
        src_die_id,
        ruby_system,
        haId,
        hAaddrRangeMap[haId],
        None,
        None) for haId in hAList ]
    
    for snf in snfs:
        assert(snf.getAllControllers() == snf.getNetworkSideControllers())
        network_nodes.append(snf)
        mem_cntrls.extend(snf.getAllControllers())
        all_cntrls.extend(snf.getAllControllers())

    ret['hAs']        = hAs
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
    
    # Assign downstream destinations (HNF --> {HA,D2D})
    for hnf in hnfs:
        hnf.setDownstream(ha_dests+d2d_dests)
    
    # Assign downstream destinations (HA --> SNF)
    for ha in hAs:
        ha.setDownstream(mem_cntrls)

    # Fwd incoming requests from (D2D --> HA)
    for d2d in d2dnodes:
        d2d.setHADestination(ha_dests)

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
