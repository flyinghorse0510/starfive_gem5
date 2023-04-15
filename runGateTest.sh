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
   echo "r    Run Regression Tests. 1CPU. L1 and L2 Hit b/w and latency"
   echo "s    Run Regression Tests. multiple CPU LLC Hit b/w and latency"
   echo "t    Run Regression Tests. multiple CPU DDR Hit b/w and latency"
   echo
}

BUILD=""
GATETEST=""

while getopts "hbrst" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) L1L2HIT="yes"
           ;;
        s) L3HIT="yes"
           ;;
        t) DDR="yes"
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

TRANS=4
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/GateTest"
# PY3=$(which python3)
PY3=/home/arka.maity/anaconda3/bin/python3
DEBUG_FLAGS=SeqMemLatTest
DCT_CONFIGS=(False)
DMT_CONFIGS=(False)

# DDR Config parameters
NUM_MEM=1
NUM_DDR_XP=2
NUM_DDR_Side=1
MultiCoreAddrMode=True
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

if [ "$L1L2HIT" != "" ]; then
l1d_size="4KiB"
l1i_size="4KiB"
l2_size="8KiB"
l3_size="1KiB"
l1d_assoc=4
l1i_assoc=4
l2_assoc=8
l3_assoc=8
NUM_LLC=16
SEQ_TBE_SET=(1 32)
WKSETLIST=(2048 8192)
NUM_CPU_SET=(1) # For LLC and DDR bw tests, numcpus must be 16
LoadFactor=100 # Set it to large value to ameliorate the effect of cold caches

for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for SEQ_TBE in ${SEQ_TBE_SET[@]}; do
          # Latency Tests
          OUTPUT_PREFIX="L1L2_${NETWORK}"
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_DCT${DCT}_SEQ${SEQ_TBE}_LoadFactor${LoadFactor}" 
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
wait

for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for SEQ_TBE in ${SEQ_TBE_SET[@]}; do
          OUTPUT_PREFIX="L1L2_${NETWORK}"
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_DCT${DCT}_SEQ${SEQ_TBE}_LoadFactor${LoadFactor}" 
          grep -E 'ReqBegin=LD|ReqDone=LD' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/simple.trace
          ${PY3} stats_parser_new.py \
             --input-dir ${OUTPUT_DIR} \
             --output ${OUTPUT_DIR}/stats.log \
             --num_cpu ${NUMCPUS} \
             --num_llc ${NUM_LLC} \
             --num_ddr ${NUM_MEM} \
             --trans ${TRANS} \
             --snf_tbe ${SNF_TBE} \
             --dmt ${DMT} \
             --linkwidth ${LINKWIDTH} \
             --injintv 1 \
             --seq_tbe ${SEQ_TBE} \
             --bench L1L2Hit \
             --working-set ${WKSET} >> "${OUTPUT_ROOT}/Summary.json"
          echo "," >> "${OUTPUT_ROOT}/Summary.json"
        done
      done
    done
  done
done

fi

if [ "$L3HIT" != "" ]; then
l1d_size="1KiB"
l1i_size="1KiB"
l2_size="2KiB"
l3_size="64KiB" #"32KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=4
l1i_assoc=4
l2_assoc=8
l3_assoc=8
NUM_LLC=16
WKSETLIST=(65536)
SEQ_TBE_SET=(32)
NUM_CPU_SET=(16) # For LLC and DDR bw tests, numcpus must be 16
LoadFactor=100 # Set it to large value to ameliorate the effect of cold caches

for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for SEQ_TBE in ${SEQ_TBE_SET[@]}; do
          OUTPUT_PREFIX="L3Hit_${NETWORK}"
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_DCT${DCT}_SEQ${SEQ_TBE}_LoadFactor${LoadFactor}" 
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
wait

