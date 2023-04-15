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
    reqTbeSizePat=re.compile(f'system.ruby.hnf(\d*).cntrl.avg_size( +)(\d*[.,]?\d*)( +)# TBE Request Occupancy')
    replTbeSizePat=re.compile(f'system.ruby.hnf(\d*).cntrl.avg_size( +)(\d*[.,]?\d*)( +)# TBE Repl Occupancy')
    retryAckPats=re.compile(f'system.ruby.hnf(\d*).cntrl.cache.m_RetryAcks( +)(\d+)')
    numReads=-1
    numWrites=-1
    tickPerCyc=-1
    cyc=0
    simTicks=0
    statsFile=options.stats_file
    numHNFHits=0
    numHNFMisses=0
    reqTbeUtil=0
    replTbeSizeUtil=0
    retryAcks=0
    with open(statsFile,'r') as sf:
        for line in sf:
            readsMatch=readsPat.search(line)
            writesMatch=writesPat.search(line)
            tickPerCycMatch=tickPerCycPat.search(line)
            simTickMatch=simTicksPat.search(line)
            hnfHitMatch=hnfHitPat.search(line)
            hnfMissMatch=hnfMissPat.search(line)
            reqTbeUtilMatch=reqTbeSizePat.search(line)
            retryAckMatch=retryAckPats.search(line)
            replTbeSizeMatch=replTbeSizePat.search(line)
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
                reqTbeUtil += float(reqTbeUtilMatch.group(3))
            elif replTbeSizeMatch :
                replTbeSizeUtil += float(replTbeSizeMatch.group(3))
            elif retryAckMatch:
                retryAcks += int(retryAckMatch.group(3))
    assert(tickPerCyc > 0)
    cyc=simTicks/tickPerCyc
    bw=64*(numReads+numWrites)/cyc
    totalHNFAcc=numHNFHits+numHNFMisses
    hnfMissRate=-1
    replTbeSizeUtil=replTbeSizeUtil/(options.num_l3caches)
    reqTbeUtil=reqTbeUtil/(options.num_l3caches)
    if totalHNFAcc > 0:
        hnfMissRate=numHNFMisses/totalHNFAcc
    with open(options.collated_outfile,'a+') as fsw:
        print(f'{options.working_set},{options.num_cpus},{options.hnf_tbe},{options.allow_infinite_SF_entries},{options.unify_repl_TBEs},{reqTbeUtil},{replTbeSizeUtil},{retryAcks},{hnfMissRate},{bw}',file=fsw)

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--unify_repl_TBEs',required=True,type=ast.literal_eval,help=f'Unify repl and req TBEs')
    parser.add_argument('--working-set',required=True,type=str,help='Working set')
    parser.add_argument('--num_cpus',required=True,type=str,help='Number of CPUs')
    parser.add_argument('--stats_file',required=True,type=str,help='Statistic file')
    parser.add_argument('--collated_outfile',required=True,type=str,help='Collated stats file')
    parser.add_argument('--hnf-tbe',required=True,type=str,help='Collated stats file')
    parser.add_argument('--num-l3caches',required=True,type=int,help=f'Num of L3 caches')
    parser.add_argument('--allow-infinite-SF-entries',default=True, type=ast.literal_eval, help="Allow infinite SnoopFilter entries.")
    options=parser.parse_args()
    getReadWriteStats(options)

if __name__=="__main__":
    main()