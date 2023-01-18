import re
import sys
import argparse
import pprint as pp

class CacheLineTransition(object):
    """
        Keeps tracks of 
        the transaction an address passes through
    """
    # Suppress tracking dumps for instruction addresses
    # We assume instruction address and data address do 
    # not overlap
    instAddressMap=set()
    
    def __init__(self, addr, op, evicting_addr=None):
        self.addr = addr
        self.op = op
        self.lineTransition = dict()
        self.evicting_addr = evicting_addr
    
    def __str__(self):
        return pp.pformat(self.lineTransition)

    def addControllerTransition(self,cacheTranInfoDict):
        if self.evicting_addr :
            evicting_addr = self.evicting_addr
        else :
            evicting_addr = '-'
        self.lineTransition = {
            'time': cacheTranInfoDict['Time'],
            'addr': self.addr,
            'evicting_addr': evicting_addr,
            'agent' : cacheTranInfoDict['agent'],
            'state': cacheTranInfoDict['state'],
            'event': cacheTranInfoDict['event'],
            'action_list' : []
        }
       

    
    def addAction(self, line):
        infoSuffix = line.split(':')[2:]
        propEntryToks =  [__t.lstrip().rstrip() for __t in infoSuffix][0]
        propEntryToks2 = propEntryToks.split(' ')
        action = propEntryToks2[1].lstrip().rstrip()
        self.lineTransition['action_list'].append(action)

    def clearActionList(self):
        self.lineTransition['action_list'].clear()

    def addNextState(self,line):
        infoSuffix = line.split(':')[2:]
        propEntryToks =  [__t.lstrip().rstrip() for __t in infoSuffix]
        self.lineTransition['next_state'] = propEntryToks[1]

    def dump(self,hdrSeq,dumpFd):
        printStr=f''
        for i,k in enumerate(hdrSeq) :
            if k == 'addr' :
                printStr+=f'{self.addr}'
            else :
                val=self.lineTransition.get(k,'NA')
                if k == 'action_list' :
                    printStr+='|'.join(val)
                else :
                    printStr+=f'{val}'
            if i < len(hdrSeq)-1 :
                printStr+=','
        print(f'{printStr}',file=dumpFd) 

def processCacheTranLine(cacheTranLine):
    """
        Process each line 
        representing a cache transition
    """
    toks=cacheTranLine.split(',')
    toksClean = [tok.lstrip().rstrip() for tok in toks]
    cacheTranInfoDict=dict()
    for i,tok in enumerate(toksClean) :
        __tmp = tok.split(':')
        propEntryToks = [__t.lstrip().rstrip() for __t in __tmp]
        if i > 0 :
            k, v = propEntryToks[0], propEntryToks[1]
        else :
            k, v = 'agent', propEntryToks[1] #, propEntryToks[2]
        if v.isdigit() :
            v = int(v)
        cacheTranInfoDict[k] = v
    return cacheTranInfoDict

def processTxnStartLine(line):
    toks = line.split(':')[2:]
    toksClean = [tok.lstrip().rstrip() for tok in toks]
    addr = '0x'+(toksClean[0].split(' ')[3]).lstrip().rstrip()
    op = (toksClean[0].split(' ')[4]).lstrip().rstrip()
    return (addr, op)

def processTxnEndLine(line):
    toks = line.split(':')[2:]
    toksClean = [tok.lstrip().rstrip() for tok in toks]
    addr = '0x'+(toksClean[0].split(' ')[4]).lstrip().rstrip()
    return addr

def readCHIDebugTrace(traceFd,dumpFd):
    ccuTransitionPattern=r"\[Cache_Controller [0-9]+\]"
    memoryTransitionPattern=r"\[Memory_Controller [0-9]+\]"
    txnStartPattern=r"system.cpu: Initiating at addr"
    txnEndPattern=r"system.cpu: Completing"
    actionExecPattern=r" executing "
    nextStatePattern=r" next_state"
    cacheMatcher=re.compile(ccuTransitionPattern)
    memoryMatcher=re.compile(memoryTransitionPattern)
    tranStartMatcher=re.compile(txnStartPattern)
    actionExecMatcher=re.compile(actionExecPattern)
    nextStateMatcher=re.compile(nextStatePattern)
    txnEndMatcher=re.compile(txnEndPattern)
    inFlightAddrMap = dict()
    currentAddrValid = False
    hdrSeq=['time', 'addr', 'evicting_addr', 'agent', 'state', 'event', 'next_state', 'action_list']
    print(','.join(hdrSeq),file=dumpFd)
    for line in traceFd :
        cacheMatch = cacheMatcher.search(line)
        memoryMatch = memoryMatcher.search(line)
        tranStartMatch = tranStartMatcher.search(line)
        actionMatch = actionExecMatcher.search(line)
        nextStateMatch = nextStateMatcher.search(line)
        txnEndMatch = txnEndMatcher.search(line)
        if tranStartMatch :
            currentAddr, op = processTxnStartLine(line)
            currentAddrValid = True
            inFlightAddrMap[currentAddr] = CacheLineTransition(currentAddr, op, None)
        elif txnEndMatch : 
            currentAddr = processTxnEndLine(line)
            print(','.join(['-' for _ in range(len(hdrSeq))]),file=dumpFd)
            del inFlightAddrMap[currentAddr]
            currentAddrValid = False
        elif cacheMatch or memoryMatch :
            cacheTranInfoDict = processCacheTranLine(line)
            inTranAddr = cacheTranInfoDict['addr']
            if currentAddrValid :
                if (inTranAddr != currentAddr) :
                    inFlightAddrMap[inTranAddr] = CacheLineTransition(inTranAddr, op, currentAddr)
            inFlightAddrMap[inTranAddr].addControllerTransition(cacheTranInfoDict)
        elif actionMatch :
            inFlightAddrMap[inTranAddr].addAction(line)
        elif nextStateMatch :
            inFlightAddrMap[inTranAddr].addNextState(line)
            inFlightAddrMap[inTranAddr].dump(hdrSeq,dumpFd)
            inFlightAddrMap[inTranAddr].clearActionList()
        

def main(dump_dir):
    traceFileName = f'{dump_dir}/debug.trace'
    outFileName   = f'{dump_dir}/AddrTxnLog.csv'
    with open(traceFileName,'r') as traceFd :
        with open(outFileName, 'w') as dumpFd :
            readCHIDebugTrace(traceFd,dumpFd)

if __name__=="__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--dump-dir', type=str, default=None, help=f'gem5 dump directory')
    args = parser.parse_args()
    main(args.dump_dir)