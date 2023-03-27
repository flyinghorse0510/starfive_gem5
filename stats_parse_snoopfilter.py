import re
import os
import ast
import logging
import argparse
import subprocess
from typing import List
from functools import reduce

# add a new log level
LOG_MSG = 60
tick = 0

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.CRITICAL)
logging.addLevelName(LOG_MSG, 'MSG')

tick_pat = re.compile('^simTicks[\s]+(\d+)')

# llc's pattern
# three groups we need : 1) hnf's id 2) hit/miss/access 3) num of hit/miss/access
# idx can be nullstr, not None
# llc_pat = re.compile('^system.ruby.hnf(\d*).cntrl.cache.m_demand_([a-z]+)\s+(\d+)')

snoopfilter_pat = re.compile('^system.ruby.hnf(\d*).cntrl.m_snoopfilter_([a-z]+)\s+(\d+)')

# l1d, l1i, l2p's pattern
# four groups we need: 1) cpu's id 2) l1d/l1i/l2 3) hit/miss/access 4) num of hit/miss/access
# 
# priv_cache_pat = re.compile('^system.cpu(\d*).(\w*).cache.m_demand_([a-z]+)\s+(\d+)')

# llc_reack_pat = re.compile('^system.ruby.hnf(\d*).cntrl.cache.m_RetryAcks\s+(\d+)[\s\S]*$')

# snf_remsg_pat = re.compile('^system.ruby.snf(\d*).cntrl.rspOut.m_retry_msgs\s+(\d+)[\s\S]*$')

# ddr's pattern
# groupes we need: 1) mem_ctrls's id 2) write/read 3) num of read/write requests
# ddr_pat = re.compile('system.mem_ctrls(\d*).([a-z]+)Reqs\s+(\d+)')

# cpu's pattern
# groups we need: 1) cpu's id 2) read/write 3) num of read/write requests
# cpu_pat = re.compile('^system.cpu(\d*).num([a-zA-Z]+)\s+(\d+)')

class CacheStats:
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


class SnoopFilterStats(CacheStats):
    def __init__(self,id,hit=0,miss=0,alloc=0,access=0):
        super(SnoopFilterStats, self).__init__(id,hit,miss,access)
        self.alloc = alloc
        self.cold_hits = self.alloc - self.miss
    
    def calc_cold_hits(self):
        return self.cold_hits
    
    def calc_miss_rate(self):
        return round(self.miss/self.access,4)
    
    def calc_hit_rate(self):
        return (1-self.calc_hit_rate())

    def table_print(self):
        self.cal_hit_rate()
        return f'||{self.id:^16}|{self.hit:^16}|{self.miss:^16}|{self.alloc:^16}|{self.access:^16}|{self.calc_miss_rate():^16}||'

def gen_header(name:List[str]):
    width = 16*len(name)+len(name)-1+4
    h1_str = '='*width+'\n'
    h2_str = '||' + '|'.join([f'{n:^16}' for n in name]) + '||\n'
    h3_str = '='*width+'\n'
    h_str = h1_str + h2_str + h3_str
    return h_str,width

def gen_bottom(width):
    return '='*width+'\n'

def gen_cache_str(caches:List[SnoopFilterStats], name:str):
    cache_str,cache_table_width = gen_header([name,'HIT','MISS','ALLOC','ACCESS','MISS_RATE'])
    cache_str += '\n'.join([cache.table_print() for cache in caches]) + '\n'
    cache_hit_sum = reduce(lambda x,y:x+y, [cache.hit for cache in caches])
    cache_miss_sum = reduce(lambda x,y:x+y, [cache.miss for cache in caches])
    cache_access_sum = reduce(lambda x,y:x+y, [cache.access for cache in caches])
    cache_alloc_sum = reduce(lambda x,y:x+y, [cache.alloc for cache in caches])
    try:
        cache_miss_rate = round(cache_miss_sum/cache_access_sum,4)
    except:
        cache_miss_rate = 'NIL'
    cache_str += '-'*cache_table_width+'\n'
    cache_str += f'||{"TOTAL":^16}|{cache_hit_sum:^16}|{cache_miss_sum:^16}|{cache_alloc_sum:^16}|{cache_access_sum:^16}|{cache_miss_rate:^16}||\n'
    cache_str += gen_bottom(cache_table_width)
    return cache_str

def gen_print_str(snoopfilters):
    # print caches
    snoopfilter_str = gen_cache_str(snoopfilters,'SnoopFilter')
    return {'snoopfilter':snoopfilter_str} # you can add more options to print

# parse one line each time
def parse_stats(line, llcs:List[SnoopFilterStats]) :
    tick_sch = re.search(tick_pat, line)
    snoopfilter_sch = re.search(snoopfilter_pat,line)

    if tick_sch:
        global tick
        tick = int(tick_sch.group(1))
    
    elif snoopfilter_sch :
        sf_id = 0 if len(llcs) == 1 else int(snoopfilter_sch.group(1))
        sf_status = snoopfilter_sch.group(2) # alloc/hit/miss/access
        sf_op = int(snoopfilter_sch.group(3))
        if sf_status == 'hits' :
            llcs[sf_id].hit = sf_op
        elif sf_status == 'misses' :
            llcs[sf_id].miss = sf_op
        elif sf_status == 'accesses' :
            llcs[sf_id].access = sf_op
        elif sf_status == 'alloc' :
            llcs[sf_id].alloc = sf_op

