import re 
import os

def getTime(line):
    if len(line) > 0 :
        return int(line.split(':')[0])
    else :
        return 0

def getTxnId(line):
    if len(line) > 0 :
        return line.split(':')[3]
    else :
        return 0

def main():
    dctFile=open(f'/home/arka.maity/Desktop/gem5_starlink2.0_memtest/output/GEM5_PDCP/C2C_9_simple/PRODCONS_BW/WS1024_Core_Prod1_Cons1_L132KiB_L2256KiB_L31024KiB_DCTTrue/debug.ReqAnalyses.trace','r')
    nDctFile=open(f'/home/arka.maity/Desktop/gem5_starlink2.0_memtest/output/GEM5_PDCP/C2C_9_simple/PRODCONS_BW/WS1024_Core_Prod1_Cons1_L132KiB_L2256KiB_L31024KiB_DCTFalse/debug.ReqAnalyses.trace','r')
    dctFileLines=dctFile.readlines()
    nDctFileLines=nDctFile.readlines()
    for idx,line in enumerate(nDctFileLines):
        nDctTime=getTime(line)
        dctTime=getTime(dctFileLines[idx])
        if (dctTime > nDctTime):
            cycDiff=((dctTime-nDctTime)/500)
            txId=getTxnId(line)
            print(f'{txId} injected after {cycDiff}')
            break
        elif (dctTime < nDctTime):
            print(idx)

if __name__=="__main__":
    main()
    