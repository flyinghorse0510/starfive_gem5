
## Export these for bash
```
export GEM5_DIR=/home/arka.maity/Desktop/gem5_jh8100_starlink2.0 && \
export OUTPUT_DIR=/home/arka.maity/Desktop/04_gem5Dump/DMACHI/9CPUs_8L3 && \
export ISA=RISCV
```


## Building gem5 (PROTOCOL: CHI/MSI/MESI/MOESI)

```
scons RUBY=TRUE PROTOCOL=CHI build/RISCV/gem5.opt -j`nproc`
```

## Running a system config (Ruby+MemTest.py)
1. `num-l3caches`: Number of CHI_HNFs
2. `num-dirs`: Number of CHI_SNFs

0@HNF_0 ranges : 0:4294967296 : 0 : 64:128:256
1@HNF_1 ranges : 0:4294967296 : 1 : 64:128:256
2@HNF_2 ranges : 0:4294967296 : 2 : 64:128:256
3@HNF_3 ranges : 0:4294967296 : 3 : 64:128:256
4@HNF_4 ranges : 0:4294967296 : 4 : 64:128:256
5@HNF_5 ranges : 0:4294967296 : 5 : 64:128:256
6@HNF_6 ranges : 0:4294967296 : 6 : 64:128:256
7@HNF_7 ranges : 0:4294967296 : 7 : 64:128:256