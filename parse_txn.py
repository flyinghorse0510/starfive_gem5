import os
from tqdm import tqdm
import argparse
import re

CPU_LINE = re.compile(r'^(\d+):\s+.*\.cpu\.l2\.(\w+):\s+(\w+):\s+txsn:\s+(\w+),.*$')
RUBY_LINE = re.compile('system.ruby.(\w*).(\w*).(\w*)')

FILE_DIR="/home/lester.leong/simulation/gem5_starlink2/output/GEM5_PDCP/GateTest/DDR_garnet/WS524288_Core1_L14KiB_L28KiB_L34KiB_MEM1_DMTTrue_DCTFalse_SEQ32_LoadFactor10_INJINTV1_BUF4_VCVNET4_HNF32_SNF32/debug.trac"
# FILE_DIR ="/home/lester.leong/simulation/gem5_starlink2/output/GEM5_PDCP/GateTest/DDR_simple/WS524288_Core1_L14KiB_L28KiB_L34KiB_MEM1_DMTTrue_DCTFalse_SEQ32_LoadFactor10_INJINTV1_BUF4_VCVNET4_HNF32_SNF32/debug.trac"
OUT_FILE="stat_garnet_lf10.csv"
TICKS_PER_CYCLE=500

#test lines
line = "237000: system.cpu.l2.reqIn: txsn: 0x0003000000000061, type: ReadShared, isArrival: 1, addr: 0x1840, reqtor: Cache-1, dest: 2,"
line2 = "6628000: system.ruby.hnf00.cntrl.rspOut: txsn: 0x0000000000000000, type: CompDBIDResp, isArrival: 0, addr: 0x18400, reqtor: Cache-3, dest: 2,"

lines = ["33973000: system.cpu.data_sequencer: txsn: 0x0003000000002061, ReqBegin=LD, addr: 0x1840",
         "34095000: system.cpu.data_sequencer: txsn: 0x0003000000002061, ReqDone=LD, addr: 0x1840, 244 cycles, 40 hops"]

TXN_OUT = "0x0000000000000000"
def main():
    pattern = r"(\d+):\s*system\.(\w+)\.(\w+)\.(\w+):\s*txsn:\s*(0x[0-9a-fA-F]+).*addr:\s*(0x[0-9a-fA-F]+)"
    pattern_dataseq = r"(\d+):\s*system\.((\w+\.){1}\w+):\s*txsn:\s*(0x[0-9a-fA-F]+),\s*(ReqBegin|ReqDone).*addr:\s*(0x[0-9a-fA-F]+)"
    pattern2 = r"(\d+):\s*system\.(\w+)\.((\w+\.){1}\w+)\.(\w+):\s*txsn:\s*(0x[0-9a-fA-F]+).*addr:\s*(0x[0-9a-fA-F]+)"
    txn_dict = {}
    print(f"opening {FILE_DIR}")
    # matches = re.search(pattern2, line2)
    # if matches:
    #     for i in range(1, 8):
    #         print(f"Group {i}: {matches.group(i)}")
    with open(FILE_DIR,'r') as lf:
        with open(OUT_FILE,'w') as f:
            print("Tick, dt (cycles), Agent, Address, TxnType, TxnNo",file=f)
            lines = lf.readlines()
            last_tick = 0
            for line in lines:
                matches = re.search(pattern, line)
                matches2 = re.search(pattern2, line)
                matches_dataseq = re.search(pattern_dataseq,line)
                if matches:
                    tick = int(matches.group(1))
                    agent = matches.group(3)
                    reqType = matches.group(4)
                    txn = matches.group(5)
                    addr=matches.group(6)
                    if TXN_OUT == txn: continue
                    if("network" in agent):continue
                    if (txn not in txn_dict.keys()):txn_dict[txn] = tick
                    dt = (tick-txn_dict[txn])/TICKS_PER_CYCLE
                    txn_dict[txn] = tick #record the last tick
                    print(f"{tick},{dt},{agent},{addr},{reqType},{txn}", file=f)

                elif matches2:
                    tick = int(matches2.group(1))
                    agent = matches2.group(3)
                    reqType = matches2.group(5)
                    txn = matches2.group(6)
                    addr=matches2.group(7)
                    if TXN_OUT == txn: continue
                    if("network" in agent):continue
                    if (txn not in txn_dict.keys()):txn_dict[txn] = tick
                    dt = (tick-txn_dict[txn])/TICKS_PER_CYCLE
                    txn_dict[txn] = tick
                    print(f"{tick},{dt},{agent},{addr},{reqType},{txn}",file=f)
                
                elif matches_dataseq:
                    tick = int(matches_dataseq.group(1))
                    agent = matches_dataseq.group(2)
                    reqType = matches_dataseq.group(5)
                    txn = matches_dataseq.group(4)
                    addr=matches_dataseq.group(6)
                    if TXN_OUT == txn: continue
                    if reqType=="ReqBegin":
                        txn_dict[txn] = tick
                        last_tick = tick
                        print(f"{tick},0,{agent},{addr},{reqType},{txn}",file=f)
                    if reqType=="ReqDone":
                        print(f"{tick},{(tick-last_tick)/TICKS_PER_CYCLE},{agent},{addr},{reqType},{txn},{(tick-last_tick)/TICKS_PER_CYCLE}",file=f)
                        last_tick = tick

if __name__=="__main__":
    main()