#!/usr/bin/env python3

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
clk_domain_pat = re.compile('^system.cpu_clk_domain.clock\s+(\d+)')

# llc_demand's pattern
# three groups we need : 1) hnf's id 2) hit/miss/access 3) num of hit/miss/access
# idx can be nullstr, not None
llc_demand_pat = re.compile('^system.ruby.hnf(\d*).cntrl.cache.m_demand_([a-z]+)\s+(\d+)')
llc_txn_pat = re.compile('^system.ruby.hnf(\d*).cntrl.inTransLatHist.(ReadShared|ReadUnique_PoC|WriteBackFull).total\s+(\d+)')
l2p_txn_pat = re.compile('^system.cpu(\d*).l2.inTransLatHist.(ReadShared|ReadUnique|WriteBackFull).total\s+(\d+)')

# l1d, l1i, l2p's pattern
# four groups we need: 1) cpu's id 2) l1d/l1i/l2 3) hit/miss/access 4) num of hit/miss/access
priv_cache_demand_pat = re.compile('^system.cpu(\d*).(\w*).cache.m_demand_([a-z]+)\s+(\d+)')

# ddr's pattern
# groupes we need: 1) mem_ctrls's id 2) write/read 3) num of read/write requests
ddr_pat = re.compile('system.mem_ctrls(\d*).([a-z]+)Reqs\s+(\d+)')

# cpu's pattern
# groups we need: 1) cpu's id 2) load/store 3) num of load/store requests
cpu_inst_pat = re.compile('^system.cpu(\d*).exec_context.thread_0.num(Load|Store|)Insts\s+(\d+)')
cpu_cycle_pat = re.compile('^system.cpu(\d*).numCycles\s+(\d+)')

def test_cpu():
    l1 = "system.cpu0.exec_context.thread_0.numLoadInsts     18911203                       # Number of load instructions (Count)\n"
    l2 = "system.cpu0.exec_context.thread_0.numStoreInsts      7082663                       # Number of store instructions (Count)\n"
    l3 = "system.cpu0.exec_context.thread_0.numInsts     25993866                       # Number of memory refs (Count)\n"

    print("test_cpu:")
    for l in [l1,l2,l3]:
        cpu_search = re.search(cpu_inst_pat, l)
        if cpu_search:
            print(f'group0:{cpu_search.group(0)}, group1:{cpu_search.group(1)}, group2:{cpu_search.group(2)}, group3:{cpu_search.group(3)}')

class Printable:
    def __repr__(self):
        return str(vars(self))

class CPU(Printable):
    def __init__(self,id=0,read=0,write=0,inst=0,cycle=0):
        self.id = id
        self.read = read
        self.write = write
        self.inst = inst
        self.cycle = cycle

class Cache(Printable):
    def __init__(self,hit=0,miss=0,access=0):
        self.hit = hit
        self.miss = miss
        self.access = access

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
    def __init__(self, sim_tick=0, clk_domain=0):
        self.sim_tick = sim_tick
        self.clk_domain = clk_domain

# parse one line each time
def parse_stats(line, clk:CLK, cpus:List[CPU], llcs:List[LLC], ddrs:List[DDR], l1ds:List[L1D], l1is:List[L1I], l2ps:List[L2P]):
    sim_tick_sch = re.search(sim_tick_pat, line)
    clk_domain_sch = re.search(clk_domain_pat, line)
    llc_demand_sch = re.search(llc_demand_pat, line)
    l2p_txn_sch = re.search(l2p_txn_pat, line)
    llc_txn_sch = re.search(llc_txn_pat, line)
    ddr_sch = re.search(ddr_pat, line)
    cpu_inst_sch = re.search(cpu_inst_pat, line)
    cpu_cycle_sch = re.search(cpu_cycle_pat, line)
    priv_cache_sch = re.search(priv_cache_demand_pat, line)

    if sim_tick_sch:
        clk.sim_tick = int(sim_tick_sch.group(1))
    
    elif clk_domain_sch:
        clk.clk_domain = int(clk_domain_sch.group(1))
    
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
    
    elif cpu_cycle_sch:
        cpu_id = 0 if len(cpus) == 1 else int(cpu_cycle_sch.group(1))
        cpus[cpu_id].cycle = int(cpu_cycle_sch.group(2))


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
        'NUMCPUS':int,
        'NUM_LLC':int,
        'NUM_MEM':int,
        'DCT':ast.literal_eval,
        'DMT':ast.literal_eval,
        'HNF_TBE':int,
        'SNF_TBE':int,
        'SEQ_TBE':int,
        'TRANS':int,
        'LINKWIDTH':int,
        'NETWORK':str,
        'OUTPUT_DIR':str,
        'l1d_size':str,
        'l1i_size':str,
        'l2_size':str,
        'l3_size':str,
    }

    var_dict = {key:ops(all_var_dict[key]) for key,ops in var_list.items()}
    logging.debug(f'variable_file_parser:var_dict: {var_dict}')

    import copy
    args = copy.deepcopy(args)

    for key,val in var_dict.items():
        setattr(args, key, val)

    logging.debug(f'variable_file_parser:args: {args}')

    return args


