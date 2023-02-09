'''
May need to refine the re match
Only process XXXin and XXXout msgs, no rdy msgs

Current implementation skip mandatoryQueue(seqIn) msg
'''

import re
import matplotlib.pyplot as plt
from typing import List, Dict
import logging
from enum import Enum
import argparse
import os

# add a new log level
LOG_MSG = 60
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.CRITICAL)
logging.addLevelName(LOG_MSG, 'MSG')

# we donot use CHIXXXMsg to categorize different messages
# instead, we use port name
class MsgType(Enum):
    NIL = 0
    REQ = 1
    RSP = 2
    DAT = 3
    SNP = 4

class Ctrl:
    def __init__(self, idx):
        self.idx = idx

class Cache(Ctrl):
    @classmethod
    def getName():
        pass

    def __str__(self):
        return self.getName()

class SNF(Ctrl):
    @classmethod
    def getName():
        pass
    
    def __str__(self):
        return self.getName()

MsgTypeTable = {
    "req":MsgType.REQ,
    "rsp":MsgType.RSP,
    "dat":MsgType.DAT,
    "snp":MsgType.SNP}

# MessageFlow type to record flow of Messages
class MessageFlow:
    def __init__(self, time, type, dir, src, dest):
        self.time = -1
        self.type = MsgType.NIL # 
        self.dir = None # In or Out, if In, msg to receive; if Out, msg to send
        self.dest: List[int] = [] # [TODO]: snp msgs may have more than 1 dests
        self.src: int = -1 # cache id

# Request type to manage the information of Request
class Request:
    def __init__(self, seq_num, req_start, req_typ):
        self.seq_num = seq_num # this works as id for this request
        self.req_typ = req_typ
        self.req_start = req_start # 
        self.req_end = None # 
        self.req_latency = None # entire round trip time
        # memory statistics
        self.mem_addr = None # memory address
        self.mem_start = None # memory access time
        self.mem_end = None
        self.mem_latency = None
        self.success = None # this request is successful or not 
        # messages used for breakdown of message traffic
        self.messages: List[MessageFlow] = []

    def __str__(self):
        return str(self.seq_num)
    def __repl__(self):
        return str(self.seq_num)
    
# RequestList type to record all the requests
RequestList = Dict[int, Request]
req_dict : RequestList = dict()


# side effect of this function is Request only. We donot need to return anything
def parse_breakdown(line, cache_to_idx, idx_to_cache, num_caches, tick, name, seq_num):
    # default RubySequence msg won't have TxSeqNum
    # therefore, TxSeqNum+arr_time is definitely the CHIXXXMsg
    arr_time_search = re.search('Enqueue arrival_time: (\d+)', line)

    # [TODO]: need to check which port receives the msg
    if arr_time_search : # CHIXXXMsg
        arr_time = arr_time_search.group(1)

        # system.cpu0.l2.snpIn system.ruby.hnf.cntrl.snpIn
        port = name.split(".")[-1] # snpIn

        if port == 'mandatoryQueue':
            return # in while loop this is continue

        msgtype_search = re.search("[a-z]+", port)
        msgtype = msgtype_search.group(0) # snp / mandatory
        dir = port[len(msgtype):] # In or Out


        from functools import reduce
        cache_name = reduce(lambda x,y:x+"."+y, name.split(".")[-3:-1]) # hnf.cntrl or cpu0.l2

        # get the dest info from NetDest
        netdest_search = re.search("\[NetDest[^\n]*?\]", line) # use *? for shortest match

        try:
            assert netdest_search != None # must find the netdest
        except AssertionError:
            print("assert netdest_search != None failed")
            print(line)
            print(netdest_search)
            exit(0)
        
        bitmask_search = re.search(f'([0|1]\s){{{num_caches}}}', netdest_search.group(0)) # use {num_caches} to match data
        
        try:
            assert bitmask_search != None # must find the dest bitmask
        except AssertionError:
            print(" assert bitmask_search != None failed")
            print(line)
            print(netdest_search.group(0))
            print(bitmask_search)
            exit(0)
        bitmask = bitmask_search.group(1).split(" ")

        try:
            assert len(bitmask) == num_caches
        except AssertionError:
            logging.error("assert len(bitmask) == num_caches failed")

        bitmask = list(map(bool, bitmask)) # cast to bool
        dests = [idx for (idx,val) in enumerate(bitmask) if val] # collect the selected idx of cache

        # get the src
        # if dir is Out, src is cache_name, dest is from NetDest
        # if dir is In, src is from NetDest, dest is cache_name

        # the following code refers to the table entry
        # 	            rspIn/datIn	reqIn/snpIn	rspOut/datOut	reqOut/snpOut
        #   src	        responder	requestor	cache_name	    cache_name
        #   dst	        cache_name	cache_name	netdest	        netdest

        src = None
        dst = [] # dst should be potentially a list
        if dir == "In" and msgtype in ['rsp','dat']:
            responder_search = re.search("responder = Cache-(\d+)", line)
            assert responder_search != None
            src = int(responder_search.group(1))
            dst = [cache_to_idx[cache_name]]
        elif dir == "In" and msgtype in ['req','snp']:
            requestor_search = re.search("requestor = Cache-(\d+)", line)
            assert requestor_search != None
            src = int(requestor_search.group(1))
            dst = [cache_to_idx[cache_name]]
        elif dir == "Out" and msgtype in ['rsp','dat']:
            src = cache_to_idx[cache_name]
            dst = dests
        elif dir == "Out" and msgtype in ['req','snp']:
            src = cache_to_idx[cache_name]
            dst = dests
        elif dir == 'Queue' and msgtype == 'mandatory':
            src = cache_to_idx[cache_name]
            dst = [cache_to_idx[cache_name]]
        
        msg = MessageFlow(arr_time, MsgTypeTable[msgtype], dir, src, dst)
        req = req_dict[seq_num]
        req.messages.append(msg)


