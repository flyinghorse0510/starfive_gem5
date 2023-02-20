import re
import numpy as np
import matplotlib.pyplot as plt
import json
import networkx as nx
import os
import argparse
from typing import Dict,List
import logging
import pandas as pd
from collections import namedtuple

logging.basicConfig(level=logging.INFO)

CHIMsgType = namedtuple('CHIMsgType', ['abbr','type'])

'''
MessageBuffer * reqOut,   network="To", virtual_network="0", vnet_type="none";
MessageBuffer * snpOut,   network="To", virtual_network="1", vnet_type="none";
MessageBuffer * rspOut,   network="To", virtual_network="2", vnet_type="none";
MessageBuffer * datOut,   network="To", virtual_network="3", vnet_type="response";
'''
CHIMsgType_dict = {
    # ReqMsg
    'Load':CHIMsgType('LD', 0),
    'Store':CHIMsgType('ST', 0),
    'StoreLine':CHIMsgType('STLine', 0),
    # Incoming DVM-related requests generated by the sequencer
    'DvmTlbi_Initiate':CHIMsgType('DvmTlbiInit', 0),
    'DvmSync_Initiate':CHIMsgType('DvmSyncInit', 0),
    'DvmSync_ExternCompleted':CHIMsgType('DvmSyncExtCmp', 0),
    'ReadShared':CHIMsgType('ReadS', 0),
    'ReadNotSharedDirty':CHIMsgType('ReadNSD',0),
    'ReadUnique':CHIMsgType('ReadU',0),
    'ReadOnce':CHIMsgType('ReadO',0),
    'CleanUnique':CHIMsgType('CleanU',0),
    'Evict':CHIMsgType('Evict',0),
    'WriteBackFull':CHIMsgType('WBFull',0),
    'WriteCleanFull':CHIMsgType('WCFull',0),
    'WriteEvictFull':CHIMsgType('WEFull',0),
    'WriteUniquePtl':CHIMsgType('WUPtl',0),
    'WriteUniqueFull':CHIMsgType('WUFull',0),
    # Snps
    'SnpSharedFwd':CHIMsgType('SnpSFwd',1),
    'SnpNotSharedDirtyFwd':CHIMsgType('SnpNSDFwd',1),
    'SnpUniqueFwd':CHIMsgType('SnpUFwd',1),
    'SnpOnceFwd':CHIMsgType('SnpOFwd',1),
    'SnpOnce':CHIMsgType('SnpOnce',1),
    'SnpShared':CHIMsgType('SnpS',1),
    'SnpUnique':CHIMsgType('SnpU',1),
    'SnpCleanInvalid':CHIMsgType('SnpCI',1),
    'SnpDvmOpSync_P1':CHIMsgType('SnpDvmSyncP1',1),
    'SnpDvmOpSync_P2':CHIMsgType('SnpDvmSyncP2',1),
    'SnpDvmOpNonSync_P1':CHIMsgType('SnpDvmNSyncP1',1),
    'SnpDvmOpNonSync_P2':CHIMsgType('SnpDvmNSyncP2',1),
    # ReqMsgs
    'WriteNoSnpPtl':CHIMsgType('WriteNSnpPtl',0),
    'WriteNoSnp':CHIMsgType('WriteNSnp',0),
    'ReadNoSnp':CHIMsgType('ReadNoSnp',0),
    'ReadNoSnpSep':CHIMsgType('ReadNSnpSep',0),
    'DvmOpNonSync':CHIMsgType('DvmOpNSync',0),
    'DvmOpSync':CHIMsgType('DvnOpSync',0),
    # RspMsg
    'Comp_I':CHIMsgType('CmpI',2),
    'Comp_UC':CHIMsgType('CmpUC',2),
    'Comp_SC':CHIMsgType('CmpSC',2),
    'CompAck':CHIMsgType('CmpAck',2),
    'CompDBIDResp':CHIMsgType('CmpDBIDRsp',2),
    'DBIDResp':CHIMsgType('DBIDRsp',2),
    'Comp':CHIMsgType('Cmp', 2),
    'ReadReceipt':CHIMsgType('ReadReceipt', 2),
    'RespSepData':CHIMsgType('RspSepData', 2),
    'SnpResp_I':CHIMsgType('SnpRspI', 2),
    'SnpResp_I_Fwded_UC':CHIMsgType('SnpRspIFwdUC', 2),
    'SnpResp_I_Fwded_UD_PD':CHIMsgType('SnpRspIFwdUDPD', 2),
    'SnpResp_SC':CHIMsgType('SnpRspSC', 2),
    'SnpResp_SC_Fwded_SC':CHIMsgType('SnpRspSCFwdSC', 2),
    'SnpResp_SC_Fwded_SD_PD':CHIMsgType('SnpRspSCFwdSDPD', 2),
    'SnpResp_UC_Fwded_I':CHIMsgType('SnpRsp', 2),
    'SnpResp_UD_Fwded_I':CHIMsgType('SnpRspUDFwdI', 2),
    'SnpResp_SC_Fwded_I':CHIMsgType('SnpRspSCFwdI', 2),
    'SnpResp_SD_Fwded_I':CHIMsgType('SnpRspSDFwdI', 2),
    'RetryAck':CHIMsgType('RetryAck', 2),
    'PCrdGrant':CHIMsgType('PCrdGrant', 2),
    # DatMsg
    'CompData_I':CHIMsgType('CmpDatI', 3),
    'CompData_UC':CHIMsgType('CmpDatUC', 3),
    'CompData_SC':CHIMsgType('CmpDatSC', 3),
    'CompData_UD_PD':CHIMsgType('CmpDatUDPD', 3),
    'CompData_SD_PD':CHIMsgType('CmpDatSDPD', 3),
    'DataSepResp_UC':CHIMsgType('DatSepRsp', 3),
    'CBWrData_UC':CHIMsgType('CBWrDatUC', 3),
    'CBWrData_SC':CHIMsgType('CBWrDatSC', 3),
    'CBWrData_UD_PD':CHIMsgType('CBWrDatUDPD', 3),
    'CBWrData_SD_PD':CHIMsgType('CBWrDatSDPD', 3),
    'CBWrData_I':CHIMsgType('CBWrDatI', 3),
    'NCBWrData':CHIMsgType('NCBWrDat', 3),
    'SnpRespData_I':CHIMsgType('SnpRspDatI', 3),
    'SnpRespData_I_PD':CHIMsgType('SnpRspDatIPD', 3),
    'SnpRespData_SC':CHIMsgType('SnpRspDatSC', 3),
    'SnpRespData_SC_PD':CHIMsgType('SnpRspDatSCPD', 3),
    'SnpRespData_SD':CHIMsgType('SnpRspDatSD', 3),
    'SnpRespData_UC':CHIMsgType('SnpRspDatUC', 3),
    'SnpRespData_UD':CHIMsgType('SnpRspDatUD', 3),
    'SnpRespData_SC_Fwded_SC':CHIMsgType('SnpRspDatSCFwdSC', 3),
    'SnpRespData_SC_Fwded_SD_PD':CHIMsgType('SnpRspDatSCFwdSDPD', 3),
    'SnpRespData_SC_PD_Fwded_SC':CHIMsgType('SnpRspDatSCPDFwdSC', 3),
    'SnpRespData_I_Fwded_SD_PD':CHIMsgType('SnpRspDatIFwdSDPD', 3),
    'SnpRespData_I_PD_Fwded_SC':CHIMsgType('SnpRspDatIFwdSC', 3),
    'SnpRespData_I_Fwded_SC':CHIMsgType('SnpRspDatIFwdSC', 2)
}


