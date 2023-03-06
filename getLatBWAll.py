import os
import json
import argparse
import pandas as pd

def punchTestName(row) :
    if row['BENCH'] == 'L1L2Hit' :
        if row['WS'] <= 2048 :
            if row['SEQTBE'] == 1 :
                return 'L1HitLat'
            else :
                return 'L1HitBW'
        elif row['WS'] <= 8192 :
            if row['SEQTBE'] == 1 :
                return 'L2HitLat'
            else :
                return 'L2HitBW'
    elif row['BENCH'] == 'DDR' :
        return 'DDRBW'
    elif row['BENCH'] == 'L3Hit' :
        return 'L3HitBW'
    return 'INV'


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output',required=True, type=str)
    options = parser.parse_args()
    df=pd.read_json(options.input)
    df['Test'] = df.apply(lambda row : punchTestName(row),axis=1)
    df.drop(labels='BENCH',inplace=True,axis=1)
    df.to_csv(options.output,index=False)

if __name__=="__main__":
    main()