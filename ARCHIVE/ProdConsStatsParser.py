import re 
import os
import json
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
                msgMatch = matcher.match(line)
                if msgMatch :
                    CurCyc = (int(msgMatch.group(1)))/tickPerCyc
                    Loc = msgMatch.group(2)
                    StallTime = (int(msgMatch.group(3)))/tickPerCyc
                    AggDelay = (int(msgMatch.group(4)))/tickPerCyc
                    MsgType = msgMatch.group(5)
                    print(f'{CurCyc},{Loc},{StallTime},{AggDelay},{MsgType}',file=fw)

def parseReadWriteTxn(logfile,dumpfile):
    startPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), ReqBegin=LD, addr: ([x0-9a-f]+)')
    endPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), ReqDone=LD, addr: ([x0-9a-f]+), [\s\S]*$')
    tickPerCyc=500
    msgDict=dict()
    addrReqCount=dict()
    with open(logfile,'r') as f:
        for line in f:
            startMatch=startPat.match(line)
            endMatch=endPat.match(line)
            if startMatch:
                TxSeqNum=startMatch.group(3)
                time=(int(startMatch.group(1)))/tickPerCyc
                addr=startMatch.group(4)
                reqAgent=(startMatch.group(2)).lstrip('system.').rstrip('.data_sequencer')
                
                if (reqAgent,addr) in addrReqCount:
                    addrReqCount[(reqAgent,addr)]+=1
                else:
                    addrReqCount[(reqAgent,addr)]=1
                msgDict[TxSeqNum] = {
                    'StartTime': time,
                    'Addr' : addr,
                    'ReqAgent': reqAgent,
                    'ReqCount':addrReqCount[(reqAgent,addr)],
                    'EndTime': -1
                }
            elif endMatch:
                TxSeqNum=endMatch.group(3)
                time=(int(endMatch.group(1)))/tickPerCyc
                if TxSeqNum in msgDict:
                    msgDict[TxSeqNum]['EndTime'] = time
                else :
                    raise KeyError(f'{TxSeqNum} does not exist \n {line}')
            else:
                print(f'DOES NOT MATCH')
                print(line)
    with open(dumpfile, 'w') as fw:
        print(f'TxSeqNum,StartTime,EndTime,Addr,ReqAgent,ReqCount',file=fw)
        for k,v in msgDict.items():
            StartTime=v['StartTime']
            EndTime=v['EndTime']
            Addr=v['Addr']
            ReqCount=v['ReqCount']
            ReqAgent=v['ReqAgent']
            if (EndTime > 0) :
                assert(EndTime > StartTime)
                print(f'{k},{StartTime},{EndTime},{Addr},{ReqAgent},{ReqCount}',file=fw)
            else :
                print(f'{k},{StartTime},,{Addr},{ReqCount}',file=fw)

def get1P1CStats(statsFile,options):
    dX2=pd.read_csv(statsFile)
    dX2.dropna(inplace=True)
    dX=dX2.query(f'ReqCount <= 1')
    numReads=len(dX.index)
    endTime=dX['EndTime'].max()
    startTime=dX['StartTime'].min()
    dX['lat']=dX['EndTime']-dX['StartTime']
    totalCyc=endTime-startTime
    avgLat=dX['lat'].mean()
    minLat=dX['lat'].min()
    medLat=dX['lat'].median()
    maxLat=dX['lat'].max()
    bw=(numReads*64)/totalCyc
    retDict=dict({
        'bench_name': options.bench_name,
        'link_bw': options.link_bw,
        'prod_id': options.chs_prod_id,
        'cons_id':  options.chs_cons_id,
        'StartTime': startTime,
        'EndTime': endTime,
        'num_consumers': options.chs_num_consumers,
        'num_pairs': options.chs_num_pairs,
        'inj_interval': options.inj_rate,
        'dct': options.dct,
        'bw': bw,
        'min_lat': minLat,
        'avg_lat': avgLat,
        'med_lat': medLat,
        'max_lat': maxLat
    })
    return retDict

def getMsgTrace(msgTraceFile,msgCSVFile,startTime=0,tgtAddr='0x4780',agent='system.ruby.hnf14.cntrl.reqIn'):
    tickPerCyc=500
    msg_pat= re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), type: (\w+), isArrival: ([0-1]), addr: ([0-9a-fx]+), reqtor: (\S+), dest: ([\w,-]+)')
    with open(msgTraceFile,'r') as f:
        with open(msgCSVFile,'w') as fw:
            print(f'Txn,Addr,Time,Agent,MsgType,Reqtor,Dest',file=fw)
            for line in f:
                msgMatch = re.match(msg_pat,line)
                if msgMatch :
                    Txn = msgMatch.group(3)
                    Addr = msgMatch.group(6)
                    reqtor = msgMatch.group(7)
                    dest = msgMatch.group(8).replace(',','|')
                    isArrival = int(msgMatch.group(5))
                    Time = (int(msgMatch.group(1)))/tickPerCyc
                    Agent = msgMatch.group(2)
                    MsgType = msgMatch.group(4)
                    if (isArrival == 1) and (not ('network' in Agent)):
                        print(f'{Txn},{Addr},{Time},{Agent},{MsgType},{reqtor},{dest}',file=fw)
    
    if agent == 'all' :
        dfX=pd.read_csv(msgCSVFile).query('(Time >= @startTime)')
        dfX.to_csv(msgCSVFile,index=False)
    else:
        dfX=pd.read_csv(msgCSVFile).query('(Time >= @startTime) and (Agent == @agent)')
        dfX.to_csv(msgCSVFile,index=False)

def getAllMsgPerformanceDetails(StartTime):
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output',required=True, type=str)
    parser.add_argument('--dct',required=True)
    parser.add_argument('--link-bw',required=True,type=int)
    parser.add_argument('--inj-rate',required=True,type=int)
    parser.add_argument('--bench-name',required=True,type=str)
    parser.add_argument('--chs-prod-id',default=-1,type=int)
    parser.add_argument('--chs-cons-id',default=-1,type=int)
    parser.add_argument('--chs-num-pairs',default=-1,type=int)
    parser.add_argument('--chs-num-consumers',default=-1,type=int)
    options = parser.parse_args()
    msgTraceFile = os.path.join(options.input,'debug.trace')
    msgCSVFile = os.path.join(options.input,'AllMsgDetails.csv')
    getMsgTrace(msgTraceFile,msgCSVFile,StartTime)

def getAllMsgPerformance():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output',required=True, type=str)
    parser.add_argument('--dct',required=True)
    parser.add_argument('--link-bw',required=True,type=int)
    parser.add_argument('--inj-rate',required=True,type=int)
    parser.add_argument('--bench-name',required=True,type=str)
    parser.add_argument('--chs-prod-id',default=-1,type=int)
    parser.add_argument('--chs-cons-id',default=-1,type=int)
    parser.add_argument('--chs-num-pairs',default=-1,type=int)
    parser.add_argument('--chs-num-consumers',default=-1,type=int)
    options = parser.parse_args()
    msgPerfDumFile=os.path.join(options.input,'AllMsgLatDump.csv')
    allMsgLog=os.path.join(options.input,'simple.trace')
    parseReadWriteTxn(allMsgLog,msgPerfDumFile)
    if os.path.isfile(msgPerfDumFile):
        retDict=get1P1CStats(msgPerfDumFile,options)
        print(json.dumps(retDict))
        return retDict['StartTime']
    return 0

def main():
    StartTime=getAllMsgPerformance()
    getAllMsgPerformanceDetails(StartTime)

if __name__=="__main__":
    main()
