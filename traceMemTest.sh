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

export WORKSPACE="$(pwd)/output"
export GEM5_DIR=$(pwd)
export ISA="RISCV"
export CCPROT="CHI"
export NUMCPUS=2

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/gem5.debug --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN2" != "" ]; then
    OUTPUT_DIR="${WORKSPACE}/04_gem5dump/ExpMEMTest"
    mkdir -p $OUTPUT_DIR
    $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.debug \
        --debug-flags=TxnTrace  --debug-file=debug.trace \
        -d ${OUTPUT_DIR} \
        ${GEM5_DIR}/configs/example/isolated_ruby_mem_test.py \
        --num-dirs=1 \
        --num-l3caches=2 \
        --network=simple \
        --topology=CustomMesh \
        --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_2x2Mesh.py \
        --ruby \
        --maxloads=10 \
        --mem-size="4GB" \
        --num-cpus=${NUMCPUS}
    # grep -rwI -e 'system\.ruby\.hnf\.cntrl' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.hnf.trace
    # sed -i '/triggerQueue/d' $OUTPUT_DIR/debug.trace
    # sed -i '/system.ruby.network/d' $OUTPUT_DIR/debug.trace
    # sed -i '/reqRdy/d' $OUTPUT_DIR/debug.trace
    sed -i '/triggerQueue/d; /system.ruby.network/d; /reqRdy/d' $OUTPUT_DIR/debug.trace
fi