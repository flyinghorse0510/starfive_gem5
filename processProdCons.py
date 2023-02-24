import os
import json
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output',required=True, type=str)
    options = parser.parse_args()
    df=pd.read_json(options.input)
    df.to_csv(options.output,index=False)
    # print(df)

if __name__=="__main__":
    main()