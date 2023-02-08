#!/usr/bin/env python3

'''
Usage:
Currently need to change the num_cpus num_llcs num_ddrs manually
You can choose which component to print by adding any combination from l1i,l1d,l2p,llc,cpu,ddr, the default option is cpu,llc,ddr
python3 stats_parser.py --input stats.txt --num_cpus 1 --num_llcs 1 --num_ddrs 1 --print l1d,l2p,llc,cpu,ddr
'''
import re
from typing import List
import logging

# add a new log level
LOG_MSG = 60
logging.basicConfig(format='%(levelname)s:%(message)s', level=LOG_MSG)
logging.addLevelName(LOG_MSG, 'MSG')


tick_pat = re.compile('^simTicks[\s]+(\d+)')

# llc's pattern
# three groups we need : 1) hnf's id 2) hit/miss/access 3) num of hit/miss/access
# idx can be nullstr, not None
llc_pat = re.compile('^system.ruby.hnf(\d*).cntrl.cache.m_demand_([a-z]+)\s+(\d+)')

# l1d, l1i, l2p's pattern
# four groups we need: 1) cpu's id 2) l1d/l1i/l2 3) hit/miss/access 4) num of hit/miss/access
# 
priv_cache_pat = re.compile('^system.cpu(\d*).(\w*).cache.m_demand_([a-z]+)\s+(\d+)')


# ddr's pattern
# groupes we need: 1) mem_ctrls's id 2) write/read 3) num of read/write requests
ddr_pat = re.compile('system.mem_ctrls(\d*).([a-z]+)Reqs\s+(\d+)')

# cpu's pattern
# groups we need: 1) cpu's id 2) read/write 3) num of read/write requests
cpu_pat = re.compile('^system.cpu(\d*).num([a-zA-Z]+)\s+(\d+)')

def test_tick():
    l = "simTicks                                       446001                       # Number of ticks simulated (Tick)\n"
    print("test_tick:")
    tick_search = re.search(tick_pat,l)
    if tick_search:
        print(f'group0:{tick_search.group(0)}, group1:{tick_search.group(1)}')

def test_llc():
    l1 = "system.ruby.hnf01.cntrl.cache.m_demand_hits            0                       # Number of cache demand hits (Unspecified)\n"
    l2 = "system.ruby.hnf15.cntrl.cache.m_demand_misses            8                       # Number of cache demand misses (Unspecified)\n"
    l3 = "system.ruby.hnf.cntrl.cache.m_demand_accesses            8                       # Number of cache demand accesses (Unspecified)\n"

    print("test_llc:")
    for l in [l1,l2,l3]:
        llc_search = re.search(llc_pat, l)
        if llc_search:
            print(f'group0:{llc_search.group(0)}, group1:{llc_search.group(1)}, group2:{llc_search.group(2)}, group3:{llc_search.group(3)}')


def test_priv_cache_pat():
    l1 = "system.cpu0.l2.cache.m_demand_hits                  0                       # Number of cache demand hits (Unspecified)\n"
    l2 = "system.cpu1.l2.cache.m_demand_misses              521                       # Number of cache demand misses (Unspecified)\n"
    l3 = "system.cpu2.l1d.cache.m_demand_accesses            521                       # Number of cache demand accesses (Unspecified)\n"
    l4 = "system.cpu0.l1i.cache.m_demand_hits                  0                       # Number of cache demand hits (Unspecified)\n"
    l5 = "system.cpu1.l2.cache.m_demand_misses              521                       # Number of cache demand misses (Unspecified)\n"
    l6 = "system.cpu2.l2.cache.m_demand_accesses            521                       # Number of cache demand accesses (Unspecified)\n"
    print("test priv cache:")

    for l in [l1,l2,l3,l4,l5,l6]:
        priv_cache_search = re.search(priv_cache_pat,l)
        if priv_cache_search:
            print(f'group0:{priv_cache_search.group(0)}, group1:{priv_cache_search.group(1)}, group2:{priv_cache_search.group(2)}, group3:{priv_cache_search.group(3)}, group4:{priv_cache_search.group(4)}')


def test_cpu():
    l1 = "system.cpu0.numReads                            25257                       # number of read accesses completed (Count)\n"
    l2 = "system.cpu.numWrite                            25257                       # number of write accesses completed (Count)\n"
    l3 = "system.cpu10.numReads                           25283                       # number of read accesses completed (Count)\n"

    print("test_cpu:")
    for l in [l1,l2,l3]:
        cpu_search = re.search(cpu_pat, l)
        if cpu_search:
            print(f'group0:{cpu_search.group(0)}, group1:{cpu_search.group(1)}, group2:{cpu_search.group(2)}, group3:{cpu_search.group(3)}')

