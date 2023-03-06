#!/bin/bash

##
# L1 Hit latency and bw
# L2 Hit latency and bw
# LLC Hit latency and bw
# DDR Hit latency and bw

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|h]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build"
   echo "r    Run Regression Tests"
   echo
}

BUILD=""
GATETEST=""

while getopts "hbr" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) GATETEST="yes"
           ;;
    esac
done

WORKSPACE="$(pwd)/output"
GEM5_DIR=$(pwd)
ISA="RISCV"
CCPROT="CHI"
buildType="gem5.opt"

if [ "$BUILD" != "" ]; then
  echo "Start building"
  scons build/${ISA}_${CCPROT}/${buildType} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

# Constant Parameters
l1d_size="4KiB"
l1i_size="4KiB"
l2_size="16KiB"
l3_size="32KiB"
l1d_assoc=4
l1i_assoc=4
l2_assoc=8
l3_assoc=16
NUM_LLC=16
TRANS=4
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/GateTest"
# PY3=$(which python3)
PY3=/home/arka.maity/anaconda3/bin/python3
DEBUG_FLAGS=TxnTrace,ProdConsMemLatTest,RubyGenerated
DCT_CONFIGS=(False)
DMT_CONFIGS=(False)
LoadFactor=100   # Set it to large value to ameliorate the effect of cold caches
# DDR Config parameters
NUM_MEM=1
NUM_DDR_XP=2
NUM_DDR_Side=1
MultiCoreAddrMode=True
SEQ_TBE_SET=(32)
MAX_MEMTEST_OUTSTANDING_SET=(1 32)
HNF_TBE=32
SNF_TBE=32

# Network Specific Parameters
NETWORK="simple"
LINK_BW=16

# Garnet related parameters
LINK_LAT=1
ROUTER_LAT=0
VC_PER_VNET=2
LINKWIDTH=256
PHYVNET=True #True #False

WKSETLIST=(2048 5120 10240 20480)
NUM_CPU_SET=(1) #(1 16) # For LLC and DDR bw tests, numcpus must be 16

if [ "$GATETEST" != "" ]; then

for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for SEQ_TBE in ${SEQ_TBE_SET[@]}; do
          for MAX_MEMTEST_OUTSTANDING in ${MAX_MEMTEST_OUTSTANDING_SET[@]}; do
          # Latency Tests
          OUTPUT_PREFIX="${NETWORK}"
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_DCT${DCT}_SEQ${SEQ_TBE}_MTOUTSTANDING${MAX_MEMTEST_OUTSTANDING}_LoadFactor${LoadFactor}" 
          $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
            --debug-flags=$DEBUG_FLAGS --debug-file=debug.trace \
            -d $OUTPUT_DIR \
            ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
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
            --simple-link-bw-factor=${LINK_BW} \
            --link-width-bits=${LINKWIDTH} \
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
            --mem-test-type='bw_test' \
            --max-outstanding-requests=${MAX_MEMTEST_OUTSTANDING} \
            --addr-intrlvd-or-tiled=$MultiCoreAddrMode  \
            --disable-gclk-set \
            --enable-DMT=${DMT} \
            --enable-DCT=${DCT} \
            --num-HNF-TBE=${HNF_TBE}  \
            --num-SNF-TBE=${SNF_TBE}  \
            --sequencer-outstanding-requests=${SEQ_TBE} \
            --num_trans_per_cycle_llc=${TRANS} \
            --num-cpus=${NUMCPUS} \
            --inj-interval=1 \
            --num-producers=1 &
          done
        done
      done
    done
  done
done
wait

echo "[" > "${OUTPUT_ROOT}/Summary.json"
for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for SEQ_TBE in ${SEQ_TBE_SET[@]}; do
          for MAX_MEMTEST_OUTSTANDING in ${MAX_MEMTEST_OUTSTANDING_SET[@]}; do
          OUTPUT_PREFIX="${NETWORK}"
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_DCT${DCT}_SEQ${SEQ_TBE}_MTOUTSTANDING${MAX_MEMTEST_OUTSTANDING}_LoadFactor${LoadFactor}" 
          ${PY3} stats_parser.py \
             --input ${OUTPUT_DIR}/stats.txt \
             --output ${OUTPUT_DIR}/stats.log\
             --num_cpu ${NUMCPUS} \
             --num_llc ${NUM_LLC} \
             --num_ddr ${NUM_MEM} \
             --trans ${TRANS} \
             --snf_tbe ${SNF_TBE} \
             --dmt ${DMT} \
             --linkwidth ${LINKWIDTH} \
             --injintv 1 \
             --max-outstanding-requests=${MAX_MEMTEST_OUTSTANDING} \
             --seq_tbe ${SEQ_TBE} \
             --working-set ${WKSET} >> "${OUTPUT_ROOT}/Summary.json"
          echo "," >> "${OUTPUT_ROOT}/Summary.json"
          done
        done
      done
    done
  done
done

head -n -1 ${OUTPUT_ROOT}/Summary.json > ${OUTPUT_ROOT}/Summary2.json # Remove the last comma
echo "]" >> ${OUTPUT_ROOT}/Summary2.json
${PY3} processProdCons.py \
       --input=${OUTPUT_ROOT}/Summary2.json \
       --output=${OUTPUT_ROOT}/Summary.csv
fi