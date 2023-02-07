#!/bin/bash

#command example: ./runMemTest_Scenarios.sh -t L2_Hit

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

BUILD=""
RUN=""
ANALYSIS=""
TXNTRACE=""

TEST=""

while getopts "hbr:sa:t:p:" options; do
    case $options in
       h) Help
          exit;;
       b) BUILD="yes"
           ;;
       r) RUN1="yes"
          TEST=${OPTARG}
          RUN1="yes"
          echo "Processing option 'c' with '${OPTARG}' argument"
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
       p)
         TXNTRACE="yes"
         echo ${OPTARG}
         TEST=${OPTARG}
         echo "Running TxnTrace with '${OPTARG}' argument"
    esac
done


export WORKSPACE="$(pwd)/output"
export GEM5_DIR=$(pwd)
export ISA="RISCV"
export CCPROT="CHI"
export NUMCPUS=4

buildType="gem5.opt"

#NOTE:
#1. To test latency need to set Sequencer maximal outstanding to 1
#

if [ "$TEST" == "L1_Hit" ]; then
echo $TEST

#TEST="L1_Hit"
#TEST="L2_Hit"
#TEST="L3_Hit"
#TEST="DDR_BW"

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

DMT_Config=(True False)
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
NUM_CPU_SET=(4 8 16) # = #2 #4 #16
WKSET=8192 #16384 #524288 #(32768) #
#NUM_MEM_SET=(1 2)
NUM_MEM=1
TRANS_SET=(1 2 4)
SNF_TBE_SET=(32 64)
HNF_TBE=32
NUM_LOAD_SET=(100)

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

DMT_Config=(True False)
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
#NUM_CPU_SET=(4 8 16) # = #2 #4 #16
NUM_CPU_SET=(1) # = #2 #4 #16
WKSET=8192 #131072 #8192 #16384 #524288 #(32768) #
#NUM_MEM_SET=(1 2)
NUM_MEM=1
TRANS_SET=(1 2 4)
SNF_TBE_SET=(32 64)
HNF_TBE=32
NUM_LOAD_SET=(100) #no eviction/writeback. if more than 5000, more writeback/eviction

DEBUG_FLAGS=PseudoInst
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MEMBW"
fi

if [ "$TEST" == "L3_Hit" ]; then
  echo "Test $TEST"

l1d_size="2KiB"
l1i_size="2KiB"
l2_size="8KiB"
l3_size="64KiB" #"32KiB" #"16KiB" #"1024KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NETWORK="simple" #"garnet" #"simple"

DMT_Config=(False)
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
NUM_CPU_SET=(1 2 4) # = #2 #4 #16
WKSET=65536 #262144 #131072 #8192 #16384 #524288 #(32768) #
#NUM_MEM_SET=(1 2)
NUM_MEM=1
TRANS_SET=(1 2 4)
SNF_TBE_SET=(32 64)
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

DMT_Config=(True False)
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
NUM_CPU_SET=(4 8 16) # = #2 #4 #16
WKSET=524288 #8192 #16384 #524288 #(32768) #Total working set shared by all CPUs
#NUM_MEM_SET=(1 2)
NUM_MEM=1
TRANS_SET=(1 2 4)
SNF_TBE_SET=(32)
HNF_TBE=32
NUM_LOAD_SET=(50)

#DEBUG_FLAGS=SeqMemLatTest,TxnTrace 
#DEBUG_FLAGS=SeqMemLatTest
DEBUG_FLAGS=PseudoInst
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MEMBW"
fi

#DMT_Config=(True False)
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
#NUM_CPU_SET=(4 8 16) # = #2 #4 #16
##NUM_CPU_SET=(2 4 8 16) # = #2 #4 #16

#Sinlge Core
#NUM_CPU_SET=(1) # = #2 #4 #16

#Multi Core
NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
#NUM_CPU_SET=(16) # = #2 #4 #16


#WKSET=131072 #8192 #16384 #524288 #(32768) #
#NUM_MEM_SET=(1 2)
NUM_MEM=1
TRANS_SET=(4)
HNF_TBE=32
SNF_TBE_SET=(32)
#NUM_LOAD_SET=(80000)

#DEBUG_FLAGS="SeqMemLatTest,TxnTrace"
#DEBUG_FLAGS=TxnTrace
#DEBUG_FLAGS=RubySlicc
DEBUG_FLAGS="SeqMemLatTest"

MultiCoreAddrMode=False #False #True #--addr-intrlvd-or-tiled true then interleaved 

OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MEM_Hier_MEMADDInteLeaving2"
OUTPUT_PREFIX="TEST_${TEST}/NETWK${NETWORK}_LinkFactor40_SysClk2GHz"

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${buildType} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN1" != "" ]; then
    #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
    #mkdir -p $OUTPUT_DIR
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do
                for NUM_LOAD in ${NUM_LOAD_SET[@]}; do 
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}_NUMLOAD${NUM_LOAD}" 
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
              --maxloads=${NUM_LOAD} \
              --mem-size="16GB" \
              --size-ws=${WKSET} \
              --mem-type=DDR4_3200_8x8 \
              --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
              --mem-test-type='bw_test' \
              --addr-intrlvd-or-tiled=$MultiCoreAddrMode  \
              --disable-gclk-set \
              --enable-DMT=${DMT} \
              --num-HNF-TBE=${HNF_TBE}  \
              --num-SNF-TBE=${SNF_TBE}  \
              --num_trans_per_cycle_llc=${TRANS} \
              --num-cpus=${NUMCPUS} \
              --num-producers=1 &
       grep -rwI -e 'system\.cpu0' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu0.trace
       grep -rwI -e 'system\.cpu1' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu1.trace
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
fi

  if [ "$TXNTRACE" != "" ]; then
    #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do 
                for NUM_LOAD in ${NUM_LOAD_SET[@]}; do 
 
          OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}_NUMLOAD${NUM_LOAD}" 

          # change -o ${OUTPUT_DIR} to place profile to somewhere else, default is to place the same dir as debug.trace
          python3 logparser.py -i ${OUTPUT_DIR} -o ${OUTPUT_DIR}
         done
       done
     done
   done
  done
fi