#!/usr/bin/env python3

## USAGE:
## This parser reads stats.txt generated by run_arm_fs.sh and dump results to stats.log
## It reads in variables.txt generated by ./run_arm_fs.py [-r|-d] REAL and obtain env variables from it.

## To add features to this file, you can modify the following functions:
## parse_stats(): parse one line at a time in stats.txt. You can add more regexp patterns to match more stats you want.
## get_all_sim_dir(): find all generated sub folders of a workspace of simulation. You donot need to modify it.
## variable_file_parser(): parse variables.txt and add env variables to Namespace args. You can add more env variables to var_list if you want.
## parse_stats_file(): parse one stats.txt at a time and generates stats.log(csv). It returns agg_df which is an entry in stats_all.log(csv). 
##                     You can modify header of agg_df to add/delete columns of stats_all.log(csv)


import re
from typing import List
import logging
from functools import reduce
import argparse
import ast
import os
import pandas as pd

# add a new log level
LOG_MSG = 60
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
logging.addLevelName(LOG_MSG, 'MSG')

# sim_tick's pattern & clk_domain's pattern
sim_tick_pat = re.compile('^simTicks\s+(\d+)')
clk_domain_pat = re.compile('^system\.cpu_clk_domain\.clock\s+(\d+)')
sim_freq_pat = re.compile('^simFreq\s+(\d+)')

# llc_demand's pattern
# three groups we need : 1) hnf's id 2) hit/miss/access 3) num of hit/miss/access
# idx can be nullstr, not None
llc_demand_pat = re.compile('^system\.ruby\.hnf(\d*)\.cntrl\.cache\.m_demand_([a-z]+)\s+(\d+)')
llc_txn_pat = re.compile('^system\.ruby\.hnf(\d*)\.cntrl\.inTransLatHist\.(ReadShared|ReadUnique_PoC|WriteBackFull)\.total\s+(\d+)')
l2p_txn_pat = re.compile('^system\.cpu(\d*)\.l2\.inTransLatHist\.(ReadShared|ReadUnique|WriteBackFull)\.total\s+(\d+)')

# l1d, l1i, l2p's pattern
# four groups we need: 1) cpu's id 2) l1d/l1i/l2 3) hit/miss/access 4) num of hit/miss/access
priv_cache_demand_pat = re.compile('^system\.cpu(\d*)\.(\w*)\.cache\.m_demand_([a-z]+)\s+(\d+)')

# ddr's pattern
# groupes we need: 1) mem_ctrls's id 2) write/read 3) num of read/write requests
ddr_pat = re.compile('^system\.mem_ctrls(\d*)\.([a-z]+)Reqs\s+(\d+)')

# cpu's pattern
# groups we need: 1) cpu's id 2) load/store 3) num of load/store requests
cpu_inst_pat = re.compile('^system\.cpu(\d*)\.exec_context\.thread_0\.num(Load|Store|)Insts\s+(\d+)')
cpu_o3inst_pat = re.compile('^system\.cpu(\d*)\.committedInsts\s+(\d+)')
cpu_o3mem_pat = re.compile('^system\.cpu(\d*)\.commit\.(loads|memRefs)\s+(\d+)')
cpu_cycle_pat = re.compile('^system\.cpu(\d*)\.numCycles\s+(\d+)')
cpu_qscyc_pat = re.compile('^system\.cpu(\d*)\.quiesceCycles\s+(\d+)')

## sequencer's pattern
## TODO: Current stats taken from two parts. 
## 1) In seq.csv, stats.txt, only cpu data sequencers are taken into account
## 2) In all_stats.txt, both cpu and dma sequencers are taken into account
## groups we need: 1) cpu's id 2) LD/ST 3) mean/min_value/max_value 4) latency
seq_lat_cpu_pat = re.compile('^system\.cpu(\d*)\.data_sequencer\.(LD|ST|LL|SC)LatDist::(mean|samples)\s+(\d+\.?\d+|\d+)')
seq_lat_all_pat = re.compile('^system\.ruby\.RequestType\.(LD|ST|Load_Linked|Store_Conditional)\.latency_hist_seqr::mean\s+(\d+\.?\d+|\d+)')


