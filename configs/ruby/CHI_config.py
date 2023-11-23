
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

'''
Definitions for CHI nodes and controller types. These are used by
create_system in configs/ruby/CHI.py or may be used in custom configuration
scripts. When used with create_system, the user may provide an additional
configuration file as the --chi-config parameter to specialize the classes
defined here.

When using the CustomMesh topology, --chi-config must be provided with
specialization of the NoC_Param classes defining the NoC dimensions and
node to router binding. See configs/example/noc_config/2x4.py for an example.
'''

from curses.ascii import NUL
import math
import m5
from m5.objects import *

from common import Options
import pprint as pp

class Versions:
    '''
    Helper class to obtain unique ids for a given controller class.
    These are passed as the 'version' parameter when creating the controller.
    '''
    _seqs = 0
    @classmethod
    def getSeqId(cls):
        val = cls._seqs
        cls._seqs += 1
        return val

    _version = {}
    @classmethod
    def getVersion(cls, tp):
        if tp not in cls._version:
            cls._version[tp] = 0
        val = cls._version[tp]
        cls._version[tp] = val + 1
        return val


class NoC_Params:
    '''
    Default parameters for the interconnect. The value of data_width is
    also used to set the data_channel_size for all CHI controllers.
    (see configs/ruby/CHI.py)
    '''
    router_link_latency = 1
    node_link_latency   = 1
    router_latency      = 1
    router_buffer_size  = 4
    cntrl_msg_size      = 8
    data_width          = 64
    cross_links         = []
    cross_link_latency  = 0

class CHI_Node(SubSystem):
    '''
    Base class with common functions for setting up Cache or Memory
    controllers that are part of a CHI RNF, RNFI, HNF, or SNF nodes.
    Notice getNetworkSideControllers and getAllControllers must be implemented
    in the derived classes.
    '''

    class NoC_Params:
        '''
            @die_router_list : 
            See 'distributeNodes' in configs/topologies/CustomMesh.py
        '''
        die_plcmnt_map      = None

    def __init__(self, ruby_system, src_die_id):
        super(CHI_Node, self).__init__()
        self._ruby_system = ruby_system
        self._network = ruby_system.networks[src_die_id]

    def getNetworkSideControllers(self):
        '''
        Returns all ruby controllers that need to be connected to the
        network
        '''
        raise NotImplementedError()

    def getAllControllers(self):
        '''
        Returns all ruby controllers associated with this node
        '''
        raise NotImplementedError()

    def setDownstream(self, cntrls):
        '''
        Sets cntrls as the downstream list of all controllers in this node
        '''
        for c in self.getNetworkSideControllers():
            c.downstream_destinations = cntrls
    
    def printDownstreamDest(self,pstr):
        for c in self.getNetworkSideControllers():
            for dest in c.downstream_destinations :
                addr_range = dest.addr_ranges
                addr_range_str = [a.__str__() for a in addr_range]
                print(f'{pstr} dest:{dest.path()}, addr_range:{addr_range_str}')

    def connectController(self, options, cntrl):
        '''
            Creates and configures the messages buffers for the CHI input/output
            ports that connect to the network
        '''
        cntrl.reqOut = MessageBuffer(buffer_size=options.chi_buffer_depth,max_dequeue_rate=options.chi_buffer_max_deq_rate)
        cntrl.rspOut = MessageBuffer(buffer_size=options.chi_buffer_depth,max_dequeue_rate=options.chi_buffer_max_deq_rate)
        cntrl.snpOut = MessageBuffer(buffer_size=options.chi_buffer_depth,max_dequeue_rate=options.chi_buffer_max_deq_rate)
        cntrl.datOut = MessageBuffer(buffer_size=options.chi_buffer_depth,max_dequeue_rate=options.chi_buffer_max_deq_rate)
        cntrl.reqIn = MessageBuffer(buffer_size=options.chi_buffer_depth,max_dequeue_rate=options.chi_buffer_max_deq_rate)
        cntrl.rspIn = MessageBuffer(buffer_size=options.chi_buffer_depth,max_dequeue_rate=options.chi_buffer_max_deq_rate)
        cntrl.snpIn = MessageBuffer(buffer_size=options.chi_buffer_depth,max_dequeue_rate=options.chi_buffer_max_deq_rate)
        cntrl.datIn = MessageBuffer(buffer_size=options.chi_buffer_depth,max_dequeue_rate=options.chi_buffer_max_deq_rate)

        # All CHI ports are always connected to the network.
        # Controllers that are not part of the getNetworkSideControllers list
        # still communicate using internal routers, thus we need to wire-up the
        # ports
        cntrl.reqOut.out_port = self._network.in_port
        cntrl.rspOut.out_port = self._network.in_port
        cntrl.snpOut.out_port = self._network.in_port
        cntrl.datOut.out_port = self._network.in_port
        cntrl.reqIn.in_port = self._network.out_port
        cntrl.rspIn.in_port = self._network.out_port
        cntrl.snpIn.in_port = self._network.out_port
        cntrl.datIn.in_port = self._network.out_port

