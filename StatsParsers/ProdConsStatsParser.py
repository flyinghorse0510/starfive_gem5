import re 
import os
import numpy as np
import pprint as pp
from tqdm import tqdm
from dataclasses import dataclass
import itertools as it

@dataclass
class Gem5SysConfigInfo:
    producers: int
    consumers: int
    working_set: int
    bwOrC2C: bool
    outdir_root: str
    outdir_prefix: str
    enable_dct: bool
    num_cpus_total: int = 16
    l1i_size: str = '32KiB'
    l1d_size: str = '32KiB'
    l2_size: str = '256KiB'
    hnf_size: str = '1024KiB'
    num_cpus: int = 16

    def __init__(self,outdir_root,enable_dct,working_set,producers,consumers,bwOrC2C):
        self.outdir_root = outdir_root
        self.working_set = working_set
        self.producers = producers
        self.consumers = consumers
        self.bwOrC2C = bwOrC2C
        self.enable_dct = enable_dct
        self.outdir_prefix='PRODCONS_PINGPONG'
        if bwOrC2C:
            self.outdir_prefix='PRODCONS_BW'
            
    def get_num_cpus(self):
        return self.num_cpus_total
    
    def __repr__(self):
        WKSET=self.working_set
        NUMCPUS=self.num_cpus_total
        PRODUCER_SET=self.producers
        CONSUMER_SET=self.consumers
        l1i_size=self.l1i_size
        l1d_size=self.l1d_size
        l2_size=self.l2_size
        l3_size=self.hnf_size
        DCT=self.enable_dct
        baseName=f'WS{WKSET}_Core_Prod{PRODUCER_SET}_Cons{CONSUMER_SET}_L1{l1d_size}_L2{l2_size}_L3{l3_size}_DCT{DCT}'
        return os.path.join(self.outdir_root,self.outdir_prefix,baseName)

@dataclass
class MemoryOp:
    addr: int
    data: int
    readOrWrite: bool
    prodOrCons: bool
    startOrEnd: bool

    def __init__(self,trcLine):
        trcCleanLines=[l.strip() for l in trcLine.split(',')]
        self.startOrEnd=True if trcCleanLines[0]=='Start' else False
        self.readOrWrite=True if trcCleanLines[1]=='R' else False
        self.addr=int(trcCleanLines[2],base=16)
        self.data=int(trcCleanLines[3],base=16)
        self.prodOrCons=not self.readOrWrite # This is not true in general. Only for Producer-Consumer test cases

    def getAddr(self):
        return self.addr
    
    def isTxnConcluded(self):
        """
            Txn is concluded
            whenever a read to 
            the read has completed
            by the consumer
        """
        return (self.readOrWrite and (not self.startOrEnd))
    
    def isTxnStarted(self):
        """
            When is readTxn started
        """
        return (self.readOrWrite and self.startOrEnd)


def getTickInterval(statsFileName):
    """
        Returns the tickInterval in seconds
    """
    statMatcherList=[
        re.compile(r'simTicks'),
        re.compile(r'simFreq')]

    with open(statsFileName,'r') as statFileD:
        statLines=statFileD.readlines()
        statsDict=dict()
        for line in statLines:
            for statMatcher in statMatcherList:
                statMatch=statMatcher.search(line)
                if statMatch:
                    metric=line.split()[0]
                    statsDict[metric]=int(line.split()[1])

    return (1/statsDict['simFreq'])

