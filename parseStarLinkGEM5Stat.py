import re 
import os
import sys
from time import sleep
from tqdm import tqdm

WORKINGDIR = "/home/lester.leong/Desktop/04_gem5dump/LargeIter10000_"

allSetFront=[4,16,32,64,512,1024,1600,2048,2196,2362,2500,2800,3060,3400,3800,4192,5000,6000,7000, 8192,9000, 9500,\
        10000,10500,11000,12000,14000,16384,18000,20000,22000, 24576,29696, 32768, 35840,37000, 40000, 45000, 50100,55000, 60000, 62000,65536,68000,  70000, 72000,  75100,\
        78000, 80000,83000,85000,88000,90000,93000,95000,98000,100000, 110000, 120000,\
            131072,160100,190100,229376,262144,300100,400100,450000,500100,524287,524288,524289,600100, 670000,750100, 786432,850000, 917504,\
         996148, 1048576, 1101004 ,1572864, 1966080 ,2097152, 2228224 ,2400000, 2621440,3145728]

allSetBack = [13000000,16777216,20000000,25000000,33554432,40000000,45000000,50000000,67108864]

lower, upper = (4000000, 13000000)

# length = 50

# allWorkinSet=[lower + x*(upper-lower)/length for x in range(length)]

def containsWord(s, w):
    return f' {w} ' in f' {s} '

def getNumber(word):
    try:
        return int(re.findall(r'\b\d+\b',word)[0])
    except:
        return 0

def sumDictionary(dict):
    sum = 0
    for value in dict.values():
        sum+=value
    return sum

def constructDict(line, data):
    for phrase in data.keys():
        if containsWord(line,phrase):
            data[phrase] = getNumber(line)
            if containsWord(line, "simTicks"):
                data[phrase]/=1000
    return data

def main():
    length = 50
    allSetMiddle=[int(lower + x*(upper-lower)/length) for x in range(length)]
    allSet = allSetMiddle
    path=os.getcwd()
    logFile=f'{path}/CacheAccessStatMid.csv'
    hnfSet = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
    hnfPrefix = "system.ruby.hnf"
    hnfSuffix = [".cntrl.cache.m_demand_hits",".cntrl.cache.m_demand_misses",".cntrl.cache.m_demand_accesses"]
    l3Miss = {}
    l3Access = {}
    l3Hit = {}

    for value in hnfSet:
        for suffix in hnfSuffix:
            if suffix == hnfSuffix[0]:
                l3Hit[hnfPrefix+str(value)+suffix] = 0
            elif suffix == hnfSuffix[1]:
                l3Miss[hnfPrefix+str(value)+suffix] = 0
            elif suffix == hnfSuffix[2]:
                l3Access[hnfPrefix+str(value)+suffix] = 0

    data = {"simTicks":0,"NumElements":0,"system.cpu0.l1d.cache.m_demand_hits":0,"system.cpu0.l1d.cache.m_demand_misses":0,"system.cpu0.l1d.cache.m_demand_accesses":0,\
        "system.cpu0.l1i.cache.m_demand_hits":0,"system.cpu0.l1i.cache.m_demand_misses":0,"system.cpu0.l1i.cache.m_demand_accesses":0,\
   "system.cpu0.l2.cache.m_demand_hits":0,"system.cpu0.l2.cache.m_demand_misses":0,"system.cpu0.l2.cache.m_demand_accesses":0 }

    print("\nstart parse...\n")
    with open(logFile,'w') as lf:
        print(f"simTicks,NumElements,L1DCacheHits,L1DCacheMisses,L1DCacheAccesses,L1ICacheHits,L1ICacheMisses,L1ICacheAccesses,L2CacheHits,L2CacheMisses,L2CacheAccesses,L3CacheHits,L3CacheMisses,L3CacheAccesses",file = lf)
        for value in tqdm(allSet):
            try:
                with open(WORKINGDIR+str(value)+"/stats.txt") as f:
                    #find L1 and L2 cache numbers first
                    lines = f.readlines()
                    for line in lines:
                        if containsWord(line,"End Simulation Statistics"):
                            break
                        data = constructDict(line, data)
                        l3Hit = constructDict(line, l3Hit)
                        l3Miss = constructDict(line, l3Miss)
                        l3Access = constructDict(line, l3Access)

                    data["NumElements"] = value
                    #get L3 numbers
                    data["l3HitVal"] = sumDictionary(l3Hit)
                    data["l3MissVal"] = sumDictionary(l3Miss)
                    data["l3CacheVal"] = sumDictionary(l3Access)
                    combined = ','.join(map(str,data.values()))
                    print(combined,file = lf)
            except:
                print(f"\nworking set {value} not available!\n")
                print("stopping program execution... \n")
                f.close()
                return

    f.close()
    print("parse done!")


if __name__=="__main__":
    main()
