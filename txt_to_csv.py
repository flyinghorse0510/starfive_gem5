
def convert_to_csv(file):
    with open(file,'r') as f:
        with open(f"{file}.csv",'w') as wf:
            lines = f.readlines()
            for line in lines:
                print(",".join(line.split()),file=wf)
            wf.close()
        f.close()