## snoop's pattern
llc_snpout_pat = re.compile('^system\.ruby\.hnf(\d*)\.cntrl\.snpOut\.m_msg_count\s+(\d+)')
l2p_snpin_pat = re.compile('^system\.cpu(\d*)\.l2\.snpIn\.m_msg_count\s+(\d+)')

## snoop filter's pattern
## groups we need: 1) hnf's id 2) misses/hits/alloc/accesses 3)num of misses/hits/alloc/accesses
snp_ftr_pat = re.compile('^system\.ruby\.hnf(\d*)\.cntrl\.m_snoopfilter_(misses|hits|alloc|accesses)\s+(\d+)')

class Printable:
    def __repr__(self):
        return str(vars(self))

class CPU(Printable):
    # CPU type
    typ = None

    def __init__(self,id=0,read=0,write=0,inst=0, cycle=0, qscyc=0):
        self.id = id
        self.read = read
        self.write = write
        self.inst = inst
        self.cycle = cycle
        self.qscyc = qscyc

    @classmethod
    def cpu_ipc(cls, cpu_df:pd.DataFrame):
        cpu_sum = pd.Series(cpu_df.sum(), name='Total')
        cpu_df = pd.concat([cpu_df, cpu_sum.to_frame().T])
        cpu_df['ipc'] = cpu_df['inst']/cpu_df['cycle']
        return cpu_df


class SEQ(Printable):
    ## TODO: sequencer latency use different data source
    ## for individual latency, use self-defined stats, e.g. LDLatDist
    ## for overall average latency, use GEM5 profiling stats, e.g. LD
    ## please see Sequencer.cc for more details

    ## cls variables for storing overall average latency
    ld_lat = 0
    st_lat = 0
    ll_lat = 0
    sc_lat = 0

    ## instance varaibles for storing individual latency
    def __init__(self,id=0):
        self.id = id

class Cache(Printable):
    def __init__(self,hit=0,miss=0,access=0):
        self.hit = hit
        self.miss = miss
        self.access = access

    @classmethod
    def cache_hit_rate(cls, cache_df:pd.DataFrame):
        cache_sum = pd.Series(cache_df.sum(), name='Total')
        cache_df = pd.concat([cache_df, cache_sum.to_frame().T])
        cache_df['hit_rate'] = cache_df['hit']/cache_df['access']
        return cache_df
    
    @classmethod
    def cache_readTxn(cls, cache_df:pd.DataFrame):
        cache_df['ReadS/U'] = cache_df['ReadS']+cache_df['ReadU']
        return cache_df

class LLC(Cache):
    def __init__(self,hit=0,miss=0,access=0,reack=0,ReadS=0,ReadU=0,WriteB=0):
        super(LLC, self).__init__(hit,miss,access)
        self.ReadS = ReadS
        self.ReadU = ReadU
        self.WriteB = WriteB
        self.reack=reack

class PrivCache(Cache):
    def __init__(self,cpu_id=0,hit=0,miss=0,access=0):
        super(PrivCache, self).__init__(hit,miss,access)
        self.cpu_id=cpu_id

class L1D(PrivCache):
    pass

class L1I(PrivCache):
    pass

class SNP(Cache):
    def __init__(self, llc_id, hit=0,miss=0,access=0,alloc=0):
        super(SNP,self).__init__(hit,miss,access)
        self.llc_id=llc_id
        self.alloc=alloc

    @classmethod
    def cache_miss_rate(cls, cache_df:pd.DataFrame):
        cache_sum = pd.Series(cache_df.sum(), name='Total')
        cache_df = pd.concat([cache_df, cache_sum.to_frame().T])
        cache_df['miss_rate'] = cache_df['miss']/cache_df['access']
        return cache_df

class L2P(PrivCache):
    def __init__(self, ReadS=0, ReadU=0, WriteB=0):
        self.ReadS = ReadS
        self.ReadU = ReadU
        self.WriteB = WriteB

class DDR(Printable):
    def __init__(self,id=0,read=0,write=0):
        self.id = id
        self.read = read
        self.write = write

class CLK(Printable):
    def __init__(self, sim_tick=None, clk_domain=None, sim_freq=None):
        self.sim_tick = sim_tick
        self.clk_domain = clk_domain
        self.sim_freq = sim_freq
    
    @classmethod
    def sim_second(cls, clk_df:pd.DataFrame):
        clk_df['sim_second'] = clk_df['sim_tick']/clk_df['sim_freq']
        return clk_df

