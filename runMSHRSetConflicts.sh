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
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MSHRSetBlocking"
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


# --debug-start=383302001
# --debug-end=393302001

if [ "$RUN" != "" ]; then
    l1d_size="4KiB"
    l1i_size="4KiB"
    l2_size="8KiB"
    # l3_size="4KiB"
    L3_SIZE_CONFIG=(1024) # Sizes in KiB ("16KiB" "32KiB" "64KiB" "238KiB")
    # L3_SIZE_CONFIG=(64) # Sizes in KiB ("16KiB" "32KiB" "64KiB" "238KiB")
    l1d_assoc=1
    l1i_assoc=1
    l2_assoc=1
    l3_assoc=4
    NUM_LLC=16
    # NUMCPUS=16
    # CONFIG_NUMCPUS=(1 4 8 16)
    CONFIG_NUMCPUS=(16)
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
    DEBUGFLAGS=RubyResourceStalls,RubyTxnTrace,TxnTrace,RubyCHIDebugStr5,SimpleNetworkDebug
    # DEBUGFLAGS=SeqMemLatTest
    OUTPUT_PREFIX="MSHRSetConflicts3_LargeLLC_Deadlocks"
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
    
    PART_RATIO='1-1'
    RNF_TBE=32
    # CONFIG_BENCHNAME=("bw_test_sf" "memcpy_test")
    CONFIG_BENCHNAME=("bw_test_sf")
    CONFIG_SLOTS_BLOCKED_BY_SET=(False)

    # for l3_size in ${L3_SIZE_CONFIG[@]}; do
    #     for NUMCPUS in ${CONFIG_NUMCPUS[@]}; do
    #         for BENCHNAME in ${CONFIG_BENCHNAME[@]}; do
    #            for SLOTS_BLOCKED_BY_SET in ${CONFIG_SLOTS_BLOCKED_BY_SET[@]}; do
    #                 if [ $BENCHNAME == "bw_test_sf" ]; then
    #                     # CONFIG_READ_WRITE_RATIO=('1-0' '0-1')
    #                     CONFIG_READ_WRITE_RATIO=('0-1')
    #                 elif [ $BENCHNAME == "memcpy_test" ]; then
    #                     CONFIG_READ_WRITE_RATIO=('0-1')
    #                 fi
    #                 for READ_WRITE_RATIO in ${CONFIG_READ_WRITE_RATIO[@]}; do
	# 		            WKSET=$((${NUM_LLC}*${l3_size}*1024*2))
    #                     L3_SIZE_KB="${l3_size}KiB"
    #                     OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_L3${L3_SIZE_KB}_ReadWrite${READ_WRITE_RATIO}_MSHRSlotsBlockedBySet_${SLOTS_BLOCKED_BY_SET}_Bench_${BENCHNAME}"
    #                     OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
    #                     echo "GateTest Started: ${OUTPUT_BASE}"
    #                     mkdir -p ${OUTPUT_DIR}
    #                     set > ${OUTPUT_DIR}/Variables.txt
    #                     $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
    #                         --debug-flags=$DEBUGFLAGS \
    #                         --debug-file=debug.trace \
    #                         --debug-start=383302001 \
    #                         --debug-end=393302001 \
    #                         -d $OUTPUT_DIR \
    #                         ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
    #                         --chi-data-width=${CHI_DATA_WIDTH} \
    #                         --num-dirs=${NUM_MEM} \
    #                         --DDR-loc-num=${NUM_DDR_XP} \
    #                         --DDR-side-num=${NUM_DDR_Side} \
    #                         --num-l3caches=${NUM_LLC} \
    #                         --l1d_size=${l1d_size} \
    #                         --l1i_size=${l1i_size} \
    #                         --l2_size=${l2_size} \
    #                         --l3_size=${L3_SIZE_KB} \
    #                         --l1d_assoc=${l1d_assoc} \
    #                         --l1i_assoc=${l1i_assoc} \
    #                         --l2_assoc=${l2_assoc} \
    #                         --l3_assoc=${l3_assoc} \
    #                         --network=${NETWORK} \
    #                         --buffer-size=${BUFFER_SIZE} \
    #                         --link-width-bits=${LINKWIDTH} \
    #                         --simple-ext-link-bw-factor=$(($LINKWIDTH/8)) \
    #                         --simple-int-link-bw-factor=$(($LINKWIDTH/8)) \
    #                         --vcs-per-vnet=${VC_PER_VNET} \
    #                         --link-latency=${LINK_LAT} \
    #                         --router-latency=${ROUTER_LAT} \
    #                         --topology=CustomMesh \
    #                         --simple-physical-channels \
    #                         --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
    #                         --ruby \
    #                         --maxloads=${LoadFactor} \
    #                         --mem-size="16GB" \
    #                         --size-ws=${WKSET} \
    #                         --mem-type=DDR4_3200_8x8 \
    #                         --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
    #                         --mem-test-type=$BENCHNAME \
    #                         --addr-intrlvd-or-tiled=$MultiCoreAddrMode  \
    #                         --disable-gclk-set \
    #                         --enable-DMT=${DMT} \
    #                         --enable-DCT=${DCT} \
    #                         --num-HNF-TBE=${HNF_TBE} \
    #                         --ratio-repl-req-TBE=$PART_RATIO \
    #                         --part-TBEs=$PART_TBE \
    #                         --num-SNF-TBE=${SNF_TBE}  \
    #                         --sequencer-outstanding-requests=${SEQ_TBE} \
    #                         --num_trans_per_cycle_llc=${TRANS} \
    #                         --num-cpus=${NUMCPUS} \
    #                         --num-dmas=0 \
    #                         --inj-interval=1 \
    #                         --num-snoopfilter-entries=${SNOOP_FILTER_SIZE} \
    #                         --num-snoopfilter-assoc=${SNOOP_FILTER_ASSOC} \
    #                         --allow-infinite-SF-entries=${IDEAL_SNOOP_FILTER} \
    #                         --xor-addr-bits=${XOR_ADDR_BITS} \
    #                         --block-stride-bits=${BLOCK_STRIDE_BITS} \
    #                         --randomize-acc=${RANDOMIZE_ACC} \
    #                         --ratio-read-write=${READ_WRITE_RATIO} \
    #                         --slots_bocked_by_set=${SLOTS_BLOCKED_BY_SET} \
    #                         --chi-buffer-depth=16 \
    #                         --chi-buffer-max-deq-rate=1 \
    #                         --num-producers=1 > ${OUTPUT_DIR}/cmd.log 2>&1 &
    #                 done
    #             done
    #         done
    #     done
    #     wait
    #     echo "------------------------------------------------"
    # done

    for l3_size in ${L3_SIZE_CONFIG[@]}; do
        for NUMCPUS in ${CONFIG_NUMCPUS[@]}; do
            for BENCHNAME in ${CONFIG_BENCHNAME[@]}; do
               for SLOTS_BLOCKED_BY_SET in ${CONFIG_SLOTS_BLOCKED_BY_SET[@]}; do
                    if [ $BENCHNAME == "bw_test_sf" ]; then
                        # CONFIG_READ_WRITE_RATIO=('1-0' '0-1')
                        CONFIG_READ_WRITE_RATIO=('0-1')
                    elif [ $BENCHNAME == "memcpy_test" ]; then
                        CONFIG_READ_WRITE_RATIO=('0-1')
                    fi
                    for READ_WRITE_RATIO in ${CONFIG_READ_WRITE_RATIO[@]}; do
                        WKSET=$((${NUM_LLC}*${l3_size}*1024*2))
                        L3_SIZE_KB="${l3_size}KiB"
                        OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_L3${L3_SIZE_KB}_ReadWrite${READ_WRITE_RATIO}_MSHRSlotsBlockedBySet_${SLOTS_BLOCKED_BY_SET}_Bench_${BENCHNAME}"
                        OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
                        # for llc in $(seq 0 15); do
                        #     echo "grep filtering: ${OUTPUT_BASE}/${llc}"
                        #     if [ $llc -lt 10 ]; then
                        #         grep -E "system.ruby.hnf0${llc}.cntrl" ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf0${llc}.trace &
                        #     else 
                        #         grep -E "system.ruby.hnf${llc}.cntrl" ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf${llc}.trace &
                        #     fi
                        # done
                        # wait
                        ${PY3} parseRouterIncomingMsg.py \
                              --input ${OUTPUT_DIR}
                    done
                done
            done
        done
    done

    # for snf in $(seq 0 3); do
    #     grep -E "system.ruby.snf${snf}.cntrl" debug.trace > debug.snf${snf}.trace
    # done
fi