def test_ddr():
    l1 = "system.mem_ctrls.readReqs                          10                       # Number of read requests accepted (Count)\n"
    l2 = "system.mem_ctrls.writeReqs                          0                       # Number of write requests accepted (Count)\n"
    l2 = "system.mem_ctrls0.writeReqs                          14                       # Number of write requests accepted (Count)\n"

    print("test_ddr:")
    for l in [l1,l2]:
        ddr_search = re.search(ddr_pat, l)
        if ddr_search:
            print(f'group0:{ddr_search.group(0)}, group1:{ddr_search.group(1)}, group2:{ddr_search.group(2)}, group3:{ddr_search.group(3)}')

class CPU:
    def __init__(self,id=0,read=0,write=0):
        self.id = id
        self.read = read
        self.write = write

    def table_print(self):
        return f'||{self.id:^16}|{self.read:^16}|{self.write:^16}||'

class Cache:
    def __init__(self,id=0,hit=0,miss=0,access=0):
        self.id = id
        self.hit = hit
        self.miss = miss
        self.access = access
        self.hit_rate = None

    def cal_hit_rate(self):
        try:
            self.hit_rate = round(self.hit/self.access,4)
        except:
            logging.error("error when calculate hit rate")
            self.hit_rate = 0.0

    def table_print(self):
        self.cal_hit_rate()
        return f'||{self.id:^16}|{self.hit:^16}|{self.miss:^16}|{self.access:^16}|{self.hit_rate:^16}||'

class LLC(Cache):
    pass


class PrivCache(Cache):
    def __init__(self,cpu_id=0,id=0,hit=0,miss=0,access=0):
        super(PrivCache, self).__init__(id,hit,miss,access)
        self.cpu_id=cpu_id

class L1D(PrivCache):
    def table_print(self):
        self.cal_hit_rate()
        return f'||{"cpu"+str(self.cpu_id)+"."+"l1d":^16}|{self.hit:^16}|{self.miss:^16}|{self.access:^16}|{self.hit_rate:^16}||'

class L1I(PrivCache):
    def table_print(self):
        self.cal_hit_rate()
        print(self.hit_rate)
        return f'||{"cpu"+str(self.cpu_id)+"."+"l1i":^16}|{self.hit:^16}|{self.miss:^16}|{self.access:^16}|{self.hit_rate:^16}||'

class L2P(PrivCache):
    def table_print(self):
        self.cal_hit_rate()
        return f'||{"cpu"+str(self.cpu_id)+"."+"l2":^16}|{self.hit:^16}|{self.miss:^16}|{self.access:^16}|{self.hit_rate:^16}||'

class DDR:
    def __init__(self,id=0,read=0,write=0):
        self.id = id
        self.read = read
        self.write = write

    def table_print(self):
        return f'||{self.id:^16}|{self.read:^16}|{self.write:^16}||'


def gen_header(name:List[str]):
    width = 16*len(name)+len(name)-1+4
    h1_str = '='*width+'\n'
    h2_str = '||' + '|'.join([f'{n:^16}' for n in name]) + '||\n'
    h3_str = '='*width+'\n'
    h_str = h1_str + h2_str + h3_str
    return h_str,width

def gen_bottom(width):
    return '='*width+'\n'

def gen_cache_str(caches:List[Cache], name:str):
    cache_str,cache_width = gen_header([name,'HIT','MISS','ACCESS','HIT_RATE'])
    cache_str += '\n'.join([cache.table_print() for cache in caches]) + '\n'
    cache_str += gen_bottom(cache_width)
    return cache_str

def gen_print_str(cpus, llcs, ddrs, l1ds, l1is, l2ps):
    # print cpu
    cpu_str,cpu_width = gen_header(['CPU','READ','WRITE'])
    cpu_str += '\n'.join([cpu.table_print() for cpu in cpus]) + '\n'
    cpu_str += gen_bottom(cpu_width)

    # print caches
    llc_str,l1d_str, l1i_str, l2p_str = [gen_cache_str(cache,name) for cache,name in ((llcs,'LLC'), (l1ds,'L1D'), (l1is,'L1I'), (l2ps,'L2P'))]

    # print ddr
    ddr_str,ddr_width = gen_header(['DDR','READ','WRITE'])
    ddr_str += '\n'.join([ddr.table_print() for ddr in ddrs]) + '\n'
    ddr_str += gen_bottom(ddr_width)

    return {'cpu':cpu_str,'llc':llc_str,'ddr':ddr_str,'l1d':l1d_str,'l1i':l1i_str,'l2p':l2p_str} # you can add more options to print