# parse one line each time
def parse_stats(line, clk:CLK, cpus:List[CPU], seqs:List[SEQ], llcs:List[LLC], snps:List[SNP], ddrs:List[DDR], l1ds:List[L1D], l1is:List[L1I], l2ps:List[L2P]):
    sim_tick_sch = re.search(sim_tick_pat, line)
    clk_domain_sch = re.search(clk_domain_pat, line)
    sim_freq_sch = re.search(sim_freq_pat, line)
    llc_demand_sch = re.search(llc_demand_pat, line)
    l2p_txn_sch = re.search(l2p_txn_pat, line)
    llc_txn_sch = re.search(llc_txn_pat, line)
    ddr_sch = re.search(ddr_pat, line)
    cpu_inst_sch = re.search(cpu_inst_pat, line) if CPU.typ != 'O3CPU' else None
    cpu_o3inst_sch = re.search(cpu_o3inst_pat, line) if CPU.typ == 'O3CPU' else None
    cpu_o3mem_sch = re.search(cpu_o3mem_pat, line) if CPU.typ == 'O3CPU' else None
    cpu_cycle_sch = re.search(cpu_cycle_pat, line)
    cpu_qscyc_sch = re.search(cpu_qscyc_pat, line) if CPU.typ == 'O3CPU' else None
    priv_cache_sch = re.search(priv_cache_demand_pat, line)
    seq_lat_cpu_sch = re.search(seq_lat_cpu_pat, line)
    seq_lat_all_sch = re.search(seq_lat_all_pat, line)
    llc_snpout_sch = re.search(llc_snpout_pat, line)
    l2p_snpin_sch = re.search(l2p_snpin_pat, line)
    snp_ftr_sch = re.search(snp_ftr_pat, line)

    if clk.sim_tick==None and sim_tick_sch:
        clk.sim_tick = int(sim_tick_sch.group(1))
    
    elif clk.clk_domain==None and clk_domain_sch:
        clk.clk_domain = int(clk_domain_sch.group(1))

    elif clk.sim_freq==None and sim_freq_sch:
        clk.sim_freq = int(sim_freq_sch.group(1))
    
    elif llc_demand_sch:
        llc_id = 0 if len(llcs) == 1 else int(llc_demand_sch.group(1))
        
        llc_status = llc_demand_sch.group(2) # hit/miss/access
        llc_num_op:int = int(llc_demand_sch.group(3))

        if llc_status == 'hits':
            llcs[llc_id].hit = llc_num_op
        elif llc_status == 'misses':
            llcs[llc_id].miss = llc_num_op
        elif llc_status == 'accesses':
            llcs[llc_id].access = llc_num_op
        else:
            raise TypeError(f'parse_stats():llc_demand_sch: Unrecognized llc_status {llc_status}')
    
    # system.ruby.hnf(\d*).cntrl.inTransLatHist.(ReadShared|ReadUnique_PoC|WriteBackFull).total\s+(\d+)
    elif llc_txn_sch:
        llc_id = 0 if len(llcs) == 1 else int(llc_txn_sch.group(1))

        llc_txn:str = llc_txn_sch.group(2)
        llc_num_txn:int = int(llc_txn_sch.group(3))

        if llc_txn == 'ReadShared':
            llcs[llc_id].ReadS = llc_num_txn
        elif llc_txn == 'ReadUnique_PoC':
            llcs[llc_id].ReadU = llc_num_txn
        elif llc_txn == 'WriteBackFull':
            llcs[llc_id].WriteB = llc_num_txn
        else:
            raise TypeError(f'parse_stats():llc_txn_sch: Unrecognized llc_txn {llc_txn}')
        
    # system.cpu(\d*).l2.inTransLatHist.(ReadShared|ReadUnique|WriteBackFull).total\s+(\d+)
    elif l2p_txn_sch:
        cpu_id = 0 if len(cpus) == 1 else int(l2p_txn_sch.group(1))

        l2p_txn:str = l2p_txn_sch.group(2)
        l2p_num_txn:int = int(l2p_txn_sch.group(3))

        if l2p_txn == 'ReadShared':
            l2ps[cpu_id].ReadS = l2p_num_txn
        elif l2p_txn == 'ReadUnique':
            l2ps[cpu_id].ReadU = l2p_num_txn
        elif l2p_txn == 'WriteBackFull':
            l2ps[cpu_id].WriteB = l2p_num_txn
        else:
            raise TypeError(f'parse_stats():l2p_txn_sch: Unrecognized l2p_txn {l2p_txn}')

    elif priv_cache_sch:
        cpu_id:int = 0 if len(cpus) == 1 else int(priv_cache_sch.group(1))
        cache_name = priv_cache_sch.group(2) # l1d, l1i, l2
        cache_status = priv_cache_sch.group(3)
        cache_num_op:int = int(priv_cache_sch.group(4))

        cache_dict = {'l1d':l1ds, 'l1i':l1is, 'l2':l2ps}
        if cache_status == 'hits':
            cache_dict[cache_name][cpu_id].hit = cache_num_op
        elif cache_status == 'misses':
            cache_dict[cache_name][cpu_id].miss = cache_num_op
        elif cache_status == 'accesses':
            cache_dict[cache_name][cpu_id].access = cache_num_op
        else:
            raise TypeError(f'parse_stats():priv_cache_sch: Unrecognized cache_status {cache_status}')

    elif ddr_sch:
        ddr_id = 0 if len(ddrs) == 1 else int(ddr_sch.group(1))
        ddr_op = ddr_sch.group(2) # read/write
        ddr_num_op:int = int(ddr_sch.group(3))

        if ddr_op == 'read':
            ddrs[ddr_id].read = ddr_num_op
        elif ddr_op == 'write':
            ddrs[ddr_id].write = ddr_num_op
        else:
            raise TypeError(f'parse_stats():ddr_sch: Unrecognized ddr_op {ddr_op}')

    elif cpu_inst_sch:
        cpu_id = 0 if len(cpus) == 1 else int(cpu_inst_sch.group(1))
        cpu_op = cpu_inst_sch.group(2) # Load/Store
        cpu_num_op:int = int(cpu_inst_sch.group(3))

        if cpu_op == 'Load':
            cpus[cpu_id].read = cpu_num_op
        elif cpu_op == 'Store':
            cpus[cpu_id].write = cpu_num_op
        elif cpu_op == '':
            cpus[cpu_id].inst = cpu_num_op
        else:
            raise TypeError(f'parse_stats():cpu_op: Unrecognized cpu_op {cpu_op}')
        
    elif cpu_o3inst_sch:
        cpu_id = 0 if len(cpus) == 1 else int(cpu_o3inst_sch.group(1))
        cpus[cpu_id].inst = int(cpu_o3inst_sch.group(2))

    elif cpu_o3mem_sch:
        cpu_id = 0 if len(cpus) == 1 else int(cpu_o3mem_sch.group(1))
        cpu_op = cpu_o3mem_sch.group(2)
        cpu_num_op:int = int(cpu_o3mem_sch.group(3))

        if cpu_op == 'memRefs':
            cpus[cpu_id].write = cpu_num_op
        elif cpu_op == 'loads':
            cpus[cpu_id].read = cpu_num_op
            cpus[cpu_id].write = cpus[cpu_id].write - cpus[cpu_id].read
        else:
            raise TypeError(f'parse_stats():cpu_o3mem: Unrecognized cpu_op {cpu_op}')
    
    elif cpu_cycle_sch:
        cpu_id = 0 if len(cpus) == 1 else int(cpu_cycle_sch.group(1))
        cpus[cpu_id].cycle = int(cpu_cycle_sch.group(2))

    elif cpu_qscyc_sch:
        cpu_id = 0 if len(cpus) == 1 else int(cpu_qscyc_sch.group(1))
        cpus[cpu_id].qscyc = int(cpu_qscyc_sch.group(2))

    elif seq_lat_cpu_sch:
        seq_id = 0 if len(seqs) == 1 else int(seq_lat_cpu_sch.group(1))
        seq_op:str = seq_lat_cpu_sch.group(2) # LD/ST/LL/SC
        seq_stats:str = seq_lat_cpu_sch.group(3) # mean|samples
        seq_data:float = float(seq_lat_cpu_sch.group(4))

        setattr(seqs[seq_id], seq_op+'_'+seq_stats, seq_data)

    elif seq_lat_all_sch:
        seq_op:str = seq_lat_all_sch.group(1)
        seq_lat:float = float(seq_lat_all_sch.group(2))

        if seq_op == 'LD':
            SEQ.ld_lat = seq_lat
        elif seq_op == 'ST':
            SEQ.st_lat = seq_lat
        elif seq_op == 'Load_Linked':
            SEQ.ll_lat = seq_lat
        elif seq_op == 'Store_Conditional':
            SEQ.sc_lat = seq_lat
        else:
            raise TypeError(f'parse_stats():seq_lat_all_sch: Unrecognized seq_op {seq_op}')
    
    # ^system\.ruby\.hnf(\d*)\.cntrl\.snpout\.m_msg_count\s+(\d+)
    elif llc_snpout_sch:
        llc_id = 0 if len(llcs) == 1 else int(llc_snpout_sch.group(1))
        llcs[llc_id].snpOut = int(llc_snpout_sch.group(2))
        
    # ^system\.cpu(\d*)\.l2\.snpin\.m_msg_count\s+(\d+)
    elif l2p_snpin_sch:
        cpu_id = 0 if len(cpus) == 1 else int(l2p_snpin_sch.group(1))
        l2ps[cpu_id].snpIn = int(l2p_snpin_sch.group(2))

    # groups we need: 1) hnf's id 2) misses/hits/alloc/accesses 3)num of misses/hits/alloc/accesses
    elif snp_ftr_sch:
        llc_id = 0 if len(llcs) == 1 else int(snp_ftr_sch.group(1))
        snp_ftr_op = snp_ftr_sch.group(2)
        snp_ftr_num_op = int(snp_ftr_sch.group(3))

        if snp_ftr_op == 'misses':
            snps[llc_id].miss = snp_ftr_num_op
        elif snp_ftr_op == 'hits':
            snps[llc_id].hit = snp_ftr_num_op
        elif snp_ftr_op == 'alloc':
            snps[llc_id].alloc = snp_ftr_num_op
        elif snp_ftr_op == 'accesses':
            snps[llc_id].access = snp_ftr_num_op
        else:
            raise TypeError(f'parse_stats():snp_ftr_sch: Unrecognized snp_ftr_op {snp_ftr_op}')