def getStatsFromTrace(trcFileName,srcCPU,dstCPU,tickInterval):
    print(f'Tick Interval {tickInterval}')
    trcMatcherList=[
        re.compile(r'Complete'),
        re.compile(r'Start')
    ]
    trcStatsDict=dict()
    addrCounterDict=dict()
    with open(trcFileName,'r') as trcFileD:
        trcLines=trcFileD.readlines()
        for line in trcLines:
            for trcMatcher in trcMatcherList:
                trcMatch=trcMatcher.search(line)
                if trcMatch:
                    lineComp=[l.strip() for l in line.split(':')]
                    memOp=MemoryOp(lineComp[2])
                    if memOp.isTxnStarted():
                        if memOp.getAddr() in addrCounterDict:
                            addrCounterDict[memOp.getAddr()] += 1
                            pcTxnId = addrCounterDict[memOp.getAddr()]
                        else :
                            pcTxnId = 0
                            addrCounterDict[memOp.getAddr()]=pcTxnId
                        pcTxnIdPair=(memOp.getAddr(),pcTxnId)
                        assert (pcTxnIdPair not in trcStatsDict), f'{pcTxnIdPair} stats collection unfinished'
                        trcStatsDict[pcTxnIdPair] = {
                            'start': int(lineComp[0])
                        }
                    elif memOp.isTxnConcluded():
                        memAddr = memOp.getAddr()
                        assert (memAddr in addrCounterDict), f'{memAddr} stats collection has not been initiated'
                        pcTxnId = addrCounterDict[memAddr]
                        pcTxnIdPair = (memAddr,pcTxnId)
                        assert ('start' in trcStatsDict[pcTxnIdPair]), f'{pcTxnIdPair} has not started {int(lineComp[0])}\n{memOp}\n{trcStatsDict}'
                        trcStatsDict[pcTxnIdPair]['end']=int(lineComp[0])
                        trcStatsDict[pcTxnIdPair]['lat']=1e9*tickInterval*(trcStatsDict[pcTxnIdPair]['end']-trcStatsDict[pcTxnIdPair]['start'])
    allLatencies=[]
    for k,v in trcStatsDict.items():
        addr,txnId=k
        allLatencies.append(v['lat'])
    minLat=np.array(allLatencies).min()
    medianLat=np.median(allLatencies)
    maxLat=np.array(allLatencies).max()
    print(f'Min={minLat},Median={medianLat},Max={maxLat}')
    return medianLat

def getStatsFromTraceTest(outdir_root):
    dctConfigList=[False]
    workinSetList=[65536]
    allProducerList=[0] #list(range(16))
    allConsumerList=[2] #list(range(16))
    bwOrC2C=False
    allConfigList=it.product(dctConfigList,workinSetList,allProducerList,allConsumerList)
    tickInterval=-1
    for dct,ws,prod,cons in tqdm(allConfigList):
        tc=Gem5SysConfigInfo(outdir_root,dct,ws,prod,cons,bwOrC2C)
        trcFile=tc.__repr__()+'/debug.trace'
        statsFile=tc.__repr__()+'/stats.txt'
        if tickInterval <= 0:
            tickInterval=getTickInterval(statsFile)
        if os.path.isfile(trcFile):
            getStatsFromTrace(trcFile,prod,cons,tickInterval)

def getStats(statsFileName,dstCPU):
    statMatcherList=[
        re.compile(r'simTicks'),
        re.compile(r'system\.cpu'+str(dstCPU)+r'\.numReads'),
        re.compile(r'simFreq')]
    statsDict={}
    with open(statsFileName,'r') as statFileD:
        statLines=statFileD.readlines()
        for line in statLines:
            for statMatcher in statMatcherList:
                statMatch=statMatcher.search(line)
                if statMatch:
                    # statList=statMatch.group().strip(' ')
                    metric=line.split()[0]
                    if metric.endswith('numReads') :
                        statsDict['numReads']=int(line.split()[1])
                    else :
                        statsDict[metric]=int(line.split()[1])
    newStatsDict={}
    newStatsDict['Latency']=(statsDict['simTicks']/statsDict['simFreq'])
    newStatsDict['numReads']=statsDict['numReads']
    perUnitLatency=1e9*(newStatsDict['Latency']/statsDict['numReads'])
    print(f'Latency={perUnitLatency}')
    return newStatsDict

def getPingPong(outdir_root):
    dctConfigList=[True,False]
    workinSetList=[1024, 65536]
    allProducerList=list(range(16))
    allConsumerList=list(range(16))
    bwOrC2C=False
    allConfigList=it.product(dctConfigList,workinSetList,allProducerList,allConsumerList)
    for dct,ws,prod,cons in tqdm(allConfigList):
        tc=Gem5SysConfigInfo(outdir_root,dct,ws,prod,cons,bwOrC2C)
        statsFile=tc.__repr__()+'/stats.txt'
        if os.path.isfile(statsFile):
            statsDict=getStats(statsFile,cons)
        
def main():
    outdir_root='/home/arka.maity/Desktop/gem5_starlink2.0_memtest/output/GEM5_PDCP/C2C_5_garnet'
    # getPingPong(outdir_root)
    getStatsFromTraceTest(outdir_root)

if __name__=="__main__":
    main()
