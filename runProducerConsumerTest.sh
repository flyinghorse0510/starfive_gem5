#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|p|w|h|m|t]"
   echo "options:"
   echo "h     Print this Help"
   echo "b     Build"
   echo "p     Pingpong latency test"
   echo "w     Producer-Consumer C2C BW test"
   echo "m     Producer-Consumer C2C BW test. Multiple independent pairs"
   echo "t     Producer-Multiple Consumer C2C BW tests"
   echo
}

BUILD=""
PINGPONG=""
C2CBW=""
while getopts "hbpwmt" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        p) PINGPONG="yes"
           ;;
        w) C2CBW="yes"
           ;;
        m) MC2CBW="yes"
           ;;
        t) C2CMBW="yes"
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
l3_size="1024KiB"
l1d_assoc=2
l1i_assoc=2
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NUM_MEM=1
DEBUG_FLAGS=TxnTrace,ProdConsMemLatTest,RubyGenerated
DCT_CONFIGS=(True) #(False True)
LINK_BW_CONFIGS=(16)
INJ_INTERVAL_CONFIGS=(5 10) #(1 2 3 4 5 6 7 8 9 10 12 15 20 25 30 40 50)
NETWORK="simple"
MAXNUMLOADS=1
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/C2C_13_${NETWORK}"
PY3=/home/arka.maity/anaconda3/bin/python3

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${buildType} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

echo "[" > "${OUTPUT_ROOT}/Summary.json"