# we need 7 groups: 1) curTick, 2) name, 3) txsn, 4) arr time, 5) path, 6) type, 7) reqPtr
# msg_pat = re.compile('^(\s*\d*): (\S+): txsn: (\w+), arr: (\d*), (\S+), type: (\w+), req: (\w+), [\s\S]*$')

# we need 7 groups: 1) curTick, 2) name, 3) txsn, 4) arr time, 5) addon for msg breakdown, 6) path, 7) type, 8) reqPtr
msg_pat = re.compile('^(\s*\d*): (\S+): txsn: (\w+), arr: (\d*)(.*), (\S+), type: (.*), req: (\w+), [\s\S]*$')

# we need 9 groups: 1) curTick, 2) name, 3) txsn, 4) arr time, 5) last_link, 6) last_link_time, 7) path, 8) type, 9) reqPtr
# msg_pat = re.compile('^(\s*\d*): (\S+): txsn: (\w+), arr: (\d*)\((\S+):\d*\), (\S+), type: (\w+), req: (\w+), [\s\S]*$')

def test_msg_pat():
    l1 = '  87000: system.ruby.hnf.cntrl.rspIn: txsn: 0x0009000000000000, arr: 87500(int_links02.buffers2:1000), Cache-5->6, type: CompAck(0), req: 0x55fe84f46910, addr: [0x40, line 0x40]\n'
    for l in [l1]:
        msg_srch = re.search(msg_pat, l)
        msg_str = "Groups: "
        msg_str += ','.join([grp for grp in msg_srch.groups()])
        print(msg_str)