def parse_stats_file(args:argparse.Namespace):

    cpus = [CPU(i) for i in range(args.NUMCPUS)]
    llcs = [LLC(i) for i in range(args.NUM_LLC)]
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

    # Only parse the stats after m5_reset_stats 
    start_to_parse = False
    with open(stats_file_path, 'r') as f:
        for idx,line in enumerate(f):
            if line == '---------- End Simulation Statistics   ----------\n':
                start_to_parse = True
                logging.debug(f'Found End Simulation Statistics at line {idx}')
            if start_to_parse == True:
                parse_stats(line, clk, cpus, llcs, ddrs, l1ds, l1is, l2ps)
    if start_to_parse == False:
        logging.critical(f'Cannot find a stats_reset in {stats_file_path}. Please check if your test has finished.')
    
    logging.debug(f'clk:{clk}\ncpus:{cpus}\nllcs:{llcs}\nl1ds:{l1ds}\nl1is:{l1is}\nl2ps:{l2ps}\nddrs:{ddrs}')

    df_dict = {
        'clk': pd.DataFrame([vars(clk)]),
        'cpu': pd.DataFrame([vars(item) for item in cpus]),
        'llc': pd.DataFrame([vars(item) for item in llcs]),
        'l1d': pd.DataFrame([vars(item) for item in l1ds]),
        'l1i': pd.DataFrame([vars(item) for item in l1is]),
        'l2p': pd.DataFrame([vars(item) for item in l2ps]),
        'ddr': pd.DataFrame([vars(item) for item in ddrs]),
    }

    def cache_hit_rate(cache_df:pd.DataFrame):
        cache_sum = pd.Series(cache_df.sum(), name='Total')
        cache_df = pd.concat([cache_df, cache_sum.to_frame().T])
        cache_df['hit_rate'] = cache_df['hit']/cache_df['access']
        return cache_df
    
    def cache_readTxn(cache_df:pd.DataFrame):
        cache_df['ReadS/U'] = cache_df['ReadS']+cache_df['ReadU']
        return cache_df
    
    def cpu_ipc(cache_df:pd.DataFrame):
        cache_df['ipc'] = cache_df['inst']/cache_df['cycle']
        return cache_df

    df_dict['l1d'] = cache_hit_rate(df_dict['l1d'])
    df_dict['l1i'] = cache_hit_rate(df_dict['l1i'])
    df_dict['l2p'] = cache_hit_rate(df_dict['l2p'])
    df_dict['llc'] = cache_hit_rate(df_dict['llc'])
    
    df_dict['llc'] = cache_readTxn(df_dict['llc'])
    df_dict['l2p'] = cache_readTxn(df_dict['l2p'])

    df_dict['cpu'] = cpu_ipc(df_dict['cpu'])

    logging.debug(f'DataFrames:\ncpu:\n{df_dict["cpu"]}\nl1d:\n{df_dict["l1d"]}\nl1i:\n{df_dict["l1i"]}\nl2p:\n{df_dict["l2p"]}\nllc:\n{df_dict["llc"]}')

    [df.to_csv(f'{args.OUTPUT_DIR}/{name}.csv') for name, df in df_dict.items()]

    with open(output_file_path, 'w') as f:
        f.write(f'clk:\n{df_dict["clk"]}\n\ncpu:\n{df_dict["cpu"]}\n\nl1d:\n{df_dict["l1d"]}\n\nl1i:\n{df_dict["l1i"]}\n\nl2p:\n{df_dict["l2p"]}\n\nllc:\n{df_dict["llc"]}')

    logging.info(f'written to {output_file_path}')

    return df_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--root-dir', required=True)
    args = parser.parse_args()

    sim_dir_list = get_all_sim_dir(args.root_dir)
    logging.debug(f'output_dir_list: {sim_dir_list}')

    sim_data_dict = {sim_dir:variable_file_parser(args, sim_dir) for sim_dir in sim_dir_list}
    logging.debug(f'data_dict: {sim_data_dict}')

    for _,sim_data in sim_data_dict.items():
        parse_stats_file(sim_data)