if [ "$C2CBW" != "" ]; then
  echo "1P1C BW test"
  NUM_CPUS=16
  CONSUMER_SET_CONFIGS=(1)
  PRODUCER_SET_CONFIGS=(0)
  WKSETLIST=(65536)
  OUTPUT_PREFIX="PRODCONS_1P1C_BW_INJRATE"
  
  for DCT in ${DCT_CONFIGS[@]}; do
    for LOC_PROD in ${PRODUCER_SET_CONFIGS[@]}; do
      for LOC_CONS in ${CONSUMER_SET_CONFIGS[@]}; do
        if [[ $LOC_PROD -ne $LOC_CONS ]]; then
          for WKSET in ${WKSETLIST[@]}; do
            for LINK_BW in ${LINK_BW_CONFIGS[@]}; do
              for INJ_INTERVAL in ${INJ_INTERVAL_CONFIGS[@]}; do
                OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_Prod${LOC_PROD}_Cons${LOC_CONS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_INJRATE_${INJ_INTERVAL}"
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
                   --mem-test-type='prod_cons_test' \
                   --inj-interval=${INJ_INTERVAL} \
                   --disable-gclk-set \
                   --enable-DMT=False \
                   --enable-DCT=${DCT} \
                   --num_trans_per_cycle_llc=4 \
                   --addr-intrlvd-or-tiled=True \
                   --bench-c2cbw-mode=True \
                   --maxloads=${MAXNUMLOADS} \
                   --size-ws=${WKSET} \
                   --num-cpus=${NUM_CPUS} \
                   --sequencer-outstanding-requests=32 \
                   --chs-1p1c \
                   --chs-cons-id=${LOC_CONS} \
                   --chs-prod-id=${LOC_PROD} &
              done
            done
          done
        fi
      done
    done
  done
  wait


  for DCT in ${DCT_CONFIGS[@]}; do
    for LOC_PROD in ${PRODUCER_SET_CONFIGS[@]}; do
      for LOC_CONS in ${CONSUMER_SET_CONFIGS[@]}; do
        if [[ $LOC_PROD -ne $LOC_CONS ]]; then
          for WKSET in ${WKSETLIST[@]}; do
            for LINK_BW in ${LINK_BW_CONFIGS[@]}; do
              for INJ_INTERVAL in ${INJ_INTERVAL_CONFIGS[@]}; do
                OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_Prod${LOC_PROD}_Cons${LOC_CONS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_INJRATE_${INJ_INTERVAL}"
                if [ -d ${OUTPUT_DIR} ]; then
                  grep -E 'ReqBegin=LD|ReqDone=LD' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/simple.trace 
                  ${PY3} ProdConsStatsParser.py \
                         --input=${OUTPUT_DIR} \
                         --output=${OUTPUT_DIR} \
                         --dct=${DCT} \
                         --link-bw=${LINK_BW} \
                         --inj-rate=${INJ_INTERVAL} \
                         --bench-name='chs-1p1c' \
                         --chs-cons-id=${LOC_CONS} \
                         --chs-prod-id=${LOC_PROD} >> "${OUTPUT_ROOT}/Summary.json"
                  echo "," >> "${OUTPUT_ROOT}/Summary.json"
                fi
              done
            done
          done
        fi
      done
    done
  done
fi

if [ "$C2CMBW" != "" ]; then
  echo "1PMC BW test"
  NUM_CPUS=16
  NUM_CONSUMER_SET_CONFIGS=(4)
  PRODUCER_SET_CONFIGS=(0)
  WKSETLIST=(65536)
  OUTPUT_PREFIX="PRODCONS_1PMC_BW_INJRATE"
  
  # for DCT in ${DCT_CONFIGS[@]}; do
  #   for LOC_PROD in ${PRODUCER_SET_CONFIGS[@]}; do
  #     for NUM_CONS in ${NUM_CONSUMER_SET_CONFIGS[@]}; do
  #         for WKSET in ${WKSETLIST[@]}; do
  #           for LINK_BW in ${LINK_BW_CONFIGS[@]}; do
  #             for INJ_INTERVAL in ${INJ_INTERVAL_CONFIGS[@]}; do
  #               OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_Prod${LOC_PROD}_NumCons${NUM_CONS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_INJRATE_${INJ_INTERVAL}"
  #               mkdir -p $OUTPUT_DIR
  #               $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
  #                  --debug-flags=$DEBUG_FLAGS --debug-file=debug.trace \
  #                  -d $OUTPUT_DIR \
  #                  ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
  #                  --ruby \
  #                  --num-dirs=${NUM_MEM} \
  #                  --num-l3caches=${NUM_LLC} \
  #                  --l1d_size=${l1d_size} \
  #                  --l1i_size=${l1i_size} \
  #                  --l2_size=${l2_size} \
  #                  --l3_size=${l3_size} \
  #                  --l1d_assoc=${l1d_assoc} \
  #                  --l1i_assoc=${l1i_assoc} \
  #                  --l2_assoc=${l2_assoc} \
  #                  --l3_assoc=${l3_assoc} \
  #                  --network=${NETWORK} \
  #                  --topology=CustomMesh \
  #                  --simple-link-bw-factor=${LINK_BW} \
  #                  --simple-physical-channels \
  #                  --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
  #                  --mem-size="16GB" \
  #                  --mem-type=DDR4_3200_8x8 \
  #                  --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
  #                  --mem-test-type='prod_cons_test' \
  #                  --inj-interval=${INJ_INTERVAL} \
  #                  --disable-gclk-set \
  #                  --enable-DMT=False \
  #                  --enable-DCT=${DCT} \
  #                  --num_trans_per_cycle_llc=4 \
  #                  --addr-intrlvd-or-tiled=True \
  #                  --bench-c2cbw-mode=True \
  #                  --maxloads=${MAXNUMLOADS} \
  #                  --size-ws=${WKSET} \
  #                  --num-cpus=${NUM_CPUS} \
  #                  --sequencer-outstanding-requests=32 \
  #                  --chs-1pMc \
  #                  --chs-1p-MSharers=${NUM_CONS} \
  #                  --chs-prod-id=${LOC_PROD} &
  #               done
  #           done
  #         done
  #     done
  #   done
  # done
  # wait

  for DCT in ${DCT_CONFIGS[@]}; do
    for LOC_PROD in ${PRODUCER_SET_CONFIGS[@]}; do
      for NUM_CONS in ${NUM_CONSUMER_SET_CONFIGS[@]}; do
        for WKSET in ${WKSETLIST[@]}; do
          for LINK_BW in ${LINK_BW_CONFIGS[@]}; do
            for INJ_INTERVAL in ${INJ_INTERVAL_CONFIGS[@]}; do
              OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_Prod${LOC_PROD}_NumCons${NUM_CONS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_INJRATE_${INJ_INTERVAL}"
              if [ -d ${OUTPUT_DIR} ]; then
                grep -E 'ReqBegin=LD|ReqDone=LD' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/simple.trace 
                grep -E 'system.ruby.hnf14' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/hnf14.trace 
                ${PY3} ProdConsStatsParser.py \
                             --input=${OUTPUT_DIR} \
                             --output=${OUTPUT_DIR} \
                             --dct=${DCT} \
                             --link-bw=${LINK_BW} \
                             --inj-rate=${INJ_INTERVAL} \
                             --bench-name='chs-1pMc' \
                             --chs-num-consumers=${NUM_CONS} # >> "${OUTPUT_ROOT}/Summary.json"
                # echo "," >> "${OUTPUT_ROOT}/Summary.json"
              fi
            done
          done
        done
      done
    done
  done
fi

if [ "$MC2CBW" != "" ]; then
  echo "multiple 1P1C BW test"
  NUM_CPUS=16
  NUM_PAIRS_CONFIG=(2 4 8)
  WKSETLIST=(65536)
  OUTPUT_PREFIX="PRODCONS_M1P1C_BW_INJRATE"
  
  for DCT in ${DCT_CONFIGS[@]}; do
    for NUM_PAIRS in ${NUM_PAIRS_CONFIG[@]}; do
      for WKSET in ${WKSETLIST[@]}; do
        for LINK_BW in ${LINK_BW_CONFIGS[@]}; do
          for INJ_INTERVAL in ${INJ_INTERVAL_CONFIGS[@]}; do
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_PCPairs${NUM_PAIRS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_INJRATE_${INJ_INTERVAL}"
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
               --mem-test-type='prod_cons_test' \
               --inj-interval=${INJ_INTERVAL} \
               --disable-gclk-set \
               --enable-DMT=False \
               --enable-DCT=${DCT} \
               --num_trans_per_cycle_llc=4 \
               --addr-intrlvd-or-tiled=True \
               --bench-c2cbw-mode=True \
               --maxloads=${MAXNUMLOADS} \
               --size-ws=${WKSET} \
               --num-cpus=${NUM_CPUS} \
               --sequencer-outstanding-requests=32 \
               --chs-1p1c-num-pairs=${NUM_PAIRS} &
          done
        done
      done
    done
  done
  wait

  for DCT in ${DCT_CONFIGS[@]}; do
    for NUM_PAIRS in ${NUM_PAIRS_CONFIG[@]}; do
      for WKSET in ${WKSETLIST[@]}; do
        for LINK_BW in ${LINK_BW_CONFIGS[@]}; do
          for INJ_INTERVAL in ${INJ_INTERVAL_CONFIGS[@]}; do
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_LINKBW${LINK_BW}_Core${NUM_CPUS}_PCPairs${NUM_PAIRS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_INJRATE_${INJ_INTERVAL}"
            if [ -d ${OUTPUT_DIR} ]; then
              grep -E 'ReqBegin=LD|ReqDone=LD' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/simple.trace 
              ${PY3} ProdConsStatsParser.py \
                     --input=${OUTPUT_DIR} \
                     --output=${OUTPUT_DIR} \
                     --dct=${DCT} \
                     --link-bw=${LINK_BW} \
                     --inj-rate=${INJ_INTERVAL} \
                     --bench-name='chs-m1p1c' \
                     --chs-num-pairs=${NUM_PAIRS} >> "${OUTPUT_ROOT}/Summary.json"
              echo "," >> "${OUTPUT_ROOT}/Summary.json"
            fi
          done
        done
      done
    done
  done
fi

# head -n -1 ${OUTPUT_ROOT}/Summary.json > ${OUTPUT_ROOT}/Summary2.json # Remove the last comma
# echo "]" >> ${OUTPUT_ROOT}/Summary2.json
# ${PY3} processProdCons.py \
#        --input=${OUTPUT_ROOT}/Summary2.json \
#        --output=${OUTPUT_ROOT}/Summary.csv
# rm ${OUTPUT_ROOT}/Summary2.json ${OUTPUT_ROOT}/Summary.json