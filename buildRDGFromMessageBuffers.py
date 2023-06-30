import re
import os
import sys
import json
import argparse
import pprint as pp
import networkx as nx
import netparse as ntp
from typing import Dict,List
from dataclasses import dataclass
import matplotlib.pyplot as plt

def convertId(id):
    if id in range(32, 48):
        return f'rnf_{(id-32):02d}'
    elif id in range(48, 64):
        return f'hnf_{(id-48):02d}'
    elif id in range(64,96):
        return f'snf_{(id-64):02d}'
    else:
        print(f'{id} not found')
        
@dataclass
class CHIStuckMessage:
    addr: str
    opCode: str
    allowRetry: str
    srcId: str
    dstId: str
    incomingPort: int
    outgoingPort: int

    @classmethod
    def nullMessage(cls):
        return cls(
            addr='0x0',
            opCode='null',
            allowRetry='0',
            srcId='null',
            dstId='null',
            incomingPort=-1,
            outgoingPort=-1
        )

    def __eq__(self, other):
        return (self.addr == other.addr) and \
               (self.opCode == other.opCode) and \
               (self.allowRetry == other.allowRetry) and \
               (self.srcId == other.srcId) and \
               (self.dstId == other.dstId)

    def getCsvEntry(self):
        return f'{self.addr}|{self.opCode}|{self.srcId}-->{self.dstId}|{self.allowRetry}|{self.incomingPort}-->{self.outgoingPort}'

def parseSwitchMessages(trcFile):
    """
        Get the Messages blocked at
        the router input port
    """
    routerIncomingPat = re.compile(r'393302000: PerfectSwitch-(\d+): VNET_0 Incoming_(\d+) Outgoing_(\d+) Msg_\[addr: ([0-9a-fx]+)\|([\w]+)\|Cache-(\d+)-->(\d+),\|([0-1])\] blocked')
    messageBufferPat = re.compile(r'393302000: (\S+): MessageBufferContents: \[addr: ([0-9a-fx]+)\|([\w]+)\|Cache-(\d+)-->(\d+),\|([0-1])\]')
    portBufferpat = re.compile(r'system.ruby.network.int_links(\d+).(src|dst)_node.port_buffers(\d+)')
    allocReqPat = re.compile(r'393302000: (\S+): addr: ([0-9a-fx]+), Resource Stall \(is:([\w]+),e:AllocRequestChecked,fs:([\w]+)\)')
    cntrlNodes = set()
    tickPerCyc = 500
    routerIncomingMsgDict=dict()
    portBufferDict = dict()
    linkBufferDict = dict()
    with open(trcFile,'r+') as f:
        for line in f :
            routerIncomingMatch = routerIncomingPat.search(line)
            messageBufferMatch = messageBufferPat.search(line)
            allocReqMatch = allocReqPat.search(line)
            if routerIncomingMatch :
                routerId = int(routerIncomingMatch.group(1))
                incomingPort = int(routerIncomingMatch.group(2))
                outgoingPort = int(routerIncomingMatch.group(3))
                addr = routerIncomingMatch.group(4)
                opCode = routerIncomingMatch.group(5)
                srcId = convertId(int(routerIncomingMatch.group(6)))
                dstId = convertId(int(routerIncomingMatch.group(7)))
                allowRetry = int(routerIncomingMatch.group(8))
                routerIncomingMsgDict[(routerId,incomingPort)] = CHIStuckMessage(
                    addr=addr,
                    incomingPort=incomingPort,
                    outgoingPort=outgoingPort,
                    opCode=opCode,
                    srcId=srcId,
                    dstId=dstId,
                    allowRetry=allowRetry
                )
            elif messageBufferMatch :
                bufferStr = messageBufferMatch.group(1)
                portBufferMatch = portBufferpat.search(bufferStr)
                addr = messageBufferMatch.group(2)
                opCode = messageBufferMatch.group(3)
                srcId = convertId(int(messageBufferMatch.group(4)))
                dstId = convertId(int(messageBufferMatch.group(5)))
                allowRetry = int(messageBufferMatch.group(6))
                if portBufferMatch :
                    portBufferDict[bufferStr] = CHIStuckMessage(
                        addr=addr,
                        incomingPort=-1,
                        outgoingPort=-1,
                        opCode=opCode,
                        srcId=srcId,
                        dstId=dstId,
                        allowRetry=allowRetry
                    )
                else :
                    linkBufferDict[bufferStr] = CHIStuckMessage(
                        addr=addr,
                        incomingPort=-1,
                        outgoingPort=-1,
                        opCode=opCode,
                        srcId=srcId,
                        dstId=dstId,
                        allowRetry=allowRetry
                    )
            elif allocReqMatch :
                agent = allocReqMatch.group(1)
                addr = allocReqMatch.group(2)
                cntrlNodes.add(agent)

    return (routerIncomingMsgDict, portBufferDict, linkBufferDict, cntrlNodes)

