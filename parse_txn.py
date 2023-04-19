import os
from tqdm import tqdm
import argparse
import re

CPU_LINE = re.compile(r'^(\d+):\s+.*\.cpu\.l2\.(\w+):\s+(\w+):\s+txsn:\s+(\w+),.*$')
RUBY_LINE = re.compile('system.ruby.(\w*).(\w*).(\w*)')

# FILE_DIR="/home/lester.leong/simulation/gem5_starlink2/output/GEM5_PDCP/GateTest/DDR_garnet/WS524288_Core1_L14KiB_L28KiB_L34KiB_MEM1_DMTTrue_DCTFalse_SEQ32_LoadFactor10_INJINTV1_BUF4_VCVNET4_HNF32_SNF32/debug.trac"
# FILE_DIR ="/home/lester.leong/simulation/gem5_starlink2/output/GEM5_PDCP/GateTest/DDR_simple/WS524288_Core1_L14KiB_L28KiB_L34KiB_MEM1_DMTTrue_DCTFalse_SEQ32_LoadFactor10_INJINTV1_BUF4_VCVNET4_HNF32_SNF32/debug.trac"
TICKS_PER_CYCLE=500

TXN_OUT = "0x0000000000000000"
ADDRESS = "0x10300"
TXN = "0x000300000000040c"
MESSAGE_TYPE = "CompData_SC"
AGENT = "l2"
TYPE = "datOut"
MAX_LINES = 1000000

def filter_statement(addr,txn,agent,test):
    # if addr != ADDRESS and not test: return True
    # if txn != TXN and not test: return True
    if TXN_OUT == txn: return True
    if("network" in agent): return True
    return False

#parse all transactions except TXN_OUT
def parse_txn(pattern,pattern2, pattern_dataseq,lines,f,test):
    last_tick = 0
    txn_dict = {}
    arrival_count_req = {}
    dequeue_count_req = {}
    bufsize_count = {}

    for line in lines:
        matches = re.search(pattern, line)
        matches2 = re.search(pattern2, line)
        matches_dataseq = re.search(pattern_dataseq,line)
        if matches:
            tick = int(matches.group(1))
            agent = matches.group(3)
            reqType = matches.group(4)
            txn = matches.group(5)
            msgType = matches.group(6)
            isArrival = int(matches.group(7))
            addr=matches.group(8)
            bufsize = int(matches.group(9))
            dest = int(matches.group(10))

            if filter_statement(addr,txn,agent,test): continue

            #encoding to keep the time for that specific transaction
            encoding = txn+reqType+agent

            #counts the elapsed time from when the message is enqueued to the point it is dequeued
            if isArrival == 1:
                if encoding not in arrival_count_req.keys(): arrival_count_req[encoding] = 0
                else: 
                    arrival_count_req[encoding]+=1
                dt = 0
                current_count = arrival_count_req[encoding]
                txn_dict[encoding+str(current_count)] = tick
                bufsize_count[encoding+str(current_count)] = bufsize

            elif isArrival == 0:
                if encoding not in dequeue_count_req.keys(): dequeue_count_req[encoding] = 0
                else: 
                    dequeue_count_req[encoding]+=1
                current_count = dequeue_count_req[encoding]
                dt = (tick-txn_dict[encoding+str(current_count)])/TICKS_PER_CYCLE

            if not test:
                print(f"{tick},{dt},{agent},{addr},{reqType},{current_count},{isArrival},{txn},{bufsize_count[encoding+str(current_count)]}", file=f)
            else:
                print(f"{tick},{dt},{agent},{addr},{reqType},{isArrival},{txn},{bufsize}")
                assert(tick == 77500)
                assert(agent=="l2")
                assert(addr=="0")
                assert(txn=="0x0003000000000000")
                assert(msgType == "CompData_SC")
                assert(reqType=="datOut")
                assert(bufsize==2)
                assert(isArrival==1)
                assert(dest==1)

        elif matches2: #for lines that contain more tokens, like hnf
            tick = int(matches2.group(1))
            agent = matches2.group(3)
            reqType = matches2.group(5)
            txn = matches2.group(6)
            addr=matches2.group(8)
            isArrival = int(matches2.group(7))
            bufsize = int(matches2.group(9))

            #FILTERS, uncomment if you want to filter the statements
            if filter_statement(addr,txn,agent,test): continue

            encoding = txn+reqType+agent

            #counts the elapsed time from when the message is enqueued to the point it is dequeued
            if isArrival == 1:
                if encoding not in arrival_count_req.keys(): arrival_count_req[encoding] = 0
                else: 
                    arrival_count_req[encoding]+=1
                dt = 0
                current_count = arrival_count_req[encoding]
                txn_dict[encoding+str(current_count)] = tick
                bufsize_count[encoding+str(current_count)] = bufsize

            elif isArrival == 0:
                if encoding not in dequeue_count_req.keys(): dequeue_count_req[encoding] = 0
                else: 
                    dequeue_count_req[encoding]+=1
                current_count = dequeue_count_req[encoding]
                dt = (tick-txn_dict[encoding+str(current_count)])/TICKS_PER_CYCLE

            if not test:
                print(f"{tick},{dt},{agent},{addr},{reqType},{current_count},{isArrival},{txn},{bufsize_count[encoding+str(current_count)]}", file=f)
            else:
                print(f"{tick},{dt},{agent},{addr},{reqType},{isArrival},{txn},{bufsize}")
                assert(tick == 6628000)
                assert(agent=="hnf00.cntrl")
                assert(addr=="0x18400")
                assert(txn=="0x0000000000000001")
                assert(reqType=="rspOut")
                assert(bufsize==4)
                assert(isArrival==1)
        
        elif matches_dataseq:
            tick = int(matches_dataseq.group(1))
            agent = matches_dataseq.group(2)
            reqType = matches_dataseq.group(5)
            txn = matches_dataseq.group(4)
            addr=matches_dataseq.group(6)
            if txn != TXN and not test: continue
            if addr != ADDRESS and not test: continue
            if TXN_OUT == txn: continue

            if reqType=="ReqBegin":
                txn_dict[txn] = tick
                last_tick = tick
                if not test:
                    print(f"{tick},0,{agent},{addr},{reqType},{txn}",file=f)
                else:
                    print(f"{tick},0,{agent},{addr},{reqType},{txn}")
                    assert(tick == 33973000)
                    assert(agent=="cpu.data_sequencer")
                    assert(addr=="0x1840")
                    assert(txn=="0x0003000000002061")
                    assert(reqType=="ReqBegin")
            if reqType=="ReqDone":
                if not test:
                    print(f"{tick},{(tick-last_tick)/TICKS_PER_CYCLE},{agent},{addr},{reqType},{txn},{(tick-last_tick)/TICKS_PER_CYCLE}",file=f)
                else:
                    print(f"{tick},{(tick-last_tick)/TICKS_PER_CYCLE},{agent},{addr},{reqType},{txn},{(tick-last_tick)/TICKS_PER_CYCLE}")
                    assert(tick == 34095000)
                    assert(agent=="cpu.data_sequencer")
                    assert(addr=="0x1840")
                    assert(txn=="0x0003000000002061")
                    assert(reqType=="ReqDone")
                last_tick = tick