class TriggerMessageBuffer(MessageBuffer):
    '''
    MessageBuffer for triggering internal controller events.
    These buffers should not be affected by the Ruby tester randomization
    and allow poping messages enqueued in the same cycle.
    '''
    randomization = 'disabled'
    allow_zero_latency = True

class OrderedTriggerMessageBuffer(TriggerMessageBuffer):
    ordered = True

class CHI_IdealSnoopFilter(RubySnoopFilter):
    allow_infinite_entries=True

class CHI_Cache_Controller(Cache_Controller):
    '''
    Default parameters for a Cache controller
    The Cache_Controller can also be used as a DMA requester or as
    a pure directory if all cache allocation policies are disabled.
    '''

    def __init__(self, options, ruby_system):
        super(CHI_Cache_Controller, self).__init__(
            version = Versions.getVersion(Cache_Controller),
            ruby_system = ruby_system,
            mandatoryQueue = MessageBuffer(),
            prefetchQueue = MessageBuffer(),
            triggerQueue = TriggerMessageBuffer(),
            retryTriggerQueue = OrderedTriggerMessageBuffer(),
            replTriggerQueue = OrderedTriggerMessageBuffer(),
            sfReplTriggerQueue = OrderedTriggerMessageBuffer(),
            reqRdy = TriggerMessageBuffer(),
            snpRdy = TriggerMessageBuffer())
        # Set somewhat large number since we really a lot on internal
        # triggers. To limit the controller performance, tweak other
        # params such as: input port buffer size, cache banks, and output
        # port latency
        self.transitions_per_cycle = 128
        # This should be set to true in the data cache controller to enable
        # timeouts on unique lines when a store conditional fails
        self.sc_lock_enabled = False
        self.decoupled_req_alloc = False
        self.number_of_reqRdyBuffers = 16
        self.unify_repl_TBEs = True

class CHI_L1Controller(CHI_Cache_Controller):
    '''
    Default parameters for a L1 Cache controller
    '''

    def __init__(self, options, ruby_system, sequencer, cache, prefetcher):  #modification
        super(CHI_L1Controller, self).__init__(options, ruby_system)
        self.sequencer = sequencer
        self.cache = cache
        self.directory = CHI_IdealSnoopFilter()
        self.use_prefetcher = False
        self.send_evictions = True
        self.is_HN = False
        self.enable_DMT = False
        self.enable_DCT = False
        # Strict inclusive MOESI
        self.allow_SD = options.allow_SD
        self.alloc_on_seq_acc = True
        self.alloc_on_seq_line_write = False
        self.alloc_on_readshared = True
        self.alloc_on_readunique = True
        self.alloc_on_readonce = True
        self.alloc_on_writeback = True
        self.dealloc_on_unique = False
        self.dealloc_on_shared = False
        self.dealloc_backinv_unique = True
        self.dealloc_backinv_shared = True
        # Some reasonable default TBE params
        self.number_of_TBEs = 32 #ZHIGUO #16 
        self.number_of_repl_TBEs = 32 #ZHIGUO #16
        self.number_of_snoop_TBEs = 4
        self.number_of_DVM_TBEs = 16
        self.number_of_DVM_snoop_TBEs = 4
        self.slots_bocked_by_set = False

class CHI_L2Controller(CHI_Cache_Controller):                 
    '''
    Default parameters for a L2 Cache controller
    '''

    def __init__(self, options, ruby_system, cache, prefetcher):         #New modification
        super(CHI_L2Controller, self).__init__(options, ruby_system)
        self.sequencer = NULL
        self.cache = cache
        self.directory = CHI_IdealSnoopFilter()
        self.use_prefetcher = False
        self.allow_SD = options.allow_SD
        self.is_HN = False
        self.enable_DMT = False
        self.enable_DCT = False
        self.send_evictions = False
        # Strict inclusive MOESI
        self.alloc_on_seq_acc = False
        self.alloc_on_seq_line_write = False
        self.alloc_on_readshared = True
        self.alloc_on_readunique = True
        self.alloc_on_readonce = True
        self.alloc_on_writeback = True
        self.dealloc_on_unique = False
        self.dealloc_on_shared = False
        self.dealloc_backinv_unique = True
        self.dealloc_backinv_shared = True
        # Some reasonable default TBE params
        self.number_of_TBEs = options.num_RNF_TBE
        self.number_of_repl_TBEs = 32
        self.number_of_snoop_TBEs = 16
        self.number_of_DVM_TBEs = 1 # should not receive any dvm
        self.number_of_DVM_snoop_TBEs = 1 # should not receive any dvm
        self.slots_bocked_by_set = False

