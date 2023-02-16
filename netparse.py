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

logging.basicConfig(level=logging.INFO)

# we need 7 groups: 1) curTick, 2) name, 3) txsn, 4) arr time, 5) path, 6) type, 7) reqPtr
msg_pat = re.compile('^(\s*\d*): (\S+): txsn: (\w+), arr: (\d*), (\S+), type: (\w+), req: (\w+), [\s\S]*$')


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
    def __init__(self):
        pass

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
    def __init__(self, name, path, id, src_node=None, dst_node=None):
        super(IntLink,self).__init__(name,path,id)
        self.src_node = src_node
        self.dst_node = dst_node
        self.stats:Stats = Stats()

    def __repr__(self):
        return f'IntLink{self.id}: {self.src_node}-->{self.dst_node}'
    
    def __str__(self):
        return f'i{self.name[self.name.find("s")+1:]},\n{self.stats}'

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

    network = JSON['system']['ruby']['network'] # system.ruby.network
    routers = network['routers']
    routers = [Router(path=r,id=i) for i,r in enumerate(routers)]
    logging.debug(f'routers:{routers}')
    ext_links = network['ext_links']
    ext_links = [ExtLink(name=l['name'],path=l['path'],id=i,ext_node=get_node(routers,l['ext_node']),int_node=get_node(routers,l['int_node'])) for i,l in enumerate(ext_links)]
    logging.debug(f'ext_links:{ext_links}')
    logging.debug(f'controllers:{controllers}')
    int_links = network['int_links']
    int_links = [IntLink(name=l['name'],path=l['path'],id=i,src_node=get_node(routers,l['src_node']),dst_node=get_node(routers,l['dst_node'])) for i,l in enumerate(int_links)]
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

            # 1) curTick, 2) name, 3) txsn, 4) arr tick, 5) path, 6) type, 7) reqPtr
            curtick = int(msg_srch.group(1))
            issuer:str = msg_srch.group(2)
            txsn = msg_srch.group(3)
            arrtick = int(msg_srch.group(4))
            path = msg_srch.group(5)
            typ = msg_srch.group(6)
            reqptr = msg_srch.group(7)

            link:str = issuer[:issuer.rfind('.')]
            logging.debug(f'router matched: {link}')
            
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

def draw_network(G, output_file, num_int_router, num_ext_router, num_ctrl, draw_ctrl:bool):
    pos = nx.kamada_kawai_layout(G)
    node_color = ['#6096B4']*num_int_router+['#EEE9DA']*num_ext_router
    if draw_ctrl:
        node_color += ['#A7727D']*num_ctrl

    nx.draw_networkx_nodes(G, pos, node_size=20, node_color=node_color)
    nx.draw_networkx_labels(G, pos, font_size=2)
    nx.draw_networkx_edges(G, pos, edge_color='k',connectionstyle='arc3,rad=0.1',width=0.3,arrowsize=2, node_size=20)
    my_draw_networkx_edge_labels(G, pos, edge_labels={(u, v): edge['data'] for (u, v, edge) in G.edges(data=True)},font_size=1,rad=0.1)
    plt.savefig(output_file,dpi = 800)
    logging.info(f'save fig to {output_file}')


def dump_log(ext_links:List[ExtLink],int_links:List[IntLink],routers:List[Router],dump_path):
    int_links_stats = {l.name:{'src_node':l.src_node.__repr__(), 'dst_node':l.dst_node.__repr__(), 'msg':l.stats.__dict__} for l in int_links}

    with open(dump_path, 'w+') as f:
        json.dump(int_links_stats, f, indent=2)
    
    logging.info(f'details dump to {dump_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--input', required=True, type=str)
    parser.add_argument('--output', required=True, type=str)
    parser.add_argument('--draw-ctrl', required=False, action='store_true')
    parser.add_argument('--num_int_router', required=False, default=16, type=int)
    parser.add_argument('--start-time', required=False, default=0, type=int)
    parser.add_argument('--end-time', required=False, default=float('inf'), type=float)
    options = parser.parse_args()

    json_file = os.path.join(options.input,'config.json')
    link_log = os.path.join(options.input,'link.log')
    diagram_path = os.path.join(options.output, 'noc_diagram.png')
    dump_path = os.path.join(options.output, 'noc_details.json')

    logging.info(f'Parsing network from {json_file}')

    ext_links, int_links, routers = None, None, None
    with open(json_file,'r') as f:
        JSON = json.load(f)
        ext_links, int_links, routers = parse_json(JSON)
    
    parse_link_log(link_log, routers, ext_links, int_links)
    dump_log(ext_links, int_links, routers, dump_path)

    graph = build_network(ext_links,int_links,routers,draw_ctrl=options.draw_ctrl)
    draw_network(G=graph, output_file=diagram_path, 
                 num_int_router=options.num_int_router, 
                 num_ext_router=len(routers)-options.num_int_router, 
                 num_ctrl=len(controllers), draw_ctrl=options.draw_ctrl)