import re
import os
import json
import pandas as pd
import argparse
import ProdConsStatsParser as pcp

def parseMigratoryTrace(logFile, dumpFile):
    readStartPat = re.compile(r'^(\s*\d*): (\S+): MiGMemLaT\|Addr:([0-9a-fx]+),Iter:([0-9]+),Reqtor:([0-9]+),Start:R')
    readEndPat = re.compile(r'^(\s*\d*): (\S+): MiGMemLaT\|Addr:([0-9a-fx]+),Iter:([0-9]+),Reqtor:([0-9]+),Complete:R,misMatch:([0-1]+)')
    writeStartPat = re.compile(r'^(\s*\d*): (\S+): MiGMemLaT\|Addr:([0-9a-fx]+),Iter:([0-9]+),Reqtor:([0-9]+),Start:W')
    writeEndPat = re.compile(r'^(\s*\d*): (\S+): MiGMemLaT\|Addr:([0-9a-fx]+),Iter:([0-9]+),Reqtor:([0-9]+),Complete:W,misMatch:([0-1]+)')
    txnDict = dict()
    tickPerCyc = 500
    with open(logFile,'r') as f :
        for line in f :
            readStartMatch = readStartPat.match(line)
            readEndMatch = readEndPat.match(line)
            writeStartMatch = writeStartPat.match(line)
            writeEndMatch = writeEndPat.match(line)
            if readStartMatch :
                # This is the start of migratory transactions
                time = (int(readStartMatch.group(1)))/tickPerCyc
                agent = readStartMatch.group(2)
                addr = readStartMatch.group(3)
                it = int(readStartMatch.group(4))
                txnDict[(addr,it)] = {
                    'read_start' : time,
                    'read_end' : -1,
                    'write_start' : -1,
                    'write_end' : -1
                }
            elif readEndMatch :
                time = (int(readEndMatch.group(1)))/tickPerCyc
                agent = readEndMatch.group(2)
                addr = readEndMatch.group(3)
                it = int(readEndMatch.group(4))
                assert((addr,it) in txnDict)
                txnDict[(addr,it)]['read_end'] = time
            elif writeStartMatch :
                time = (int(writeStartMatch.group(1)))/tickPerCyc
                agent = writeStartMatch.group(2)
                addr = writeStartMatch.group(3)
                it = int(writeStartMatch.group(4))
                assert((addr,it) in txnDict)
                txnDict[(addr,it)]['write_start'] = time
            elif writeEndMatch :
                time = (int(writeEndMatch.group(1)))/tickPerCyc
                agent = writeEndMatch.group(2)
                addr = writeEndMatch.group(3)
                it = int(writeEndMatch.group(4))
                assert((addr,it) in txnDict)
                txnDict[(addr,it)]['write_end'] = time
            
    with open(dumpFile, 'w') as fw:
        print(f'Addr,It,ReadStart,ReadEnd,WriteStart,WriteEnd',file=fw)
        for k,v in txnDict.items():
            addr,it = k
            ReadStart=v['read_start']
            ReadEnd=v['read_end']
            WriteStart=v['write_start']
            WriteEnd=v['write_end']
            print(f'{addr},{it},{ReadStart},{ReadEnd},{WriteStart},{WriteEnd}',file=fw)

