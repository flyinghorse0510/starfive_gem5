import re
import argparse

class AddrTxnFlow(object):
    # Suppress tracking dumps for instruction addresses
    # We assume instruction address and data address do 
    # not overlap
    instAddressMap=set()
    
    def __init__(self, cacheTranInfoDict):
        self.addr = cacheTranInfoDict['addr']
        self.flowEvents = []
        self.txnEvents = []
        self.suppressPrinting = False
        if cacheTranInfoDict['agent'].endswith('l1i') :
            self.suppressPrinting = True
            AddrTxnFlow.instAddressMap.add(self.addr)
        elif self.addr in AddrTxnFlow.instAddressMap :
            self.suppressPrinting = True
        self.addFlowEvent(cacheTranInfoDict)
    
    def addFlowEvent(self,cacheTranInfoDict):
        assert self.addr == cacheTranInfoDict['addr'], "Address mismatch"
        self.flowEvents.append({
            'time': cacheTranInfoDict['Time'],
            'agent' : cacheTranInfoDict['agent'],
            'state': cacheTranInfoDict['state'],
            'event': cacheTranInfoDict['event'],
        })
        
    
    def addAditionalFlowEvent(self,additionalTranInfoLines):
        for line in additionalTranInfoLines :
            lineSuffix = line.split(':')[2:]            
            propEntryToks =  [__t.lstrip().rstrip() for __t in lineSuffix]
            if propEntryToks[0].startswith('next_state'):
                self.flowEvents[-1]['next_state'] = propEntryToks[1]
                    
    
    def dump(self,hdrSeq,dumpFd):
        if not self.suppressPrinting :
            for flowEvt in self.flowEvents:
                printStr=f''
                for i,k in enumerate(hdrSeq) :
                    if k == 'addr' :
                        printStr+=f'{self.addr},'
                    else :
                        val=flowEvt.get(k,'NA')
                        if i == len(hdrSeq)-1 :
                            printStr+=f'{val}'
                        else :
                            printStr+=f'{val},'
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

def readCHIDebugTrace(traceFd,dumpFd):
    cacheControllerTranPatter=r"\[Cache_Controller [0-9]+\]"
    memoryControllerTranPatter=r"\[Memory_Controller [0-9]+\]"
    cacheMatcher=re.compile(cacheControllerTranPatter)
    memoryMatcher=re.compile(memoryControllerTranPatter)
    additionalTranInfoLines = []
    currentAddrTxnFlow = None
    hdrSeq=['time', 'addr', 'agent', 'state', 'event', 'next_state']
    print(','.join(hdrSeq),file=dumpFd)
    for line in traceFd :
        cacheMatch = cacheMatcher.search(line)
        memoryMatch = memoryMatcher.search(line)
        if cacheMatch or memoryMatch :
            if currentAddrTxnFlow is not None:
                currentAddrTxnFlow.addAditionalFlowEvent(additionalTranInfoLines)
                currentAddrTxnFlow.dump(hdrSeq,dumpFd)
            cleanLine = line.strip()
            cacheTranInfoDict = processCacheTranLine(cleanLine)
            currentAddrTxnFlow = AddrTxnFlow(cacheTranInfoDict)
            additionalTranInfoLines.clear()
        else :
            cleanLine = line.strip()
            additionalTranInfoLines.append(cleanLine)

def main(dump_dir):
    traceFileName = f'{dump_dir}/debug.trace'
    outFileName   = f'{dump_dir}/AddrTxnLog.txt'
    with open(traceFileName,'r') as traceFd :
        with open(outFileName, 'w') as dumpFd :
            readCHIDebugTrace(traceFd,dumpFd)

if __name__=="__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--dump-dir', type=str, default=None, help=f'gem5 dump directory')
    args = parser.parse_args()
    main(args.dump_dir)