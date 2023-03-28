import re
import os
import argparse
import numpy as np

def processRubyGeneratedFlags(logFile,dumpFile,tgtAddr):
    transitionPat=re.compile(r'^(\s*\d*): (\S+): \[Cache_Controller ([0-9]+)\], Time: ([0-9]+), state: ([\w]+), event: ([\w]+), addr: ([0-9a-fx]+)')
    actionPat=re.compile(r'^(\s*\d*): (\S+): executing ([\w]+)')
    nextStatePat=re.compile(r'^(\s*\d*): (\S+): next_state: ([\w]+)')
    tbeStatePat=re.compile(r'^(\s*\d*): (\S+): ([\S]+):([\d]+): TBEState')
    addrDict=dict() # Each address consist of a list of transitions and actions
    addr='INVALID'
    with open(logFile,'r') as f:
        for line in f :
            line=line.rstrip()
            tranMatch=transitionPat.match(line)
            actionMatch=actionPat.match(line)
            nextStateMatch=nextStatePat.match(line)
            tbeStateMatch=tbeStatePat.match(line)
            if tranMatch :
                addr=tranMatch.group(7)
                if addr in addrDict:
                    addrDict[addr].append(line)
                else :
                    addrDict[addr] = [line]
            elif (actionMatch or nextStateMatch or tbeStateMatch):
                assert(addr != 'INVALID')
                assert(addr in addrDict)
                addrDict[addr].append(line)
    with open(dumpFile,'w') as fw:
        if tgtAddr in addrDict :
            v = addrDict[tgtAddr]
            for line in v:
                print(line,file=fw)
        else :
            print(f'Addr={tgtAddr} not found',file=fw)

def bitSelect(addr,start,end):
    assert(start >= end)
    binAddr=bin(addr).lstrip('0b').rjust(64,'0')
    setBinAddr=binAddr[-start:-end]
    # print(f'setBinAddr: {len(binAddr)}, hexAddr: {hex(addr)},{start},{end}')
    return int(setBinAddr, base=2)

def processCHIReqInputs(options,logFile,dumpFile):
    reqInPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), type: ([a-zA-Z_]+), isArrival: ([0-1]), addr: ([xa-f0-9]+), reqtor: Cache-([\d]+), dest: ([\d]+),')
    tickPerCyc=500
    num_sets = (options.num_snoopfilter_entries / options.num_snoopfilter_assoc)
    num_set_bits=int(np.log2(num_sets))
    with open(logFile,'r') as f:
        with open(dumpFile,'w') as fw :
            print(f'Addr,ReqType,Reqtor,Dest,Cyc,SetIdx',file=fw)
            for line in f :
                reqInMatch=reqInPat.search(line)
                if reqInMatch :
                    msgBufferStr=reqInMatch.group(2)
                    if 'reqIn' in msgBufferStr:
                        cyc=int(reqInMatch.group(1))/tickPerCyc
                        reqType=reqInMatch.group(4)
                        addr=int(reqInMatch.group(6),base=16)
                        setIdx=bitSelect(addr,6+num_set_bits,6)
                        addrStr=reqInMatch.group(6)
                        reqtor=reqInMatch.group(7)
                        dest=reqInMatch.group(8)
                        print(f'{addrStr},{reqType},{reqtor},{dest},{cyc},{setIdx}',file=fw)

def processSnoopFilterEviction(options,logFile,dumpFile):
    tickPerCyc=500
    sfEvictPat=re.compile(r'^(\s*\d*): system.ruby.hnf01.cntrl: \[Cache_Controller ([0-9]+)\], Time: ([0-9]+), state: ([\w]+), event: SnoopFilterEviction, addr: ([0-9a-fx]+)')
    num_sets = (options.num_snoopfilter_entries / options.num_snoopfilter_assoc)
    num_set_bits=int(np.log2(num_sets))
    with open(logFile,'r') as f:
        with open(dumpFile,'w') as fw :
            print(f'Time,InitState,Addr,SetIdx',file=fw)
            for line in f:
                sfEvictMatch=sfEvictPat.search(line)
                if sfEvictMatch :
                    initState=sfEvictMatch.group(4)
                    if (initState == 'BUSY_BLKD') or (initState == 'BUSY_INTR') :
                        continue
                    cyc=int(sfEvictMatch.group(1))/tickPerCyc
                    addr=int(sfEvictMatch.group(5),base=16)
                    setIdx=bitSelect(addr,6+num_set_bits,6)
                    addrStr=sfEvictMatch.group(5)
                    print(f'{cyc},{initState},{addrStr},{setIdx}',file=fw)


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input',required=True,type=str)
    parser.add_argument('--output',required=True,type=str)
    parser.add_argument('--dbg-output',required=True,type=str)
    parser.add_argument('--num-snoopfilter-assoc',required=True,type=int)
    parser.add_argument('--num-snoopfilter-entries',required=True,type=int)
    parser.add_argument('--tgt-addr',required=False,type=str,default='0x400')
    options=parser.parse_args()
    logFile=options.input
    dumpFile=options.output
    tgtAddr=options.tgt_addr
    # processRubyGeneratedFlags(logFile,dumpFile,tgtAddr)
    processCHIReqInputs(options,logFile,dumpFile)
    processSnoopFilterEviction(options,logFile,options.dbg_output)

if __name__=="__main__":
    main()