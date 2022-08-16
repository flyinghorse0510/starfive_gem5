
## Export these for tcsh
```
export GEM5_DIR=/home/arka.maity/Desktop/gem5_jh8100_starlink2.0 && \
export OUTPUT_DIR=/home/arka.maity/Desktop/04_gem5Dump/DMACHI && \
export ISA=RISCV
```


## Building gem5 (PROTOCOL: CHI/MSI/MESI/MOESI)

```
scons RUBY=TRUE PROTOCOL=CHI build/RISCV/gem5.opt -j`nproc`
```

## Running a system config (Ruby+MemTest.py)
```
$GEM5_DIR/build/$ISA/gem5.opt \
    --debug-flags=SeqMemLatTest,SeqMemTest --debug-file=debug.trace \
    -d $OUTPUT_DIR/CHITraceStudy \
    ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
    --num-dirs=1 \
    --num-l3caches=1 \
    --network=simple \
    --topology=CustomMesh \
    --chi-config=${GEM5_DIR}/configs/example/noc_config/2x2.py \
    --ruby \
    --mem-size="4GB" \
    --num-dmas=0 \
    --num-cpus=1 \
    --progress=1000000 \
    --maxloads=5
```

## Important notes
1. RubySlicc_*.sm contain func decls for commonly used functions


