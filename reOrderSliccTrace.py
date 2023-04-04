import re
import os
import argparse
import json
import ast
import pandas as pd
import numpy as np

def getTransitionsActions(logFile,dumpFile):
    transitionPat=re.compile(r'^(\s*\d*): (\S+): \[Cache_Controller ([0-9]+)\], Time: ([0-9]+), state: ([\w]+), event: ([\w]+), addr: ([0-9a-fx]+)')
    actionPat=re.compile(r'^(\s*\d*): (\S+): executing ([\w]+)')
    nextStatePat=re.compile(r'^(\s*\d*): (\S+): next_state: ([\w]+)')
    tbeStatePat=re.compile(r'^(\s*\d*): (\S+): ([\S]+):([\d]+): TBEState')
    addrDict=dict() # Each address consist of a list of transitions and actions
    addr='INVALID'
    tickPerCyc=500
    with open(logFile,'r') as f:
        for line in f :
            line=line.rstrip()
            tranMatch=transitionPat.match(line)
            actionMatch=actionPat.match(line)
            nextStateMatch=nextStatePat.match(line)
            tbeStateMatch=tbeStatePat.match(line)
            if tranMatch :
                addr=tranMatch.group(7)
                initState=tranMatch.group(5)
                event=tranMatch.group(6)
                cyc=int(tranMatch.group(1))/tickPerCyc
                agent=tranMatch.group(2)
                infoDict={
                    'cyc': cyc,
                    'addr': addr,
                    'agent': agent,
                    'init': initState,
                    'event': event,
                    'final': 'NULL2',
                    'actions': []
                }
                if addr in addrDict:
                    addrDict[addr].append(infoDict)
                else :
                    addrDict[addr] = [infoDict]
            elif actionMatch :
                assert(addr != 'INVALID')
                assert(addr in addrDict)
                action=actionMatch.group(3)
                addrDict[addr][-1]['actions'].append(action)
            elif nextStateMatch :
                assert(addr != 'INVALID')
                assert(addr in addrDict)
                addrDict[addr][-1]['final']=nextStateMatch.group(3)
    with open(dumpFile,'w') as fw:
        print(f'Cyc,Addr,Agent,InitState,Event,NextState,Action',file=fw)
        for k,vl in addrDict.items():
            addr=k
            for v in vl:
                cyc=v['cyc']
                agent=v['agent']
                init=v['init']
                event=v['event']
                final=v['final']
                for action in v['actions'] :
                    print(f'{cyc},{addr},{agent},{init},{event},{final},{action}',file=fw)


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input',required=True,type=str)
    parser.add_argument('--output',required=True,type=str)
    options=parser.parse_args()
    logFile=options.input
    dumpFile=options.output
    getTransitionsActions(logFile,dumpFile)

if __name__=="__main__":
    main()