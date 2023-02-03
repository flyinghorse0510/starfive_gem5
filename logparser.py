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
    def __init__(self, seq_num, start_time):
        self.seq_num = seq_num # this works as id for this request
        self.start_time = start_time # 
        self.end_time = None # 
        self.cycles = None # 
        self.success = None # this request is successful or not 
        # messages used for breakdown of message traffic
        self.messages: List[MessageFlow] = []

    def __str__(self):
        return "Request " + str(self.seq_num) + ":{start_time: " + str(self.start_time) + "}"
    
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
            print("assert len(bitmask) == num_caches failed")

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


def parse_roundtrip(line, tick, seq_num):
    seqreq_search = re.search('Req (\w+) ', line)
    if seqreq_search : 
        seqReq = seqreq_search.group(1)
        if seqReq == 'Done': # this is the end of request
            cycle_search = re.search('(\d+)\scycles$',line)
            req: Request = req_dict[seq_num]
            req.end_time = tick
            req.cycles = int(cycle_search.group(1))
            req.success = None # [TODO]: extract the status of the request

        if seqReq == 'Begin': # this is the start of request
            # create a new request with seq_num as the id and tick as the start time
            req: Request = Request(seq_num, tick)
            try:
                assert req_dict.get(seq_num) == None # we should never start a same seqNum for more than once
            except AssertionError:
                print(f"TxSeqNum{seq_num} runs twice: First one is {req_dict.get(seq_num)}, Second is {tick}")
            req_dict[seq_num] = req

def parse_log(filename, cache_to_idx, idx_to_cache, num_caches, breakdown=False):
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
                tick = int(tick_search.group(1))
                name = name_search.group(1)
                seq_num = seq_num_search.group(1)

                try:
                    assert seq_num != '0000000000000000'
                except:
                    print("assert seq_num != 0 failed")
                    print(line)

                # print(tick, name, txsn)

                # Second, parse different logs
                # Currently we have two types of logs
                # 1) CHIXXXMsg: only when enable breakdown
                if breakdown:
                    parse_breakdown(line, cache_to_idx, idx_to_cache, num_caches, tick, name, seq_num)
                
                # 2) Sequencer and snf
                parse_roundtrip(line, tick, seq_num)



def breakdown():
    pass


def profiling(draw=False, console=False):
    # avg_cycles = total_cycles/num_req 
    num_req = len(req_dict)
    total_cycles = 0

    assert num_req != 0 # should have at lease 1 request in trace message
    print(f'{num_req} of requests in total')

    # cycle_stat used for distribution plot
    cycle_stat: List[int] = []
    prof_str = []
    prof_str.append(f'{"TxSeqNum": >16}\t{"start_time": >16}\t{"end_time": >16}\t{"cycles": >16}\n')
    for seq_num,req in req_dict.items():
        try:
            total_cycles += req.cycles
            cycle_stat.append(req.cycles)
            prof_str.append(f'{seq_num:>16}\t{req.start_time: >16}\t{req.end_time: >16}\t{req.cycles: >16}\n')
        except:
            prof_str.append(f'{seq_num:>16}\t{req.start_time: >16}\t{"---": >16}\t{"---": >16}\n')

    # debug print
    # print out the prof_str
    if console:
        for s in prof_str:
            print(s,end="")
    
    # write to file
    with open('profile_stat.log','w+') as f:
        f.writelines(prof_str)

    print('Written to profile_stat.log')

    # print avg cycle
    avg_req_cycle = total_cycles / num_req
    print(f'Avg cycle is {avg_req_cycle}')

    if draw :
    # Creating histogram
        fig, axs = plt.subplots(1, 1,
                            figsize =(10, 7),
                            tight_layout = True)
    
        axs.hist(cycle_stat, bins = 50)
        plt.savefig("profile_stat.png")
        print("Saved to profile_state.png")


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

    return name_to_idx, idx_to_name, len(name_to_idx)
    


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    # [TODO]: now need to set the num_cpu and num_cache by hand
    num_cpus = 2
    num_dirs = 1 # snf
    num_l3caches = 1 # hnf
    filename= 'debug.trace'

    cache_to_idx, idx_to_cache, num_caches = gen_cache_table(num_cpus, num_l3caches)

    logging.info(f"num_cpus:{num_cpus}")
    logging.info("cache idx:")
    for k,v in cache_to_idx.items():
        logging.info(f'{k}: {v}')
    logging.info(f"num_caches:{num_caches}")

    parse_log(filename, cache_to_idx, idx_to_cache, num_caches, breakdown=False)
    # turn on plot by setting draw True
    # turn on console log by setting console True
    profiling(draw=True, console=False)