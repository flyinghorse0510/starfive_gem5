import os
import re
import argparse

ACTIVE_MSG_PAT=re.compile(r'0x0003')
def parseLines(args):
    tickPerCyc=500
    msgDict=dict()
    msgBufferEnqPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), type: ([a-zA-Z_]+), isArrival: 1, addr: (\S+), reqtor: (\S+), bufferSize: (\d+)')
    msgBufferDeqPat=re.compile(r'^(\s*\d*): (\S+): txsn: (\w+), type: ([a-zA-Z_]+), isArrival: 0, addr: (\S+), reqtor: (\S+), bufferSize: (\d+)')
    with open(args.outfile,'w') as outFile:
        print(f'Agent,CycleEnq,CycleDeq,Txsn,BufferSize,Addr,Opcode',file=outFile)
        with open(args.trace_file,'r') as trcFile:
            for line in trcFile:
                msgBufferEnqMatch=msgBufferEnqPat.search(line)
                msgBufferDeqMatch=msgBufferDeqPat.search(line)
                if msgBufferEnqMatch:
                    assert(msgBufferDeqMatch == None)
                    agent=msgBufferEnqMatch.group(2)
                    cyc=int(msgBufferEnqMatch.group(1))/tickPerCyc
                    txsn=msgBufferEnqMatch.group(3)
                    typ=msgBufferEnqMatch.group(4)
                    addr=msgBufferEnqMatch.group(5)
                    bufferSize=msgBufferEnqMatch.group(7)
                    msgDict[agent] = {
                        'agent': agent,
                        'txsn': txsn,
                        'CycleEnq': cyc,
                        'CycleDeq': -1,
                        'BufferSize': bufferSize,
                        'Addr': addr,
                        'Opcode': typ
                    }
                elif msgBufferDeqMatch:
                    assert(msgBufferEnqMatch == None)
                    agent=msgBufferDeqMatch.group(2)
                    cyc=int(msgBufferDeqMatch.group(1))/tickPerCyc
                    txsn=msgBufferDeqMatch.group(3)
                    typ=msgBufferDeqMatch.group(4)
                    addr=msgBufferDeqMatch.group(5)
                    bufferSize=msgBufferDeqMatch.group(7)
                    assert(agent in msgDict)
                    msgDict[agent]['CycleDeq']=cyc
                    
                    # Dump the agent values
                    v=msgDict[agent]
                    agent=v['agent']
                    cycEnq=v['CycleEnq']
                    cycDeq=v['CycleDeq']
                    txsn=v['txsn']
                    bufferSize=v['BufferSize']
                    addr=v['Addr']
                    typ=v['Opcode']
                    print(f'{agent},{cycEnq},{cycDeq},{txsn},{bufferSize},{addr},{typ}',file=outFile)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--working-set',required=True,type=str,help='Working set')
    parser.add_argument('--num_cpus',required=True,type=str,help='Number of CPUs')
    parser.add_argument('--trace_file',required=True,type=str,help='Trace file')
    parser.add_argument('--outfile',required=True,type=str,help='MsgBuffer Status file')
    parser.add_argument('--nw_model',required=True,type=str,help='NW model')
    parser.add_argument('--num_mem',required=True,type=str,help='Number of MCs')
    parser.add_argument('--seq_tbe',required=True,type=str,help='Number of sequencer TBEs')
    parser.add_argument('--test',required = False, default=False, action="store_true",help="enable test mode")
    parser.add_argument('--parse-l2', default=False, action="store_true",help="parsing mode, only L2 cache or all transactions")
    args = parser.parse_args()
    parseLines(args)
 
if __name__=="__main__":
    main()