import re
import os
import argparse
import json
import ast
import pandas as pd
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

def getBinaryAddr(addr):
    binAddr=bin(addr).lstrip('0b').rjust(64,'0')
    return binAddr

def getSnoopFilterStartBit(options,jsonFile):
    snoopfilter_start_bit=-1
    with open(jsonFile,'r') as fc:
        cfg=json.load(fc)
        num_llc=int(options.num_llc)
        if  num_llc > 1 :
            snoopfilter_start_bit=int(cfg['system']['ruby']['hnf'][0]['cntrl']['snoopfilter_start_index_bit'])
        else :
            snoopfilter_start_bit=int(cfg['system']['ruby']['hnf']['cntrl']['snoopfilter_start_index_bit'])
    return snoopfilter_start_bit

def getSequencerOutput(options,jsonFile,logFile):
    tickPerCyc=500
    # memTestInPat=re.compile(r'^(\s*\d*): (\S+): SFReplMemTest\|Addr:([xa-f0-9]+),Iter:1,Reqtor:0,Start:(R|W)')
    memTestInPat=re.compile(r'^(\s*\d*): system.cpu(\d*).data_sequencer: txsn: (\w+), ReqBegin=(LD|ST), addr: ([xa-f0-9]+)')
    seqOutputList=[]
    with open(logFile,'r') as f:
        for line in f:
            memTestIMatch=memTestInPat.search(line)
            if memTestIMatch :
                cyc=int(memTestIMatch.group(1))/tickPerCyc
                reqType='SeqReq'
                setIdx=-1
                addrStr=memTestIMatch.group(5)
                reqtor=memTestIMatch.group(2)
                if reqtor == '':
                    reqtor = '0'
                dest='---'
                txnIdStr=memTestIMatch.group(3)
                seqOutputList.append({
                    'Addr': addrStr,
                    'Txn': txnIdStr,
                    'ReqType': reqType,
                    'Reqtor': reqtor,
                    'Dest': dest,
                    'Cyc': cyc,
                    'SFSetId': setIdx
                })
    return seqOutputList

def getHNFInput(options,jsonFile,logFile):
    tickPerCyc=500
    hnfInPat=re.compile(r'^(\s*\d*): system\.ruby\.hnf(\d+)\.cntrl\.reqIn: txsn: (\w+), type: ([a-zA-Z_]+), isArrival: ([0-1]), addr: ([xa-f0-9]+), reqtor: Cache-([\d]+), dest: ([\d]+),')
    seqOutputList=[]
    with open(logFile,'r') as f:
        for line in f :
            hnfInMatch=hnfInPat.search(line)
            if hnfInMatch :
                # msgBufferStr=hnfInMatch.group(2)
                cyc=int(hnfInMatch.group(1))/tickPerCyc
                reqType=hnfInMatch.group(4)
                # addr=int(hnfInMatch.group(6),base=16)
                setIdx=-1 #bitSelect(addr,snoopfilterStartBit+num_set_bits,snoopfilterStartBit)
                addrStr=hnfInMatch.group(6)
                reqtor=hnfInMatch.group(7)
                dest=int(hnfInMatch.group(2))
                txnIdStr=hnfInMatch.group(3)
                seqOutputList.append({
                    'Addr':addrStr,
                    'Txn': txnIdStr,
                    'ReqType': reqType,
                    'Reqtor': reqtor,
                    'Dest': dest,
                    'Cyc': cyc,
                    'SFSetId': setIdx
                })
    return seqOutputList
    

def processAddressRequests(options,jsonFile,logFile,dumpFile,reqtorPipelineLoc=0):
    """
        @options           : Parser options
        @jsonFile          : JSON config file
        @reqtorPipelineLoc : Location of the agent in pipeline from the upstream
                             0 -- sequencer output
                             1 -- L1D output
                             2 -- L2 output
                             3 -- HNF input

    """
    isMatched=False
    if reqtorPipelineLoc == 0:
        seqOutputList = getSequencerOutput(options,jsonFile,logFile)
        isMatched=True
    elif reqtorPipelineLoc == 3:
        seqOutputList = getHNFInput(options,jsonFile,logFile)
        isMatched=True
    else :
        raise NotImplementedError(f'Implement parsers for other agents in the system')
    if isMatched:
        with open(dumpFile,'w') as fw:
            print(f'Addr,Txn,ReqType,Reqtor,Dest,Cyc,SetIdx',file=fw)
            for v in seqOutputList:
                addrStr = v['Addr'] 
                reqType = v['ReqType']
                reqtor = v['Reqtor']
                dest = v['Dest']
                cyc = v['Cyc']
                setIdx = v['SFSetId']
                txnIdStr = v['Txn']
                print(f'{addrStr},{txnIdStr},{reqType},{reqtor},{dest},{cyc},{setIdx}',file=fw)
        

