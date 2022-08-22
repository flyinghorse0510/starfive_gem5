#!/bin/bash

GEM5_DIR="/home/arka.maity/Desktop/gem5_jh8100_starlink2.0"
OUTPUT_DIR="/home/arka.maity/Desktop/04_gem5Dump/DMACHI/2CPUs_2L3"
ISA="RISCV"

$GEM5_DIR/build/$ISA/gem5.opt \
    --debug-flags=RubyCHITrace,IsolatedMemTest,RubyGenerated --debug-file=debug.trace \
    -d $OUTPUT_DIR \
    ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
    --num-dirs=1 \
    --num-l3caches=2 \
    --network=simple \
    --topology=CustomMesh \
    --chi-config=${GEM5_DIR}/configs/example/noc_config/2x2.py \
    --ruby \
    --mem-size="4GB" \
    --num-dmas=0 \
    --num-cpus=1 \
    --progress=1000000 \
    --maxloads=1

# commontrings="-e hnf -e snf"

# for i in $(seq 0 0); do
#     grep -e cpu${i} ${commontrings} ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.trace.cpu$i
# done
