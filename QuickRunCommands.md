
## Export these for bash
```
export GEM5_DIR=/home/arka.maity/Desktop/gem5_starlink2.0 && \
export OUTPUT_DIR=/home/arka.maity/Desktop/04_gem5Dump/DMACHI/SimpleRuby && \
export ISA=RISCV
```


## Building gem5 (PROTOCOL: CHI/MSI/MESI/MOESI)

```
scons RUBY=TRUE PROTOCOL=CHI build/RISCV/gem5.opt -j`nproc`
```

## Running a system config (Ruby+MemTest.py)
1. `num-l3caches`: Number of CHI_HNFs
2. `num-dirs`: Number of CHI_SNFs

## Running SE mode
build/RISCV/gem5.opt \
-d $OUTPUT_DIR \
configs/example/se.py \
    -n 1 \
    --mem-size=4GB \
    --mem-type=SimpleMemory \
    --cacheline_size=64 \
    --cmd=./benchmarks/coremark/coremark.riscv