def parse_request(line:str, tick:int, seq_num:str, name:str):
    seqreq_search = re.search('Req (\w+)', line)
    if seqreq_search : 
        seqReq = seqreq_search.group(1)
        if seqReq == 'Done': # this is the end of request
            cycle_search = re.search('(\d+)\scycles$',line)
            try:
                assert req_dict[seq_num] != None
                req: Request = req_dict[seq_num]
            except AssertionError:
                logging.warning(f"cannot find a previous begin of request {seq_num}")
                logging.warning(f"all requests are:{list(map(str, req_dict.values()))}")
            req.req_end = tick
            req.req_latency = int(cycle_search.group(1))
            req.success = None # [TODO]: extract the status of the request

        elif seqReq == 'Begin': # this is the start of request
            # create a new request with seq_num as the id and tick as the start time
            logging.debug(f"Found a request begin. line: {line}, txsn: {seq_num}")
            typ_search = re.search('type: (\w+)', line)
            typ = typ_search.group(1)
            req: Request = Request(seq_num, tick, typ)
            try:
                assert req_dict.get(seq_num) == None # we should never start a same seqNum for more than once
            except AssertionError:
                logging.error(f"TxSeqNum {seq_num} runs twice: First one is {req_dict.get(seq_num)}, Second is {tick}")
            req_dict[seq_num] = req

        else:
            logging.debug(f"Parse request found other match:{seqReq}")


def parse_mem(line:str, tick:int, seq_num:str, name:str):
    mem_req_search = re.search('requestToMemory', name)
    mem_rsp_search = re.search('responseFromMemory', name)
    if mem_req_search:
        try:
            assert req_dict.get(seq_num) != None
            req: Request = req_dict[seq_num]
            req.mem_start = tick
        except AssertionError:
            logging.error(f"Memory Request cannot find a valid Request of TxSeqNum {seq_num}.")
            logging.debug(f"all requests are:{list(map(str, req_dict.values()))}")

    if mem_rsp_search:
        try:
            assert req_dict.get(seq_num) != None
            req: Request = req_dict[seq_num]
            req.mem_end = tick
            try:
                req.mem_latency = req.mem_end - req.mem_start
            except:
                req.mem_latency = None
        except AssertionError:
            logging.error(f"Memory Response cannot find a valid Request of TxSeqNum {seq_num}.")
            logging.debug(f"all requests are:{list(map(str, req_dict.values()))}")

        

