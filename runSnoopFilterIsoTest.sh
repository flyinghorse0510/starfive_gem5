#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|h|w|t]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     IsoMemTest"
   echo "w     ProdConsMemTest"
   echo "t     seqmemtest"
   echo
}

BUILD=""
RUN=""
ISOMEMTEST=""
PRODCONSTEST=""
GATETEST=""

while getopts "hbrwt" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) ISOMEMTEST="yes"
           ;;
        w) PRODCONSTEST="yes"
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
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/SnoopFilterTest"
PY3=/home/arka.maity/anaconda3/bin/python3

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${BUILDTYPE} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$ISOMEMTEST" != "" ]; then
    NUMCPUS=1
    NUM_LLC=1
    NUM_SNF=1
    NETWORK="simple"
    l1d_size="128B"
    l1i_size="128B"
    l2_size="4KiB"
    l3_size="1024KiB" #"16KiB" #"1024KiB" #"256KiB"
    l1d_assoc=1
    l1i_assoc=1
    l2_assoc=1
    l3_assoc=16
    REPL="RandomRP"
    DEBUGFLAGS=RubyGenerated,RubyCHIDebugStr5,IsolatedMemLatTest

    OUTPUT_DIR="${WORKSPACE}/MOD0.5_SnoopFilter_IsoTest"
    mkdir -p $OUTPUT_DIR
    DEBUGFLAGS=${DEBUGFLAGS}
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
        --l1repl=${REPL} \
        --l2repl=${REPL} \
        --l3repl=${REPL} \
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
        --num-snoopfilter-entries=8 \
        --num-snoopfilter-assoc=1
    grep -E 'system\.ruby\.hnf[0-9]*' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf.trace
fi

if [ "$PRODCONSTEST" != "" ]; then
    LOC_CONS=1
    LOC_PROD=0
    l1d_size="128B"
    l1i_size="128B"
    l2_size="8KiB"
    l3_size="1KiB"
    l1d_assoc=1
    l1i_assoc=1
    l2_assoc=4
    l3_assoc=8
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
    DMT=False
    DCT=False
    HNF_TBE=32
    SNF_TBE=32
    SEQ_TBE=32
    TRANS=4
    MultiCoreAddrMode=True
    NETWORK="simple"
    SNOOP_FILTER_SIZE=2
    SNOOP_FILTER_ASSOC=1
    NUMCPUS=16
    DEBUGFLAGS=RubyGenerated,RubyCHIDebugStr5,ProdConsMemLatTest,TxnTrace
    
    WKSETLIST=(2048)
    for WKSET in ${WKSETLIST[@]}; do
    OUTPUT_PREFIX="ProdCons_${NETWORK}"
    OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_LoadFactor${LoadFactor}_SFSize${SNOOP_FILTER_SIZE}_SFAssoc${SNOOP_FILTER_ASSOC}" 
    $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
        --debug-flags=$DEBUGFLAGS --debug-file=debug.trace \
        -d $OUTPUT_DIR \
        ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
        --ruby \
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
        --topology=CustomMesh \
        --simple-physical-channels \
        --simple-link-bw-factor=${LINK_BW} \
        --link-width-bits=${LINKWIDTH} \
        --vcs-per-vnet=${VC_PER_VNET} \
        --link-latency=${LINK_LAT} \
        --router-latency=${ROUTER_LAT} \
        --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
        --mem-size="16GB" \
        --mem-type=DDR4_3200_8x8 \
        --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
        --mem-test-type='prod_cons_test' \
        --disable-gclk-set \
        --enable-DMT=${DMT} \
        --enable-DCT=${DCT} \
        --num_trans_per_cycle_llc=${TRANS} \
        --num-HNF-TBE=${HNF_TBE}  \
        --num-SNF-TBE=${SNF_TBE}  \
        --addr-intrlvd-or-tiled=$MultiCoreAddrMode \
        --bench-c2cbw-mode=True \
        --sequencer-outstanding-requests=${SEQ_TBE} \
        --maxloads=${LoadFactor} \
        --size-ws=${WKSET} \
        --num-cpus=${NUMCPUS} \
        --chs-1p1c \
        --chs-cons-id=${LOC_CONS} \
        --chs-prod-id=${LOC_PROD} \
        --num-snoopfilter-entries=${SNOOP_FILTER_SIZE} \
        --num-snoopfilter-assoc=${SNOOP_FILTER_ASSOC}
    done
    grep -E 'hnf' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf.trace
    grep -E 'Complete,R|Start,R|Reader finished generating' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.txncomplete.trace
    # grep -E 'system.cpu0:|system.cpu0.data_sequencer:' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu0.trace
fi

if [ "$GATETEST" != "" ]; then
    l1d_size="128B"
    l1i_size="128B"
    l2_size="8KiB"
    l3_size="1KiB"
    l1d_assoc=1
    l1i_assoc=1
    l2_assoc=4
    l3_assoc=8
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
    DMT=False
    DCT=False
    HNF_TBE=32
    SNF_TBE=32
    SEQ_TBE=32
    TRANS=4
    MultiCoreAddrMode=True
    NETWORK="simple"
    SNOOP_FILTER_SIZE=2
    SNOOP_FILTER_ASSOC=1
    DEBUGFLAGS=RubyCHIDebugStr5,RubyGenerated,SeqMemLatTest

    WKSETLIST=(2048)
    NUM_CPU_SET=(4)

    for NUMCPUS in ${NUM_CPU_SET[@]}; do
      for WKSET in ${WKSETLIST[@]}; do
        OUTPUT_PREFIX="SnoopFilter_${NETWORK}"
        OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_LoadFactor${LoadFactor}" 
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
          --mem-test-type='bw_test_sf' \
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
          --num-producers=1
          
          grep -E 'hnf' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf.trace
          grep -E 'CacheEntry Victim Busy|SnoopFilter Victim Busy|CacheEntry Undergoing SFRepl' ${OUTPUT_DIR}/debug.hnf.trace > ${OUTPUT_DIR}/debug.filt.trace
        
        done
    done

    # for NUMCPUS in ${NUM_CPU_SET[@]}; do
    #     for WKSET in ${WKSETLIST[@]}; do
    #         OUTPUT_PREFIX="SnoopFilter_${NETWORK}"
    #         OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_LoadFactor${LoadFactor}" 
    #         grep -E 'system.cpu: Complete|system.cpu: Start' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.seqmemtest.trace
    #         ${PY3} DebugHNFTBEAlloc.py --input ${OUTPUT_DIR} --output ${OUTPUT_DIR}
    #     done
    # done
    
    # for NUMCPUS in ${NUM_CPU_SET[@]}; do
    #   for WKSET in ${WKSETLIST[@]}; do
    #     OUTPUT_PREFIX="SnoopFilter_${NETWORK}"
    #     OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_LoadFactor${LoadFactor}" 
    #     SNOOPFILTER_MISS_STATS="${OUTPUT_ROOT}/SnoopFilterMiss.txt"
    #     echo ${SNOOPFILTER_MISS_STATS}
    #     echo "NUMCPUS=${NUMCPUS},WS=${WKSET}" > ${SNOOPFILTER_MISS_STATS}
    #     grep -E 'system\.ruby\.hnf\.cntrl\.m_snoopfilter_*' ${OUTPUT_DIR}/stats.txt >> ${SNOOPFILTER_MISS_STATS}
    #     echo "---------------------------------------------" >> ${SNOOPFILTER_MISS_STATS}
    #   done
    # done
fi