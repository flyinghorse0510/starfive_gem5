import re
import os
import ast
import copy
import json
import logging
import argparse
import numpy as np
import pprint as pp
import pandas as pd

def getAllStatsDir(root_dir):
    # Recursive function to find all files named "stats.txt" in the folder and its subfolders
    def find_output_dirs(folder):
        output_dirs = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file == "stats.txt":
                    # Check if the filepath contains "CHECKPNT"
                    if "CHECKPNT" not in root:
                        output_dirs.append(root)
                    else:
                        logging.debug(f'Skip: {root}')
        return output_dirs

    # Call the function to find all "stats.txt" files in "ARM_FS" folder and filter out files with "CHECKPNT" in their path
    output_dirs = find_output_dirs(root_dir)
    return output_dirs


def variableFileParser(args, variableFilePath):
    all_var_dict = {}
    variableFilePath = os.path.join(variableFilePath,'Variables.txt')
    with open(variableFilePath, 'r') as f:
        variables = f.readlines()
    for var in variables:
        kvpair= var.strip().split('=')
        if len(kvpair) == 2:
            all_var_dict[kvpair[0]]=kvpair[1]

    var_list = {
        'BENCHMARK':str,
        'NUMCPUS':int,
        'NUM_LLC':int,
        'WKSET': int,
        # 'RESTORE_CPU':str,
        # 'SNPFILTER_ENTRIES':str,
        'NUM_MEM':int,
        # 'NUM_DDR_Side':int,
        # 'NUM_DDR_XP':int,
        'DCT': str,
        'DMT': str,
        'HNF_TBE':int,
        'OUTPUT_DIR': str,
        'NUM_ACCEPTED_ENTRIES': int,
        'IDEAL_SNOOP_FILTER': str,
        'DECOUPLED_REQ_ALLOC': str,
        # 'SNF_TBE':int,
        # 'SEQ_TBE':int,
        # 'TRANS':int,
        # 'LINKWIDTH':int,
        # 'VC_PER_VNET':int,
        # 'BUFFER_SIZE':int,
        # 'NETWORK':str,
        # 'l1d_size':str,
        # 'l1i_size':str,
        # 'l2_size':str,
        'l3_size':str,
        # 'LLC_REPL':str
    }

    var_dict = dict()
    for key,ops in var_list.items():
        try:
            var_dict[key]=ops(all_var_dict.get(key))
        except:
            pass
    args = copy.deepcopy(args)
    for key,val in var_dict.items():
        setattr(args, key, val)
    return args

def getReadWriteStats(options):
    gen_memcpy_bw = (options.BENCHMARK == 'memcpy_test')
    readsPat        = re.compile(r'system.cpu(\d*).numReads( +)(\d+)')
    writesPat       = re.compile(r'system.cpu(\d*).numWrites( +)(\d+)')
    tickPerCycPat   = re.compile(r'system.clk_domain.clock( +)(\d+)')
    simTicksPat     = re.compile(r'simTicks( +)(\d+)')
    hnfHitPat       = re.compile(r'system.ruby.hnf(\d*).cntrl.cache.m_demand_hits( +)(\d+)')
    hnfMissPat      = re.compile(r'system.ruby.hnf(\d*).cntrl.cache.m_demand_misses( +)(\d+)')
    reqTbeSizePat   = re.compile(r'system.ruby.hnf(\d*).cntrl.avg_size( +)(\d*[.,]?\d*)( +)# TBE Request Occupancy')
    replTbeSizePat  = re.compile(r'system.ruby.hnf(\d*).cntrl.avg_size( +)(\d*[.,]?\d*)( +)# TBE Repl Occupancy')
    hnfRetryAckPats = re.compile(r'system.ruby.hnf(\d*).cntrl.cache.m_RetryAcks( +)(\d+)')
    snfRetryAckPats = re.compile(r'system.ruby.snf(\d*).cntrl.rspOut.m_retry_msgs( +)(\d+)')
    snfTbeSizePat   = re.compile(r'system.ruby.snf(\d*).cntrl.avg_size( +)(\d+)')
    numReads        = -1
    numWrites       = -1
    tickPerCyc      = -1
    cyc             = 0
    simTicks        = 0
    statsFile       = os.path.join(options.OUTPUT_DIR, 'stats.txt')
    numHNFHits      = 0
    numHNFMisses    = 0
    reqTbeUtil      = 0
    replTbeSizeUtil = 0
    hnfRetryAcks    = 0
    snfRetryAcks    = 0
    snfSizeUtil     = 0
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
    if gen_memcpy_bw :
        bw=(64*numReads)/cyc
    totalHNFAcc=numHNFHits+numHNFMisses
    hnfMissRate=-1
    replTbeSizeUtil=replTbeSizeUtil/(options.NUM_LLC)
    reqTbeUtil=reqTbeUtil/(options.NUM_LLC)
    snfSizeUtil=snfSizeUtil/(options.NUM_MEM)
    if totalHNFAcc > 0:
        hnfMissRate=numHNFMisses/totalHNFAcc

    return pd.DataFrame({
        'benchname': [options.BENCHMARK],
        'working_set': [options.WKSET],
        'num_cpus': [options.NUMCPUS],
        'num_llc': [options.NUM_LLC],
        'l3_size': [options.l3_size],
        'hnf_TBE': [options.HNF_TBE],
        'NUM_ACCEPTED_ENTRIES': [options.NUM_ACCEPTED_ENTRIES],
        'DECOUPLED_REQ_ALLOC': [options.DECOUPLED_REQ_ALLOC],
        'hnfMissRate': [hnfMissRate],
        'bw': [bw]
    }, index = None)

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--root-dir', required=True)
    parser.add_argument('--output-file', required=True)
    options=parser.parse_args()
    
    simDirList = getAllStatsDir(options.root_dir)
    simDataDict = {simDir: variableFileParser(options, simDir) for simDir in simDirList}
    df = pd.DataFrame()
    for _, simDataArgs in simDataDict.items(): 
        df = pd.concat([df, getReadWriteStats(simDataArgs)])

    with open(options.output_file, 'w') as f:
        df.to_csv(f, index=False, header=True)

if __name__=="__main__":
    main()