class CHI_HNFController(CHI_Cache_Controller):
    '''
    Default parameters for a coherent home node (HNF) cache controller
    '''

    def __init__(self, options, \
                       ruby_system, \
                       cache, \
                       real_snoopfilter, \
                       prefetcher, \
                       addr_ranges):
        super(CHI_HNFController, self).__init__(options, ruby_system)
        self.sequencer = NULL
        self.cache = cache
        self.directory = real_snoopfilter
        self.use_prefetcher = False
        self.addr_ranges = addr_ranges
        self.allow_SD = options.allow_SD
        self.is_HN = True # This must accept snoops from HA
        self.enable_DMT = options.enable_DMT #False #True #args.enable_DMT #False
        self.enable_DCT = options.enable_DCT
        self.send_evictions = False
        # MOESI / Mostly inclusive for shared / Exclusive for unique
        self.alloc_on_seq_acc = False
        self.alloc_on_seq_line_write = False
        self.alloc_on_readshared = True
        self.alloc_on_readunique = False
        self.alloc_on_readonce = True
        self.alloc_on_writeback = True
        self.dealloc_on_unique = True
        self.dealloc_on_shared = False
        self.dealloc_backinv_unique = False
        self.dealloc_backinv_shared = False
        # Some reasonable default TBE params
        splitText=options.ratio_repl_req_TBE.split('-')
        assert(len(splitText)==2)
        k1=int(splitText[0])
        k2=int(splitText[1])
        num_HNF_ReqTBE=max([1, int((k1/(k1+k2))*(options.num_HNF_TBE))])
        num_HNF_ReplTBE=max([1, int((k2/(k1+k2))*(options.num_HNF_TBE))])
        unify_repl_tbes=not options.part_TBEs
        if unify_repl_tbes :
            num_HNF_ReqTBE=options.num_HNF_TBE
            num_HNF_ReplTBE=options.num_HNF_TBE
        self.number_of_TBEs = num_HNF_ReqTBE #2
        self.number_of_repl_TBEs = num_HNF_ReplTBE #2
        self.number_of_snoop_TBEs = 1 # should not receive any snoop
        self.number_of_DVM_TBEs = 1 # should not receive any dvm
        self.number_of_DVM_snoop_TBEs = 1 # should not receive any dvm
        self.unify_repl_TBEs = unify_repl_tbes
        self.transitions_per_cycle = options.num_trans_per_cycle_llc
        self.slots_bocked_by_set = options.slots_bocked_by_set
        # For Retry scheme 2. Setting this to finite deq rate
        self.reqRdy = TriggerMessageBuffer(max_dequeue_rate = options.accepted_buffer_max_deq_rate)
        self.decoupled_req_alloc = options.decoupled_req_alloc
        self.number_of_reqRdyBuffers = options.num_accepted_entries
        
class CHI_MNController(MiscNode_Controller):
    '''
    Default parameters for a Misc Node
    '''

    def __init__(self, ruby_system, addr_range, l1d_caches,
                 early_nonsync_comp):
        super(CHI_MNController, self).__init__(
            version = Versions.getVersion(MiscNode_Controller),
            ruby_system = ruby_system,
            mandatoryQueue = MessageBuffer(),
            triggerQueue = TriggerMessageBuffer(),
            retryTriggerQueue = TriggerMessageBuffer(),
            schedRspTriggerQueue = TriggerMessageBuffer(),
            reqRdy = TriggerMessageBuffer(),
            snpRdy = TriggerMessageBuffer(),
        )
        # Set somewhat large number since we really a lot on internal
        # triggers. To limit the controller performance, tweak other
        # params such as: input port buffer size, cache banks, and output
        # port latency
        self.transitions_per_cycle = 1024
        self.addr_ranges = [addr_range]
        # 16 total transaction buffer entries, but 1 is reserved for DVMNonSync
        self.number_of_DVM_TBEs = 16
        self.number_of_non_sync_TBEs = 1
        self.early_nonsync_comp = early_nonsync_comp

        # "upstream_destinations" = targets for DVM snoops
        self.upstream_destinations = l1d_caches