def parseTrueProdConsTrace(logFile, dumpFile):
    writeStartPat = re.compile(r'^(\s*\d*): (\S+): TrPrdCnsLaT\|Addr:([0-9a-fx]+),Iter:([0-9]+),ProdId:([0-9]+),WriteStart')
    writeEndPat = re.compile(r'^(\s*\d*): (\S+): TrPrdCnsLaT\|Addr:([0-9a-fx]+),Iter:([0-9]+),ProdId:([0-9]+),WriteEnd')
    readStartPat = re.compile(r'^(\s*\d*): (\S+): TrPrdCnsLaT\|Addr:([0-9a-fx]+),Iter:([0-9]+),ConsId:([0-9]+),ReadStart')
    readEndPat = re.compile(r'^(\s*\d*): (\S+): TrPrdCnsLaT\|Addr:([0-9a-fx]+),Iter:([0-9]+),ConsId:([0-9]+),ReadEnd')
    txnDict = dict()
    tickPerCyc = 500
    with open(logFile,'r') as f :
        for line in f :
            readStartMatch = readStartPat.match(line)
            readEndMatch = readEndPat.match(line)
            writeStartMatch = writeStartPat.match(line)
            writeEndMatch = writeEndPat.match(line)
            if writeStartMatch :
                # This is the start of migratory transactions
                time = (int(writeStartMatch.group(1)))/tickPerCyc
                agent = writeStartMatch.group(2)
                addr = writeStartMatch.group(3)
                it = int(writeStartMatch.group(4))
                txnDict[(addr,it)] = {
                    'write_start' : time,
                    'write_end' : -1,
                    'read_start' : -1,
                    'read_end' : -1,
                }
            elif writeEndMatch :
                time = (int(writeEndMatch.group(1)))/tickPerCyc
                agent = writeEndMatch.group(2)
                addr = writeEndMatch.group(3)
                it = int(writeEndMatch.group(4))
                assert((addr,it) in txnDict)
                txnDict[(addr,it)]['write_end'] = time
            elif readStartMatch :
                time = (int(readStartMatch.group(1)))/tickPerCyc
                agent = readStartMatch.group(2)
                addr = readStartMatch.group(3)
                it = int(readStartMatch.group(4))
                assert((addr,it) in txnDict)
                txnDict[(addr,it)]['read_start'] = time
            elif readEndMatch :
                time = (int(readEndMatch.group(1)))/tickPerCyc
                agent = readEndMatch.group(2)
                addr = readEndMatch.group(3)
                it = int(readEndMatch.group(4))
                assert((addr,it) in txnDict)
                txnDict[(addr,it)]['read_end'] = time

    with open(dumpFile, 'w') as fw:
        print(f'Addr,It,WriteStart,WriteEnd,ReadStart,ReadEnd',file=fw)
        for k,v in txnDict.items():
            addr,it = k
            ReadStart=v['read_start']
            ReadEnd=v['read_end']
            WriteStart=v['write_start']
            WriteEnd=v['write_end']
            print(f'{addr},{it},{WriteStart},{WriteEnd},{ReadStart},{ReadEnd}',file=fw)

def analyzeCsv(options,msgDumpCsv):
    dfX = pd.read_csv(msgDumpCsv)
    dfX['lat'] = dfX['WriteEnd']-dfX['ReadStart']
    minLat = dfX['lat'].min()
    maxLat = dfX['lat'].max()
    medLat = dfX['lat'].median()
    avgLat = dfX['lat'].mean()
    retDict = dict({
        'dct': options.dct,
        'allowSD': options.allow_SD,
        'num_cpus': options.num_cpus,
        'min_lat': minLat,
        'avg_lat': avgLat,
        'med_lat': medLat,
        'max_lat': maxLat
    })
    return retDict

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output',required=True, type=str)
    parser.add_argument('--num-cpus',required=True, type=int)
    parser.add_argument('--allow-SD',required=True, help="allow SD state") # True for MOESI, False for MESI
    parser.add_argument('--dct',required=True)
    parser.add_argument('--bench',required=True,type=str,default='migratory')
    options = parser.parse_args()
    allMsgLog=os.path.join(options.input,'debug.trace')
    msgDumpCsv=os.path.join(options.output,'AllMsgLatDump.csv')
    singleMsgDumpCsv=os.path.join(options.output,'SingleMsgLatDump.csv')
    if options.bench == 'migratory' :
        parseMigratoryTrace(allMsgLog,msgDumpCsv)
        pcp.getMsgTrace(allMsgLog,singleMsgDumpCsv,0,'0x400','all')
    else :
        parseTrueProdConsTrace(allMsgLog,msgDumpCsv)
    retDict = analyzeCsv(options,msgDumpCsv)
    print(json.dumps(retDict))

if __name__=="__main__":
    main()