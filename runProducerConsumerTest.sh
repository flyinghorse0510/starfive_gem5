#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|h|a]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     Run1 (MemTest)."
   echo "a     Analyze/Grep"
   echo
}

BUILD=""
RUN=""
ANALYSIS=""

while getopts "hbra" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) RUN1="yes"
           ;;
        a) ANALYSIS="yes"
           ;;
    esac
done

export WORKSPACE="$(pwd)/output"
export GEM5_DIR=$(pwd)
export ISA="RISCV"
export CCPROT="CHI"

buildType="gem5.opt"
l1d_size="32KiB"
l1i_size="32KiB"
l2_size="256KiB"
l3_size="1024KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=2
l1i_assoc=2
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NETWORK="simple" #"garnet" #"simple"

DCT_CONFIGS=(True) #(True False)
NUM_CPU_SET=(4) #(2 4 8 16)
NUM_PROD_SET=(2) #(1 2 4 8)

WKSETLIST=(1024) #(1024 8192 32768 131072 262144 524288)
NUM_MEM=1

DEBUG_FLAGS=ProdConsMemLatTest
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/C2C_T"
OUTPUT_PREFIX="PRODCONS_BW"

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${buildType} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN1" != "" ]; then
  mkdir -p $OUTPUT_DIR
  for DCT in ${DCT_CONFIGS[@]}; do
    for NUM_PROD in ${NUM_PROD_SET[@]}; do
      for NUMCPUS in ${NUM_CPU_SET[@]}; do
        if [[ $NUMCPUS -gt $NUM_PROD ]]; then
          for WKSET in ${WKSETLIST[@]}; do
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_Prod${NUM_PROD}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}"
            mkdir -p $OUTPUT_DIR
            $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
               --debug-flags=$DEBUG_FLAGS --debug-file=debug.trace \
               -d $OUTPUT_DIR \
               ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
               --num-dirs=${NUM_MEM} \
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
               --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
               --ruby \
               --maxloads=10 \
               --mem-size="16GB" \
               --size-ws=${WKSET} \
               --mem-type=DDR4_3200_8x8 \
               --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
               --mem-test-type='prod_cons_test' \
               --disable-gclk-set \
               --enable-DMT=False \
               --enable-DCT=${DCT} \
               --num_trans_per_cycle_llc=1 \
               --num-cpus=${NUMCPUS} \
               --num-producers=${NUM_PROD} \
               --addr-intrlvd-or-tiled=True
          done
        fi
      done
      # wait
    done
  done
fi


# if [ "$ANALYSIS" != "" ]; then
#     for DMT in ${DMT_Config[@]}; do
#        for NUMCPUS in ${NUM_PROD_SET[@]}; do
#             for ADDRGEN in ${ADDR_GEN_CONFIG[@]}; do

#               OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_TRANS${TRANS}_ADDRGEN${ADDRGEN}"
#               statsfile=$OUTPUT_DIR/stats.txt
#               OUTPUT_FILE="${OUTPUT_ROOT}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_TRANS${TRANS}_ADDRGEN${ADDRGEN}.csv"
#               grep "simTicks" ${statsfile} > ${OUTPUT_FILE}
#               # grep "cache.m_demand_hits" ${statsfile} | grep "l2" >> ${OUTPUT_FILE}
#               # grep "cache.m_demand_accesses" ${statsfile} | grep "l2" >> ${OUTPUT_FILE}
#               # grep "cache.m_demand_hits" ${statsfile} | grep "hnf" >> ${OUTPUT_FILE}
#               # grep "cache.m_demand_accesses" ${statsfile} | grep "hnf" >> ${OUTPUT_FILE}
#               # grep "cntrl.snpOut.m_msg_count" ${statsfile} | grep "hnf" >> ${OUTPUT_FILE}
#               # grep "inTransLatHist" ${statsfile} | grep "\:\:total"  | grep -E "cpu[0-9]+\.l2" >> ${OUTPUT_FILE}
#               # echo "" >> ${OUTPUT_FILE}
#               # grep "inTransLatHist" ${statsfile} | grep "\:\:total"  | grep -E "hnf" >> ${OUTPUT_FILE}
#             done
#         done
#     done
# fi