class CHI_DMAController(CHI_Cache_Controller):
    '''
    Default parameters for a DMA controller
    '''

    def __init__(self, options, ruby_system, sequencer):
        super(CHI_DMAController, self).__init__(options, ruby_system)
        self.sequencer = sequencer
        class DummyCache(RubyCache):
            dataAccessLatency = 0
            tagAccessLatency = 1
            size = "128"
            assoc = 1
        self.directory = CHI_IdealSnoopFilter()
        self.use_prefetcher = False
        self.cache = DummyCache()
        self.sequencer.dcache = NULL
        # All allocations are false
        # Deallocations are true (don't really matter)
        self.allow_SD = False
        self.is_HN = False
        self.enable_DMT = False
        self.enable_DCT = False
        self.alloc_on_seq_acc = False
        self.alloc_on_seq_line_write = False
        self.alloc_on_readshared = False
        self.alloc_on_readunique = False
        self.alloc_on_readonce = False
        self.alloc_on_writeback = False
        self.dealloc_on_unique = False
        self.dealloc_on_shared = False
        self.dealloc_backinv_unique = False
        self.dealloc_backinv_shared = False
        self.send_evictions = False
        self.number_of_TBEs = 16
        self.number_of_repl_TBEs = 1
        self.number_of_snoop_TBEs = 1 # should not receive any snoop
        self.number_of_DVM_TBEs = 1 # should not receive any dvm
        self.number_of_DVM_snoop_TBEs = 1 # should not receive any dvm

class CPUSequencerWrapper:
    '''
    Other generic configuration scripts assume a matching number of sequencers
    and cpus. This wraps the instruction and data sequencer so they are
    compatible with the other scripts. This assumes all scripts are using
    connectCpuPorts/connectIOPorts to bind ports
    '''

    def __init__(self, iseq, dseq):
        # use this style due to __setattr__ override below
        self.__dict__['inst_seq'] = iseq
        self.__dict__['data_seq'] = dseq
        self.__dict__['support_data_reqs'] = True
        self.__dict__['support_inst_reqs'] = True
        # Compatibility with certain scripts that wire up ports
        # without connectCpuPorts
        self.__dict__['in_ports'] = dseq.in_ports

    def connectCpuPorts(self, cpu):
        assert(isinstance(cpu, BaseCPU))
        cpu.icache_port = self.inst_seq.in_ports
        for p in cpu._cached_ports:
            if str(p) != 'icache_port':
                exec('cpu.%s = self.data_seq.in_ports' % p)
        cpu.connectUncachedPorts(
            self.data_seq.in_ports, self.data_seq.interrupt_out_port)

    def connectIOPorts(self, piobus):
        self.data_seq.connectIOPorts(piobus)

    def __setattr__(self, name, value):
        setattr(self.inst_seq, name, value)
        setattr(self.data_seq, name, value)

class CHI_RNF(CHI_Node):
    '''
    Defines a CHI request node.
    Notice all contollers and sequencers are set as children of the cpus, so
    this object acts more like a proxy for seting things up and has no topology
    significance unless the cpus are set as its children at the top level
    '''

    def __init__(self, options,
                       src_die_id,
                       cpus,
                       ruby_system,
                       l1Icache_type, 
                       l1Dcache_type,
                       cache_line_size,
                       l1Iprefetcher_type=None,
                       l1Dprefetcher_type=None):
        super(CHI_RNF, self).__init__(ruby_system,src_die_id)

        self._block_size_bits = int(math.log(cache_line_size, 2))

        # All sequencers and controllers
        self._seqs   = []
        self._cntrls = []

        # Last level controllers in this node, i.e., the ones that will send
        # requests to the home nodes
        self._ll_cntrls = []

        self._cpus = cpus

        # First creates L1 caches and sequencers
        for cpu_id_per_cluster,cpu in enumerate(self._cpus):
            
            cpu.inst_sequencer = RubySequencer(version = Versions.getSeqId(),
                                         ruby_system = ruby_system,
                                         max_outstanding_requests = options.sequencer_outstanding_requests)
            cpu.data_sequencer = RubySequencer(version = Versions.getSeqId(),
                                         ruby_system = ruby_system,
                                         max_outstanding_requests = options.sequencer_outstanding_requests) 

            self._seqs.append(CPUSequencerWrapper(cpu.inst_sequencer,
                                                  cpu.data_sequencer))

            # caches
            l1i_cache = l1Icache_type(start_index_bit = self._block_size_bits,
                                      is_icache = True)

            l1d_cache = l1Dcache_type(start_index_bit = self._block_size_bits,
                                      is_icache = False)

            # Placeholders for future prefetcher support
            if l1Iprefetcher_type != None or l1Dprefetcher_type != None:
                m5.fatal('Prefetching not supported yet')
            l1i_pf = NULL
            l1d_pf = NULL

            # cache controllers
            cpu.l1i = CHI_L1Controller(options, ruby_system, cpu.inst_sequencer,
                                       l1i_cache, l1i_pf)

            cpu.l1d = CHI_L1Controller(options, ruby_system, cpu.data_sequencer,
                                       l1d_cache, l1d_pf)

            cpu.inst_sequencer.dcache = NULL
            cpu.data_sequencer.dcache = cpu.l1d.cache

            cpu.l1d.sc_lock_enabled = True

            cpu._ll_cntrls = [cpu.l1i, cpu.l1d]
            for c in cpu._ll_cntrls:
                self._cntrls.append(c)
                self.connectController(options, c)
                self._ll_cntrls.append(c)

    def getSequencers(self):
        return self._seqs

    def getAllControllers(self):
        return self._cntrls

    def getNetworkSideControllers(self):
        return self._cntrls

    def setDownstream(self, cntrls):
        for c in self._ll_cntrls:
            c.downstream_destinations = cntrls

    def getCpus(self):
        return self._cpus

    # Adds a private L2 for each cpu
    def addPrivL2Cache(self, options, cache_type, pf_type=None):
        self._ll_cntrls = []
        for cpu in self._cpus:
            l2_cache = cache_type(start_index_bit = self._block_size_bits,
                                  is_icache = False)
            if pf_type != None:
                m5.fatal('Prefetching not supported yet')
            l2_pf = NULL

            cpu.l2 = CHI_L2Controller(options, self._ruby_system, l2_cache, l2_pf)

            self._cntrls.append(cpu.l2)
            self.connectController(options, cpu.l2)

            self._ll_cntrls.append(cpu.l2)

            for c in cpu._ll_cntrls:
                c.downstream_destinations = [cpu.l2]
            cpu._ll_cntrls = [cpu.l2]