def get_all_sim_dir(root_dir):
    # Recursive function to find all files named "stats.txt" in the folder and its subfolders
    def find_output_dirs(folder):
        output_dirs = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file == "stats.txt":
                    # Check if the filepath contains "CHECKPNT"
                    if "CHECKPNT" not in root:
                        output_dirs.append(root)
                    else:
                        logging.debug(f'Skip: {root}')
        return output_dirs

    # Call the function to find all "stats.txt" files in "ARM_FS" folder and filter out files with "CHECKPNT" in their path
    output_dirs = find_output_dirs(root_dir)

    [logging.debug(f'Selected: {file}') for file in output_dirs]

    return output_dirs


def variable_file_parser(args:argparse.Namespace, variable_file_path):
    all_var_dict = {}
    variable_file_path = os.path.join(variable_file_path,'variables.txt')
    with open(variable_file_path, 'r') as f:
        variables = f.readlines()
    for var in variables:
        kvpair= var.strip().split('=')
        if len(kvpair) == 2:
            all_var_dict[kvpair[0]]=kvpair[1]
    logging.debug(f'variable_file_parser:all_var_dict: {all_var_dict}')

    var_list = {
        'BENCHMARK':str,
        'NUMCPUS':int,
        'NUM_LLC':int,
        'RESTORE_CPU':str,
        'SNPFILTER_ENTRIES':str,
        'NUM_MEM':int,
        'NUM_DDR_Side':int,
        'NUM_DDR_XP':int,
        'DCT':ast.literal_eval,
        'DMT':ast.literal_eval,
        'HNF_TBE':int,
        'SNF_TBE':int,
        'SEQ_TBE':int,
        'TRANS':int,
        'LINKWIDTH':int,
        'VC_PER_VNET':int,
        'BUFFER_SIZE':int,
        'NETWORK':str,
        'OUTPUT_DIR':str,
        'l1d_size':str,
        'l1i_size':str,
        'l2_size':str,
        'l3_size':str,
        'LLC_REPL':str
    }

    var_dict = dict()
    for key,ops in var_list.items():
        # logging.info(f'key={key}, value={all_var_dict.get(key)}, ops={ops}')    
        try:
            var_dict[key]=ops(all_var_dict.get(key))
        except:
            pass
    # {key:ops(all_var_dict.get(key)) for key,ops in var_list.items()}

    logging.debug(f'variable_file_parser:var_dict: {var_dict}')

    import copy
    args = copy.deepcopy(args)

    for key,val in var_dict.items():
        setattr(args, key, val)

    logging.debug(f'variable_file_parser:args: {args}')

    return args