def parse_trace_log(filename, cache_to_idx, idx_to_cache, num_caches, breakdown=False):
    with open(filename) as f:
        for line in f:
            # search for tick
            tick_search = re.search('(^\s*\d+):', line)
            # search for name
            # can also extract each part using "." as seperator
            name_search = re.search('system\.(\S*):', line)
            # search for TxSeqNum
            seq_num_search = re.search('txsn: 0x([\w]+)', line)

            # First: if all search matched, this is the message we want
            if tick_search and name_search and seq_num_search:
                logging.debug(f"Found a matched line: {line}")

                tick = int(tick_search.group(1))
                name = name_search.group(1)
                seq_num = seq_num_search.group(1)

                try:
                    assert seq_num != '0000000000000000'
                except:
                    logging.error("assert seq_num != 0 failed")
                    logging.debug(line)

                # print(tick, name, txsn)

                # Second, parse different logs
                # Currently we have two types of logs
                # 1) CHIXXXMsg: only when enable breakdown
                if breakdown:
                    parse_breakdown(line, cache_to_idx, idx_to_cache, num_caches, tick, name, seq_num)
                
                # 2) Sequencer
                parse_request(line, tick, seq_num, name)

                # 3) mem test
                parse_mem(line, tick, seq_num, name)



def breakdown():
    pass


def profiling(output_dir, draw=False, console=False):
    # 1000 ticks per ns. we need this to transfer between ns and tick
    tick_per_ns = 1000
    # avg_cycles = req_latency_sum/num_cmp_req 
    num_req = len(req_dict)
    num_cmp_req = 0 # some reqs are not completed, we only need the completed ones to calculate avg cycle
    req_latency_sum = 0
    num_cmp_mem = 0 # some mem_reqs not completed, we only need the completed ones to calculate avg mem cycle
    mem_latency_sum = 0
    

    assert num_req != 0 # should have at lease 1 request in trace message
    logging.info(f'{num_req} of requests in total')

    # cpu_req_stat used for distribution plot
    cpu_req_stat: List[int] = []
    mem_req_stat: List[int] = []
    prof_str = []
    prof_str.append(f'{"TxSeqNum": >16}\t{"req_typ": >8}\t{"req_latency": >16}\t{"req_start": >16}\t{"req_end": >16}\t{"mem_latency": >16}\t{"mem_start": >16}\t{"mem_end": >16}\n')
    for seq_num,req in req_dict.items():
        # need to deal with the cycle exceptions
        # req.req_latency may be None
        try:
            req_latency_sum += req.req_latency
            num_cmp_req += 1
            cpu_req_stat.append(req.req_latency)
        except TypeError:
            logging.warning(f"cannot find the req done of txn {req.seq_num}.")
        try:
            mem_latency_sum += req.mem_latency
            num_cmp_mem += 1
            mem_req_stat.append(req.mem_latency)
        except TypeError:
            logging.warning(f"cannot find the mem req response of request {req.seq_num}.")
        prof_str.append(f'{seq_num:>16}\t{req.req_typ: >8}\t{req.req_latency if req.req_latency else "---": >16}\t{req.req_start: >16}\t{req.req_end if req.req_end else "---": >16}\t{req.mem_latency/tick_per_ns if req.mem_latency else "---":>16}\t{req.mem_start if req.mem_start else "---":>16}\t{req.mem_end if req.mem_end else "---":>16}\n')
    # debug print
    # print out the prof_str
    if console:
        for s in prof_str:
            logging.log(LOG_MSG, s, end="")
    
    output_log = os.path.join(output_dir, 'profile_stat.log')
    output_fig = os.path.join(output_dir, 'profile_stat.png')
    
    avg_req_cycle = round(req_latency_sum / num_cmp_req, 4)
    avg_mem_latency = round(mem_latency_sum / num_cmp_mem / tick_per_ns, 4) # in ns

    avg_mem_str = f'{num_cmp_mem} of completed memory requests. Avg mem access time is {avg_mem_latency} ns. Min is {min(mem_req_stat)/tick_per_ns} ns. Max is {max(mem_req_stat)/tick_per_ns} ns.'
    avg_cyc_str = f'{num_req} of requests in total. {num_cmp_req} of completed requests. Avg complete time is {avg_req_cycle} cycle. Min is {min(cpu_req_stat)} cycle. Max is {max(cpu_req_stat)} cycle.'
    prof_str.insert(0, avg_mem_str+'\n')
    prof_str.insert(0, avg_cyc_str+'\n')

    # print avg cycle
    logging.log(LOG_MSG, avg_cyc_str)
    logging.log(LOG_MSG, avg_mem_str)

    # write to file
    with open(output_log,'w+') as f:
        f.writelines(prof_str)

    logging.log(LOG_MSG, f'Written to {output_log}')

    if draw :
    # Creating histogram
        # logging.debug(f"cpu_req_stat: {cpu_req_stat}")
        fig, (axs1,axs2) = plt.subplots(2, 1,
                            figsize =(10, 10),
                            tight_layout = True)

        # translate tick to cycle
        import numpy as np
        mem_req_stat = np.array(mem_req_stat)/tick_per_ns

        bins = 64
        axs1.hist(cpu_req_stat, bins)
        axs1.set_title(f"cpu request latency distribution (bins={bins},total_num={num_cmp_req},avg_latency={avg_req_cycle} cycles)")
        axs1.set_xlabel('latency(cycles)')
        axs1.set_ylabel('nums of cpu requests')
        axs2.hist(mem_req_stat, bins)
        axs2.set_title(f"memory latency distribution (bins={bins},total_num={num_cmp_mem},avg_latency={avg_mem_latency} ns)")
        axs2.set_xlabel('latency(ns)')
        axs2.set_ylabel('nums of memory requests')
        fig.suptitle(os.path.basename(os.path.normpath(output_dir)))
        plt.savefig(output_fig)
        logging.log(LOG_MSG, f"Saved to {output_fig}")


