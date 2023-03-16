#!/bin/bash

#command example: ./runMemTest_Scenarios.sh -t L2_Hit

#2023-02-17 18 19 23 

## IMPORTANT:
## to create checkpoint: ./run-arm-fs.sh -c REAL
## to restore from checkpoint: ./run-arm-fs.sh -r REAL
## important parameters:
## CHECKPNT_CPU : cpu model to create checkpoint
## RESTORE_CPU_SET : cpu models to run after restoring from checkpoint

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|h]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     Run1 (MemTest)."
   echo
}

export M5_PATH="/home/zhiang.li/arm/m5_path"
WORKSPACE="$(pwd)/output"
GEM5_DIR=$(pwd)
ISA="ARM"
CCPROT="CHI"
CHECKPNT_IDX="1"
CHECKPNT_CPU="NonCachingSimpleCPU"  # NonCachingSimpleCPU
RESTORE_CPU_SET=("TimingSimpleCPU")  # AtomicSimpleCPU

# BENCHMARK_NAMES=("blackscholes" "canneal" "facesim" "ferret" "fluidanimate" "freqmine" "streamcluster" "swaptions")
BENCHMARK_NAMES=("blackscholes" "canneal" "facesim" "ferret" "fluidanimate" "freqmine" "streamcluster" "swaptions")
BENCHMARK_SIZE="simsmall" # simmedium

buildType="gem5.fast"

while getopts "hbc:r:d:s:a:t:g:" options; do
    case $options in
       h) Help
          exit;;
       b) BUILD="yes"
           ;;
       c) CHECKPNT="yes"
          TEST=${OPTARG}
          CHECKPNT="yes"
          echo "CHECKPNTing FS simulation with '${OPTARG}' Test"
          ;;
       r) RESTORE="yes"
          TEST=${OPTARG}
          RESTORE="yes"
          echo "Restoring FS simulation with '${OPTARG}' Test"
          echo "Benchmarks: ${BENCHMARK_NAMES[*]}"
          ;;
       d) DIRRUN="yes"
          TEST=${OPTARG}
          DIRRUN="yes"
          echo "Directly run FS simulation with '${OPTARG}' Test"
          echo "Benchmarks: ${BENCHMARK_NAMES[*]}"
          ;;
       a) ANALYSIS="yes"
          TEST=${OPTARG}
          echo "Analyze results '${OPTARG}' argument"
          ;;
       t)
          echo ${OPTARG}
          TEST=${OPTARG}
          echo "Processing option 'c' with '${OPTARG}' argument"
          ;;
       s)
         STATS="yes"
         TEST=${OPTARG}
         echo "Running STATS parser"
         ;;
       g)
         GRAPH="yes"
         DEBUG_FLAGS=TxnLink
         TEST=${OPTARG}
         echo "Running link graphing, need to turn on TxnLink"
    esac
done

CHECKPNT_SCRIPT="${GEM5_DIR}/configs/boot/hack_back_ckpt.rcS"
PARSEC_SCRIPT_DIR="/home/zhiang.li/arm/m5_path/parsec_scripts"

#NOTE:
#1. To test latency need to set Sequencer maximal outstanding to 1
#

if [ "$TEST" == "L1_Hit" ]; then
echo $TEST

l1d_size="32KiB"
l1i_size="32KiB"
l2_size="64KiB"
l3_size="32KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NETWORK="simple" #"garnet" #"simple"

#Garnet configurations 
Router_Lat=1
Link_Lat_SET=(1 2)
Link_Width=128
VC_per_VNET=2

#

DMT_Config=(True False)
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
NUM_CPU_SET=(4 8 16) # = #2 #4 #16
WKSET=8192 #16384 #524288 #(32768) #
#NUM_MEM_SET=(1 2)
NUM_MEM=1
TRANS_SET=(1 2 4)
SNF_TBE_SET=(32 64)
HNF_TBE=32
NUM_LOAD_SET=(200)

#DEBUG_FLAGS=SeqMemLatTest,TxnTrace 
#DEBUG_FLAGS=SeqMemLatTest
DEBUG_FLAGS=PseudoInst
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MEMBW_MultCore_WorkSetAddressNoGap"
#OUTPUT_PREFIX="LLC_HIT_BW_MEM1_TestHNFTBE"
#OUTPUT_PREFIX="SysClkRubyClk2GHz_LLC_HIT_BW_MEM1_HNF${HNF_TBE}"
fi

if [ "$TEST" == "L2_Hit" ]; then
  echo "Test $TEST"

l1d_size="4KiB"
l1i_size="4KiB"
l2_size="64KiB"
l3_size="32KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NETWORK="simple" #"garnet" #"simple"

