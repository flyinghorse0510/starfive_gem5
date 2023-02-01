#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|s|h]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     Run1 (MemTest)."
   echo "s     Run2 (IsoMemTest)."
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
        s) RUN2="yes"
           ;;
    esac
done

export WORKSPACE="${HOME}/Desktop"
export GEM5_DIR=$(pwd)
export ISA="RISCV"
export CCPROT="CHI"
export NUMCPUS=2

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/gem5.debug --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN2" != "" ]; then
    OUTPUT_DIR="${WORKSPACE}/04_gem5dump/HAS0.5"
    mkdir -p $OUTPUT_DIR
    $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.debug \
        --debug-flags=ProdConsMemLatTest --debug-file=debug.trace \
        -d ${OUTPUT_DIR} \
        ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
        --num-dirs=1 \
        --num-l3caches=1 \
        --network=simple \
        --topology=CustomMesh \
        --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_2x2Mesh.py \
        --ruby \
        --maxloads=3000 \
        --mem-size="4GB" \
        --mem-test-type='prod_cons_test' \
        --num-cpus=${NUMCPUS}
    grep -rwI -e 'system\.cpu0' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu0.trace
    grep -rwI -e 'system\.cpu1' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu1.trace
fi