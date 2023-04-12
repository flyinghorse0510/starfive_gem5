import json

SEQTBE_SET= [1,32]

def process_L3(json_data):
    data_dict = {}
    for node in json_data:
        if node["WS"] not in data_dict.keys():
            data_dict[node["WS"]]={node["INJINTV"]:{"LAT":node["LAT"],"BW":node["BW"]}}
        else:
            data_dict[node["WS"]][node["INJINTV"]]={"LAT":node["LAT"],"BW":node["BW"]}
    return data_dict
def process_L1L2(json_data):
    data_dict = {}
    for node in json_data:
        if node["SEQTBE"] == SEQTBE_SET[0]: #latency
            print(str(node["LAT"]))
            newdict = {"LAT":node["LAT"]}
        elif node["SEQTBE"] == SEQTBE_SET[1]: #bandwidth
            newdict = {"BW":node["BW"]}
        if node["WS"] not in data_dict.keys():
            data_dict[node["WS"]]={node["INJINTV"]:newdict}
        else:
            if node["INJINTV"] not in data_dict[node["WS"]].keys():
                data_dict[node["WS"]][node["INJINTV"]]=newdict
            else:
                data_dict[node["WS"]][node["INJINTV"]].update(newdict)
    return data_dict
with open("/home/lester.leong/simulation/gem5_starlink2/output/GEM5_PDCP/GateTest/Summary.json",'r') as jsonfile:
    #assumption that the json file is single layered
    json_data = json.load(jsonfile)
    print(json.dumps(json_data,indent=4))

    data_dict = process_L3(json_data)

    with open("result.csv", 'w') as csvfile:
        print("Injection Interval, Working Set, Bandwidth, Packet Latency",file=csvfile)
        for ws,data in data_dict.items():
            for injintv,bw_lat in data.items():
                print(bw_lat)
                workingstr = [str(injintv),str(ws),str(bw_lat["BW"]),str(bw_lat["LAT"])]
                print(",".join(workingstr),file = csvfile)

        csvfile.close()

    jsonfile.close()