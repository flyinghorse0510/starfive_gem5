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
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MSHRAllocTest"
PY3=/home/arka.maity/anaconda3/bin/python3

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${BUILDTYPE} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$GATETEST" != "" ]; then
    l1d_size="4KiB"
    l1i_size="4KiB"
    l2_size="8KiB"
    l3_size="4KiB" #"16KiB" #"1024KiB" #"256KiB"
    l1d_assoc=8
    l1i_assoc=8
    l2_assoc=8
    l3_assoc=16
    NUM_LLC=16
    LoadFactor=10
    NUM_MEM=4
    NUM_DDR_XP=4
    NUM_DDR_Side=2
    LINK_BW=16
    LINKWIDTH=320
    VC_PER_VNET=2
    LINK_LAT=1
    ROUTER_LAT=0
    DMT=False
    DCT=False
    SNF_TBE_CONFIG_SET=(64 128)
    SEQ_TBE=32
    TRANS=4
    MultiCoreAddrMode=True
    NETWORK="simple"
    # NETWORK="garnet"
    IDEAL_SNOOP_FILTER=False
    # DEBUGFLAGS=SeqMemLatTest,SimpleNetworkDebug
    DEBUGFLAGS=SeqMemLatTest
    OUTPUT_PREFIX="MSHRAlloc_${NETWORK}"
    WKSET=524288
    XOR_ADDR_BITS=4
    RANDOMIZE_ACC=False
    BLOCK_STRIDE_BITS=0
    # NUM_CPU_SET=(1 2 4 8 16)
    NUM_CPU_SET=(16)
    LLC_ASSOC_CONFIGSET=(16)
    SNOOP_FILTER_ASSOC=4
    SNOOP_FILTER_SIZE=256
    PART_TBE_CONFIG_SET=(False True)
    IDEAL_SNOOPFILTER_CONFIG_SET=(False)
    HNF_TBE_CONFIG_SET=(16 32)
    IDEAL_SNOOPFILTER=False
    CHI_DATA_WIDTH_CONFIGSET=(64)
    BUFFER_SIZE_CONFIGSET=(4)

    for NUMCPUS in ${NUM_CPU_SET[@]}; do
        for CHI_DATA_WIDTH in ${CHI_DATA_WIDTH_CONFIGSET[@]}; do
            for SNF_TBE in ${SNF_TBE_CONFIG_SET[@]}; do
                for PART_TBE in ${PART_TBE_CONFIG_SET[@]}; do
                    for BUFFER_SIZE in ${BUFFER_SIZE_CONFIGSET[@]}; do
                        PART_RATIO_CONFIG_SET=('1-1' '15-1' '13-3' '11-5' '9-7' '31-1' '25-7' '23-9' '19-13' '17-15' '1-15' '3-13' '5-11' '7-9' '1-31' '7-25' '9-23' '13-19' '15-17')
                        if [ "$PART_TBE" == "False" ]; then
                            PART_RATIO_CONFIG_SET=('1-1')
                            HNF_TBE_CONFIG_SET=(2 4 8 16 24 32)
                        fi
                        for HNF_TBE in ${HNF_TBE_CONFIG_SET[@]}; do
                            for PART_RATIO in ${PART_RATIO_CONFIG_SET[@]}; do
                                OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_HNFTBE${HNF_TBE}_SNFTBE${SNF_TBE}_CHIDATAWIDTH${CHI_DATA_WIDTH}_PARTTBE${PART_TBE}_PartRatio${PART_RATIO}_BuffSize${BUFFER_SIZE}"
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
                                  --num-producers=1 > ${OUTPUT_DIR}/cmd.log 2>&1 &
                            done
                        done
                        wait
                    done
                done
            done
        done
    done
    # wait

    echo "WS,NumCPUs,CHIDataWidth,BuffSize,ReqTBE,ReplTBE,PartitionTBE,ReqTBEUtil,ReplTBEUtil,HNFRetryAcks,SNFTBE,SNFTBEUtil,SNFRetryAcks,LLCMissRate,BW" > "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats.csv"
    for NUMCPUS in ${NUM_CPU_SET[@]}; do
        for CHI_DATA_WIDTH in ${CHI_DATA_WIDTH_CONFIGSET[@]}; do
            for SNF_TBE in ${SNF_TBE_CONFIG_SET[@]}; do
                for PART_TBE in ${PART_TBE_CONFIG_SET[@]}; do
                    for BUFFER_SIZE in ${BUFFER_SIZE_CONFIGSET[@]}; do
                        PART_RATIO_CONFIG_SET=('1-1' '15-1' '13-3' '11-5' '9-7' '31-1' '25-7' '23-9' '19-13' '17-15' '1-15' '3-13' '5-11' '7-9' '1-31' '7-25' '9-23' '13-19' '15-17')
                        if [ "$PART_TBE" == "False" ]; then
                            PART_RATIO_CONFIG_SET=('1-1')
                            HNF_TBE_CONFIG_SET=(2 4 8 16 24 32)
                        fi
                        for HNF_TBE in ${HNF_TBE_CONFIG_SET[@]}; do
                            for PART_RATIO in ${PART_RATIO_CONFIG_SET[@]}; do
                                OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_HNFTBE${HNF_TBE}_SNFTBE${SNF_TBE}_CHIDATAWIDTH${CHI_DATA_WIDTH}_PARTTBE${PART_TBE}_PartRatio${PART_RATIO}_BuffSize${BUFFER_SIZE}"
                                OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
                                echo "GateTest Parsing: ${OUTPUT_BASE}"
                                ${PY3} stats_parser_simple.py \
                                    --stats_file="${OUTPUT_DIR}/stats.txt" \
                                    --working-set=$WKSET \
                                    --chi-data-width=${CHI_DATA_WIDTH} \
                                    --buffer-size=${BUFFER_SIZE} \
                                    --num_cpus=$NUMCPUS \
                                    --num-dirs=${NUM_MEM} \
                                    --num-l3caches=$NUM_LLC \
                                    --part-TBEs=$PART_TBE \
                                    --hnf-tbe=$HNF_TBE \
                                    --config_file="${OUTPUT_DIR}/config.json" \
                                    --collated_outfile="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats.csv"
                            done
                        done
                    done
                done
            done
        done
    done

    ${PY3} AggAllStatsMSHR.py --collated_outfile="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats.csv"
fi
