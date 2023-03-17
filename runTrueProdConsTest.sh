#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|h|t]"
   echo "options:"
   echo "h     Print this Help"
   echo "b     Build"
   echo "t     Run migratory test"
   echo "r     Run true producer consumer test"
   echo
}

BUILD=""
TEST1=""
TEST2=""
while getopts "hbrt" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        t) TEST1="yes"
           ;;
        r) TEST2="yes"
           ;;
    esac
done

export WORKSPACE="$(pwd)/output"
export GEM5_DIR=$(pwd)
export ISA="RISCV"
export CCPROT="CHI"

buildType="gem5.opt"
l1d_size="2KiB"
l1i_size="2KiB"
l2_size="8KiB"
l3_size="16KiB"
l1d_assoc=2
l1i_assoc=2
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NUM_MEM=1
DEBUG_FLAGS=TrueProdConsMemLatTest,RubyGenerated
DCT_CONFIGS=(False)
LINK_BW=16
INJ_INTERVAL=1
NETWORK="simple"
MAXNUMLOADS=100
ALLOW_SD_SET=(True)
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/TRUEPRODCONS_${NETWORK}"
PY3=/home/arka.maity/anaconda3/bin/python3
LOC_CONS=0
LOC_PROD=1

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${buildType} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

echo "[" > "${OUTPUT_ROOT}/Summary.json"

if [ "$TEST1" != "" ]; then
  echo "True ProdCons test"
  NUM_CPU_SET=(16)
  WKSET=4096
  OUTPUT_PREFIX="TRUEPRODCONS"
  
  
  for DCT in ${DCT_CONFIGS[@]}; do
    for NUM_CPUS in ${NUM_CPU_SET[@]}; do
      for ALLOWSD in ${ALLOW_SD_SET[@]}; do
      OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_ALLOWSD${ALLOWSD}_DCT${DCT}"
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
         --simple-link-bw-factor=${LINK_BW} \
         --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
         --mem-size="16GB" \
         --mem-type=DDR4_3200_8x8 \
         --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
         --mem-test-type='true_prod_cons' \
         --inj-interval=${INJ_INTERVAL} \
         --disable-gclk-set \
         --enable-DMT=False \
         --enable-DCT=${DCT} \
         --allow-SD=${ALLOWSD} \
         --num_trans_per_cycle_llc=4 \
         --addr-intrlvd-or-tiled=True \
         --bench-c2cbw-mode=True \
         --maxloads=${MAXNUMLOADS} \
         --size-ws=${WKSET} \
         --num-cpus=${NUM_CPUS} \
         --outstanding-req=100 \
         --sequencer-outstanding-requests=32 \
         --chs-1p1c \
         --chs-cons-id=${LOC_CONS} \
         --chs-prod-id=${LOC_PROD}
      done
    done
  done

  # for DCT in ${DCT_CONFIGS[@]}; do
  #   for NUM_CPUS in ${NUM_CPU_SET[@]}; do
  #     for ALLOWSD in ${ALLOW_SD_SET[@]}; do
  #     OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_ALLOWSD${ALLOWSD}_DCT${DCT}"
  #     ${PY3} processMigratoryTrace.py \
  #       --input=${OUTPUT_DIR} \
  #       --output=${OUTPUT_DIR} \
  #       --dct=${DCT} \
  #       --allow-SD=${ALLOWSD} \
  #       --bench='true_prod_cons' \
  #       --num-cpus=${NUM_CPUS} >> "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/Summary.json"
  #     echo "," >> "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/Summary.json"
  #     done
  #   done
  # done


fi

# if [ "$TEST2" != "" ]; then
#   echo "True ProdCons test"
#   NUM_CPU_SET=(16)
#   WKSET=4096
#   OUTPUT_PREFIX="TRUEPRODCONS_1PMC"
#   NUM_CPUS=16
#   NUM_CONSUMER_SET_CONFIGS=(2)
#   echo "[" > "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/Summary.json"
  
#   for DCT in ${DCT_CONFIGS[@]}; do
#     for NUM_CONS in ${NUM_CONSUMER_SET_CONFIGS[@]}; do
#       for ALLOWSD in ${ALLOW_SD_SET[@]}; do
#           OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_ALLOWSD${ALLOWSD}_DCT${DCT}"
#           echo $OUTPUT_DIR
#           mkdir -p $OUTPUT_DIR
#           $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
#               --debug-flags=$DEBUG_FLAGS --debug-file=debug.trace \
#               -d $OUTPUT_DIR \
#               ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
#               --ruby \
#               --num-dirs=${NUM_MEM} \
#               --num-l3caches=${NUM_LLC} \
#               --l1d_size=${l1d_size} \
#               --l1i_size=${l1i_size} \
#               --l2_size=${l2_size} \
#               --l3_size=${l3_size} \
#               --l1d_assoc=${l1d_assoc} \
#               --l1i_assoc=${l1i_assoc} \
#               --l2_assoc=${l2_assoc} \
#               --l3_assoc=${l3_assoc} \
#               --network=${NETWORK} \
#               --topology=CustomMesh \
#               --simple-physical-channels \
#               --simple-link-bw-factor=${LINK_BW} \
#               --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
#               --mem-size="16GB" \
#               --mem-type=DDR4_3200_8x8 \
#               --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
#               --mem-test-type='true_prod_cons' \
#               --inj-interval=${INJ_INTERVAL} \
#               --disable-gclk-set \
#               --enable-DMT=False \
#               --enable-DCT=${DCT} \
#               --allow-SD=${ALLOWSD} \
#               --num_trans_per_cycle_llc=4 \
#               --addr-intrlvd-or-tiled=True \
#               --bench-c2cbw-mode=True \
#               --maxloads=${MAXNUMLOADS} \
#               --size-ws=${WKSET} \
#               --num-cpus=${NUM_CPUS} \
#               --outstanding-req=100 \
#               --sequencer-outstanding-requests=32 \
#               --chs-1pMc \
#               --chs-1p-MSharers=${NUM_CONS} \
#               --chs-prod-id=${LOC_PROD} &
#       done
#     done
#   done
#   wait

#   for DCT in ${DCT_CONFIGS[@]}; do
#     for NUM_CONS in ${NUM_CONSUMER_SET_CONFIGS[@]}; do
#       for ALLOWSD in ${ALLOW_SD_SET[@]}; do
#         OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_ALLOWSD${ALLOWSD}_DCT${DCT}"
#         ${PY3} processMigratoryTrace.py \
#           --input=${OUTPUT_DIR} \
#           --output=${OUTPUT_DIR} \
#           --dct=${DCT} \
#           --allow-SD=${ALLOWSD} \
#           --bench='true_prod_cons' \
#           --num-cpus=${NUM_CPUS} >> "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/Summary.json"
#         echo "," >> "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/Summary.json"
#       done
#     done
#   done

# fi

# head -n -1 ${OUTPUT_ROOT}/Summary.json > ${OUTPUT_ROOT}/Summary2.json # Remove the last comma
# echo "]" >> ${OUTPUT_ROOT}/Summary2.json
# ${PY3} getCsvFromJson.py \
#        --input=${OUTPUT_ROOT}/Summary2.json \
#        --output=${OUTPUT_ROOT}/Summary.csv
# rm ${OUTPUT_ROOT}/Summary2.json ${OUTPUT_ROOT}/Summary.json