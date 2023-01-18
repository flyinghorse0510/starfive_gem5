import re
import argparse

def processHNFAccessTrace(traceLine):
    toks = traceLine.split(':')
    cleanToks = [t.lstrip(' ').rstrip(' ') for t in toks]
    timeStamp = int(cleanToks[0])
    hnfAgent = cleanToks[1]
    accessParams = cleanToks[-1].split('=')
    cleanAccessParams = [a.lstrip(' ').rstrip(' ') for a in accessParams]