def snoopfilter_summary(snoopfilters: List[SnoopFilterStats]):
    total_hit, total_miss, total_access, total_alloc = 0,0,0,0
    for sf_stat in snoopfilters:
        total_hit += sf_stat.hit
        total_miss += sf_stat.miss
        total_alloc += sf_stat.alloc
        total_access += sf_stat.access
    miss_rate = total_miss/total_access
    hit_rate = 1-miss_rate
    return f'SnoopFilter summary: hit rate:{hit_rate}, miss rate: {miss_rate}'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    parser.add_argument('--num_cpu', required=True, type=int)
    parser.add_argument('--num_llc', required=True, type=int)
    parser.add_argument('--print_path', required=False, default=False, type=ast.literal_eval)
    args = parser.parse_args()

    snoopfilters = [SnoopFilterStats(i) for i in range(args.num_llc)]

    out = subprocess.getoutput('wc -l %s' % args.input)
    if int(out.split()[0]) == 0:
        logging.critical(f'{args.input} has no content. Please check if your test has finished.')
        exit()

    with open(args.input, 'r') as f:
        for line in f:
            parse_stats(line, snoopfilters)

    # print tick
    tick_str = f'total cycle is {tick/1000}\n'

    # generate print strings
    print_dict = gen_print_str(snoopfilters)
    stats_str = tick_str

    print_args = ['snoopfilter']

    import pprint as pp
    for k,v in print_dict.items():
        if k in print_args:
            pp.pprint(v)
            stats_str += v
    
    # if args.print:
    #     print(f'Stats for configuration {os.path.basename(os.path.dirname(args.input))}')
    #     print(stats_str)
    #     print(snoopfilter_summary(snoopfilters))

    with open(args.output,'w+') as f:
        f.write(stats_str)
        f.write(snoopfilter_summary(snoopfilters))
    print(f'written to {args.output}')

    # # need to create a new file by .sh to avoid historical data from last run
    # # --num_cpu ${NUMCPUS} --num_llc ${NUM_LLC} --num_ddr ${NUM_MEM} --dmt ${DMT} --trans ${TRANS} --snf_tbe ${SNF_TBE} --linkwidth ${LINKWIDTH}

    # # generate the header for throughput.txt
    # if not os.path.getsize('throughput.txt'):
    #     with open('throughput.txt', 'w') as f:
    #         if args.print_path:
    #             f.write(f'{"CPU":^8}{"LLC":^8}{"DDR":^8}{"DMT":^8}{"TRANS":^8}{"SNF_TBE":^8}{"LINKWD":^8}{"INJINTV":^8}{"READ(B)":^16}{"WRITE(B)":16}{"TICK(ps)":^16}{"THROUGHPUT(GB/s)":^16}{"HNF_RETRY_ACK:":^16}{"SNF_RETRY_MSG":^16}{"PATH"}\n')
    #         else:
    #             f.write(f'{"CPU":^8}{"LLC":^8}{"DDR":^8}{"DMT":^8}{"TRANS":^8}{"SNF_TBE":^8}{"LINKWD":^8}{"INJINTV":^8}{"READ(B)":^16}{"WRITE(B)":16}{"TICK(ps)":^16}{"THROUGHPUT(GB/s)":^16}{"HNF_RETRY_ACK:":^16}{"SNF_RETRY_MSG":^16}\n')
    
    # cpu_read_byte, cpu_write_byte, throughput = gen_throughput(cpus)
    # total_snf_remsg = reduce(lambda x,y:x+y, [snf.remsg for snf in snfs])
    # total_hnf_reack = reduce(lambda x,y:x+y, [llc.reack for llc in llcs])
    
    # with open('throughput.txt', 'a+') as f:
    #     if args.print_path:
    #         f.write(f'{args.num_cpu:^8}{args.num_llc:^8}{args.num_ddr:^8}{args.dmt:^8}{args.trans:^8}{args.snf_tbe:^8}{args.linkwidth:^8}{args.injintv:^8}{cpu_read_byte:^16}{cpu_write_byte:^16}{tick:^16}{throughput:^16}{total_hnf_reack:^16}{total_snf_remsg:^16}{args.input}\n')
    #     else:
    #         f.write(f'{args.num_cpu:^8}{args.num_llc:^8}{args.num_ddr:^8}{args.dmt:^8}{args.trans:^8}{args.snf_tbe:^8}{args.linkwidth:^8}{args.injintv:^8}{cpu_read_byte:^16}{cpu_write_byte:^16}{tick:^16}{throughput:^16}{total_hnf_reack:^16}{total_snf_remsg:^16}\n')
    
    # print(f'written to ./throughput.txt')