def getLinkIdFromRouterPortId(routers, switchPortMapFile):
    """
        Obtain the IntLinkId (or ExtLinkId) from the Router and port Id
        Returns in the following format:
            {
                (routerId, portId) : IntLink/ExtLink
            }
    """
    switchInportLinkMapPat = re.compile(r'Switch_PerfectSwitch-(\d+) Inport_(\d+): Link (\S+)')
    switchOutportLinkMapPat = re.compile(r'Switch_(\S+) OutPortBuffer (\S+) Link (\S+)')
    with open(switchPortMapFile,'r') as sfw:
        routerInportLinkMap = dict()
        routerOutportLinkMap = dict()
        for line in sfw:
            switchInportLinkMapMatch = switchInportLinkMapPat.search(line)
            switchOutportLinkMapMatch = switchOutportLinkMapPat.search(line)
            if switchInportLinkMapMatch :
                routerId = int(switchInportLinkMapMatch.group(1))
                portId = int(switchInportLinkMapMatch.group(2))
                linkPath = switchInportLinkMapMatch.group(3)
                routerInportLinkMap[(routerId,portId)] = linkPath
            if switchOutportLinkMapMatch :
                router_path_str = switchOutportLinkMapMatch.group(1)
                routerId = ntp.get_node(routers,router_path_str).id
                portBufferPath = switchOutportLinkMapMatch.group(2)
                linkPath = switchOutportLinkMapMatch.group(3)
                routerOutportLinkMap[(routerId,portBufferPath)] = linkPath
    return (routerInportLinkMap, routerOutportLinkMap)

def getOutgoingPortBufferPath(routers, routerId, outportId):
    num_vnets = 4
    routerPath = routers[routerId].path
    return f'{routerPath}.port_buffers{(num_vnets*outportId):02d}'

