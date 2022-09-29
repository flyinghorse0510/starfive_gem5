
## Export these for bash. Change as per your convenience
```
export WORKSPACE=${HOME}/Desktop
export GEM5_DIR=${WORKSPACE}/gem5_starlink2.0 && \
export OUTPUT_DIR=${WORKSPACE}/04_gem5Dump/DMACHI/SimpleRubyCHI && \
export ISA=RISCV
export CCPROT=CHI
```

## Building gem5 (PROTOCOL: CHI/MSI/MESI/MOESI)
```
scons build/${ISA}_${CCPROT}/gem5.opt --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
```

## Running SE mode 
export CCPROT=MESI_Two_Level && \
build/${ISA}_${CCPROT}/gem5.opt \
--debug-flags=MemRandomTest,RubyCacheCalibSTR5 --debug-file=debug.trace \
-d $OUTPUT_DIR \
 ${GEM5_DIR}/configs/example/se_memtest.py \
    --num-cpus=1 \
    --ruby \
    --mem-size=4GB \
    --mem-type=SimpleMemory \
    --cacheline_size=64 \
    --workingset-size=2048 \
    --progress=1000000 \
    --maxloads=1000000

## Running SE mode (CHI)
build/${ISA}_${CCPROT}/gem5.opt\
       --debug-flags=MemRandomTest,RubyCacheCalibSTR5 --debug-file=debug.trace \
       -d $OUTPUT_DIR \
       ${GEM5_DIR}/configs/example/se_memtest.py \
       --num-cpus=1 \
       --num-dirs=1 \
       --num-l3caches=1 \
       --ruby \
       --cacheline_size=64 \
       --workingset-size=2048 \
       --mem-size="4GB" \
       --progress=1000000 \
       --maxloads=1000