for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for SEQ_TBE in ${SEQ_TBE_SET[@]}; do
          OUTPUT_PREFIX="L3Hit_${NETWORK}"
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_DCT${DCT}_SEQ${SEQ_TBE}_LoadFactor${LoadFactor}" 
          grep -E 'ReqBegin=LD|ReqDone=LD' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/simple.trace
          ${PY3} stats_parser_new.py \
             --input-dir ${OUTPUT_DIR} \
             --output ${OUTPUT_DIR}/stats.log \
             --num_cpu ${NUMCPUS} \
             --num_llc ${NUM_LLC} \
             --num_ddr ${NUM_MEM} \
             --trans ${TRANS} \
             --snf_tbe ${SNF_TBE} \
             --dmt ${DMT} \
             --linkwidth ${LINKWIDTH} \
             --injintv 1 \
             --seq_tbe ${SEQ_TBE} \
             --bench L3Hit \
             --working-set ${WKSET} >> "${OUTPUT_ROOT}/Summary.json"
          echo "," >> "${OUTPUT_ROOT}/Summary.json"
        done
      done
    done
  done
done

fi


if [ "$DDR" != "" ]; then
l1d_size="4KiB"
l1i_size="4KiB"
l2_size="8KiB"
l3_size="4KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16
WKSETLIST=(524288)
NUM_CPU_SET=(16) # For LLC and DDR bw tests, numcpus must be 16
LoadFactor=10
SEQ_TBE_SET=(1 32)
NUM_MEM=4
NUM_DDR_XP=4
NUM_DDR_Side=2
MultiCoreAddrMode=True
XOR_ADDR_BITS=4
OUTPUT_PREFIX="DDR_${NETWORK}"

for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for SEQ_TBE in ${SEQ_TBE_SET[@]}; do
          # Latency Tests
          OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_DCT${DCT}_SEQ${SEQ_TBE}_LoadFactor${LoadFactor}"
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}" 
          echo "GateTest Started: ${OUTPUT_BASE}"
          mkdir -p ${OUTPUT_DIR}
          set > ${OUTPUT_DIR}/Variables.txt
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
            --addr-intrlvd-or-tiled=$MultiCoreAddrMode \
            --xor-addr-bits=${XOR_ADDR_BITS} \
            --disable-gclk-set \
            --enable-DMT=${DMT} \
            --enable-DCT=${DCT} \
            --num-HNF-TBE=${HNF_TBE}  \
            --num-SNF-TBE=${SNF_TBE}  \
            --sequencer-outstanding-requests=${SEQ_TBE} \
            --num_trans_per_cycle_llc=${TRANS} \
            --num-cpus=${NUMCPUS} \
            --num-dmas=0 \
            --inj-interval=1 \
            --num-producers=1 > ${OUTPUT_DIR}/cmd.log 2>&1 &
        done
      done
    done
  done
done
wait

echo "WS,NUM_CPUS,SEQ_TBE,NUM_DDR,RETRY_ACKS,HNF_MISSRATE,BW" > "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats.csv"
for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for SEQ_TBE in ${SEQ_TBE_SET[@]}; do
          OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_DMT${DMT}_DCT${DCT}_SEQ${SEQ_TBE}_LoadFactor${LoadFactor}" 
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}" 
          echo "GateTest Parsing: ${OUTPUT_BASE}"
          ${PY3} stats_parser_bw.py \
             --input-dir ${OUTPUT_DIR} \
             --output ${OUTPUT_DIR}/stats.txt \
             --num_cpu ${NUMCPUS} \
             --num_llc ${NUM_LLC} \
             --num_ddr ${NUM_MEM} \
             --trans ${TRANS} \
             --snf_tbe ${SNF_TBE} \
             --dmt ${DMT} \
             --linkwidth ${LINKWIDTH} \
             --injintv 1 \
             --seq_tbe ${SEQ_TBE} \
             --bench DDR \
             --working-set ${WKSET} \
             --dump_file "${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats.csv"
        done
      done
    done
  done
done

fi