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
    hnfRetryAckPats=re.compile(f'system.ruby.hnf(\d*).cntrl.cache.m_RetryAcks( +)(\d+)')
    snfRetryAckPats=re.compile(f'system.ruby.snf(\d*).cntrl.rspOut.m_retry_msgs( +)(\d+)')
    snfTbeSizePat=re.compile(f'system.ruby.snf(\d*).cntrl.avg_size( +)(\d+)')
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
    hnfRetryAcks=0
    snfRetryAcks=0
    snfSizeUtil=0
    with open(statsFile,'r') as sf:
        for line in sf:
            readsMatch=readsPat.search(line)
            writesMatch=writesPat.search(line)
            tickPerCycMatch=tickPerCycPat.search(line)
            simTickMatch=simTicksPat.search(line)
            hnfHitMatch=hnfHitPat.search(line)
            hnfMissMatch=hnfMissPat.search(line)
            reqTbeUtilMatch=reqTbeSizePat.search(line)
            hnfRetryAckMatch=hnfRetryAckPats.search(line)
            snfRetryAckMatch=snfRetryAckPats.search(line)
            replTbeSizeMatch=replTbeSizePat.search(line)
            snfTbeSizeMatch=snfTbeSizePat.search(line)
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
            elif hnfRetryAckMatch:
                hnfRetryAcks += int(hnfRetryAckMatch.group(3))
            elif snfRetryAckMatch:
                snfRetryAcks += int(snfRetryAckMatch.group(3))
            elif snfTbeSizeMatch:
                snfSizeUtil += int(snfTbeSizeMatch.group(3))
    assert(tickPerCyc > 0)
    cyc=simTicks/tickPerCyc
    bw=64*(numReads+numWrites)/cyc
    totalHNFAcc=numHNFHits+numHNFMisses
    hnfMissRate=-1
    replTbeSizeUtil=replTbeSizeUtil/(options.num_l3caches)
    reqTbeUtil=reqTbeUtil/(options.num_l3caches)
    snfSizeUtil=snfSizeUtil/(options.num_dirs)
    if totalHNFAcc > 0:
        hnfMissRate=numHNFMisses/totalHNFAcc
    configFile=options.config_file
    reqTBE=0
    replTBE=0
    snfTBE=0
    with open(configFile,'r') as fc:
        cfg=json.load(fc)
        if options.num_l3caches > 1 :
            reqTBE=cfg['system']['ruby']['hnf'][0]['cntrl']['number_of_TBEs']
            replTBE=cfg['system']['ruby']['hnf'][0]['cntrl']['number_of_repl_TBEs']
        else :
            reqTBE=cfg['system']['ruby']['hnf']['cntrl']['number_of_TBEs']
            replTBE=cfg['system']['ruby']['hnf']['cntrl']['number_of_repl_TBEs']
        if options.num_dirs > 1:
            snfTBE=cfg['system']['ruby']['snf'][0]['cntrl']['number_of_TBEs']
        else :
            snfTBE=cfg['system']['ruby']['snf']['cntrl']['number_of_TBEs']

    with open(options.collated_outfile,'a+') as fsw:
        print(f'{options.working_set},{options.num_cpus},{options.chi_data_width},{reqTBE},{replTBE},{options.part_TBEs},{reqTbeUtil},{replTbeSizeUtil},{hnfRetryAcks},{snfTBE},{snfSizeUtil},{snfRetryAcks},{hnfMissRate},{bw}',file=fsw)

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--part-TBEs',required=True,type=ast.literal_eval,help=f'Unify repl and req TBEs')
    parser.add_argument('--working-set',required=True,type=str,help='Working set')
    parser.add_argument('--num_cpus',required=True,type=str,help='Number of CPUs')
    parser.add_argument('--stats_file',required=True,type=str,help='Statistic file')
    parser.add_argument('--config_file',required=True,type=str,help='Config file (json)')
    parser.add_argument('--collated_outfile',required=True,type=str,help='Collated stats file')
    parser.add_argument('--hnf-tbe',required=True,type=str,help='Collated stats file')
    parser.add_argument('--num-l3caches',required=True,type=int,help=f'Num of L3 caches')
    parser.add_argument('--num-dirs',default=1,type=int,help=f'Number of memory controllers')
    parser.add_argument('--chi-data-width',default=16,type=int,help=f'DAT channel width of CHI cache controllers. Same for all controllers')

    options=parser.parse_args()
    getReadWriteStats(options)

if __name__=="__main__":
    main()