def my_draw_networkx_edge_labels(
    G,
    pos,
    edge_labels=None,
    label_pos=0.5,
    font_size=10,
    font_color="k",
    font_family="sans-serif",
    font_weight="normal",
    alpha=None,
    bbox=None,
    horizontalalignment="center",
    verticalalignment="center",
    ax=None,
    rotate=True,
    clip_on=True,
    rad=0
):

    if ax is None:
        ax = plt.gca()
    if edge_labels is None:
        labels = {(u, v): d for u, v, d in G.edges(data=True)}
    else:
        labels = edge_labels
    text_items = {}
    for (n1, n2), label in labels.items():
        (x1, y1) = pos[n1]
        (x2, y2) = pos[n2]
        (x, y) = (
            x1 * label_pos + x2 * (1.0 - label_pos),
            y1 * label_pos + y2 * (1.0 - label_pos),
        )
        pos_1 = ax.transData.transform(np.array(pos[n1]))
        pos_2 = ax.transData.transform(np.array(pos[n2]))
        linear_mid = 0.5*pos_1 + 0.5*pos_2
        d_pos = pos_2 - pos_1
        rotation_matrix = np.array([(0,1), (-1,0)])
        ctrl_1 = linear_mid + rad*rotation_matrix@d_pos
        ctrl_mid_1 = 0.5*pos_1 + 0.5*ctrl_1
        ctrl_mid_2 = 0.5*pos_2 + 0.5*ctrl_1
        bezier_mid = 0.5*ctrl_mid_1 + 0.5*ctrl_mid_2
        (x, y) = ax.transData.inverted().transform(bezier_mid)

        if rotate:
            # in degrees
            angle = np.arctan2(y2 - y1, x2 - x1) / (2.0 * np.pi) * 360
            # make label orientation "right-side-up"
            if angle > 90:
                angle -= 180
            if angle < -90:
                angle += 180
            # transform data coordinate angle to screen coordinate angle
            xy = np.array((x, y))
            trans_angle = ax.transData.transform_angles(
                np.array((angle,)), xy.reshape((1, 2))
            )[0]
        else:
            trans_angle = 0.0
        # use default box of white with white border
        if bbox is None:
            bbox = dict(boxstyle="round", ec=(1.0, 1.0, 1.0), fc=(1.0, 1.0, 1.0))
        if not isinstance(label, str):
            label = str(label)  # this makes "1" and 1 labeled the same

        t = ax.text(
            x,
            y,
            label,
            size=font_size,
            color=font_color,
            family=font_family,
            weight=font_weight,
            alpha=alpha,
            horizontalalignment=horizontalalignment,
            verticalalignment=verticalalignment,
            rotation=trans_angle,
            transform=ax.transData,
            bbox=bbox,
            zorder=1,
            clip_on=clip_on,
        )
        text_items[(n1, n2)] = t

    ax.tick_params(
        axis="both",
        which="both",
        bottom=False,
        left=False,
        labelbottom=False,
        labelleft=False,
    )

    return text_items


class Stats:
    def __init__(self, num_vnet):
        self.vnets = [0]*num_vnet

    def __str__(self):
        return f'{self.__dict__}'

class Controller:
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return self.path.split('.')[-2]

controllers:List[Controller] = []

class Router:
    def __init__(self, path, id):
        self.path = path
        self.id = id

    def __repr__(self):
        return f'R{self.id}'

class Link:
    def __init__(self, name, path, id):
        self.name = name
        self.path = path
        self.id = id

    def __repr__(self):
        return self.name

class ExtLink(Link):
    def __init__(self, name, path, id, int_node=None, ext_node=None):
        super(ExtLink,self).__init__(name,path,id)
        self.int_node = int_node
        self.ext_node = ext_node

    def __repr__(self):
        return f'ExtLink{self.id}: {self.int_node}<->{self.ext_node}'
    
    def __str__(self):
        return f'e{self.name[self.name.find("s")+1:]}'