def processEvents(options,jsonFile,logFile,dumpFile):
    tickPerCyc=500
    evtList=[r'SnoopFilterEviction',
             r'ReadUnique_PoC',
             r'ReadShared',
             r'CleanUnique',
             r'Evict',
             r'WriteBackFull',
             r'WriteEvictFull',
             r'LocalHN_Eviction',
             r'Global_Eviction']
    txnPat=re.compile(r'^(\s*\d*): (\S+): \[Cache_Controller ([0-9]+)\], Time: ([0-9]+), state: ([\w]+), event: ('+'|'.join(evtList)+r'), addr: ([0-9a-fx]+)')
    num_sets = (options.num_snoopfilter_entries / options.num_snoopfilter_assoc)
    num_set_bits=int(np.log2(num_sets))
    snoopfilterStartBit = getSnoopFilterStartBit(options,jsonFile)
    assert(snoopfilterStartBit > 0)
    with open(logFile,'r') as f:
        with open(dumpFile,'w') as fw :
            print(f'Cyc,Addr,SetIdx,InitState,Event,Dest',file=fw)
            for line in f:
                txnMatch=txnPat.search(line)
                if txnMatch :
                    initState=txnMatch.group(5)
                    if (initState == 'BUSY_BLKD') or (initState == 'BUSY_INTR') :
                        continue
                    cyc=int(txnMatch.group(1))/tickPerCyc
                    addrStr=txnMatch.group(7)
                    addr=int(addrStr,base=16)
                    setIdx=bitSelect(addr,snoopfilterStartBit+num_set_bits,snoopfilterStartBit)
                    hnfId=txnMatch.group(3)
                    event=txnMatch.group(6)
                    print(f'{cyc},{addrStr},{setIdx},{initState},{event},{hnfId}',file=fw)

def estimateDTMCMatrix(stateSeq,stateIds):
    """
        Estimate the DTMC transition
        probability given an 
        @stateSeq : Input Sequence
        @stateIds : State IDs
    """
    X=[0 for _ in range(len(stateIds))]
    Y_t=stateSeq
    T=range(len(Y_t)-1)
    for s in stateIds:
        n = sum([1 if ((Y_t[t]==s) and (Y_t[t+1]==s)) else 0 for t in T])
        d = sum([1 if (Y_t[t]==s) else 0 for t in T])
        if (d == 0) : # Current State 's' is never entered
            X[s] = -1
        else :
            X[s] = n/d
    return X

def getHNFTransitionProbability(options,dumpFile_hnf):
    acceptableReq=set({'ReadShared', 'ReadUnique', 'CleanUnique'})
    # dfX2=pd.read_csv(dumpFile_hnf).query(f'ReqType in @acceptableReq').sort_values(by=['Cyc'],ascending=[True])
    dfX2=pd.read_csv(dumpFile_hnf).sort_values(by=['Cyc'],ascending=[True])
    hnfSet=set(range(options.num_llc))
    X = estimateDTMCMatrix(dfX2['Dest'].values,hnfSet)
    return X

