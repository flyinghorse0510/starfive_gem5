#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|h|t]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "t     seqmemtest"
   echo
}

BUILD=""
RUN=""
ISOMEMTEST=""
PRODCONSTEST=""
GATETEST=""

while getopts "hbt" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        t) GATETEST="yes"
           ;;
    esac
done

WORKSPACE="$(pwd)/output"
GEM5_DIR=$(pwd)
ISA="RISCV"
CCPROT="CHI"
BUILDTYPE="gem5.opt"
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/DMAAllocTest"
PY3=/home/arka.maity/anaconda3/bin/python3

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${BUILDTYPE} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi


if [ "$GATETEST" != "" ]; then
    l1d_size="128B"
    l1i_size="128B"
    l2_size="512B"
    l3_size="2KiB"
    l1d_assoc=1
    l1i_assoc=1
    l2_assoc=1
    l3_assoc=1
    NUM_LLC=1
    SEQ_TBE=32
    LoadFactor=10
    NUM_MEM=4
    NUM_DDR_XP=2
    NUM_DDR_Side=1
    LINK_BW=16
    LINKWIDTH=256
    VC_PER_VNET=2
    LINK_LAT=1
    ROUTER_LAT=0
    DMT=True
    DCT=False
    HNF_TBE=32
    SNF_TBE=32
    SEQ_TBE=32
    TRANS=4
    MultiCoreAddrMode=True
    NETWORK="simple"
    IDEAL_SNOOP_FILTER=False
    DEBUGFLAGS=RubyGenerated,RubyCHIDebugStr5
    OUTPUT_PREFIX="CHITxnTest_${NETWORK}"

    WKSETLIST=(1024)
    NUM_CPU_SET=(1)
    SNOOP_FILTER_SIZE=128
    SNOOP_FILTER_ASSOC=4
    UNIFY_REPL_TBE=False
    XOR_ADDR_BITS=4
    RANDOMIZE_ACC_CONFIG_SET=(False)
    BLOCK_STRIDE_BITS=0
    RANDOMIZE_ACC=False

    for NUMCPUS in ${NUM_CPU_SET[@]}; do
        for WKSET in ${WKSETLIST[@]}; do
            OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
            echo "GateTest Started: ${OUTPUT_BASE}"
            mkdir -p ${OUTPUT_DIR}
            set > ${OUTPUT_DIR}/Variables.txt
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
              --mem-test-type='bw_test_sf' \
              --addr-intrlvd-or-tiled=$MultiCoreAddrMode  \
              --disable-gclk-set \
              --enable-DMT=${DMT} \
              --enable-DCT=${DCT} \
              --num-HNF-TBE=${HNF_TBE}  \
              --num-SNF-TBE=${SNF_TBE}  \
              --sequencer-outstanding-requests=${SEQ_TBE} \
              --num_trans_per_cycle_llc=${TRANS} \
              --num-cpus=1 \
              --num-dmas=${NUMCPUS} \
              --inj-interval=1 \
              --num-snoopfilter-entries=${SNOOP_FILTER_SIZE} \
              --num-snoopfilter-assoc=${SNOOP_FILTER_ASSOC} \
              --allow-infinite-SF-entries=${IDEAL_SNOOP_FILTER} \
              --xor-addr-bits=${XOR_ADDR_BITS} \
              --block-stride-bits=${BLOCK_STRIDE_BITS} \
              --randomize-acc=${RANDOMIZE_ACC} \
              --unify_repl_TBEs=$UNIFY_REPL_TBE > ${OUTPUT_DIR}/cmd.log 2>&1 &
        done
    done
    wait
    
    for NUMCPUS in ${NUM_CPU_SET[@]}; do
        for WKSET in ${WKSETLIST[@]}; do
            OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
            echo "GateTest Parsing: ${OUTPUT_BASE}"
            grep 'hnf' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf.trace
            ${PY3} reOrderSliccTrace.py \
                --input="${OUTPUT_DIR}/debug.hnf.trace" \
                --output="${OUTPUT_DIR}/debug.hnf.trace.csv"
                            
        done
    done
fi