class CHI_HNF(CHI_Node):
    '''
    Encapsulates an HNF cache/directory controller.
    Before the first controller is created, the class method
    CHI_HNF.createAddrRanges must be called before creating any CHI_HNF object
    to set-up the interleaved address ranges used by the HNFs
    '''

    class NoC_Params(CHI_Node.NoC_Params):
        '''HNFs may also define the 'pairing' parameter to allow pairing'''
        pairing = None

    _addr_ranges = {}
    @classmethod
    def createAddrRanges(cls, 
                         options, 
                         sys_mem_ranges, 
                         cache_line_size,
                         hnfs):
        assert(len(hnfs) > 0)
        # Create the HNFs interleaved addr ranges
        block_size_bits = int(math.log(cache_line_size, 2))
        llc_bits = int(math.log(len(hnfs), 2))
        numa_bit = block_size_bits + llc_bits - 1
        for i, hnf in enumerate(hnfs):
            ranges = []
            for r in sys_mem_ranges:
                addr_range = AddrRange(r.start, size = r.size(),
                                        intlvHighBit = numa_bit,
                                        intlvBits = llc_bits,
                                        intlvMatch = i)
                # Check the StarFive MAS
                if (options.xor_addr_bits > 1):
                    masks=[0 for _ in range(llc_bits)]
                    for j in range(llc_bits) :
                        masks[j] = 0
                        total_xor_addr_bits = options.xor_addr_bits
                        for k in range(block_size_bits,48,llc_bits):
                            if total_xor_addr_bits <= 0:
                                break
                            masks[j] |= (1 << (j+k))
                            total_xor_addr_bits -= 1
                    addr_range.setIntlvMatch(i)
                    addr_range.setIntlvBits(llc_bits)
                    addr_range.setMasks(masks)
                ranges.append(addr_range)
            cls._addr_ranges[hnf] = (ranges, numa_bit)
            
    @classmethod
    def getAddrRanges(cls, hnf_idx):
        assert(len(cls._addr_ranges) != 0)
        return cls._addr_ranges[hnf_idx]

    # The CHI controller can be a child of this object or another if
    # 'parent' if specified
    def __init__(self, options, 
                       src_die_id, 
                       hnf_idx, 
                       ruby_system, 
                       llcache_type, 
                       snoopfilter_type, 
                       parent):
        super(CHI_HNF, self).__init__(ruby_system,src_die_id)

        addr_ranges,intlvHighBit = self.getAddrRanges(hnf_idx)
        # All ranges should have the same interleaving
        assert(len(addr_ranges) >= 1)

        ll_cache = llcache_type(start_index_bit = intlvHighBit + 1)
        real_snoopfilter = snoopfilter_type()
        self._cntrl = CHI_HNFController(options, ruby_system, ll_cache, real_snoopfilter, NULL, addr_ranges)

        if parent == None:
            self.cntrl = self._cntrl
        else:
            parent.cntrl = self._cntrl

        self.connectController(options, self._cntrl)

    def getAllControllers(self):
        return [self._cntrl]

    def getNetworkSideControllers(self):
        return [self._cntrl]

