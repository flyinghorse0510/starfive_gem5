import re 
import os
import pprint as pp
from tqdm import tqdm

USER = "arka.maity"
WORKINGDIR = f"/home/{USER}/Desktop/04_gem5dump/FixedStrideINTELConfig_"

allSet=[64, 128, 256, 512, 640, 704, 1024, 1280, 1408, 1536, 1600, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216]
lower, upper = (4000000, 13000000)

def containsWord(s, w):
    return f' {w} ' in f' {s} '

def getStat(word):
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
            data[phrase] = getStat(line)
    return data

def getCacheAccLat():
    length = 50
    path=os.getcwd()
    logFile=f'{path}/CacheAccessStatFixedStride.csv'
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

    data = {
                "simTicks":0,
                "WorkingSet":0,
                "system.cpu0.numCycles":0,
                "system.cpu0.l1d.cache.m_demand_misses":0,
                "system.cpu0.l1d.cache.m_demand_accesses":0,
                "system.cpu0.l2.cache.m_demand_misses":0,
                "system.cpu0.l2.cache.m_demand_accesses":0 
            }

    print(f"\nstart parse for {len(allSet)} experiments...\n")
    with open(logFile,'w') as lf:
        print(f"simTicks,WorkingSet,NumCycles,L1DCacheMisses,L1DCacheAccesses,L2CacheMisses,L2CacheAccesses,L3CacheMisses,L3CacheAccesses",file = lf)
        for value in tqdm(allSet):
            try:
                with open(WORKINGDIR+str(value)+"/stats.txt") as f:
                    #find L1 and L2 cache numbers first
                    lines = f.readlines()
                    for line in lines:
                        #terminate at first dump
                        if containsWord(line,"End Simulation Statistics"):
                            break
                        data = constructDict(line, data)
                        l3Hit = constructDict(line, l3Hit)
                        l3Miss = constructDict(line, l3Miss)
                        l3Access = constructDict(line, l3Access)

                    data["WorkingSet"] = (value*64)/1024 # Each element is cache line size aligned
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
    print("\nparse done!")


def main():
    flName=f'/home/arka.maity/Desktop/04_gem5dump/STREAM_1024/stats.txt'
    inst_count_pat=re.compile(r'system\.cpu0+\.commit\.instsCommitted')
    with open(flName) as statFD :
        data=statFD.read()
        matches=re.findall(inst_count_pat,data)
        pp.pprint(matches)

if __name__=="__main__":
    main()
