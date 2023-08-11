import re
import os
import ast
import argparse
import pandas as pd

def getTransitionsActions(logFile,xlsxFile,shorten=True):
    dumpFile=f'/tmp/01.csv'
    dumpFile2=f'/tmp/02.csv'
    transitionPat=re.compile(r'^(\s*\d*): (\S+): \[Cache_Controller ([0-9]+)\], Time: ([0-9]+), state: ([\w]+), event: ([\w]+), addr: ([0-9a-fx]+)')
    actionPat=re.compile(r'^(\s*\d*): (\S+): addr: ([0-9a-fx]+), executing ([\w]+)')
    nextStatePat=re.compile(r'^(\s*\d*): (\S+): addr: ([0-9a-fx]+), next_state: ([\w]+)')
    addrDict=dict() # Each address consist of a list of transitions and actions
    addrTransitionCount=dict()
    addrTxnCount=dict()
    addr='INVALID'
    tickPerCyc=500
    with open(logFile,'r') as f:
        for line in f :
            line=line.rstrip()
            tranMatch=transitionPat.match(line)
            actionMatch=actionPat.match(line)
            nextStateMatch=nextStatePat.match(line)
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
                    'count': addrTransitionCount.get(addr,0),
                    'actions': []
                }
                if addr in addrDict:
                    addrDict[addr].append(infoDict)
                    addrTransitionCount[addr] += 1
                else :
                    addrDict[addr] = [infoDict]
                    addrTransitionCount[addr] = 0
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
    with open(dumpFile,'w') as fw:
        if shorten:
            print(f'Cyc,Addr,Agent,InitState,Event,NextState,Count',file=fw)
        else :
            print(f'Cyc,Addr,Agent,InitState,Event,NextState,Action,Count',file=fw)
        with open(dumpFile2,'w') as fw2:
            print(f'Addr,Agent,Init,InitCyc,Final,FinalCyc,Count',file=fw2)
            for k,vl in addrDict.items():
                addr = k
                txnCount = addrTxnCount.get(addr,1)
                initial = vl[0]['init']
                initCyc = vl[0]['cyc']
                final =  vl[-1]['final']
                finalCyc =  vl[-1]['cyc']
                agent=vl[0]['agent']
                print(f'{addr},{agent},{initial},{initCyc},{final},{finalCyc},{txnCount}',file=fw2)
                if addr in addrTxnCount :
                    addrTxnCount[addr] += 1
                else :
                    addrTxnCount[addr] = 1
                
                for v in vl:
                    cyc=v['cyc']
                    agent=v['agent']
                    init=v['init']
                    event=v['event']
                    final=v['final']
                    count=v['count']
                    if shorten:
                        print(f'{cyc},{addr},{agent},{init},{event},{final},{count}',file=fw)
                    else :
                        for action in v['actions'] :
                            print(f'{cyc},{addr},{agent},{init},{event},{final},{action},{count}',file=fw)

    dfX = pd.read_csv(dumpFile).sort_values(by=['Cyc','Count'],ascending=[True,True])
    transientStates=set(['BUSY_BLKD','BUSY_INTR'])
    dfX2 = pd.read_csv(dumpFile2).query(f'Final in @transientStates')
    with pd.ExcelWriter(xlsxFile) as xlw:
        dfX.to_excel(xlw,sheet_name='Sheet1',index=False)
        dfX2.to_excel(xlw,sheet_name='Sheet2',index=False)
    # dfX.to_csv(dumpFile,index=False)


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