class CHI_MN(CHI_Node):
    '''
    Encapsulates a Misc Node controller.
    '''

    class NoC_Params(CHI_Node.NoC_Params):
        '''MNs may also define the 'pairing' parameter to allow pairing'''
        pairing = None


    # The CHI controller can be a child of this object or another if
    # 'parent' if specified
    def __init__(self, options,
                 src_die_id,
                 ruby_system, 
                 l1d_caches, 
                 early_nonsync_comp=False):
        super(CHI_MN, self).__init__(ruby_system,src_die_id)

        # MiscNode has internal address range starting at 0
        addr_range = AddrRange(0, size = "1kB")

        self._cntrl = CHI_MNController(ruby_system, addr_range, l1d_caches,
                                       early_nonsync_comp)

        self.cntrl = self._cntrl

        self.connectController(options, self._cntrl)

    def connectController(self, options, cntrl):
        CHI_Node.connectController(self, options, cntrl)

    def getAllControllers(self):
        return [self._cntrl]

    def getNetworkSideControllers(self):
        return [self._cntrl]

class CHI_SNF_Base(CHI_Node):
    '''
    Creates CHI node controllers for the memory controllers
    '''

    # The CHI controller can be a child of this object or another if
    # 'parent' if specified
    def __init__(self, options, src_die_id, ruby_system, parent):
        super(CHI_SNF_Base, self).__init__(ruby_system, src_die_id)

        self._cntrl = Memory_Controller(
                          version = Versions.getVersion(Memory_Controller),
                          ruby_system = ruby_system,
                          triggerQueue = TriggerMessageBuffer(),
                          responseFromMemory = MessageBuffer(),
                          requestToMemory = MessageBuffer(ordered = True),
                          reqRdy = TriggerMessageBuffer(),
                          number_of_TBEs=options.num_SNF_TBE,
                          snf_allow_retry=options.snf_allow_retry)

        self.connectController(options,self._cntrl)

        if parent:
            parent.cntrl = self._cntrl
        else:
            self.cntrl = self._cntrl

    def getAllControllers(self):
        return [self._cntrl]

    def getNetworkSideControllers(self):
        return [self._cntrl]

    def getMemRange(self, mem_ctrl):
        # TODO need some kind of transparent API for
        # MemCtrl+DRAM vs SimpleMemory
        if hasattr(mem_ctrl, 'range'):
            return mem_ctrl.range
        else:
            return mem_ctrl.dram.range

class CHI_SNF_BootMem(CHI_SNF_Base):
    '''
    Create the SNF for the boot memory
    '''

    def __init__(self, options, src_die_id, ruby_system, parent, bootmem):
        super(CHI_SNF_BootMem, self).__init__(options,src_die_id, ruby_system, parent)
        self._cntrl.memory_out_port = bootmem.port
        self._cntrl.addr_ranges = self.getMemRange(bootmem)

class CHI_SNF_MainMem(CHI_SNF_Base):
    '''
    Create the SNF for a list main memory controllers
    '''

    def __init__(self, options, src_die_id, ruby_system, parent, mem_ctrl = None):
        super(CHI_SNF_MainMem, self).__init__(options,src_die_id, ruby_system, parent)
        if mem_ctrl:
            self._cntrl.memory_out_port = mem_ctrl.port
            self._cntrl.addr_ranges = self.getMemRange(mem_ctrl)
        # else bind ports and range later
    
    def setAddrRange(self,addr_ranges):
        self._cntrl.addr_ranges = addr_ranges

class CHI_RNI_Base(CHI_Node):
    '''
    Request node without cache / DMA
    '''

    # The CHI controller can be a child of this object or another if
    # 'parent' if specified
    def __init__(self, options, src_die_id, ruby_system, parent):
        super(CHI_RNI_Base, self).__init__(ruby_system, src_die_id)

        self._sequencer = RubySequencer(version = Versions.getSeqId(),
                                         ruby_system = ruby_system,
                                         clk_domain = ruby_system.clk_domain)
        self._cntrl = CHI_DMAController(ruby_system, options, self._sequencer)

        if parent:
            parent.cntrl = self._cntrl
        else:
            self.cntrl = self._cntrl

        self.connectController(options, self._cntrl)

    def getAllControllers(self):
        return [self._cntrl]

    def getNetworkSideControllers(self):
        return [self._cntrl]

class CHI_RNI_DMA(CHI_RNI_Base):
    '''
        DMA controller wiredup to a given dma port
    '''
    def __init__(self, options, src_die_id, ruby_system, dma_port, parent):
        super(CHI_RNI_DMA, self).__init__(options, ruby_system, src_die_id, parent)
        assert(dma_port != None)
        self._sequencer.in_ports = dma_port

class CHI_RNI_IO(CHI_RNI_Base):
    '''
        DMA controller wiredup to ruby_system IO port
    '''
    def __init__(self, options, src_die_id, ruby_system, parent):
        super(CHI_RNI_IO, self).__init__(options, ruby_system, src_die_id, parent)
        ruby_system._io_port = self._sequencer



