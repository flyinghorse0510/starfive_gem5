import re
import os
import json
import ast
import argparse
import numpy as np
import pandas as pd

def getReadWriteStats(options):
    readsPat=re.compile(f'system.cpu(\d*).numReads( +)(\d+)')
    writesPat=re.compile(f'system.cpu(\d*).numWrites( +)(\d+)')
    tickPerCycPat=re.compile(f'system.clk_domain.clock( +)(\d+)')
    simTicksPat=re.compile(f'simTicks( +)(\d+)')
    numReads=0
    numWrites=0
    tickPerCyc=0
    cyc=0
    simTicks=0
    statsFile=options.stats_file
    with open(statsFile,'r') as sf:
        for line in sf:
            readsMatch=readsPat.search(line)
            writesMatch=writesPat.search(line)
            tickPerCycMatch=tickPerCycPat.search(line)
            simTickMatch=simTicksPat.search(line)
            if readsMatch :
                numReads += int(readsMatch.group(3))
            elif writesMatch :
                numWrites += int(writesMatch.group(3))
            elif tickPerCycMatch :
                tickPerCyc = int(tickPerCycMatch.group(2))
            elif simTickMatch :
                simTicks = int(simTickMatch.group(2))
    assert(tickPerCyc > 0)
    cyc=simTicks/tickPerCyc
    bw=64*(numReads+numWrites)/cyc
    accLat=cyc/(numReads+numWrites)
    with open(options.collated_outfile,'a+') as fsw:
        print(f'{options.working_set},{options.num_cpus},{options.seq_tbe},{options.num_mem},{options.nw_model},{options.linkwidth},{bw},{accLat}',file=fsw)

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--working-set',required=True,type=str,help='Working set')
    parser.add_argument('--num_cpus',required=True,type=str,help='Number of CPUs')
    parser.add_argument('--stats_file',required=True,type=str,help='Statistic file')
    parser.add_argument('--collated_outfile',required=True,type=str,help='Collated stats file')
    parser.add_argument('--nw_model',required=True,type=str,help='NW model')
    parser.add_argument('--num_mem',required=True,type=str,help='Number of MCs')
    parser.add_argument('--seq_tbe',required=True,type=str,help='Number of sequencer TBEs')
    parser.add_argument('--linkwidth',required=True,type=int,help='Link Width')
    options=parser.parse_args()
    getReadWriteStats(options)

if __name__=="__main__":
    main()