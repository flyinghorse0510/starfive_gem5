import re 
import os
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

def getStats(statsFileName,dstCPU):
    statMatcherList= [
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
    outdir_root='/home/arka.maity/Desktop/gem5_starlink2.0_memtest/output/GEM5_PDCP/C2C_3_simple'
    getPingPong(outdir_root)

if __name__=="__main__":
    main()
