#!/bin/bash
WORKSPACE="${HOME}/Desktop"
GEM5_DIR="${WORKSPACE}/gem5_starlink2.0"
OUTPUT_DIR="${WORKSPACE}/04_gem5Dump/DMACHI/SimpleRubyCHI_STATS"
ISA="RISCV"
CCPROT="CHI"

WS_LIST=(784788)
for ws in ${WS_LIST[@]}; do
    echo "running ${ws}"
    build/${ISA}_${CCPROT}/gem5.opt \
        --debug-flags=MemRandomTest,RubyCacheCalibSTR5 --debug-file=debug_${CCPROT}_${ws}.trace \
        -d $OUTPUT_DIR \
        ${GEM5_DIR}/configs/example/se_memtest.py \
        --num-cpus=1 \
        --num-dirs=1 \
        --num-l3caches=1 \
        --ruby \
        --cacheline_size=64 \
        --workingset-size=${ws} \
        --mem-size="4GB" \
        --progress=1000000 \
        --maxloads=1000000
    mv $OUTPUT_DIR/stats.txt $OUTPUT_DIR/stats_${CCPROT}_${ws}.txt
done