def parse_stats_file(args:argparse.Namespace):
    CPU.typ = args.RESTORE_CPU # O3CPU or other types
    cpus = [CPU(i) for i in range(args.NUMCPUS)]
    seqs = [SEQ(i) for i in range(args.NUMCPUS)]
    llcs = [LLC(i) for i in range(args.NUM_LLC)]
    snps = [SNP(i) for i in range(args.NUM_LLC)]
    l1ds = [L1D(i) for i in range(args.NUMCPUS)]
    l1is = [L1I(i) for i in range(args.NUMCPUS)]
    l2ps = [L2P(i) for i in range(args.NUMCPUS)]
    ddrs = [DDR(i) for i in range(args.NUM_MEM)]
    clk = CLK()

    import subprocess
    stats_file_path = os.path.join(args.OUTPUT_DIR, 'stats.txt')
    output_file_path = os.path.join(args.OUTPUT_DIR, 'stats.log')
    out = subprocess.getoutput('wc -l %s' % stats_file_path)
    if int(out.split()[0]) == 0:
        logging.critical(f'{stats_file_path} has no content. Please check if your test has finished.')
        return None # return None instead of shutting down the whole parser

    # Only parse the stats before m5_reset_stats 
    with open(stats_file_path, 'r') as f:
        for idx,line in enumerate(f):
            if line == '---------- End Simulation Statistics   ----------\n':
                break
            parse_stats(line, clk, cpus, seqs, llcs, snps, ddrs, l1ds, l1is, l2ps)
    
    logging.debug(f'clk:{clk}\ncpus:{cpus}\nseqs:{seqs}\nllcs:{llcs}\nsnps:{snps}\nl1ds:{l1ds}\nl1is:{l1is}\nl2ps:{l2ps}\nddrs:{ddrs}')

    df_dict = {
        'clk': pd.DataFrame([vars(clk)]),
        'cpu': pd.DataFrame([vars(item) for item in cpus]),
        'seq': pd.DataFrame([vars(item) for item in seqs]),
        'llc': pd.DataFrame([vars(item) for item in llcs]),
        'snp': pd.DataFrame([vars(item) for item in snps]),
        'l1d': pd.DataFrame([vars(item) for item in l1ds]),
        'l1i': pd.DataFrame([vars(item) for item in l1is]),
        'l2p': pd.DataFrame([vars(item) for item in l2ps]),
        'ddr': pd.DataFrame([vars(item) for item in ddrs]),
    }    

    # cache hit rate
    df_dict['l1d'] = Cache.cache_hit_rate(df_dict['l1d'])
    df_dict['l1i'] = Cache.cache_hit_rate(df_dict['l1i'])
    df_dict['l2p'] = Cache.cache_hit_rate(df_dict['l2p'])
    df_dict['llc'] = Cache.cache_hit_rate(df_dict['llc'])
    
    # cache readS/U
    df_dict['llc'] = Cache.cache_readTxn(df_dict['llc'])
    df_dict['l2p'] = Cache.cache_readTxn(df_dict['l2p'])

    # cpu ipc
    df_dict['cpu'] = CPU.cpu_ipc(df_dict['cpu'])

    # snoop filter
    df_dict['snp'] = SNP.cache_miss_rate(df_dict['snp'])

    # clk
    df_dict['clk'] = CLK.sim_second(df_dict['clk'])

    logging.debug(f'DataFrames:\ncpu:\n{df_dict["cpu"]}\nl1d:\n{df_dict["l1d"]}\nl1i:\n{df_dict["l1i"]}\nl2p:\n{df_dict["l2p"]}\nllc:\n{df_dict["llc"]}')

    [df.to_csv(f'{args.OUTPUT_DIR}/{name}.csv') for name, df in df_dict.items()]

    with open(output_file_path, 'w') as f:
        f.write(f'clk:\n{df_dict["clk"]}\n\ncpu:\n{df_dict["cpu"]}\n\nseq:\n{df_dict["seq"]}\n\nl1d:\n{df_dict["l1d"]}\n\nl1i:\n{df_dict["l1i"]}\n\nl2p:\n{df_dict["l2p"]}\n\nllc:\n{df_dict["llc"]}\n\nsnoop filter:\n{df_dict["snp"]}')

    logging.info(f'written to {output_file_path}')

    # add/delete headers here to customize the stats you want to put inside all_stats.log
    # aggregate stats together
    agg_df = pd.DataFrame({
        'benchmark':[args.BENCHMARK],
        'sim_second':[clk.sim_tick/clk.sim_freq],
        '#cpu':[args.NUMCPUS],
        '#llc':[args.NUM_LLC],
        '#mem':[args.NUM_MEM],
        'ddr_xp':[args.NUM_DDR_XP],
        'ddr_side':[args.NUM_DDR_Side],
        '#sf_entry':[args.SNPFILTER_ENTRIES],
        'dct':[args.DCT],
        'dmt':[args.DMT],
        'hnf_tbe':[args.HNF_TBE],
        'seq_tbe':[args.SEQ_TBE],
        'snf_tbe':[args.SNF_TBE],
        'trans':[args.TRANS],
        'linkwid':[args.LINKWIDTH],
        'vc/vnet':[args.VC_PER_VNET],
        'bufsz':[args.BUFFER_SIZE] if hasattr(args, "BUFFER_SIZE") else None,
        'net':[args.NETWORK],
        'l1d_size':[args.l1d_size],
        'l3repl':[args.LLC_REPL],
        # 'l1i_size':[args.l1i_size],
        'l2_size':[args.l2_size],
        'l3_size':[args.l3_size],
        'cpu_ipc':[df_dict['cpu'].loc['Total','ipc']],
        'cpu_qscyc':[df_dict['cpu'].loc['Total','qscyc']],
        'ld_lat':SEQ.ld_lat,
        'st_lat':SEQ.st_lat,
        # 'll_lat':SEQ.ll_lat,
        # 'sc_lat':SEQ.sc_lat,
        'l1d_hitrate':[df_dict['l1d'].loc['Total','hit_rate']],
        'l2p_read': [df_dict['l2p'].loc['Total','ReadS/U']],
        'l2p_write': [df_dict['l2p'].loc['Total','WriteB']],
        # 'l2p_hit':[df_dict['l2p'].loc['Total','hit']],
        # 'l2p_miss':[df_dict['l2p'].loc['Total','miss']],
        # 'l2p_access':[df_dict['l2p'].loc['Total','access']],
        'l2p_hitrate':[df_dict['l2p'].loc['Total','hit_rate']],
        'llc_read': [df_dict['llc'].loc['Total','ReadS/U']],
        'llc_write': [df_dict['llc'].loc['Total','WriteB']],
        # 'llc_hit':[df_dict['llc'].loc['Total','hit']],
        # 'llc_miss':[df_dict['llc'].loc['Total','miss']],
        # 'llc_access':[df_dict['llc'].loc['Total','access']],
        'llc_hitrate':[df_dict['llc'].loc['Total','hit_rate']],
        'sf_missrate':[df_dict['snp'].loc['Total','miss_rate']]
    },index=None)
    if args.print_dir:
        agg_df['outdir'] = args.OUTPUT_DIR

    logging.debug(f'agg_pd: {agg_df}')
    return agg_df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--root-dir', required=True)
    parser.add_argument('--print-dir', action='store_true')
    args = parser.parse_args()

    sim_dir_list = get_all_sim_dir(args.root_dir)
    logging.debug(f'output_dir_list: {sim_dir_list}')

    sim_data_dict = {sim_dir:variable_file_parser(args, sim_dir) for sim_dir in sim_dir_list}
    logging.debug(f'data_dict: {sim_data_dict}')

    agg_df = pd.DataFrame()
    for _,sim_data in sim_data_dict.items():
        agg_df = pd.concat([agg_df, parse_stats_file(sim_data)])

    # dump all stats in a single file
    with open(f'{args.root_dir}/all_stats.log', 'w') as f:
        f.write(agg_df.to_string(index=False, header=True))
    agg_df.to_csv(f'{args.root_dir}/all_stats.csv',index=False)
    logging.info(f'Written to {args.root_dir}/all_stats.log(csv).')
