#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|p|w|h]"
   echo "options:"
   echo "h     Print this Help"
   echo "b     Build"
   echo "p     Pingpong latency test"
   echo "w     Producer-Consumer C2C BW test"
   echo
}

BUILD=""
PINGPONG=""
C2CBW=""
while getopts "hbpw" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        p) PINGPONG="yes"
           ;;
        w) C2CBW="yes"
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
NUM_MEM=1
DEBUG_FLAGS=RubyGenerated,TxnTrace #RubyCHIDebugStr5,RubyGenerated
DCT_CONFIGS=(True) #(False True) #(True False)
NETWORK="simple"
LINKWIDTH=128 #(128 256)
VC_PER_VNET=4
ROUTER_LAT=1
LINK_LAT=1
MAXNUMLOADS=2
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/C2C_9_${NETWORK}"

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${buildType} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$PINGPONG" != "" ]; then
  echo "Pingpong latency test"
  NUM_CPUS=16
  CONSUMER_SET_CONFIGS=(0) #$(seq 0 $((${NUM_CPUS}-1))) #("1") #(2 4 8 16)
  PRODUCER_SET_CONFIGS=(2) #$(seq 0 $((${NUM_CPUS}-1))) #("0") #(1 2 4 8)
  WKSETLIST=(64) #(65536) #(1024 8192 32768 131072 262144 524288)
  OUTPUT_PREFIX="PRODCONS_PINGPONG"

  for DCT in ${DCT_CONFIGS[@]}; do
    for PRODUCER_SET in ${PRODUCER_SET_CONFIGS[@]}; do
      for CONSUMER_SET in ${CONSUMER_SET_CONFIGS[@]}; do
        if [[ $PRODUCER_SET -ne $CONSUMER_SET ]]; then
          for WKSET in ${WKSETLIST[@]}; do
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_Prod${PRODUCER_SET}_Cons${CONSUMER_SET}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}"
            echo $OUTPUT_DIR
            mkdir -p $OUTPUT_DIR
            $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
               --debug-flags=$DEBUG_FLAGS --debug-file=debug.trace \
               -d $OUTPUT_DIR \
               ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
               --ruby \
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
               --simple-physical-channels \
               --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
               --mem-size="16GB" \
               --mem-type=DDR4_3200_8x8 \
               --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
               --mem-test-type='prod_cons_test' \
               --disable-gclk-set \
               --enable-DMT=False \
               --enable-DCT=${DCT} \
               --num_trans_per_cycle_llc=4 \
               --addr-intrlvd-or-tiled=True \
               --bench-c2cbw-mode=False \
               --maxloads=${MAXNUMLOADS} \
               --size-ws=${WKSET} \
               --num-cpus=${NUM_CPUS} \
               --producers=${PRODUCER_SET} \
               --consumers=${CONSUMER_SET} &
          done
        fi
      done
      wait
    done
  done
fi

# if [ "$C2CBW" != "" ]; then
#   echo "Producer-Consumer C2C BW test"
#   NUM_CPUS=16
#   CONSUMER_SET_CONFIGS=(1 2 4 8) #$(seq 0 $((${NUM_CPUS}-1))) #("1") #(2 4 8 16)
#   PRODUCER_SET_CONFIGS=(1 2 4 8) #$(seq 0 $((${NUM_CPUS}-1))) #("0") #(1 2 4 8)
#   WKSETLIST=(1024 65536)
#   OUTPUT_PREFIX="PRODCONS_BW"
  
#   for DCT in ${DCT_CONFIGS[@]}; do
#     for PRODUCER_SET in ${PRODUCER_SET_CONFIGS[@]}; do
#       for CONSUMER_SET in ${CONSUMER_SET_CONFIGS[@]}; do
#         if [[ $(($PRODUCER_SET + $CONSUMER_SET)) -lt ${NUM_CPUS} ]]; then
#           for WKSET in ${WKSETLIST[@]}; do
#             OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_Prod${PRODUCER_SET}_Cons${CONSUMER_SET}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}"
#             echo $OUTPUT_DIR
#             mkdir -p $OUTPUT_DIR
#             $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
#                --debug-flags=$DEBUG_FLAGS --debug-file=debug.trace \
#                -d $OUTPUT_DIR \
#                ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
#                --ruby \
#                --num-dirs=${NUM_MEM} \
#                --num-l3caches=${NUM_LLC} \
#                --l1d_size=${l1d_size} \
#                --l1i_size=${l1i_size} \
#                --l2_size=${l2_size} \
#                --l3_size=${l3_size} \
#                --l1d_assoc=${l1d_assoc} \
#                --l1i_assoc=${l1i_assoc} \
#                --l2_assoc=${l2_assoc} \
#                --l3_assoc=${l3_assoc} \
#                --network=${NETWORK} \
#                --topology=CustomMesh \
#                --simple-physical-channels \
#                --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
#                --mem-size="16GB" \
#                --mem-type=DDR4_3200_8x8 \
#                --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
#                --mem-test-type='prod_cons_test' \
#                --disable-gclk-set \
#                --enable-DMT=False \
#                --enable-DCT=${DCT} \
#                --num_trans_per_cycle_llc=4 \
#                --addr-intrlvd-or-tiled=True \
#                --bench-c2cbw-mode=True \
#                --maxloads=${MAXNUMLOADS} \
#                --size-ws=${WKSET} \
#                --num-cpus=${NUM_CPUS} \
#                --num-producers=${PRODUCER_SET} \
#                --num-consumers=${CONSUMER_SET} &
#           done
#         fi
#       done
#       wait
#     done
#   done
# fi