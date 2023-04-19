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

while getopts "hbrstp" options; do
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
        p)
         STATS="yes"
         echo "Debug txn parser"
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
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/DDR"
# PY3=$(which python3)
PY3=/home/arka.maity/anaconda3/bin/python3
DEBUG_FLAGS=SeqMemLatTest
DEBUG_FLAGS=TxnTrace
DEBUG_FLAGS=NIDequeue,TxnTrace
DCT_CONFIGS=(False)
DMT_CONFIGS=(True)

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
NETWORK="garnet"
LINK_BW=16

# Garnet related parameters
LINK_LAT=1
ROUTER_LAT=1
VC_PER_VNET=2
LINKWIDTH=256
PHYVNET=True #True #False
INJ_INTV_SET=(2 4 8 16 20 24 32)
INJ_INTV_SET=(1)


if [ "$DDR" != "" ]; then
#
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
NUM_CPU_SET=(1) # For LLC and DDR bw tests, numcpus must be 16
LoadFactor=1
NUM_MEM_SET=(4)
NUM_DDR_XP=4
NUM_DDR_Side=2
INJ_INTV_SET=(1)
MultiCoreAddrMode=True
BUFFER_SIZE_SET=(4)
HNF_TBE=32
SNF_TBE=64
SEQ_TBE_CONFIG_SET=(64)
DMT_CONFIGS=(True)
NETWORK_CONFIG_SET=("simple" "garnet")
VC_PER_VNET_SET=(4)
LINKWIDTH=(256)
INJ_INTV=1
OUTPUT_PREFIX="DEBUG_THROTTLE"

for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for NETWORK in ${NETWORK_CONFIG_SET[@]}; do
          for NUM_MEM in ${NUM_MEM_SET[@]}; do
            for VC_PER_VNET in ${VC_PER_VNET_SET[@]}; do
              for BUFFER_SIZE in ${BUFFER_SIZE_SET[@]}; do
                for SEQ_TBE in ${SEQ_TBE_CONFIG_SET[@]}; do
                  # Latency Tests
                  OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_Network${NETWORK}_DMT${DMT}_DCT${DCT}_BUF${BUFFER_SIZE}_VCVNET${VC_PER_VNET}_NumMem${NUM_MEM}_SeqTBE${SEQ_TBE}"
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
                    --simple-ext-link-bw-factor=32 \
                    --simple-int-link-bw-factor=32 \
                    --simple-physical-channels \
                    --link-width-bits=${LINKWIDTH} \
                    --vcs-per-vnet=${VC_PER_VNET} \
                    --buffer-size=${BUFFER_SIZE} \
                    --link-latency=${LINK_LAT} \
                    --router-latency=${ROUTER_LAT} \
                    --topology=CustomMesh \
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
                    --inj-interval=${INJ_INTV} \
                    --num-producers=1  > ${OUTPUT_DIR}/cmd.log 2>&1 &
                done
              done
            done 
          done
        done
      done
    done
  done
done
wait

echo "WS,NUM_CPUS,SeqTBE,NumMem,NWModel,BW,AccLat" > ${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats_collate.csv
for NUMCPUS in ${NUM_CPU_SET[@]}; do
  for WKSET in ${WKSETLIST[@]}; do
    for DMT in ${DMT_CONFIGS[@]}; do
      for DCT in ${DCT_CONFIGS[@]}; do
        for NETWORK in ${NETWORK_CONFIG_SET[@]}; do
          for NUM_MEM in ${NUM_MEM_SET[@]}; do
            for VC_PER_VNET in ${VC_PER_VNET_SET[@]}; do
              for BUFFER_SIZE in ${BUFFER_SIZE_SET[@]}; do
                for SEQ_TBE in ${SEQ_TBE_CONFIG_SET[@]}; do
                  OUTPUT_BASE="WS${WKSET}_Core${NUMCPUS}_Network${NETWORK}_DMT${DMT}_DCT${DCT}_BUF${BUFFER_SIZE}_VCVNET${VC_PER_VNET}_NumMem${NUM_MEM}_SeqTBE${SEQ_TBE}"
                  OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/${OUTPUT_BASE}"
                  echo "GateTest Parsing: ${OUTPUT_BASE}"
                  ${PY3} stats_parser_simple.py \
                    --working-set=$WKSET \
                    --num_cpus=$NUMCPUS \
                    --stats_file="$OUTPUT_DIR/stats.txt" \
                    --nw_model=$NETWORK \
                    --num_mem=$NUM_MEM \
                    --seq_tbe=${SEQ_TBE} \
                    --collated_outfile="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/stats_collate.csv"
                  ${PY3} parse_txn.py \
                    --working-set=$WKSET \
                    --num_cpus=$NUMCPUS \
                    --trace_file="$OUTPUT_DIR/debug.trace" \
                    --nw_model=$NETWORK \
                    --num_mem=$NUM_MEM \
                    --seq_tbe=${SEQ_TBE} \
                    --outfile="$OUTPUT_DIR/dequeue_rate_$NETWORK.csv" \
                    --outfile2="$OUTPUT_DIR/enqueue_rate_$NETWORK.csv" \
                    --parse-l2
                done
              done
            done 
          done
        done
      done
    done
  done
done

fi

if [ "$STATS" != "" ]; then
  ${PY3} parse_txn.py \
    --working-set=500 \
    --num_cpus=1 \
    --trace_file="none" \
    --nw_model=garnet \
    --num_mem=1 \
    --seq_tbe=32 \
    --outfile="none" \
    --test
fi