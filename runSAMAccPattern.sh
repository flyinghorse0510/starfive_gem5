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


if [ "$GATETEST" != "" ]; then
    l1d_size="1KiB"
    l1i_size="1KiB"
    l2_size="4KiB"
    l3_size="64KiB"
    l1d_assoc=1
    l1i_assoc=1
    l3_assoc=8
    NUM_LLC=4
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
    IDEAL_SNOOP_FILTER=False
    DEBUGFLAGS=SeqMemLatTest,TxnTrace,RubyGenerated
    OUTPUT_PREFIX="SeqMemLoadAddrPat_${NETWORK}"

    WKSETLIST=(262144) #(4096 8192 10240 12288 16384 65536)
    NUM_CPU_SET=(1)
    L2_ASSOC_CONFIG_SET=(1) #(1 2 4 8)
    SNOOP_FILTER_SIZE_CONFIG_SET=(128) #(64 128)
    SNOOP_FILTER_ASSOC_CONFIG_SET=8
    XOR_ADDR_BITS_SET=(1 2 4 8 12 16 20)
    BLOCK_STRIDE_CONFIG_SET=(0 1 2 4 8)
    RANDOMIZE_ACC_CONFIG_SET=(False True)

    # for NUMCPUS in ${NUM_CPU_SET[@]}; do
    #     for WKSET in ${WKSETLIST[@]}; do
    #         for l2_assoc in ${L2_ASSOC_CONFIG_SET[@]}; do
    #             for SNOOP_FILTER_SIZE in ${SNOOP_FILTER_SIZE_CONFIG_SET[@]}; do
    #                 for SNOOP_FILTER_ASSOC in ${SNOOP_FILTER_ASSOC_CONFIG_SET[@]}; do
    #                     for BLOCK_STRIDE_BITS in ${BLOCK_STRIDE_CONFIG_SET[@]}; do
    #                         for XOR_ADDR_BITS in ${XOR_ADDR_BITS_SET[@]}; do
    #                             for RANDOMIZE_ACC in ${RANDOMIZE_ACC_CONFIG_SET[@]}; do
    #                                 OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_NumLLC${NUM_LLC}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_L2Assoc${l2_assoc}_XorAddrBits${XOR_ADDR_BITS}_BlockStrideBits${BLOCK_STRIDE_BITS}_RandomizeAcc${RANDOMIZE_ACC}"
    #                                 OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
    #                                 echo "GateTest Started: ${OUTPUT_BASE}"
    #                                 mkdir -p ${OUTPUT_DIR}
    #                                 set > ${OUTPUT_DIR}/Variables.txt
    #                                 $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
    #                                   --debug-flags=$DEBUGFLAGS --debug-file=debug.trace \
    #                                   -d $OUTPUT_DIR \
    #                                   ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
    #                                   --num-dirs=${NUM_MEM} \
    #                                   --DDR-loc-num=${NUM_DDR_XP} \
    #                                   --DDR-side-num=${NUM_DDR_Side} \
    #                                   --num-l3caches=${NUM_LLC} \
    #                                   --l1d_size=${l1d_size} \
    #                                   --l1i_size=${l1i_size} \
    #                                   --l2_size=${l2_size} \
    #                                   --l3_size=${l3_size} \
    #                                   --l1d_assoc=${l1d_assoc} \
    #                                   --l1i_assoc=${l1i_assoc} \
    #                                   --l2_assoc=${l2_assoc} \
    #                                   --l3_assoc=${l3_assoc} \
    #                                   --network=${NETWORK} \
    #                                   --simple-link-bw-factor=${LINK_BW} \
    #                                   --link-width-bits=${LINKWIDTH} \
    #                                   --vcs-per-vnet=${VC_PER_VNET} \
    #                                   --link-latency=${LINK_LAT} \
    #                                   --router-latency=${ROUTER_LAT} \
    #                                   --topology=CustomMesh \
    #                                   --simple-physical-channels \
    #                                   --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
    #                                   --ruby \
    #                                   --maxloads=${LoadFactor} \
    #                                   --mem-size="16GB" \
    #                                   --size-ws=${WKSET} \
    #                                   --mem-type=DDR4_3200_8x8 \
    #                                   --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
    #                                   --mem-test-type='bw_test_sf' \
    #                                   --addr-intrlvd-or-tiled=$MultiCoreAddrMode  \
    #                                   --disable-gclk-set \
    #                                   --enable-DMT=${DMT} \
    #                                   --enable-DCT=${DCT} \
    #                                   --num-HNF-TBE=${HNF_TBE}  \
    #                                   --num-SNF-TBE=${SNF_TBE}  \
    #                                   --sequencer-outstanding-requests=${SEQ_TBE} \
    #                                   --num_trans_per_cycle_llc=${TRANS} \
    #                                   --num-cpus=${NUMCPUS} \
    #                                   --inj-interval=1 \
    #                                   --num-snoopfilter-entries=${SNOOP_FILTER_SIZE} \
    #                                   --num-snoopfilter-assoc=${SNOOP_FILTER_ASSOC} \
    #                                   --allow-infinite-SF-entries=${IDEAL_SNOOP_FILTER} \
    #                                   --xor-addr-bits=${XOR_ADDR_BITS} \
    #                                   --block-stride-bits=${BLOCK_STRIDE_BITS} \
    #                                   --randomize-acc=${RANDOMIZE_ACC} \
    #                                   --num-producers=1 > ${OUTPUT_DIR}/cmd.log 2>&1 &
    #                             done
    #                         done
    #                     done
    #                 done
    #             done
    #         done
    #     done
    # done
    # wait

    # for NUMCPUS in ${NUM_CPU_SET[@]}; do
    #     for WKSET in ${WKSETLIST[@]}; do
    #         for l2_assoc in ${L2_ASSOC_CONFIG_SET[@]}; do
    #             for SNOOP_FILTER_SIZE in ${SNOOP_FILTER_SIZE_CONFIG_SET[@]}; do
    #                 for SNOOP_FILTER_ASSOC in ${SNOOP_FILTER_ASSOC_CONFIG_SET[@]}; do
    #                     for BLOCK_STRIDE_BITS in ${BLOCK_STRIDE_CONFIG_SET[@]}; do
    #                         for XOR_ADDR_BITS in ${XOR_ADDR_BITS_SET[@]}; do
    #                             for RANDOMIZE_ACC in ${RANDOMIZE_ACC_CONFIG_SET[@]}; do
    #                                 OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_NumLLC${NUM_LLC}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_L2Assoc${l2_assoc}_XorAddrBits${XOR_ADDR_BITS}_BlockStrideBits${BLOCK_STRIDE_BITS}_RandomizeAcc${RANDOMIZE_ACC}"
    #                                 OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
    #                                 echo "GateTest Parsing: ${OUTPUT_BASE}"
    #                                 grep 'hnf' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/debug.hnf.trace
    #                                 # ${PY3} stats_parse_snoopfilter.py \
    #                                 #     --input="${OUTPUT_DIR}/stats.txt" \
    #                                 #     --output="${OUTPUT_DIR}/log.txt" \
    #                                 #     --num_cpu=${NUMCPUS} \
    #                                 #     --num_llc=${NUM_LLC} \
    #                                 #     --l2-assoc=${l2_assoc} \
    #                                 #     --working-set=${WKSET} \
    #                                 #     --summary-dump-file="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/SFMissRateSummary.txt" &
    #                                 ${PY3} processSnoopFilterHNFAccTrace.py \
    #                                     --input="${OUTPUT_DIR}/debug.trace" \
    #                                     --input-cfg="${OUTPUT_DIR}/config.json" \
    #                                     --output-hnf="${OUTPUT_DIR}/debug.hnf.csv" \
    #                                     --output-seq="${OUTPUT_DIR}/debug.seq.csv" \
    #                                     --output-dbg="${OUTPUT_DIR}/debug.hnfevents.csv" \
    #                                     --block-stride=${BLOCK_STRIDE_BITS} \
    #                                     --randomized-acc=${RANDOMIZE_ACC} \
    #                                     --num_llc=${NUM_LLC} \
    #                                     --xored-addr=${XOR_ADDR_BITS} \
    #                                     --num-snoopfilter-assoc=$SNOOP_FILTER_ASSOC \
    #                                     --num-snoopfilter-entries=$SNOOP_FILTER_SIZE &
    #                             done
    #                         done
    #                     done
    #                 done
    #             done
    #         done
    #     done
    # done
    # wait

    echo "BlockStride,RandomizedAcc,addr_xored,BW,LLCMissRate,AggSFMissRate,Pii" > "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/Summary.csv"
    for NUMCPUS in ${NUM_CPU_SET[@]}; do
        for WKSET in ${WKSETLIST[@]}; do
            for l2_assoc in ${L2_ASSOC_CONFIG_SET[@]}; do
                for SNOOP_FILTER_SIZE in ${SNOOP_FILTER_SIZE_CONFIG_SET[@]}; do
                    for SNOOP_FILTER_ASSOC in ${SNOOP_FILTER_ASSOC_CONFIG_SET[@]}; do
                        for BLOCK_STRIDE_BITS in ${BLOCK_STRIDE_CONFIG_SET[@]}; do
                            for XOR_ADDR_BITS in ${XOR_ADDR_BITS_SET[@]}; do
                                for RANDOMIZE_ACC in ${RANDOMIZE_ACC_CONFIG_SET[@]}; do
                                    OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_NumLLC${NUM_LLC}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_L2Assoc${l2_assoc}_XorAddrBits${XOR_ADDR_BITS}_BlockStrideBits${BLOCK_STRIDE_BITS}_RandomizeAcc${RANDOMIZE_ACC}"
                                    OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
                                    echo "GateTest Collating: ${OUTPUT_BASE}"
                                    ${PY3} processSnoopFilterHNFAccTrace.py \
                                        --input="${OUTPUT_DIR}/debug.trace" \
                                        --input-cfg="${OUTPUT_DIR}/config.json" \
                                        --output-hnf="${OUTPUT_DIR}/debug.hnf.csv" \
                                        --output-seq="${OUTPUT_DIR}/debug.seq.csv" \
                                        --output-dbg="${OUTPUT_DIR}/debug.hnfevents.csv" \
                                        --collated-outfile="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/Summary.csv" \
                                        --stats-file="${OUTPUT_DIR}/stats.txt" \
                                        --block-stride=${BLOCK_STRIDE_BITS} \
                                        --randomized-acc=${RANDOMIZE_ACC} \
                                        --num_llc=${NUM_LLC} \
                                        --xored-addr=${XOR_ADDR_BITS} \
                                        --num-snoopfilter-assoc=$SNOOP_FILTER_ASSOC \
                                        --num-snoopfilter-entries=$SNOOP_FILTER_SIZE
                                done
                            done
                        done
                    done
                done
            done
        done
    done
fi