##################################################################################
######                      For cross die modelling                         ######
##################################################################################

class CHI_D2DNodeController(D2DNode_Controller):
    def __init__(self, options,
                       src_die_id,
                       ruby_system,
                       addr_ranges,
                       dst_die_id):
        super(CHI_D2DNodeController, self).__init__(
            version = Versions.getVersion(D2DNode_Controller),
            ruby_system = ruby_system
        )
       
        self.src_die_id    = src_die_id
        self.dst_die_id    = dst_die_id
        
        self.addr_ranges   = addr_ranges
        self.reqRdy        = MessageBuffer()
        
class CHI_D2DNode(CHI_Node):

    _addr_ranges = {}
    
    @classmethod
    def createAddrRanges(cls, 
                         options, 
                         sys_mem_ranges, 
                         cache_line_size, 
                         die_list):
        # block_size_bits = int(math.log(cache_line_size, 2))
        phys_mem_addr_bit = int(math.log(AddrRange(options.mem_size).size(),2))
        d2d_bits = int(math.log(len(die_list),2))
        numa_bit = phys_mem_addr_bit #block_size_bits + d2d_bits - 1
        for i, die_id in enumerate(die_list):
            ranges = []
            for r in sys_mem_ranges:
                addr_range = AddrRange(r.start, size = r.size(),
                                        intlvHighBit = numa_bit,
                                        intlvBits = d2d_bits,
                                        intlvMatch = i)
                ranges.append(addr_range)
            cls._addr_ranges[die_id] = (ranges, numa_bit)

    @classmethod
    def getAddrRanges(cls,die_id):
        assert(len(cls._addr_ranges) != 0)
        return cls._addr_ranges[die_id]

    def connectD2DBridge(self, 
                         options):
        class D2DBridgeBuffer(MessageBuffer):
            ordered = True
            randomization = 'ruby_system'
            
        d2dbridge_buff_depth    = 2
        d2dbridge_buff_deq_rate = 1
    
        assert(hasattr(self,'_cntrl'))
        self._cntrl.d2dnode_reqIn  = D2DBridgeBuffer(buffer_size=d2dbridge_buff_depth,max_dequeue_rate=d2dbridge_buff_deq_rate)
        self._cntrl.d2dnode_snpIn  = D2DBridgeBuffer(buffer_size=d2dbridge_buff_depth,max_dequeue_rate=d2dbridge_buff_deq_rate)
        self._cntrl.d2dnode_rspIn  = D2DBridgeBuffer(buffer_size=d2dbridge_buff_depth,max_dequeue_rate=d2dbridge_buff_deq_rate)
        self._cntrl.d2dnode_datIn  = D2DBridgeBuffer(buffer_size=d2dbridge_buff_depth,max_dequeue_rate=d2dbridge_buff_deq_rate)
        self._cntrl.d2dnode_reqOut = D2DBridgeBuffer(buffer_size=d2dbridge_buff_depth,max_dequeue_rate=d2dbridge_buff_deq_rate)
        self._cntrl.d2dnode_snpOut = D2DBridgeBuffer(buffer_size=d2dbridge_buff_depth,max_dequeue_rate=d2dbridge_buff_deq_rate)
        self._cntrl.d2dnode_rspOut = D2DBridgeBuffer(buffer_size=d2dbridge_buff_depth,max_dequeue_rate=d2dbridge_buff_deq_rate)
        self._cntrl.d2dnode_datOut = D2DBridgeBuffer(buffer_size=d2dbridge_buff_depth,max_dequeue_rate=d2dbridge_buff_deq_rate)

        self._d2d_bridge = D2DBridge(d2d_width=options.d2d_width,
                                     src_die_id=self._srd_die_id,
                                     dst_die_id=self._dst_die_id)
        self._d2d_bridge.chi_d2d_cntrl = self._cntrl

    def __init__(self,
                 options,
                 srd_die_id,
                 dst_die_id,
                 ruby_system):
        super(CHI_D2DNode, self).__init__(ruby_system, srd_die_id)
        self._srd_die_id = srd_die_id
        self._dst_die_id = dst_die_id
        self._d2d_bridge = None
        addr_ranges, intlvHighBit = self.getAddrRanges(dst_die_id)
        addr_range_str = [a.__str__() for a in addr_ranges]
        print(f'D2D@{self._srd_die_id}-->{self._dst_die_id} addr_range:{addr_range_str}')
        self._cntrl = CHI_D2DNodeController(options,
                                            srd_die_id,
                                            ruby_system,
                                            addr_ranges,
                                            dst_die_id)
        
        self.connectController(options, self._cntrl)

        self.connectD2DBridge(options)
    
    def getD2DBridge(self):
        assert(self._d2d_bridge is not None)
        return self._d2d_bridge
    
    def getSrcDstPair(self):
        return (self._srd_die_id, self._dst_die_id)
    
    def getAllControllers(self):
        return [self._cntrl]

    def getNetworkSideControllers(self):
        return [self._cntrl]

