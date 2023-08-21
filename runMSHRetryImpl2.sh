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
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MSHRRetryModelling"
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
    # L3_SIZE_CONFIG=(1024) # Sizes in KiB ("16KiB" "32KiB" "64KiB" "238KiB")
    l3_size=1024
    l1d_assoc=1
    l1i_assoc=1
    l2_assoc=1
    l3_assoc=4
    NUM_LLC=16
    CONFIG_NUMCPUS=(1 4 8 16)
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
    OUTPUT_PREFIX="MSHRetryImpl05_ArchExploration"
    XOR_ADDR_BITS=4
    RANDOMIZE_ACC=False
    BLOCK_STRIDE_BITS=0
    SNOOP_FILTER_ASSOC=8
    SNOOP_FILTER_SIZE=256
    PART_TBE=False
    CHI_DATA_WIDTH=64
    NUM_MEM=4
    NUM_DDR_XP=4
    NUM_DDR_Side=2
    BUFFER_SIZE=4
    SNF_TBE=32
    PART_RATIO='1-1'
    RNF_TBE=32
    CONFIG_BENCHNAME=("bw_test_sf" "memcpy_test")
    CONFIG_SLOTS_BLOCKED_BY_SET=(False)
    ACCEPTED_BUFFER_MAX_DEQ_RATE_CONFIG_SET=(0)
    SLOTS_BLOCKED_BY_SET=False
    CONFIG_DECOUPLED_REQ_ALLOC=(True False)
    IDEAL_SNOOP_FILTER=True
    CONFIG_READ_WRITE_RATIO=('1-0')
    CONFIG_HNF_TBE=(2 4 8 16 32)
    # CONFIG_HNF_TBE=(32)


    for DECOUPLED_REQ_ALLOC in ${CONFIG_DECOUPLED_REQ_ALLOC[@]}; do
        if [ "$DECOUPLED_REQ_ALLOC" == "True" ] ; then
            CONFIG_NUM_ACCEPTED_ENTRIES=(2 4 8 16)
        else
            CONFIG_NUM_ACCEPTED_ENTRIES=(16)
        fi
        for NUM_ACCEPTED_ENTRIES in ${CONFIG_NUM_ACCEPTED_ENTRIES[@]}; do
            for HNF_TBE in ${CONFIG_HNF_TBE[@]}; do
                for NUMCPUS in ${CONFIG_NUMCPUS[@]}; do
                    for BENCHMARK in ${CONFIG_BENCHNAME[@]}; do
                        for READ_WRITE_RATIO in ${CONFIG_READ_WRITE_RATIO[@]}; do
                            for ACCEPTED_BUFFER_MAX_DEQ_RATE in ${ACCEPTED_BUFFER_MAX_DEQ_RATE_CONFIG_SET[@]}; do
			                    WKSET=$((${NUM_LLC}*${l3_size}*1024*2))
                                L3_SIZE_KB="${l3_size}KiB"
                                OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_HNFTBE${HNF_TBE}_MSHRDecoupledReqAlloc${DECOUPLED_REQ_ALLOC}_NumAcceptedEntries${NUM_ACCEPTED_ENTRIES}_Bench_${BENCHMARK}"
                                OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
                                echo "GateTest Started: ${OUTPUT_BASE}"
                                mkdir -p ${OUTPUT_DIR}
                                set > ${OUTPUT_DIR}/Variables.txt
                                $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
                                    --debug-flags=$DEBUGFLAGS \
                                    --debug-file=debug.trace \
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
                                    --l3_size=${L3_SIZE_KB} \
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
                                    --mem-test-type=$BENCHMARK \
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
                                    --chi-buffer-depth=16 \
                                    --chi-buffer-max-deq-rate=1 \
                                    --accepted_buffer_max_deq_rate=${ACCEPTED_BUFFER_MAX_DEQ_RATE} \
                                    --decoupled_req_alloc=${DECOUPLED_REQ_ALLOC} \
                                    --num_accepted_entries=${NUM_ACCEPTED_ENTRIES} \
                                    --num-producers=1 > ${OUTPUT_DIR}/cmd.log 2>&1 &
                            done
                        done
                    done
                done
            done
            wait
            echo "------------------------------------------------"
        done
    done
    
    ${PY3} stats_parser.py --root-dir ${OUTPUT_ROOT}/${OUTPUT_PREFIX} \
                           --output-file ${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats.csv

fi