def constructResourceDepGraph(ext_links, int_links, routers, trcFile, switchPortMapFile, dumpFile, dumpGraphFile, draw = False):
    """
        Construct the dependency graph
        for the blocked messages
    """
    G = nx.DiGraph()
    routerInportLinkMap, routerOutportLinkMap = getLinkIdFromRouterPortId(routers, switchPortMapFile)
    routerIncomingMsgDict, portBufferDict, linkBufferDict, cntrlNodes = parseSwitchMessages(trcFile)
    addedLink = set()
    linkPathMap = dict()
    for ext_link in ext_links:
        linkPathMap[ext_link.path] = ext_link
    for int_link in int_links:
        linkPathMap[int_link.path] = int_link

    for (routerId, inPortId), msg in routerIncomingMsgDict.items():
        outgoingPort = msg.outgoingPort
        assert(outgoingPort >= 0)
        outPortBufferPath = getOutgoingPortBufferPath(routers, routerId, outgoingPort)
        incomingLink = routerInportLinkMap[(routerId,inPortId)]
        outgoingLink = routerOutportLinkMap[(routerId,outPortBufferPath)]
        incomingLinkAlias = ntp.Link.getLinkAliasFromPath(incomingLink)
        outgoingLinkAlias = ntp.Link.getLinkAliasFromPath(outgoingLink)
        
        # Incoming link node
        if not incomingLinkAlias in addedLink :
            G.add_node(incomingLinkAlias,
                msg = msg,
                nodeTy = 'link')
            addedLink.add(incomingLinkAlias)

        # Router_Inport node (has the same msg as the previous one)
        G.add_node(f'R{routerId}.I{inPortId}',
                msg = msg,
                nodeTy = 'router')

        G.add_edge(incomingLinkAlias,f'R{routerId}.I{inPortId}')

        # Router_OutportBuffer node
        outgoingPortBufferMsg = portBufferDict[outPortBufferPath]
        G.add_node(f'R{routerId}.O{outgoingPort}',
                msg = outgoingPortBufferMsg,
                nodeTy = 'router')

        G.add_edge(f'R{routerId}.I{inPortId}', f'R{routerId}.O{outgoingPort}')

        # Outgoing link node
        if not outgoingLinkAlias in addedLink :
            outgoingMsg = linkBufferDict[outgoingLink]
            G.add_node(outgoingLinkAlias,
                msg = outgoingMsg,
                nodeTy = 'link')
            addedLink.add(outgoingLinkAlias)

        G.add_edge(f'R{routerId}.O{outgoingPort}', outgoingLinkAlias)

    for cntrlNode in cntrlNodes :
        incomingLink = f'{cntrlNode}.reqIn'
        outgoingLink = f'{cntrlNode}.reqOut'
        incomingMsg = linkBufferDict[incomingLink]
        outgoingMsg = linkBufferDict[outgoingLink]
        incomingLinkAlias = ntp.Link.getLinkAliasFromPath(incomingLink)
        outgoingLinkAlias = ntp.Link.getLinkAliasFromPath(outgoingLink)

        if not incomingLinkAlias in addedLink :
            G.add_node(incomingLinkAlias,
                msg = incomingMsg,
                node_for_adding = 'link')
            addedLink.add(incomingLinkAlias)
    
        if not outgoingLinkAlias in addedLink :
            G.add_node(outgoingLinkAlias,
                msg = outgoingMsg,
                node_for_adding = 'link')
            addedLink.add(outgoingLinkAlias)
        
        G.add_node(cntrlNode,
            msg = CHIStuckMessage.nullMessage(),
            nodeTy = 'cntrl')
        
        G.add_edge(incomingLinkAlias,cntrlNode)
        G.add_edge(cntrlNode, outgoingLinkAlias)

    cycles = sorted(nx.simple_cycles(G))
    G2 = None
    with open(dumpFile,'w') as fw:
        print(f'Agent,Message',file=fw)
        if len(cycles) > 0 :
            cycNodes = cycles[0]
            G2 = G.subgraph(cycNodes).copy()

            nodeTyRouters = []
            nodeTyLinks = []
            nodeTyCntrls = []

            for u in cycNodes :
                data = G2.nodes[u]
                blockedMsg = data['msg']
                if data['nodeTy'] == 'router' :
                    nodeTyRouters.append(u)
                elif data['nodeTy'] == 'link' :
                    nodeTyLinks.append(u)
                elif data['nodeTy'] == 'cntrl' :
                    nodeTyCntrls.append(u)
                print(f'{u},{blockedMsg.getCsvEntry()}',file=fw)
    if draw :
        pos = nx.planar_layout(cycNodes)
        plt.figure(figsize=(12,12))
        nx.draw_networkx_nodes(G2,pos=pos,nodelist=nodeTyRouters,node_color='r')
        nx.draw_networkx_nodes(G2,pos=pos,nodelist=nodeTyLinks,node_color='b')
        nx.draw_networkx_nodes(G2,pos=pos,nodelist=nodeTyCntrls,node_color='g')
        nx.draw_networkx_edges(G2, pos, edge_color='k', arrows=True)
        nx.draw_networkx_labels(G2,pos)
        plt.savefig(dumpGraphFile,dpi = 800)
    return G2
    

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--input-sw-port',required=True, type=str)
    options = parser.parse_args()
    trcFile=os.path.join(options.input,'debug.trace')
    jsonFile=os.path.join(options.input,'config.json')
    dumpFile=os.path.join(options.input,'blocked.csv')
    dumpGraphFile=os.path.join(options.input,'blocked.png')

    ext_links, int_links, routers = None, None, None
    with open(jsonFile,'r') as f:
        JSON = json.load(f)
        ext_links, int_links, routers, cyc_tick = ntp.parse_json(JSON)

    
    G = constructResourceDepGraph(ext_links, int_links, routers, trcFile, options.input_sw_port, dumpFile, dumpGraphFile, True)

if __name__=="__main__":
    main()