class IntLink(Link):
    def __init__(self, name, path, id, src_node=None, dst_node=None, num_vnet=1):
        super(IntLink,self).__init__(name,path,id)
        self.src_node = src_node
        self.dst_node = dst_node
        self.stats:Stats = Stats(num_vnet=num_vnet)

    def __repr__(self):
        return f'IntLink{self.id}: {self.src_node}-->{self.dst_node}'
    
    def __str__(self):
        link_str = ''
        for i,(k,v) in enumerate(self.stats.__dict__.items()):
            if i%3==2:
                link_str += f'{k}:{v}\n'
            else:
                link_str += f'{k}:{v}, '

        return f'i{self.name[self.name.find("s")+1:]}, {link_str}'

def get_node(routers:List[Router], path):
    if isinstance(path, dict):
        path = path['path']

    for r in routers:
        if r.path == path:
            return r

    for c in controllers:
        if c.path == path:
            return c
    
    ctrl = Controller(path)
    controllers.append(ctrl)
    return ctrl

def parse_json(JSON: Dict):
    num_vnet = JSON['system']['ruby']['number_of_virtual_networks']
    logging.debug(f'num_vnet:{num_vnet}')
    network = JSON['system']['ruby']['network'] # system.ruby.network
    routers = network['routers']
    routers = [Router(path=r,id=i) for i,r in enumerate(routers)]
    logging.debug(f'routers:{routers}')
    ext_links = network['ext_links']
    ext_links = [ExtLink(name=l['name'],path=l['path'],id=i,ext_node=get_node(routers,l['ext_node']),int_node=get_node(routers,l['int_node'])) for i,l in enumerate(ext_links)]
    logging.debug(f'ext_links:{ext_links}')
    logging.debug(f'controllers:{controllers}')
    int_links = network['int_links']
    int_links = [IntLink(name=l['name'],path=l['path'],id=i,src_node=get_node(routers,l['src_node']),dst_node=get_node(routers,l['dst_node']),num_vnet=num_vnet) for i,l in enumerate(int_links)]
    logging.debug(f'int_links:{int_links}')
    logging.debug(f'controllers:{controllers}')

    return ext_links, int_links, routers

def parse_link_log(log_path: str, routers: List[Router], ext_links: List[ExtLink], int_links: List[IntLink]):
    with open(log_path,'r') as f:
        for line in f:

            routers_dict = {r.path:r for r in routers}
            int_links_dict = {l.path:l for l in int_links}
            ext_links_dict = {l.path:l for l in ext_links}

            logging.debug(f'router_dict: {routers_dict}')

            msg_srch = re.search(msg_pat, line)
            assert msg_srch != None

            # 1) curTick, 2) name, 3) txsn, 4) arr time, 5) last_arr_time, 6) last_link 7) path, 8) type, 9) reqPtr
            curtick = int(msg_srch.group(1))
            issuer:str = msg_srch.group(2)
            txsn = msg_srch.group(3)
            arrtick = int(msg_srch.group(4))
            addon_msg = msg_srch.group(5)
            path = msg_srch.group(6)
            typ = msg_srch.group(7)
            reqptr = msg_srch.group(8)

            issuer:str = issuer[:issuer.rfind('.')]

            # typ can be 1) CompAck:0 2) CompAck
            # if 2) we assume there is only one channel.
            if typ.find(':') == -1:
                typ,vnet = typ,0
            else:
                typ,vnet = typ.split(':')
            typ = CHIMsgType_dict[typ].abbr # use abbr

            # issuer can be int_links or req/rsp/snp/datIn
            # this is done by grep
            if issuer.find('int_links') == -1: # req/rsp/snp/datIn
                last_link_name, last_link_time = addon_msg.strip(')').split(':')
                last_link_time = int(last_link_time)
                logging.debug(f'cntrl port found: {issuer}, last_link:{last_link_name}({last_link_time})ticks')
            else: # links
                link = issuer
                logging.debug(f'router matched: {issuer}')
                int_links_dict[link].stats.vnets[int(vnet)]+=1
                # add new field to link's stats
                if int_links_dict[link].stats.__dict__.get(typ) == None:
                    int_links_dict[link].stats.__dict__[typ] = 1
                else:
                    int_links_dict[link].stats.__dict__[typ] += 1