#DMT_Config=(True False)
DMT_Config=(True)
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
#NUM_CPU_SET=(4 8 16) # = #2 #4 #16
NUM_CPU_SET=(1) # = #2 #4 #16
WKSET=8192 #131072 #8192 #16384 #524288 #(32768) #
#NUM_MEM_SET=(1 2)
NUM_MEM=1
TRANS_SET=(1 2 4)
SNF_TBE_SET=(32 64)
HNF_TBE=32
NUM_LOAD_SET=(2) #no eviction/writeback. if more than 5000, more writeback/eviction

DEBUG_FLAGS=PseudoInst
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MEMBW"
fi

if [ "$TEST" == "L3_Hit" ]; then
  echo "Test $TEST"

l1d_size="1KiB"
l1i_size="1KiB"
l2_size="2KiB"
l3_size="64KiB" #"32KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NETWORK="garnet" #"garnet" #"simple"

DMT_Config=(False)
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
NUM_CPU_SET=(1 2 4) # = #2 #4 #16
WKSET=65536 #262144 #131072 #8192 #16384 #524288 #(32768) #
#NUM_MEM_SET=(1 2)
NUM_MEM=1
TRANS_SET=(1 2 4)
SNF_TBE_SET=(32)
HNF_TBE=32

##Set Working set size and Load set carefully!
NUM_LOAD_SET=(100) #need more transactions. if just several thousand transaction, BW is low


#DEBUG_FLAGS=SeqMemLatTest,TxnTrace 
DEBUG_FLAGS=PseudoInst
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MEMBW"
fi

if [ "$TEST" == "DDR_BW" ]; then
  echo "Test $TEST"

l1d_size="4KiB"
l1i_size="4KiB"
l2_size="8KiB"
l3_size="4KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NETWORK="simple" #"garnet" #"simple"

#DMT_Config=(True False)
NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
#NUM_CPU_SET=(4 8 16) # = #2 #4 #16
WKSET=524288 #8192 #16384 #524288 #(32768) #Total working set shared by all CPUs
NUM_MEM_SET=(1 2 4)
#NUM_MEM_SET=(1 2 4)
#NUM_MEM=1
TRANS_SET=(1 2 4)
SNF_TBE_SET=(32)
HNF_TBE=32

OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MEMBW"
fi

if [ "$TEST" == "REAL" ]; then
  echo "Test $TEST"

l1d_size="64KiB"
l1i_size="64KiB"
l2_size="512KiB"
l3_size="2MiB" #"32KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NETWORK="simple" #"garnet" #"simple"

DMT_Config=(True False)
NUM_CPU_SET=(16) # = #2 #4 #16
NUM_MEM=1
TRANS_SET=(4)
SNF_TBE_SET=(32)
HNF_TBE=32
fi

DMT_Config=(True False) #(True False)

NUM_CPU_SET=(16) # = #2 #4 #16
DCT_CONFIGS=(True False)

#Memory Retry Test
NUM_MEM_SET=(2)
NUM_DDR_XP_SET=(2)
NUM_DDR_SIDE_SET=(2)


TRANS_SET=(4)
HNF_TBE=32
SNF_TBE_SET=(32) #(32 64) #(32)
SEQ_TBE=32 #1
#NUM_LOAD_SET=(80000)

#Network/Garnet
LINKWIDTH_SET=(256) #(128 256 512)
NETWORK="simple"
LINK_LAT=1
ROUTER_LAT=0
VC_PER_VNET=2
PHYVNET=True #True #False
#

INJ_INTV_SET=(4)

MultiCoreAddrMode="True"


DEBUG_FLAGS=PseudoInst


#OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/Garnet_PHYVNET_SEQTBE1_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
#OUTPUT_PREFIX="NETWK${NETWORK}"

FS_ROOT="${WORKSPACE}/GEM5_ARM_FS_DCTDMT"

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${buildType} --default=${ISA} PROTOCOL=${CCPROT} NUMBER_BITS_PER_SET='128' -j`nproc`
fi


