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
    statsFile=options.stats_file
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
    with open(options.collated_outfile,'a+') as fsw:
        print(f'{options.working_set},{options.num_cpus},{options.l3assoc},{options.unify_repl_TBEs},{reqTbeUtil},{retryAcks},{hnfMissRate},{bw}',file=fsw)

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--unify_repl_TBEs',required=True,type=ast.literal_eval,help=f'Unify repl and req TBEs')
    parser.add_argument('--working-set',required=True,type=str,help='Working set')
    parser.add_argument('--num_cpus',required=True,type=str,help='Number of CPUs')
    parser.add_argument('--stats_file',required=True,type=str,help='Statistic file')
    parser.add_argument('--collated_outfile',required=True,type=str,help='Collated stats file')
    parser.add_argument('--l3assoc',required=True,type=str,help='Collated stats file')
    options=parser.parse_args()
    getReadWriteStats(options)

if __name__=="__main__":
    main()