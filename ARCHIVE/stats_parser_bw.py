import re
import os
import argparse
import json
import ast
import pandas as pd
import numpy as np

def getReadWriteStats(options):
    readsPat=re.compile(f'system.cpu(\d*).numReads( +)(\d+)')
    writesPat=re.compile(f'system.cpu(\d*).numWrites( +)(\d+)')
    tickPerCycPat=re.compile(f'system.clk_domain.clock( +)(\d+)')
    simTicksPat=re.compile(f'simTicks( +)(\d+)')
    hnfHitPat=re.compile(f'system.ruby.hnf(\d*).cntrl.cache.m_demand_hits( +)(\d+)')
    hnfMissPat=re.compile(f'system.ruby.hnf(\d*).cntrl.cache.m_demand_misses( +)(\d+)')
    reqTbeUtilPat=re.compile(f'system.ruby.hnf(\d*).cntrl.avg_util( +)(\d*[.,]\d+)')
    retryAckPats=re.compile(f'system.ruby.hnf(\d*).cntrl.cache.m_RetryAcks( +)(\d+)')
    numReads=-1
    numWrites=-1
    tickPerCyc=-1
    cyc=0
    simTicks=0
    statsFile=options.output
    numHNFHits=0
    numHNFMisses=0
    reqTbeUtil=0
    retryAcks=0
    with open(statsFile,'r') as sf:
        for line in sf:
            readsMatch=readsPat.search(line)
            writesMatch=writesPat.search(line)
            tickPerCycMatch=tickPerCycPat.search(line)
            simTickMatch=simTicksPat.search(line)
            hnfHitMatch=hnfHitPat.search(line)
            hnfMissMatch=hnfMissPat.search(line)
            reqTbeUtilMatch=reqTbeUtilPat.search(line)
            retryAckMatch=retryAckPats.search(line)
            if readsMatch :
                numReads += int(readsMatch.group(3))
            elif writesMatch :
                numWrites += int(writesMatch.group(3))
            elif tickPerCycMatch :
                tickPerCyc = int(tickPerCycMatch.group(2))
            elif simTickMatch :
                simTicks = int(simTickMatch.group(2))
            elif hnfHitMatch :
                numHNFHits += int(hnfHitMatch.group(3))
            elif hnfMissMatch :
                numHNFMisses += int(hnfMissMatch.group(3))
            elif reqTbeUtilMatch :
                reqTbeUtil = float(reqTbeUtilMatch.group(3))
            elif retryAckMatch:
                retryAcks = int(retryAckMatch.group(3))
    assert(tickPerCyc > 0)
    cyc=simTicks/tickPerCyc
    bw=64*(numReads+numWrites)/cyc
    totalHNFAcc=numHNFHits+numHNFMisses
    hnfMissRate=-1
    if totalHNFAcc > 0:
        hnfMissRate=numHNFMisses/totalHNFAcc
    with open(options.dump_file,'a+') as fsw:
        print(f'{options.working_set},{options.num_cpu},{options.seq_tbe},{options.num_ddr},{retryAcks},{hnfMissRate},{bw}',file=fsw)


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--input-dir',required=True,type=str)
    parser.add_argument('--output', required=True, type=str)
    parser.add_argument('--num_cpu', required=True, type=int)
    parser.add_argument('--num_llc', required=True, type=int)
    parser.add_argument('--num_ddr', required=True, type=int)
    parser.add_argument('--trans', required=True, type=int)
    parser.add_argument('--snf_tbe', required=True, type=int)
    parser.add_argument('--dmt', required=True, type=ast.literal_eval)
    parser.add_argument('--linkwidth', required=True, type=int)
    parser.add_argument('--print', required=False,type=str,default='',help='choose what to print from [cpu,l1d,l1i,l2,llc,ddr] with comma as delimiter. e.g. --print cpu,llc will only print cpu and llc. default options is cpu,llc,ddr')
    parser.add_argument('--print_path', required=False, default=False, type=ast.literal_eval)
    parser.add_argument('--injintv', required=True, type=int)
    parser.add_argument('--seq_tbe', required=True, type=int) # SEQ_TBE
    parser.add_argument('--working-set',required=True,type=int)
    parser.add_argument('--bench',required=True,type=str)
    parser.add_argument('--dump_file',required=True,type=str,help='Dump file')
    options=parser.parse_args()
    getReadWriteStats(options)

if __name__=="__main__":
    main()
