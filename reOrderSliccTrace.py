import re
import os
import argparse
import json
import ast
import pandas as pd
import numpy as np

def getTransitionsActions(logFile,dumpFile,shorten=True):
    transitionPat=re.compile(r'^(\s*\d*): (\S+): \[Cache_Controller ([0-9]+)\], Time: ([0-9]+), state: ([\w]+), event: ([\w]+), addr: ([0-9a-fx]+)')
    actionPat=re.compile(r'^(\s*\d*): (\S+): addr: ([0-9a-fx]+), executing ([\w]+)')
    nextStatePat=re.compile(r'^(\s*\d*): (\S+): addr: ([0-9a-fx]+), next_state: ([\w]+)')
    tbeStatePat=re.compile(r'^(\s*\d*): (\S+): ([\S]+):([\d]+): TBEState')
    stallPat=re.compile(r'^(\s*\d*): (\S+): ([\S]+):([\d]+): addr: ([0-9a-fx]+), Stalled reqType: ([\w]+), dest: ([\S\d]+)')
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
            stallMatch=stallPat.match(line)
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
                addr=actionMatch.group(3)
                action=actionMatch.group(4)
                addrDict[addr][-1]['actions'].append(action)
            elif nextStateMatch :
                assert(addr != 'INVALID')
                assert(addr in addrDict)
                addr=nextStateMatch.group(3)
                addrDict[addr][-1]['final']=nextStateMatch.group(4)
            elif stallMatch:
                addr=stallMatch.group(5)
                assert(addr in addrDict)
                addrDict[addr][-1]['final']='STALL'
    with open(dumpFile,'w') as fw:
        if shorten:
            print(f'Cyc,Addr,Agent,InitState,Event,NextState',file=fw)
        else :
            print(f'Cyc,Addr,Agent,InitState,Event,NextState,Action',file=fw)
        for k,vl in addrDict.items():
            addr=k
            for v in vl:
                cyc=v['cyc']
                agent=v['agent']
                init=v['init']
                event=v['event']
                final=v['final']
                if shorten:
                    print(f'{cyc},{addr},{agent},{init},{event},{final}',file=fw)
                else :
                    for action in v['actions'] :
                        print(f'{cyc},{addr},{agent},{init},{event},{final},{action}',file=fw)
                


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input',required=True,type=str)
    parser.add_argument('--output',required=True,type=str)
    parser.add_argument('--shorten',type=ast.literal_eval,required=True,help='Ignore the action prints')
    options=parser.parse_args()
    logFile=options.input
    dumpFile=options.output
    getTransitionsActions(logFile,dumpFile,options.shorten)

if __name__=="__main__":
    main()