def getReadWriteStats(options,dumpFile_hnf):
    readsPat=re.compile(f'system.cpu(\d*).numReads( +)(\d+)')
    writesPat=re.compile(f'system.cpu(\d*).numWrites( +)(\d+)')
    tickPerCycPat=re.compile(f'system.clk_domain.clock( +)(\d+)')
    simTicksPat=re.compile(f'simTicks( +)(\d+)')
    hnfHitPat=re.compile(f'system.ruby.hnf(\d*).cntrl.cache.m_demand_hits( +)(\d+)')
    hnfMissPat=re.compile(f'system.ruby.hnf(\d*).cntrl.cache.m_demand_misses( +)(\d+)')
    sfMissPat=re.compile(f'system.ruby.hnf(\d*).cntrl.directory.m_snoopfilter_misses( +)(\d+)')
    sfAccPat=re.compile(f'system.ruby.hnf(\d*).cntrl.directory.m_snoopfilter_accesses( +)(\d+)')
    numReads=-1
    numWrites=-1
    tickPerCyc=-1
    cyc=0
    simTicks=0
    statsFile=options.stats_file
    numHNFHits=0
    numHNFMisses=0
    numSFMiss=0
    numSFAcc=0
    with open(statsFile,'r') as sf:
        for line in sf:
            readsMatch=readsPat.search(line)
            writesMatch=writesPat.search(line)
            tickPerCycMatch=tickPerCycPat.search(line)
            simTickMatch=simTicksPat.search(line)
            hnfHitMatch=hnfHitPat.search(line)
            hnfMissMatch=hnfMissPat.search(line)
            sfMissMatch=sfMissPat.search(line)
            sfAccMatch=sfAccPat.match(line)
            if readsMatch :
                numReads = int(readsMatch.group(3))
            elif writesMatch :
                numWrites=int(writesMatch.group(3))
            elif tickPerCycMatch :
                tickPerCyc = int(tickPerCycMatch.group(2))
            elif simTickMatch :
                simTicks = int(simTickMatch.group(2))
            elif hnfHitMatch :
                numHNFHits += int(hnfHitMatch.group(3))
            elif hnfMissMatch :
                numHNFMisses += int(hnfMissMatch.group(3))
            elif sfMissMatch :
                numSFMiss += int(sfMissMatch.group(3))
            elif sfAccMatch :
                numSFAcc += int(sfAccMatch.group(3))
    assert(tickPerCyc > 0)
    cyc=simTicks/tickPerCyc
    bw=64*(numReads+numWrites)/cyc
    totalHNFAcc=numHNFHits+numHNFMisses
    hnfMissRate=-1
    sfMissRate=-1
    if totalHNFAcc > 0:
        hnfMissRate=numHNFMisses/totalHNFAcc
    if numSFAcc > 0:
        sfMissRate=numSFMiss/numSFAcc
    X=getHNFTransitionProbability(options,dumpFile_hnf)
    with open(options.collated_outfile,'a+') as fsw:
        jstr=','.join([f'{x:.2f}' for x in X])
        print(f'{options.block_stride},{options.randomized_acc},{options.xored_addr},{bw},{hnfMissRate},{sfMissRate},{jstr}',file=fsw)



def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input',required=True,type=str)
    parser.add_argument('--input-cfg',required=True,type=str)
    parser.add_argument('--output-seq',required=True,type=str)
    parser.add_argument('--output-hnf',required=True,type=str)
    parser.add_argument('--output-dbg',required=True,type=str)
    parser.add_argument('--num_llc',required=True,type=int)
    parser.add_argument('--num-snoopfilter-assoc',required=True,type=int)
    parser.add_argument('--num-snoopfilter-entries',required=True,type=int)
    parser.add_argument('--block-stride',required=False,default=0,type=int,help=f'Block Stride. Stride=2^(block_stride)')
    parser.add_argument('--randomized-acc',required=False,default=False,type=ast.literal_eval,help=f'randomized access pattern')
    parser.add_argument('--xored-addr',required=False,default=False,type=ast.literal_eval,help='Addr xored')
    parser.add_argument('--collated-outfile',required=False,default='null',type=str,help='Collated Output filename')
    parser.add_argument('--stats-file',required=False,default='null',type=str,help='')
    options=parser.parse_args()
    logFile=options.input
    dumpFile_seq=options.output_seq
    dumpFile_hnf=options.output_hnf
    jsonFile=options.input_cfg
    # processRubyGeneratedFlags(logFile,dumpFile,tgtAddr)
    if options.collated_outfile != 'null' :
        getReadWriteStats(options,dumpFile_hnf)
    else :
        processAddressRequests(options,jsonFile,logFile,dumpFile_seq,0)
        processAddressRequests(options,jsonFile,logFile,dumpFile_hnf,3)


if __name__=="__main__":
    main()