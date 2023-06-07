#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|h|t]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "t     run."
   echo
}

BUILD=""
RUN=""
WORKSPACE="$(pwd)/output"
GEM5_DIR=$(pwd)
ISA="RISCV"
CCPROT="CHI"
BUILDTYPE="gem5.opt"
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MSHRAllocTest"
PY3=/home/arka.maity/anaconda3/bin/python3

while getopts "hbt" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        t) RUN="yes"
    esac
done

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${BUILDTYPE} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN" != "" ]; then
    l1d_size="4KiB"
    l1i_size="4KiB"
    l2_size="8KiB"
    l3_size="4KiB"
    l1d_assoc=1
    l1i_assoc=1
    l2_assoc=1
    l3_assoc=4
    NUM_LLC=2
    NUMCPUS=16
    LoadFactor=10
    LINK_BW=16
    LINKWIDTH=320
    VC_PER_VNET=2
    LINK_LAT=1
    ROUTER_LAT=0
    DMT=False
    DCT=False
    SEQ_TBE=32
    TRANS=4
    MultiCoreAddrMode=True
    NETWORK="simple"
    DEBUGFLAGS=SeqMemLatTest
    OUTPUT_PREFIX="MSHR_TagConflicts"
    WKSET=524288
    XOR_ADDR_BITS=4
    RANDOMIZE_ACC=False
    BLOCK_STRIDE_BITS=0
    SNOOP_FILTER_ASSOC=4
    SNOOP_FILTER_SIZE=256
    IDEAL_SNOOP_FILTER=True
    PART_TBE=False
    HNF_TBE=32
    CHI_DATA_WIDTH=64
    NUM_MEM=4
    NUM_DDR_XP=4
    NUM_DDR_Side=2
    BUFFER_SIZE=4
    SNF_TBE=32
    READ_WRITE_RATIO='1-0'
    PART_RATIO='1-1'
    RNF_TBE=32
    SLOTS_BLOCKED_BY_SET=True

    OUTPUT_BASE='GDBTracing'
    OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
    echo "GateTest Started: ${OUTPUT_BASE}"
    mkdir -p ${OUTPUT_DIR}
    set > ${OUTPUT_DIR}/Variables.txt

    $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
        --debug-flags=$DEBUGFLAGS --debug-file=debug.trace \
        -d $OUTPUT_DIR \
        ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
        --chi-data-width=${CHI_DATA_WIDTH} \
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
        --buffer-size=${BUFFER_SIZE} \
        --link-width-bits=${LINKWIDTH} \
        --simple-ext-link-bw-factor=$(($LINKWIDTH/8)) \
        --simple-int-link-bw-factor=$(($LINKWIDTH/8)) \
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
        --num-HNF-TBE=${HNF_TBE} \
        --ratio-repl-req-TBE=$PART_RATIO \
        --part-TBEs=$PART_TBE \
        --num-SNF-TBE=${SNF_TBE}  \
        --sequencer-outstanding-requests=${SEQ_TBE} \
        --num_trans_per_cycle_llc=${TRANS} \
        --num-cpus=${NUMCPUS} \
        --num-dmas=0 \
        --inj-interval=1 \
        --num-snoopfilter-entries=${SNOOP_FILTER_SIZE} \
        --num-snoopfilter-assoc=${SNOOP_FILTER_ASSOC} \
        --allow-infinite-SF-entries=${IDEAL_SNOOP_FILTER} \
        --xor-addr-bits=${XOR_ADDR_BITS} \
        --block-stride-bits=${BLOCK_STRIDE_BITS} \
        --randomize-acc=${RANDOMIZE_ACC} \
        --ratio-read-write=${READ_WRITE_RATIO} \
        --slots_bocked_by_set=${SLOTS_BLOCKED_BY_SET} \
        --num-producers=1

    echo "Benchname,WS,NumCPUs,NumMem,NumLLC,ReadWriteRatio,RNFReqTBE,HNFReqTBE,HNFReplTBE,PartitionTBE,ReqTBEAvg,ReplTBEAvg,HNFRetryAcks,SNFTBE,SNFTBEUtil,SNFRetryAcks,LLCMissRate,BW" > "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats.csv"
    ${PY3} stats_parser_mshralloc.py \
        --stats_file="${OUTPUT_DIR}/stats.txt" \
        --working-set=$WKSET \
        --chi-data-width=${CHI_DATA_WIDTH} \
        --buffer-size=${BUFFER_SIZE} \
        --num_cpus=$NUMCPUS \
        --num-dirs=${NUM_MEM} \
        --num-l3caches=$NUM_LLC \
        --part-TBEs=$PART_TBE \
        --hnf-tbe=$HNF_TBE \
        --rnf-tbe=$RNF_TBE \
        --ratio-read-write=$READ_WRITE_RATIO \
        --config_file="${OUTPUT_DIR}/config.json" \
        --num-iters=$LoadFactor \
        --benchname='bw_test_sf' \
        --collated_outfile="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats.csv"
fi

# build/RISCV_CHI/mem/ruby/common/Address.cc:43
# build/RISCV_CHI/mem/ruby/structures/CacheMemory.hh:158 if m_cache_num_set_bits <= 0
# build/RISCV_CHI/mem/ruby/structures/TBEStorage.hh:308