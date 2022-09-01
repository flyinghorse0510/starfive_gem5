
## Export these for bash. Change as per your convenience
```
export WORKSPACE=${HOME}/Desktop
export GEM5_DIR=${WORKSPACE}/gem5_starlink2.0 && \
export OUTPUT_DIR=${WORKSPACE}/04_gem5Dump/DMACHI/SimpleRuby && \
export ISA=RISCV
```

## Building gem5 (PROTOCOL: CHI/MSI/MESI/MOESI)
```
scons RUBY=TRUE PROTOCOL=CHI build/RISCV/gem5.opt -j`nproc`
```

## Running SE mode
build/RISCV/gem5.opt \
-d $OUTPUT_DIR \
configs/example/se.py \
    -n 1 \
    --mem-size=4GB \
    --mem-type=SimpleMemory \
    --cacheline_size=64 \
    --cmd=./benchmarks/coremark/coremark.riscv