if [ "$CHECKPNT" != "" ]; then
    #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
    #mkdir -p $OUTPUT_DIR
    for DCT in ${DCT_CONFIGS[@]}; do
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do
                   for LINKWIDTH in ${LINKWIDTH_SET[@]}; do
                      for NUM_MEM in ${NUM_MEM_SET[@]}; do
                          for NUM_DDR_XP in ${NUM_DDR_XP_SET[@]}; do
                              for NUM_DDR_Side in ${NUM_DDR_SIDE_SET[@]}; do
                              if [[ $NUM_DDR_Side > $NUM_DDR_XP ]]; then
                                  continue #continue
                              fi
 
                              if [[ $NUM_MEM < $NUM_DDR_XP ]]; then
                                 echo " $NUM_MEM < $NUM_DDR_XP "
                                 continue #continue [2]
                              fi
                              echo "-------- Exec_NUMMEM(${NUM_MEM})_DDRXP(${NUM_DDR_XP}_DDRSide${NUM_DDR_Side}) ----------------"

            OUTPUT_ROOT="$FS_ROOT/PHYVNET${PHYVNET}_DDRLocDMT"
            OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_MEM${NUM_MEM}_MEMLOC${NUM_DDR_XP}Side${NUM_DDR_Side}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}" 
            CHECKPNT_DIR="${OUTPUT_DIR}/CHECKPNT"

            $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
              -d $CHECKPNT_DIR \
              ${GEM5_DIR}/configs/example/fs_starlink.py \
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
              --mem-size="16GB" \
              --mem-type=DDR4_3200_8x8 \
              --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
              --disable-gclk-set \
              --enable-DMT=${DMT} \
              --num-HNF-TBE=${HNF_TBE}  \
              --num-SNF-TBE=${SNF_TBE}  \
              --sequencer-outstanding-requests=${SEQ_TBE} \
              --num_trans_per_cycle_llc=${TRANS} \
              --num-cpus=${NUMCPUS} \
              --inj-interval=1      \
              --enable-DCT=${DCT} \
              --machine-type VExpress_GEM5_V1 \
              --kernel=$M5_PATH/binaries/vmlinux.vexpress_gem5_v1_64 \
              --bootloader=$M5_PATH/binaries/boot_emm.arm64 \
              --dtb-filename=$M5_PATH/binaries/armv8_gem5_v1_${NUMCPUS}cpu.dtb \
              --disk-image $M5_PATH/disks/expanded-ubuntu-18.04-arm64-docker.img \
              --param 'system.realview.gic.gem5_extensions = True' \
              --cpu-type=$CHECKPNT_CPU \
              --checkpoint-dir=$CHECKPNT_DIR \
              --script=$CHECKPNT_SCRIPT &
            
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


if [ "$RESTORE" != "" ]; then
    #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
    #mkdir -p $OUTPUT_DIR
  for DCT in ${DCT_CONFIGS[@]}; do
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do
                   for LINKWIDTH in ${LINKWIDTH_SET[@]}; do
                      for NUM_MEM in ${NUM_MEM_SET[@]}; do
                          for NUM_DDR_XP in ${NUM_DDR_XP_SET[@]}; do
                              for NUM_DDR_Side in ${NUM_DDR_SIDE_SET[@]}; do
                              if [[ $NUM_DDR_Side > $NUM_DDR_XP ]]; then
                                  continue #continue
                              fi
 
                              if [[ $NUM_MEM < $NUM_DDR_XP ]]; then
                                 echo " $NUM_MEM < $NUM_DDR_XP "
                                 continue #continue [2]
                              fi
                              echo "-------- Exec_NUMMEM(${NUM_MEM})_DDRXP(${NUM_DDR_XP}_DDRSide${NUM_DDR_Side}) ----------------"

            n=${#BENCHMARK_NAMES[@]}
            for ((i=0;i<$n;i++)); do
              BENCHMARK_SET[$i]="${BENCHMARK_NAMES[$i]}_${BENCHMARK_SIZE}_${NUMCPUS}"
              echo "Running BENCHMARK ${BENCHMARK_SET[$i]}"
            done

            for BENCHMARK in ${BENCHMARK_SET[@]}; do
            for RESTORE_CPU in ${RESTORE_CPU_SET[@]}; do
            OUTPUT_ROOT="$FS_ROOT/PHYVNET${PHYVNET}_DDRLocDMT"
            OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_MEM${NUM_MEM}_MEMLOC${NUM_DDR_XP}Side${NUM_DDR_Side}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}" 
            CHECKPNT_DIR="${OUTPUT_DIR}/CHECKPNT"
            OUTPUT_DIR="${OUTPUT_DIR}/${BENCHMARK}"

            # dump all variables to variables.txt and ease the parsing for STATS
            set > "${OUTPUT_DIR}/variables.txt"

            $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
              -d $OUTPUT_DIR \
              ${GEM5_DIR}/configs/example/fs_starlink.py \
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
              --link-width-bits=${LINKWIDTH} \
              --vcs-per-vnet=${VC_PER_VNET} \
              --link-latency=${LINK_LAT} \
              --router-latency=${ROUTER_LAT} \
              --topology=CustomMesh \
              --simple-physical-channels \
              --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
              --mem-size="16GB" \
              --mem-type=DDR4_3200_8x8 \
              --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
              --disable-gclk-set \
              --enable-DMT=${DMT} \
              --num-HNF-TBE=${HNF_TBE}  \
              --num-SNF-TBE=${SNF_TBE}  \
              --sequencer-outstanding-requests=${SEQ_TBE} \
              --num_trans_per_cycle_llc=${TRANS} \
              --num-cpus=${NUMCPUS} \
              --inj-interval=1      \
              --enable-DCT=${DCT} \
              --ruby \
              --checkpoint-restore ${CHECKPNT_IDX} \
              --machine-type VExpress_GEM5_V1 \
              --restore-with-cpu=${RESTORE_CPU} \
              --cpu-type ${RESTORE_CPU} \
              --kernel=$M5_PATH/binaries/vmlinux.vexpress_gem5_v1_64 \
              --bootloader=$M5_PATH/binaries/boot_emm.arm64 \
              --dtb-filename=$M5_PATH/binaries/armv8_gem5_v1_${NUMCPUS}cpu.dtb \
              --disk-image $M5_PATH/disks/expanded-ubuntu-18.04-arm64-docker.img \
              --param 'system.realview.gic.gem5_extensions = True' \
              --checkpoint-dir ${CHECKPNT_DIR} \
              --script=${PARSEC_SCRIPT_DIR}/$BENCHMARK.rcS &

                      done
                    done
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


