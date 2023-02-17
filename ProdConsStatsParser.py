import re 
import os
import argparse
import numpy as np
import pprint as pp
import pandas as pd

def parseLinkLog(log_path,bottleNeckInfoFile):
    msg_pat = re.compile(r'(\s*\d*): (\S+): StallTime=(\d+),TotalMsgDelay=(\d+),MsgType=(\S+)')
    tickPerCyc=500
    with open(log_path,'r') as f:
        with open(bottleNeckInfoFile,'w') as fw:
            print(f'CurCyc,Loc,StallTime,TotalDelay,MsgType',file=fw)
            matcher=re.compile(msg_pat)
            for line in f:
                msg_srch = matcher.match(line)
                if msg_srch :
                    CurCyc = (int(msg_srch.group(1)))/tickPerCyc
                    Loc = msg_srch.group(2)
                    StallTime = (int(msg_srch.group(3)))/tickPerCyc
                    AggDelay = (int(msg_srch.group(4)))/tickPerCyc
                    MsgType = msg_srch.group(5)
                    print(f'{CurCyc},{Loc},{StallTime},{AggDelay},{MsgType}',file=fw)

def parseReadWriteTxn(logfile,dumpfile):
    startPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), ReqBegin=LD, [\s\S]*$')
    endPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), ReqDone=LD, [\s\S]*$')
    tickPerCyc=500
    msgDict=dict()
    with open(logfile,'r') as f:
        for line in f:
            startMatch=startPat.match(line)
            endMatch=endPat.match(line)
            if startMatch:
                TxSeqNum=startMatch.group(3)
                time=(int(startMatch.group(1)))/tickPerCyc
                msgDict[TxSeqNum] = {
                    'StartTime': time,
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
        print(f'TxSeqNum,StartTime,EndTime',file=fw)
        for k,v in msgDict.items():
            StartTime=v['StartTime']
            EndTime=v['EndTime']
            if (EndTime > 0) :
                assert(EndTime > StartTime)
                print(f'{k},{StartTime},{EndTime}',file=fw)
            else :
                print(f'{k},{StartTime},',file=fw)

def get1P1CStats(statsFile):
    dX=pd.read_csv(statsFile)
    dX.dropna(inplace=True)
    numReads=len(dX.index)
    endTime=dX['EndTime'].max()
    startTime=dX['StartTime'].min()
    dX['lat']=dX['EndTime']-dX['StartTime']
    totalCyc=endTime-startTime
    avgLat=dX['lat'].mean()
    minLat=dX['lat'].min()
    maxLat=dX['lat'].max()
    bw=(numReads*64)/totalCyc
    print(f'numReads={numReads},totalCyc={totalCyc},Bandwidth={bw}')
    print(f'Lat=({minLat,avgLat,maxLat})')
    return (startTime,endTime)

def getMsgTrace(msgTraceFile,msgCSVFile):
    tickPerCyc=500
    # msg_pat = re.compile(r'(\d*): (\S+): (\S+)')
    msg_pat= re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), arr: (\d*), (\S+), type: (\w+), req: (\w+), ')
    with open(msgTraceFile,'r') as f:
        with open(msgCSVFile,'w') as fw:
            print(f'ArrTime,Agent,MsgType',file=fw)
            # matcher=re.compile(msg_pat)
            for line in f:
                msg_srch = re.search(msg_pat,line)
                if msg_srch :
                    arrTime = (int(msg_srch.group(1)))/tickPerCyc
                    agent = msg_srch.group(2)
                    msgType = msg_srch.group(4)
                    print(f'{arrTime},{agent},{msgType}',file=fw)
                else :
                    print(f'DOES NOT MATCH \n {line}')

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output',required=True, type=str)
    options = parser.parse_args()
    msgPerfDumFile=os.path.join(options.input,'AllMsgLatDump.csv')
    allMsgLog=os.path.join(options.input,'simple.trace')
    # bottleNeckInfoFile=os.path.join(options.output, 'bottleneck.csv')
    # msgTraceFile=os.path.join(options.input,'txsn1.txt')
    # statsFile=os.path.join(options.input,'profile_stat.csv')
    # link_log=os.path.join(options.input,'link.log')
    # msgCSVFile=os.path.join(options.output,'MsgTrace.csv')
    # bestBottleNeckAnalyses=os.path.join(options.output,'SortedBottleneck.csv')
    # getMsgTrace(msgTraceFile,msgCSVFile)
    parseReadWriteTxn(allMsgLog,msgPerfDumFile)
    # parseLinkLog(link_log, bottleNeckInfoFile)
    if os.path.isfile(msgPerfDumFile):
        print(f'{options.input}')
        get1P1CStats(msgPerfDumFile)
        
    #     bX=pd.read_csv(bottleNeckInfoFile,index_col=False)
    #     bX3=bX.query(f'CurCyc >= @startTime').sort_values(by='StallTime',ascending=False)
    #     bX3.groupby(by=[''])
        # bX3.to_csv(bestBottleNeckAnalyses,index=False)


if __name__=="__main__":
    main()
