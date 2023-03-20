#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|h|w|t]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     FalseSharingMemTest"
   echo
}

BUILD=""
RUN=""
FALSESHARINGTEST=""

while getopts "hbr" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) FALSESHARINGTEST="yes"
           ;;
    esac
done

WORKSPACE="$(pwd)/output"
GEM5_DIR=$(pwd)
ISA="RISCV"
CCPROT="CHI"
BUILDTYPE="gem5.opt"
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/FalseSharingTest"
PY3=/home/arka.maity/anaconda3/bin/python3

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${BUILDTYPE} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$FALSESHARINGTEST" != "" ]; then
    l1d_size="1KiB"
    l1i_size="1KiB"
    l2_size="8KiB"
    l3_size="16KiB"
    l1d_assoc=2
    l1i_assoc=2
    l2_assoc=4
    l3_assoc=8
    NUM_LLC=16
    SEQ_TBE=32
    LoadFactor=3
    NUM_MEM=4
    NUM_DDR_XP=2
    NUM_DDR_Side=1
    LINK_BW=16
    LINKWIDTH=256
    VC_PER_VNET=2
    LINK_LAT=1
    ROUTER_LAT=0
    DMT=False
    DCT_CONFIG_SET=(False True)
    HNF_TBE=32
    SNF_TBE=32
    SEQ_TBE=32
    TRANS=4
    MultiCoreAddrMode=True
    NETWORK="simple"
    ALLOW_SD_SET=(False True)
    IDEAL_SNOOP_FILTER=True
    SNOOP_FILTER_SIZE=128
    SNOOP_FILTER_ASSOC=1
    DEBUGFLAGS=RubyCHIDebugStr5,SeqMemLatTest,TxnTrace

    WKSET=2048
    NUM_CPU_SET=(2 4 8 16)

    for NUMCPUS in ${NUM_CPU_SET[@]}; do
      for DCT in ${DCT_CONFIG_SET[@]}; do
        for ALLOWSD in ${ALLOW_SD_SET[@]}; do
            OUTPUT_PREFIX="${OUTPUT_ROOT}_${NETWORK}"
            OUTPUT_DIR="${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_AllowSD${ALLOWSD}" 
            echo ${OUTPUT_DIR}
            $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
              --debug-flags=$DEBUGFLAGS --debug-file=debug.trace \
              -d $OUTPUT_DIR \
              ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
              --num-dirs=${NUM_MEM} \
              --DDR-loc-num=${NUM_DDR_XP} \
              --DDR-side-num=${NUM_DDR_Side} \
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
              --simple-link-bw-factor=${LINK_BW} \
              --link-width-bits=${LINKWIDTH} \
              --vcs-per-vnet=${VC_PER_VNET} \
              --link-latency=${LINK_LAT} \
              --router-latency=${ROUTER_LAT} \
              --topology=CustomMesh \
              --simple-physical-channels \
              --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
              --ruby \
              --maxloads=${LoadFactor} \
              --mem-size="16GB" \
              --size-ws=${WKSET} \
              --mem-type=DDR4_3200_8x8 \
              --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
              --mem-test-type='falsesharing_test' \
              --addr-intrlvd-or-tiled=$MultiCoreAddrMode  \
              --disable-gclk-set \
              --enable-DMT=${DMT} \
              --enable-DCT=${DCT} \
              --num-HNF-TBE=${HNF_TBE}  \
              --num-SNF-TBE=${SNF_TBE}  \
              --sequencer-outstanding-requests=${SEQ_TBE} \
              --num_trans_per_cycle_llc=${TRANS} \
              --num-cpus=${NUMCPUS} \
              --inj-interval=1 \
              --num-snoopfilter-entries=${SNOOP_FILTER_SIZE} \
              --num-snoopfilter-assoc=${SNOOP_FILTER_ASSOC} \
              --allow-infinite-SF-entries=${IDEAL_SNOOP_FILTER} \
              --num-producers=1 &
            done
        done
    done
    wait

    SUMMARY_JSON="${OUTPUT_ROOT}_${NETWORK}/Summary.json"
    echo "[" > ${SUMMARY_JSON}
    for NUMCPUS in ${NUM_CPU_SET[@]}; do
      for DCT in ${DCT_CONFIG_SET[@]}; do
        for ALLOWSD in ${ALLOW_SD_SET[@]}; do
            OUTPUT_PREFIX="${OUTPUT_ROOT}_${NETWORK}"
            OUTPUT_DIR="${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_AllowSD${ALLOWSD}" 
            ${PY3} processDebugTrace.py \
                  --input=${OUTPUT_DIR} \
                  --output=${OUTPUT_DIR} \
                  --dct=${DCT} \
                  --bench="falsesharing_test" \
                  --allow-SD=${ALLOWSD} \
                  --num-cpus=${NUMCPUS} >> ${SUMMARY_JSON}
            echo "," >> ${SUMMARY_JSON}
        done
        done
    done
fi