def build_network(ext_links:List[ExtLink],int_links:List[IntLink],routers:List[Router],draw_ctrl:bool):
    G = nx.DiGraph()

    if draw_ctrl:
        G.add_nodes_from(routers)
        G.add_nodes_from(controllers)
        for e in ext_links:
            G.add_edge(e.ext_node, e.int_node, data=e)
            G.add_edge(e.int_node, e.ext_node, data=e)
        for i in int_links:
            G.add_edge(i.src_node, i.dst_node, data=i)

    else:
        G.add_nodes_from(routers)
        for i in int_links:
            G.add_edge(i.src_node, i.dst_node, data=i)

    return G

def draw_network(G, output_file, routers, num_int_router, num_ext_router, num_ctrl, draw_ctrl:bool):
    
    for num_cols in range(1,num_int_router):
        num_rows = num_int_router//num_cols
        if num_int_router==num_cols*num_rows and num_cols>=num_rows:
            break
    
    logging.debug(f'num_rows:{num_rows}, num_cols:{num_cols}')

    pos_dict = {}
    for i in range(num_int_router):
        r = routers[i]
        pos_dict[r] = np.array([(i//num_cols)*100,(i%num_cols-1)*100])
    
    logging.debug(f'pos:{pos_dict}')
    pos = nx.spring_layout(G, pos=pos_dict, fixed=list(pos_dict.keys()))
    logging.debug(f'pos:{pos}')
    node_color = ['#6096B4']*num_int_router+['#EEE9DA']*num_ext_router
    if draw_ctrl:
        node_color += ['#A7727D']*num_ctrl

    nx.draw_networkx_nodes(G, pos, node_size=10, node_color=node_color)
    nx.draw_networkx_labels(G, pos, font_size=1)
    nx.draw_networkx_edges(G, pos, edge_color='k',connectionstyle='arc3,rad=0.1',width=0.3,arrowsize=2, node_size=10)
    my_draw_networkx_edge_labels(G, pos, edge_labels={(u, v): edge['data'] for (u, v, edge) in G.edges(data=True)},font_size=1,rad=0.1)
    plt.savefig(output_file,dpi = 800)
    logging.info(f'save fig to {output_file}')


def dump_log(ext_links:List[ExtLink],int_links:List[IntLink],routers:List[Router],dump_path):
    int_links_stats = {l.name:{'src_node':l.src_node.__repr__(), 'dst_node':l.dst_node.__repr__(), 'msg':l.stats.__dict__} for l in int_links}

    with open(dump_path, 'w+') as f:
        json.dump(int_links_stats, f, indent=2)
    
    logging.info(f'details dump to {dump_path}')


if __name__ == '__main__':
    # test_msg_pat()

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    parser.add_argument('--draw-ctrl', required=False, action='store_true')
    parser.add_argument('--num-int-router', required=False, default=16, type=int)
    parser.add_argument('--start-time', required=False, default=0, type=int)
    parser.add_argument('--end-time', required=False, default=float('inf'), type=float)
    options = parser.parse_args()

    json_file = os.path.join(options.input,'config.json')
    debug_trace = os.path.join(options.input, 'debug.trace')
    link_log = os.path.join(options.input,'link.log')
    diagram_path = os.path.join(options.output, 'noc_diagram.png')
    dump_path = os.path.join(options.output, 'noc_details.json')

    import subprocess
    subprocess.run(['grep','-E', '^[[:space:]]+[0-9]+: system\.ruby\.network\.int_links[0-9]+\.buffers[0-9]+|^[[:space:]]+[0-9]+: system.*In:', debug_trace], stdout=open(link_log,'w+'))

    logging.info(f'Parsing network from {json_file}')

    ext_links, int_links, routers = None, None, None
    with open(json_file,'r') as f:
        JSON = json.load(f)
        ext_links, int_links, routers = parse_json(JSON)
    
    parse_link_log(link_log, routers, ext_links, int_links)
    dump_log(ext_links, int_links, routers, dump_path)

    graph = build_network(ext_links,int_links,routers,draw_ctrl=options.draw_ctrl)
    draw_network(G=graph, routers=routers, output_file=diagram_path, 
                 num_int_router=options.num_int_router, 
                 num_ext_router=len(routers)-options.num_int_router, 
                 num_ctrl=len(controllers), draw_ctrl=options.draw_ctrl)