tick = 0

# parse one line each time
def parse_stats(line, cpus:List[CPU], llcs:List[LLC], ddrs:List[DDR], l1ds:List[L1D], l1is:List[L1I], l2ps:List[L2P]):
    tick_sch = re.search(tick_pat, line)
    llc_sch = re.search(llc_pat, line)
    ddr_sch = re.search(ddr_pat, line)
    cpu_sch = re.search(cpu_pat, line)
    priv_cache_sch = re.search(priv_cache_pat, line)

    if tick_sch:
        global tick
        tick = int(tick_sch.group(1))
    
    elif llc_sch:
        llc_id = 0 if len(llcs) == 1 else int(llc_sch.group(1))
        
        llc_status = llc_sch.group(2) # hit/miss/access
        llc_num_op:int = int(llc_sch.group(3))

        if llc_status == 'hits':
            llcs[llc_id].hit = llc_num_op
        elif llc_status == 'misses':
            llcs[llc_id].miss = llc_num_op
        elif llc_status == 'accesses':
            llcs[llc_id].access = llc_num_op

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
            raise TypeError

        
    elif ddr_sch:
        ddr_id = 0 if len(ddrs) == 1 else int(ddr_sch.group(1))
        ddr_op = ddr_sch.group(2) # read/write
        ddr_num_op:int = int(ddr_sch.group(3))

        if ddr_op == 'read':
            ddrs[ddr_id].read = ddr_num_op
        elif ddr_op == 'write':
            ddrs[ddr_id].write = ddr_num_op
        

    elif cpu_sch:
        cpu_id = 0 if len(cpus) == 1 else int(cpu_sch.group(1))
        cpu_op = cpu_sch.group(2) # read/write
        cpu_num_op:int = int(cpu_sch.group(3))

        if cpu_op == 'Reads':
            cpus[cpu_id].read = cpu_num_op
        elif cpu_op == 'Writes':
            cpus[cpu_id].write = cpu_num_op


def llc_summary(llcs:List[LLC]):
    total_hit, total_miss, total_access = 0,0,0
    for llc in llcs:
        total_hit += llc.hit
        total_miss += llc.miss
        total_access += llc.access
    return f'LLC summary: hit rate:{total_hit/total_access}, miss rate: {total_miss/total_access}'


if __name__ == '__main__':

    # '''
    # test funcs to help dev regex
    # '''
    # test_tick()
    # test_llc()
    # test_cpu()
    # test_ddr()
    # test_priv_cache_pat()

    import argparse
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--num_cpus', required=True, type=int)
    parser.add_argument('--num_llcs', required=True, type=int)
    parser.add_argument('--num_ddrs', required=True, type=int)
    parser.add_argument('--print', required=False,type=str,default='cpu,ddr,llc',help='choose what to print from [cpu,l1d,l1i,l2,llc,ddr] with comma as delimiter. e.g. --print cpu,llc will only print cpu and llc. default options is cpu,llc,ddr')

    args = parser.parse_args()
    cpus = [CPU(i) for i in range(args.num_cpus)]
    llcs = [LLC(i) for i in range(args.num_llcs)]
    l1ds = [L1D(i) for i in range(args.num_cpus)]
    l1is = [L1I(i) for i in range(args.num_cpus)]
    l2ps = [L2P(i) for i in range(args.num_cpus)]
    ddrs = [DDR(i) for i in range(args.num_ddrs)]

    with open(args.input, 'r') as f:
        for line in f:
            parse_stats(line, cpus, llcs, ddrs, l1ds, l1is, l2ps)
    
    num_dash = 32

    # print tick
    tick_str = f'total cycle is {tick/1000}\n'
    # generate print strings
    print_dict = gen_print_str(cpus, llcs, ddrs, l1ds, l1is, l2ps)
    stats_str = tick_str
    
    # parse print option from console
    print_args = args.print.split(',')

    for k,v in print_dict.items():
        if k in print_args:
            stats_str += v
        

    if args.print:
        print(stats_str)
        print(llc_summary(llcs))

    
    with open('stats.log','w+') as f:
        f.write(stats_str)
        f.write(llc_summary(llcs))
    print('written to stats.log')