class CHI_HA(CHI_Node):
    """
        Required for maintaining 
        cross die coherence. Also
        inherits from the common
        Cache controller.
    """
    class NoC_Params(CHI_Node.NoC_Params):
        '''HNFs may also define the 'pairing' parameter to allow pairing'''
        pairing = None

    _addr_ranges = {}

    def __init__(self, 
                 options,
                 srd_die_id,
                 addr_ranges,
                 ruby_system):
        super(CHI_HA, self).__init__(ruby_system, srd_die_id)
        addr_range_str = [a.__str__() for a in addr_ranges]
        self._cntrl = HA_Controller(
            version = Versions.getVersion(HA_Controller),
            ruby_system = ruby_system,
            addr_ranges = addr_ranges,
            data_channel_size = 128,
            triggerQueue = TriggerMessageBuffer(),
            reqRdy = TriggerMessageBuffer())
        
        self.connectController(options, self._cntrl)

    def getAllControllers(self):
        return [self._cntrl]

    def getNetworkSideControllers(self):
        return [self._cntrl]

class CHI_HNFController_Snoopable(CHI_HNFController):
    """
        HNF Controller, that can accept
        snoops from the downstream HA/D2DNodes
    """
    def __init__(self, options,
                       ruby_system,
                       cache,
                       real_snoopfilter,
                       prefetcher,
                       addr_ranges):
        super(CHI_HNFController_Snoopable, self).__init__(options,
                                                          ruby_system,
                                                          cache,
                                                          real_snoopfilter,
                                                          prefetcher,
                                                          addr_ranges)
        self.is_HN = False

class CHI_HNF_Snoopable(CHI_Node):

    class NoC_Params(CHI_Node.NoC_Params):
        '''HNFs may also define the 'pairing' parameter to allow pairing'''
        pairing = None
    
    _addr_ranges = {}
    
    @classmethod
    def createAddrRanges(cls, 
                         options, 
                         sys_mem_ranges, 
                         cache_line_size,
                         hnfs):
        assert(len(hnfs) > 0)
        # Create the HNFs interleaved addr ranges
        block_size_bits = int(math.log(cache_line_size, 2))
        llc_bits = int(math.log(len(hnfs), 2))
        numa_bit = block_size_bits + llc_bits - 1
        for i, hnf in enumerate(hnfs):
            ranges = []
            for r in sys_mem_ranges:
                addr_range = AddrRange(r.start, size = r.size(),
                                        intlvHighBit = numa_bit,
                                        intlvBits = llc_bits,
                                        intlvMatch = i)
                # Check the StarFive MAS
                if (options.xor_addr_bits > 1):
                    masks=[0 for _ in range(llc_bits)]
                    for j in range(llc_bits) :
                        masks[j] = 0
                        total_xor_addr_bits = options.xor_addr_bits
                        for k in range(block_size_bits,48,llc_bits):
                            if total_xor_addr_bits <= 0:
                                break
                            masks[j] |= (1 << (j+k))
                            total_xor_addr_bits -= 1
                    addr_range.setIntlvMatch(i)
                    addr_range.setIntlvBits(llc_bits)
                    addr_range.setMasks(masks)
                ranges.append(addr_range)
            cls._addr_ranges[hnf] = (ranges, numa_bit)
    
    @classmethod
    def getAddrRanges(cls, hnf_idx):
        assert(len(cls._addr_ranges) != 0)
        return cls._addr_ranges[hnf_idx]
    
    def __init__(self, options,
                       src_die_id,
                       hnf_idx,
                       ruby_system,
                       llcache_type,
                       snoopfilter_type,
                       parent):
        super(CHI_HNF_Snoopable, self).__init__(ruby_system,src_die_id)

        addr_ranges,intlvHighBit = self.getAddrRanges(hnf_idx)
        # All ranges should have the same interleaving
        assert(len(addr_ranges) >= 1)
        
        ll_cache = llcache_type(start_index_bit = intlvHighBit + 1)
        real_snoopfilter = snoopfilter_type()
        self._cntrl = CHI_HNFController_Snoopable(options, ruby_system, ll_cache, real_snoopfilter, NULL, addr_ranges)

        if parent == None:
            self.cntrl = self._cntrl
        else:
            parent.cntrl = self._cntrl

        self.connectController(options, self._cntrl)
    
    def setDownstream(self, cntrls):
        self._cntrl.downstream_destinations = cntrls
        
    def getAllControllers(self):
        return [self._cntrl]

    def getNetworkSideControllers(self):
        return [self._cntrl]
        
    