# this cache_table is used for name mapping for NetDest
def gen_cache_table(num_cpus, num_l3caches):

    name_to_idx: Dict[str, int] = dict()
    idx_to_name: Dict[int, str] = dict()

    for i in range(num_cpus):
        name_to_idx[f"cpu{i}.l1i"] = i*2
        name_to_idx[f"cpu{i}.l1d"] = i*2+1
        name_to_idx[f"cpu{i}.l2"] = num_cpus*2+i
        
        idx_to_name[i*2] = f"cpu{i}.l1i"
        idx_to_name[i*2+1] = f"cpu{i}.l1d"
        idx_to_name[num_cpus*2+i] = f"cpu{i}.l2"
    
    for i in range(num_l3caches):
        name_to_idx[f"hnf.cntrl"] = num_cpus*3+i
        idx_to_name[num_cpus*3+i] = f"hnf.cntrl"
    
    num_caches = len(name_to_idx)
    # logging.info(f"num_cpus:{num_cpus}")
    # logging.info("cache idx:")
    # for k,v in name_to_idx.items():
    #     logging.info(f'{k}: {v}')
    # logging.info(f"num_caches:{num_caches}")

    return name_to_idx, idx_to_name, num_caches
    

def file_path(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"not a file!")


if __name__ == '__main__':

    # [TODO]: now need to set the num_cpu and num_cache by hand
    num_cpus = None
    num_dirs = None # snf
    num_l3caches = None # hnf/llc
    dmt=None
    trans=None
    hnf_tbe=None
    snf_tbe=None
    num_load=None

    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--input', help='input file', required=True, type=str)
    parser.add_argument('--output', help='output dir', required=True, type=str)
    parser.add_argument('--num_cpu',help='num of cpu cores', required=False,type=int)
    parser.add_argument('--num_llc', help='num of hnf nodes', required=False,type=int)
    parser.add_argument('--num_mem', help='num of snf nodes', required=False,type=int)
    parser.add_argument('--num_load',required=True,type=int)

    args = vars(parser.parse_args())

    trace_file = args['input']
    output_dir = args['output']
    num_cpus = args['num_cpu']
    num_l3caches = args['num_llc']
    num_dirs = args['num_mem']

    # currently we only need input and output args

    cache_to_idx, idx_to_cache, num_caches = gen_cache_table(num_cpus, num_l3caches)

    parse_trace_log(trace_file, cache_to_idx, idx_to_cache, num_caches, breakdown=False)
    # turn on plot by setting draw True
    # turn on console log by setting console True
    profiling(output_dir, draw=True, console=False)