if [ "$DIRRUN" != "" ]; then
    #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
    #mkdir -p $OUTPUT_DIR
  for DCT in ${DCT_CONFIGS[@]}; do
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do
                   for LINKWIDTH in ${LINKWIDTH_SET[@]}; do
                      for NUM_MEM in ${NUM_MEM_SET[@]}; do
                          for NUM_DDR_XP in ${NUM_DDR_XP_SET[@]}; do
                              for NUM_DDR_Side in ${NUM_DDR_SIDE_SET[@]}; do
                              if [[ $NUM_DDR_Side > $NUM_DDR_XP ]]; then
                                  continue #continue
                              fi
 
                              if [[ $NUM_MEM < $NUM_DDR_XP ]]; then
                                 echo " $NUM_MEM < $NUM_DDR_XP "
                                 continue #continue [2]
                              fi
                              echo "-------- Exec_NUMMEM(${NUM_MEM})_DDRXP(${NUM_DDR_XP}_DDRSide${NUM_DDR_Side}) ----------------"

            n=${#BENCHMARK_NAMES[@]}
            for ((i=0;i<$n;i++)); do
              BENCHMARK_SET[$i]="${BENCHMARK_NAMES[$i]}_${BENCHMARK_SIZE}_${NUMCPUS}"
              echo "Running BENCHMARK ${BENCHMARK_SET[$i]}"
            done

            for BENCHMARK in ${BENCHMARK_SET[@]}; do
            for RESTORE_CPU in ${RESTORE_CPU_SET[@]}; do
            OUTPUT_ROOT="$FS_ROOT/PHYVNET${PHYVNET}_DDRLocDMT"
            OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_MEM${NUM_MEM}_MEMLOC${NUM_DDR_XP}Side${NUM_DDR_Side}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}" 
            CHECKPNT_DIR="${OUTPUT_DIR}/CHECKPNT"
            OUTPUT_DIR="${OUTPUT_DIR}/${BENCHMARK}"

            # dump all variables to variables.txt and ease the parsing for STATS
            set > "${OUTPUT_DIR}/variables.txt"
            
            $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
              -d $OUTPUT_DIR \
              --debug-flags=$DEBUG_FLAGS --debug-file=debug.trace \
              ${GEM5_DIR}/configs/example/fs_starlink.py \
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
              --link-width-bits=${LINKWIDTH} \
              --vcs-per-vnet=${VC_PER_VNET} \
              --link-latency=${LINK_LAT} \
              --router-latency=${ROUTER_LAT} \
              --topology=CustomMesh \
              --simple-physical-channels \
              --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
              --mem-size="16GB" \
              --mem-type=DDR4_3200_8x8 \
              --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
              --disable-gclk-set \
              --enable-DMT=${DMT} \
              --num-HNF-TBE=${HNF_TBE}  \
              --num-SNF-TBE=${SNF_TBE}  \
              --sequencer-outstanding-requests=${SEQ_TBE} \
              --num_trans_per_cycle_llc=${TRANS} \
              --num-cpus=${NUMCPUS} \
              --inj-interval=1      \
              --enable-DCT=${DCT} \
              --ruby \
              --machine-type VExpress_GEM5_V1 \
              --cpu-type ${RESTORE_CPU} \
              --kernel=$M5_PATH/binaries/vmlinux.vexpress_gem5_v1_64 \
              --bootloader=$M5_PATH/binaries/boot_emm.arm64 \
              --dtb-filename=$M5_PATH/binaries/armv8_gem5_v1_${NUMCPUS}cpu.dtb \
              --disk-image $M5_PATH/disks/expanded-ubuntu-18.04-arm64-docker.img \
              --param 'system.realview.gic.gem5_extensions = True' \
              --script=${PARSEC_SCRIPT_DIR}/$BENCHMARK.rcS &

                      done
                    done
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


  if [ "$ANALYSIS" != "" ]; then
    #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do 
                for NUM_LOAD in ${NUM_LOAD_SET[@]}; do 
                    for LINKWIDTH in ${LINKWIDTH_SET[@]}; do


            OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}_NUMLOAD${NUM_LOAD}" 
 

      #grep -rwI -e 'system\.cpu0' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu0.trace
      #grep -rwI -e 'system\.cpu1' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu1.trace
          statsfile=$OUTPUT_DIR/stats.txt
          echo $OUTPUT_DIR
          grep simTicks  ${statsfile}
          grep "mem_ctrls" ${statsfile} | grep readReqs
          ##grep "l1d.cache.numDataArrayReads" ${statsfile}
          ##grep "l1d.cache.numTagArrayReads" ${statsfile} 
          grep "l1d.cache.m_demand" ${statsfile} 
          #grep "l1d.avg_size" ${statsfile} | grep "TBE Request Occupancy"
 
          grep "l2.cache.m_demand" ${statsfile}  
          grep "cache.m_demand" ${statsfile} | grep hnf
          grep "cntrl.avg_size" ${statsfile} | grep "TBE Request Occupanc"
          grep "m_outstandReqHistSeqr::mean" ${statsfile}
          grep "snf.cntrl.avg_size" ${statsfile}
          grep "mem_ctrls.readReqs" ${statsfile}
          grep "mem_ctrls.writeReqs" ${statsfile}
          echo "**** search reqIn message in hnf"
          grep reqIn.m_msg_count ${statsfile} | grep hnf

         done
       done
     done
   done
  done
 done
