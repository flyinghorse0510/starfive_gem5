#!/bin/bash

GEM5_DIR="/home/arka.maity/Desktop/gem5_jh8100_starlink2.0"
OUTPUT_DIR="/home/arka.maity/Desktop/04_gem5Dump/DMACHI/9CPUs_8L3_ControlledMemAccess"
ISA="RISCV"

$GEM5_DIR/build/$ISA/gem5.opt \
    --debug-flags=RubyCHITrace,RubyGenerated,MemTest --debug-file=debug.trace \
    -d $OUTPUT_DIR \
    ${GEM5_DIR}/configs/example/ruby_mem_test.py \
    --num-dirs=1 \
    --num-l3caches=8 \
    --network=simple \
    --topology=CustomMesh \
    --chi-config=${GEM5_DIR}/configs/example/noc_config/4x4.py \
    --ruby \
    --mem-size="4GB" \
    --num-dmas=0 \
    --num-cpus=9 \
    --progress=1000000 \
    --maxloads=1000

echo "Parsing the address trace"
python3 ProcessCHIDebugTrace.py --dump-dir ${OUTPUT_DIR}