#just to parse the L2's transactions specifically
#in this version it filters out the datOut requests instead of all
def parse_l2(pattern,lines,f,lf,test):
    dequeue_rate = {}
    enqueue_rate = {}
    for line in lines:
        matches = re.search(pattern, line)
        if matches:
            tick = int(matches.group(1))
            agent = matches.group(3)
            reqType = matches.group(4)
            txn = matches.group(5)
            msgType = matches.group(6)
            isArrival = int(matches.group(7))
            addr=matches.group(8)
            bufsize = int(matches.group(9))
            dest = int(matches.group(10))
            if not test:
                if isArrival == 1:
                    if agent == "l2" and reqType == TYPE: #remove reqType equality to not filter request types
                        if tick not in enqueue_rate.keys(): enqueue_rate[tick] = [{"agent": agent, "addr": addr, "reqType": reqType,"msgType":msgType, "txn": txn, "dest":dest}]
                        else: enqueue_rate[tick].append({"agent": agent, "addr": addr, "reqType": reqType,"msgType":msgType, "txn": txn, "dest":dest})
                if isArrival == 0:
                    if agent == "l2" and reqType == TYPE: #remove reqType equality to not filter request types
                        if tick not in dequeue_rate.keys(): dequeue_rate[tick] = [{"agent": agent, "addr": addr, "reqType": reqType, "msgType":msgType, "txn": txn, "dest":dest}]
                        else: dequeue_rate[tick].append({"agent": agent, "addr": addr, "reqType": reqType, "msgType":msgType, "txn": txn, "dest":dest})
                        # print(f"{tick},{agent},{addr},{reqType},{txn},{diff}", file=f)
            else:
                print(matches.groups())
                assert(tick == 77500)
                assert(agent=="l2")
                assert(addr=="0")
                assert(txn=="0x0003000000000000")
                assert(msgType == "CompData_SC")
                assert(reqType=="datOut")
                assert(bufsize==2)
                assert(isArrival==1)
                assert(dest==1)
            continue

    print_all(dequeue_rate,f)
    print_all(enqueue_rate,lf)

