#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|h]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     Run1 (MemTest)."
   echo
}

BUILD=""
RUN=""
while getopts "hbrs" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) RUN1="yes"
           ;;
    esac
done

export WORKSPACE="$(pwd)/output"
export GEM5_DIR=$(pwd)
export ISA="RISCV"
export CCPROT="CHI"
export NUMCPUS=2

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${buildType} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN1" != "" ]; then
    OUTPUT_DIR="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_2DDR"
    mkdir -p $OUTPUT_DIR
    $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
        --debug-flags=ProdConsMemLatTest --debug-file=debug.trace \
        -d ${OUTPUT_DIR} \
        ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
        --num-dirs=2 \
        --num-l3caches=4 \
        --l1d_size=${l1d_size} \
        --l1i_size=${l1i_size} \
        --l2_size=${l2_size} \
        --l3_size=${l3_size} \
        --l1d_assoc=${l1d_assoc} \
        --l1i_assoc=${l1i_assoc} \
        --l2_assoc=${l2_assoc} \
        --l3_assoc=${l3_assoc} \
        --network=${NETWORK} \
        --topology=CustomMesh \
        --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
        --ruby \
        --maxloads=100 \
        --mem-size="16GB" \
        --size-ws=64 \
        --mem-type=DDR4_3200_8x8 \
        --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
        --mem-test-type='prod_cons_test' \
        --enable-DMT=False \
        --num-cpus=${NUMCPUS}
    grep -rwI -e 'system\.cpu0' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu0.trace
    grep -rwI -e 'system\.cpu1' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu1.trace
fi
