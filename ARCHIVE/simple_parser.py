import re 
import os
import json
import argparse
import numpy as np
import pprint as pp
import pandas as pd


def parseReadWriteTxn(logfile,dumpfile):
    startPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), ReqBegin=LD, addr: ([x0-9a-f]+)')
    endPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), ReqDone=LD, addr: ([x0-9a-f]+), [\s\S]*$')
    tickPerCyc=500
    msgDict=dict()

    with open(logfile,'r') as f:
        for line in f:
            startMatch=startPat.match(line)
            endMatch=endPat.match(line)
            if startMatch:
                TxSeqNum=startMatch.group(3)
                time=(int(startMatch.group(1)))/tickPerCyc
                addr=startMatch.group(4)
                reqAgent=(startMatch.group(2)).lstrip('system.').rstrip('.data_sequencer')
                
                msgDict[TxSeqNum] = {
                    'StartTime': time,
                    'Addr' : addr,
                    'ReqAgent': reqAgent,
                    'EndTime': -1
                }
            elif endMatch:
                TxSeqNum=endMatch.group(3)
                time=(int(endMatch.group(1)))/tickPerCyc
                if TxSeqNum in msgDict:
                    msgDict[TxSeqNum]['EndTime'] = time
                else :
                    raise KeyError(f'{TxSeqNum} does not exist')
            else:
                print(f'DOES NOT MATCH')
                print(line)
    with open(dumpfile, 'w') as fw:
        print(f'TxSeqNum,StartTime,EndTime,Addr,ReqAgent,ReqCount',file=fw)
        for k,v in msgDict.items():
            StartTime=v['StartTime']
            EndTime=v['EndTime']
            Addr=v['Addr']
            if (EndTime > 0) :
                assert(EndTime > StartTime)
                print(f'{k},{StartTime},{EndTime},{Addr}',file=fw)
            else :
                print(f'{k},{StartTime},,{Addr}',file=fw)

def main():
    
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)

    options = parser.parse_args()
    msgPerfDumFile=os.path.join(options.input,'AllMsgLatDump.csv')
    allMsgLog=os.path.join(options.input,'simple.trace')
    parseReadWriteTxn(allMsgLog,msgPerfDumFile)


if __name__=="__main__":
    main()