def print_all(txn_map,f):
    for key,arr in txn_map.items():
        for value in arr:
            print(f"{round(key/TICKS_PER_CYCLE,0)},{value['agent']},{value['addr']},{value['reqType']},{value['txn']},{value['msgType']},{value['dest']}", file=f)
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--working-set',required=True,type=str,help='Working set')
    parser.add_argument('--num_cpus',required=True,type=str,help='Number of CPUs')
    parser.add_argument('--trace_file',required=True,type=str,help='Trace file')
    parser.add_argument('--outfile',required=True,type=str,help='Collated stats file')
    parser.add_argument('--outfile2',required=False,type=str,help='Collated stats file')
    parser.add_argument('--nw_model',required=True,type=str,help='NW model')
    parser.add_argument('--num_mem',required=True,type=str,help='Number of MCs')
    parser.add_argument('--seq_tbe',required=True,type=str,help='Number of sequencer TBEs')
    parser.add_argument('--test',required = False, default=False, action="store_true",help="enable test mode")
    parser.add_argument('--parse-l2', default=False, action="store_true",help="parsing mode, only L2 cache or all transactions")
    args = parser.parse_args()
    FILE_DIR = args.trace_file
    OUT_FILE = args.outfile
    OUT_FILE2 = args.outfile2
    
    #pattern for l1/l2 statements
    pattern_1 = r"^\s*(\d+):\s*system\.(\w+)\.(\w+)\.(\w+):\s*txsn:\s*(0x[0-9a-fA-F]+).*type:\s*(\w+).*isArrival:\s(\d+).*addr:\s*(0x[0-9a-fA-F]+|0).*bufferSize:\s(\d+).*dest:\s(\d+)"
    #pattern for data sequencer statement
    pattern_dataseq = r"(\d+):\s*system\.((\w+\.){1}\w+):\s*txsn:\s*(0x[0-9a-fA-F]+),\s*(ReqBegin|ReqDone).*addr:\s*(0x[0-9a-fA-F]+)"
    #pattern for hnf/snf statements
    pattern_2 = r"^\s*(\d+):\s*system\.(\w+)\.((\w+\.){1}\w+)\.(\w+):\s*txsn:\s*(0x[0-9a-fA-F]+).*isArrival:\s(\d+).*addr:\s*(0x[0-9a-fA-F]+).*bufferSize:\s(\d+)"
   
    print(f"opening {FILE_DIR}")

    if args.test:
        #simple test to confirm regex
        line = ["  77500: system.cpu.l2.datOut: txsn: 0x0003000000000000, type: CompData_SC, isArrival: 1, addr: 0, reqtor: Cache-2, bufferSize: 2, dest: 1,"]
        line2 = ["6628000: system.ruby.hnf00.cntrl.rspOut: txsn: 0x0000000000000001, type: CompDBIDResp, isArrival: 1, addr: 0x18400, reqtor: Cache-3, bufferSize: 4, dest: 2,"]

        lines = ["33973000: system.cpu.data_sequencer: txsn: 0x0003000000002061, ReqBegin=LD, addr: 0x1840",
                "34095000: system.cpu.data_sequencer: txsn: 0x0003000000002061, ReqDone=LD, addr: 0x1840, 244 cycles, 40 hops"]
        print("\nstart parser tests\n")
        parse_l2(pattern_1,pattern_2,pattern_dataseq,line,None,None,args.test)
        parse_txn(pattern_1,pattern_2,pattern_dataseq,line,None,None,args.test)
        parse_txn(pattern_1,pattern_2,pattern_dataseq,line2,None,None,args.test)
        parse_txn(pattern_1,pattern_2,pattern_dataseq,lines,None,None,args.test)
        print("\nall tests pass!")

    else:
        with open(FILE_DIR,'r') as lf:
                with open(OUT_FILE,'w') as f:
                    if args.parse_l2:
                        with open(OUT_FILE2,'w') as df:
                            # print(f"working set:{args.working_set}, num_cpus: {args.num_cpus}, num_DDR: {args.num_mem}, nw_model: {args.nw_model}, seq_tbe: {args.seq_tbe} ",file = f)
                            # print("Tick, dt (cycles), Agent, Address, TxnType, TxnTypeID, isArrival, TxnNo, Buffer Size",file=f)
                            lines = lf.readlines()
                            print("Cycle,Agent,Address,TxnType,TxnNo,MsgType,Dest",file=f)
                            print("Cycle,Agent,Address,TxnType,TxnNo,MsgType,Dest",file=df)
                            parse_l2(pattern_1,lines,f,df,args.test)
                    else:
                        parse_txn(pattern_1,pattern_2,pattern_dataseq,lines,f,args.test)


if __name__=="__main__":
    main()