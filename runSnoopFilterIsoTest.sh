#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|h|w]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     IsoMemTest"
   echo "w     ProdConsMemTest"
   echo
}

BUILD=""
RUN=""
ANALYSIS=""

while getopts "hbrw" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) ISOMEMTEST="yes"
           ;;
        w) PRODCONSTEST="yes"
           ;;
    esac
done

WORKSPACE="$(pwd)/output"
GEM5_DIR=$(pwd)
ISA="RISCV"
CCPROT="CHI"
NUMCPUS=4
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
DEBUGFLAGS=RubyGenerated,RubyCHIDebugStr5,ProdConsMemLatTest,TxnTrace

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${BUILDTYPE} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$ISOMEMTEST" != "" ]; then
    OUTPUT_DIR="${WORKSPACE}/MOD0.5_SnoopFilter_IsoTest"
    mkdir -p $OUTPUT_DIR
    DEBUGFLAGS=RubyGenerated,RubyCHIDebugStr5
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
        --num-producers=1 \
        --num-snoopfilter-entries=64 \
        --num-snoopfilter-assoc=8
    grep -E 'system\.ruby\.hnf[0-9]*' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf.trace
fi

if [ "$PRODCONSTEST" != "" ]; then
    LOC_CONS=1
    LOC_PROD=0
    MAXNUMLOADS=10
    WKSET=65536
    DCT=False
    LINK_BW=16
    OUTPUT_DIR="${WORKSPACE}/MOD0.5_SnoopFilter_ProdConsTest"
    mkdir -p $OUTPUT_DIR
    $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
        --debug-flags=$DEBUGFLAGS --debug-file=debug.trace \
        -d $OUTPUT_DIR \
        ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
        --ruby \
        --num-dirs=1 \
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
        --simple-physical-channels \
        --simple-link-bw-factor=${LINK_BW} \
        --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_2x2Mesh.py \
        --mem-size="16GB" \
        --mem-type=DDR4_3200_8x8 \
        --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
        --mem-test-type='prod_cons_test' \
        --disable-gclk-set \
        --enable-DMT=False \
        --enable-DCT=${DCT} \
        --num_trans_per_cycle_llc=4 \
        --addr-intrlvd-or-tiled=True \
        --bench-c2cbw-mode=True \
        --maxloads=${MAXNUMLOADS} \
        --size-ws=${WKSET} \
        --num-cpus=${NUMCPUS} \
        --sequencer-outstanding-requests=32 \
        --chs-1p1c \
        --chs-cons-id=${LOC_CONS} \
        --chs-prod-id=${LOC_PROD} \
        --num-snoopfilter-entries=4 \
        --num-snoopfilter-assoc=2
    grep -E 'ReqDone=ST|ReqDone=LD' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.ReqBegin.trace
fi