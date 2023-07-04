import networkx as nx
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
import argparse
import re
import numpy as np

PWD = os.getcwd()
TEST="injrate"
IN_FILE_PREF = f"{PWD}/garnetdump/r_{TEST}_"
IN_FILE_SUF = "/debug.trace"
OUT_FILE = f"{PWD}/garnetdump/results.csv"

INT_ONLY = r'[\d]+'

DEST = "Dest"
SRC = "Src"
LINKID = "LinkID"
ROUTERID = "RouterID"
CNTRL = "abs_cntrl"
COMPONENT = "COMPONENT"

NUM_NODES=18

# lines of interest
LINE = "Generating IntLink" #need to check when flit has been scheduled
EXT_LINE = "Generating ExtLink"

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

    import matplotlib.pyplot as plt
    import numpy as np

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

def parse_lines(graph_edges,graph_edges_ext,lines):
    for line in tqdm(lines):
        edge_dict = {}
        if LINE in line:
            words = line.split()
            for word in words:
                if DEST in word:
                    #add dest router id to edge
                    try:
                        dest = int(re.findall(INT_ONLY,word)[0])
                        edge_dict[DEST] = dest
                    except:
                        raise Exception("unable to find parameter")
                elif SRC in word:
                    #add src id to edge
                    try:
                        src = int(re.findall(INT_ONLY,word)[0])
                        edge_dict[SRC] = src
                    except:
                        raise Exception("unable to find parameter")
                elif LINKID in word:
                    #add link id to edge
                    try:
                        id = int(re.findall(INT_ONLY,word)[0])
                        edge_dict[LINKID] = id
                    except:
                        raise Exception("unable to find parameter")
            graph_edges.append(edge_dict)
        elif EXT_LINE in line:
            words = line.split()
            for word in words:
                if ROUTERID in word:
                    #add dest router id to edge
                    try:
                        dest = int(re.findall(INT_ONLY,word)[0])
                        edge_dict[DEST] = dest
                    except:
                        raise Exception("unable to find parameter")
                elif LINKID in word:
                    try:
                        #get the link id
                        linkid = word.split('.')[3]
                        edge_dict[LINKID] = linkid
                    except:
                        raise Exception("unable to find parameter")
                elif CNTRL in word:
                    #add src id to edge
                    try:
                        src = len(graph_edges_ext)
                        edge_dict[SRC] = src
                        edge_dict[COMPONENT] = word.split(":")[1]
                    except:
                        raise Exception("unable to find parameter")
            graph_edges_ext.append(edge_dict)
    return

def process_edges_int(graph_edges,edge_links,edge_labels):
    for edge in graph_edges:
        src = edge[SRC]
        dest = edge[DEST]
        edge_links.append((src,dest))
        edge_labels[(src,dest)] = "int_links"+str(edge[LINKID]) +"\n"

def process_edges_ext(node_labels,graph_edges,edge_links,edge_labels):
    for edge in graph_edges:
        src = edge[SRC]
        dest = edge[DEST]
        edge_links.append((src,dest))
        edge_labels[(src,dest)] = "ext_links"+edge[LINKID]
        node_labels[src] = edge[COMPONENT]

def main():
    graph_edges = {}
    IN_FILE = 'debug.trace'
    in_file = open(IN_FILE)
    in_lines = in_file.readlines()

    graph_edges = []
    graph_edges_ext = []
    edge_links = []
    edge_labels = {}
    node_labels = {}
    pos = {}

    parse_lines(graph_edges,graph_edges_ext,in_lines)

    G = nx.DiGraph()
    nodes = np.arange(0, NUM_NODES).tolist()
    G.add_nodes_from(nodes)
    fig, ax = plt.subplots()
    process_edges_int(graph_edges,edge_links,edge_labels)
    process_edges_ext(node_labels,graph_edges_ext,edge_links,edge_labels)

    for edge in edge_links:
        G.add_edge(edge[0],edge[1])

    for node in nodes:
        if node == 16:
            pos[node] = (10,50)
        elif node == 17:
            pos[node] = (20,50) 
        elif node < 4:
            pos[node] = (10+(node%4)*10,(40))
        elif node >=4 and node < 8:
            pos[node] = (10+(node%4)*10,(30))
        elif node >=8 and node < 12:
            pos[node] = (10+(node%4)*10,(20))
        elif node >=12 and node < 16:
            pos[node] = (10+(node%4)*10,(10))
        else:
            pos[node] = (node%10+5,70)
        node_labels[node] = node

    nx.draw_networkx(G, pos = pos,connectionstyle='arc3, rad=0.1', labels = node_labels,arrows = True)
    nx.draw_networkx_nodes(G, pos=pos,nodelist=nodes, node_shape = "o", node_color = "skyblue",edgecolors="black")
    my_draw_networkx_edge_labels(G, pos = pos, ax=ax,edge_labels=edge_labels,font_color='black', font_size="4",rad=0.1)
    plt.title("NoC")
    plt.savefig("noc_diagram.jpeg",
 dpi = 300)
    plt.show()
if __name__=="__main__":
    main()
