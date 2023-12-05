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
CCPROT="CHID2D"
BUILDTYPE="gem5.debug"
OUTPUT_ROOT="${WORKSPACE}"
PY3=/home/arka.maity/anaconda3/bin/python3

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${BUILDTYPE} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi


if [ "$GATETEST" != "" ]; then
    l1d_size="128B"
    l1i_size="128B"
    l2_size="256B"
    l3_size="2KiB"
    l1d_assoc=1
    l1i_assoc=1
    l2_assoc=1
    l3_assoc=1
    SEQ_TBE=32
    LoadFactor=5
    NUM_DIE=2
    NUM_LLC=$(( 1*NUM_DIE ))
    NUM_MEM=$(( 1*NUM_DIE ))
    NUM_CPU=$(( 1*NUM_DIE ))
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
    DEBUGFLAGS=SeqMemLatTest,RubyGenerated,RubyCHIDebugStr5,RubyD2DStr5,RubyQueue,RubyNetwork
    OUTPUT_PREFIX="D2DTest_${NETWORK}"
    WKSETLIST=(1024)
    NUM_CPU_SET=(4)
    SNOOP_FILTER_SIZE_CONFIG_SET=(128)
    SNOOP_FILTER_ASSOC_CONFIG_SET=4
    XOR_ADDR_BITS_SET=(4)
    BLOCK_STRIDE_CONFIG_SET=(0)
    RANDOMIZE_ACC_CONFIG_SET=(False)

    for WKSET in ${WKSETLIST[@]}; do
        for SNOOP_FILTER_SIZE in ${SNOOP_FILTER_SIZE_CONFIG_SET[@]}; do
            for SNOOP_FILTER_ASSOC in ${SNOOP_FILTER_ASSOC_CONFIG_SET[@]}; do
                for BLOCK_STRIDE_BITS in ${BLOCK_STRIDE_CONFIG_SET[@]}; do
                    for XOR_ADDR_BITS in ${XOR_ADDR_BITS_SET[@]}; do
                        for RANDOMIZE_ACC in ${RANDOMIZE_ACC_CONFIG_SET[@]}; do
                            OUTPUT_BASE="WS${WKSET}_D${NUM_DIE}_Core${NUM_CPU}_L1${l1d_size}_L2${l2_size}_L3${l3_size}"
                            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
                            echo "GateTest Started: ${OUTPUT_BASE}"
                            mkdir -p ${OUTPUT_DIR}
                            set > ${OUTPUT_DIR}/Variables.txt
                            $GEM5_DIR/build/${ISA}_${CCPROT}/${BUILDTYPE} \
                              --debug-flags=$DEBUGFLAGS --debug-file=debug.trace \
                              -d $OUTPUT_DIR \
                              ${GEM5_DIR}/configs/example/d2d_ruby_mem_test.py \
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
                              --simple-int-link-bw-factor=${LINK_BW} \
                              --simple-ext-link-bw-factor=${LINK_BW} \
                              --link-width-bits=${LINKWIDTH} \
                              --vcs-per-vnet=${VC_PER_VNET} \
                              --link-latency=${LINK_LAT} \
                              --router-latency=${ROUTER_LAT} \
                              --topology=CustomMesh \
                              --simple-physical-channels \
                              --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh_D2D.py \
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
                              --num-cpus=${NUM_CPU} \
                              --inj-interval=1 \
                              --num-snoopfilter-entries=${SNOOP_FILTER_SIZE} \
                              --num-snoopfilter-assoc=${SNOOP_FILTER_ASSOC} \
                              --allow-infinite-SF-entries=${IDEAL_SNOOP_FILTER} \
                              --xor-addr-bits-hnf=${XOR_ADDR_BITS} \
                              --block-stride-bits=${BLOCK_STRIDE_BITS} \
                              --randomize-acc=${RANDOMIZE_ACC} \
                              --num-producers=1 \
                              --num-dies=${NUM_DIE} \
                              --outstanding-req=1
                            #   > ${OUTPUT_DIR}/cmd.log 2>&1 &
                        done
                    done
                done
            done
        done
    done
    # wait
fi