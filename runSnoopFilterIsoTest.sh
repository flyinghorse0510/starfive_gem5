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
ANALYSIS=""

while getopts "hbrsa" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) RUN1="yes"
           ;;
    esac
done

WORKSPACE="$(pwd)/output"
GEM5_DIR=$(pwd)
ISA="RISCV"
CCPROT="CHI"
NUMCPUS=1
NUM_LLC=1
NUM_SNF=1
NETWORK="simple"
BUILDTYPE="gem5.debug"
l1d_size="32KiB"
l1i_size="32KiB"
l2_size="256KiB"
l3_size="1024KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=2
l1i_assoc=2
l2_assoc=8
l3_assoc=16
DEBUGFLAGS=RubyGenerated,RubyCHIDebugStr5

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${BUILDTYPE} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN1" != "" ]; then
    OUTPUT_DIR="${WORKSPACE}/MOD0.5_SnoopFilter_IsoTest"
    mkdir -p $OUTPUT_DIR
    $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
        --debug-flags=${DEBUGFLAGS} --debug-file=debug.trace \
        -d ${OUTPUT_DIR} \
        ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
        --num-dirs=${NUM_SNF} \
        --num-l3caches=${NUM_LLC} \
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
        --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_2x2Mesh.py \
        --ruby \
        --maxloads=100 \
        --mem-size="4GB" \
        --size-ws=64 \
        --mem-test-type='isolated_test' \
        --num-cpus=${NUMCPUS} \
        --num-producers=1
    grep -E 'system\.ruby\.hnf' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf.trace
fi