fi

  if [ "$STATS" != "" ]; then 
    OUTPUT_ROOT="$FS_ROOT"
    python3 stats_parser_fs.py --root-dir ${OUTPUT_ROOT}
fi

   if [ "$GRAPH" != "" ]; then
     #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
     echo "GRAPH"

  for DCT in ${DCT_CONFIGS[@]}; do
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do
                   for LINKWIDTH in ${LINKWIDTH_SET[@]}; do
                      for NUM_MEM in ${NUM_MEM_SET[@]}; do
                          for NUM_DDR_XP in ${NUM_DDR_XP_SET[@]}; do
                              for NUM_DDR_Side in ${NUM_DDR_SIDE_SET[@]}; do
                              if [[ $NUM_DDR_Side > $NUM_DDR_XP ]]; then
                                  continue #continue
                              fi
 
                              if [[ $NUM_MEM < $NUM_DDR_XP ]]; then
                                 echo " $NUM_MEM < $NUM_DDR_XP "
                                 continue #continue [2]
                              fi

            n=${#BENCHMARK_NAMES[@]}
            for ((i=0;i<$n;i++)); do
              BENCHMARK_SET[$i]="${BENCHMARK_NAMES[$i]}_${BENCHMARK_SIZE}_${NUMCPUS}"
            done

            for BENCHMARK in ${BENCHMARK_SET[@]}; do
            for RESTORE_CPU in ${RESTORE_CPU_SET[@]}; do

            OUTPUT_ROOT="$FS_ROOT/PHYVNET${PHYVNET}_DDRLocDMT"
            OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_DCT${DCT}_MEM${NUM_MEM}_MEMLOC${NUM_DDR_XP}Side${NUM_DDR_Side}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}" 
            OUTPUT_DIR="${OUTPUT_DIR}/${BENCHMARK}"
 
           # grep -E "^[[:space:]]+[0-9]+: system\.ruby\.network\.int_links[0-9]+\.buffers[0-9]+" ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/link.log
           # python3 netparse.py --input ${OUTPUT_DIR} --output ${OUTPUT_DIR} --num-int-router 16
           # enable --draw-ctrl to draw controllers
           # currently need to manually pass the number of internal routers
           python3 netparse.py --input ${OUTPUT_DIR} --output ${OUTPUT_DIR} --draw-ctrl --num-int-router 16

                      done
                    done
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

