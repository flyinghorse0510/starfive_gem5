#!/bin/bash

#command example: ./runMemTest_Scenarios.sh -t L2_Hit

#2023-02-17 18 19 23 

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

while getopts "hbr:s:a:t:p:g:" options; do
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
         DEBUG_FLAGS=TxnLink,TxnTrace
         echo ${OPTARG}
         TEST=${OPTARG}
         echo "Running TxnTrace with '${OPTARG}' argument"
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
#NUM_LOAD_SET=(100)
NUM_LOAD_SET=(10) #(50)

#DEBUG_FLAGS=SeqMemLatTest,TxnTrace 
#DEBUG_FLAGS=SeqMemLatTest
DEBUG_FLAGS=PseudoInst
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/MEMBW"
fi

DMT_Config=(True False) #(True False)
##NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16

NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16

#NUM_CPU_SET=(8) # = #2 #4 #16


#NUM_CPU_SET=(4 8 16) # = #2 #4 #16
##NUM_CPU_SET=(2 4 8 16) # = #2 #4 #16

#Sinlge Core
#NUM_CPU_SET=(1) # = #2 #4 #16

#Multi Core
#NUM_CPU_SET=(1 2 4 8 16) # = #2 #4 #16
#NUM_CPU_SET=(16) # = #2 #4 #16


#WKSET=131072 #8192 #16384 #524288 #(32768) #
#NUM_MEM_SET=(1 2)
#NUM_MEM=2 #1

##Memory location exploration
#NUM_DDR_XP_SET=(1 2 4)
#NUM_DDR_XP_SET=(2)
#NUM_DDR_SIDE_SET=(1 2)

#Memory Retry Test
NUM_MEM_SET=(2 4)
NUM_DDR_XP_SET=(2)
NUM_DDR_SIDE_SET=(1)

##Memory location exploration
#NUM_DDR_XP_SET=(2 4)
#NUM_DDR_SIDE_SET=(1 2)



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

INJ_INTV_SET=(2,4,8,16,20,24,32)

#DEBUG_FLAGS="SeqMemLatTest,TxnTrace"
#DEBUG_FLAGS="SeqMemLatTest,TxnTrace,TxnLink"

#DEBUG_FLAGS=TxnTrace
#DEBUG_FLAGS=RubySlicc
DEBUG_FLAGS="SeqMemLatTest"

MultiCoreAddrMode=True #False #False #True #--addr-intrlvd-or-tiled true then interleaved 

#OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/Garnet_PHYVNET_SEQTBE1_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
#OUTPUT_PREFIX="NETWK${NETWORK}"
OUTPUT_ROOT="${WORKSPACE}/GEM5_PDCP/PHYVNET${PHYVNET}_DDRLocDMT"

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


            OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_MEMLOC${NUM_DDR_XP}Side${NUM_DDR_Side}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}_NUMLOAD${NUM_LOAD}" 
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
              --link-width-bits=${LINKWIDTH} \
              --vcs-per-vnet=${VC_PER_VNET} \
              --link-latency=${LINK_LAT} \
              --router-latency=${ROUTER_LAT} \
              --topology=CustomMesh \
              --simple-physical-channels \
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
              --sequencer-outstanding-requests=${SEQ_TBE} \
              --num_trans_per_cycle_llc=${TRANS} \
              --num-cpus=${NUMCPUS} \
              --inj-interval=2 \
              --num-producers=1 &
      #  grep -rwI -e 'system\.cpu0' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu0.trace
      #  grep -rwI -e 'system\.cpu1' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu1.trace
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
wait

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

  if [ "$TXNTRACE" != "" ]; then
    #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do 
                for NUM_LOAD in ${NUM_LOAD_SET[@]}; do 
                   for LINKWIDTH in ${LINKWIDTH_SET[@]}; do


            OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}_NUMLOAD${NUM_LOAD}" 
 

          grep -E 'Req Begin|Req Done|requestToMemory|responseFromMemory' ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/simple.trace 
          python3 logparser.py --input ${OUTPUT_DIR}/simple.trace --output ${OUTPUT_DIR} --num_cpu ${NUMCPUS} --num_llc ${NUM_LLC} --num_mem ${NUM_MEM} --num_load ${NUM_LOAD} 
         done
       done
     done
   done
  done
 done
fi

  if [ "$STATS" != "" ]; then
    #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
   for NUM_DDR_XP in ${NUM_DDR_XP_SET[@]}; do 
   touch throughput.txt
   dd if=/dev/null of=throughput.txt
    
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
          for TRANS in ${TRANS_SET[@]}; do
             for  SNF_TBE in ${SNF_TBE_SET[@]}; do 
                for NUM_LOAD in ${NUM_LOAD_SET[@]}; do 
                   for LINKWIDTH in ${LINKWIDTH_SET[@]}; do
                       for NUM_MEM in ${NUM_MEM_SET[@]}; do
  
                         for NUM_DDR_Side in ${NUM_DDR_SIDE_SET[@]}; do
                            if [[ $NUM_DDR_Side > $NUM_DDR_XP ]]; then
                               continue #continue
                            fi
 
                            if [[ $NUM_MEM < $NUM_DDR_XP ]]; then
                               echo " $NUM_MEM < $NUM_DDR_XP "
                               continue #continue [2]
                            fi
                            echo "-------- Stats_NUMMEM(${NUM_MEM})_DDRXP(${NUM_DDR_XP}_DDRSide${NUM_DDR_Side}) ----------------"

                    
#                   touch throughput.txt
#                   dd if=/dev/null of=throughput.txt
#                   for NUM_DDR_XP in ${NUM_DDR_XP_SET[@]}; do 

            OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
            OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_MEMLOC${NUM_DDR_XP}Side${NUM_DDR_Side}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}_NUMLOAD${NUM_LOAD}" 
 
          ## by default will only print cpu,ddr,llc
          ## python3 stats_parser.py --input ${OUTPUT_DIR}/stats.txt --output ${OUTPUT_DIR}/stats.log --num_cpu ${NUMCPUS} --num_llc ${NUM_LLC} --num_ddr ${NUM_MEM}
          ## also print l2p,l1d,l1i
          python3 stats_parser.py --input ${OUTPUT_DIR}/stats.txt --output ${OUTPUT_DIR}/stats.log --num_cpu ${NUMCPUS} --num_llc ${NUM_LLC} --num_ddr ${NUM_MEM} --trans ${TRANS} --snf_tbe ${SNF_TBE} --dmt ${DMT} --linkwidth ${LINKWIDTH} --injintv 0 --print l1d,l1i,l2p,llc,cpu,ddr  #True #False
                   done
#                   mv throughput.txt throughput_MEMLOC${NUM_DDR_Side}.txt
             done
           done
         done
       done
     done
   done
 done
    mv throughput.txt throughput_MEMLOC${NUM_DDR_XP}_PHYVNET${PHYVNET}.txt
 
done
fi

   if [ "$GRAPH" != "" ]; then
     #OUTPUT_ROOT="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
     echo "GRAPH"

     for DMT in ${DMT_Config[@]}; do
        for NUMCPUS in ${NUM_CPU_SET[@]}; do
           for TRANS in ${TRANS_SET[@]}; do
              for  SNF_TBE in ${SNF_TBE_SET[@]}; do
                 for NUM_LOAD in ${NUM_LOAD_SET[@]}; do
                    for LINKWIDTH in ${LINKWIDTH_SET[@]}; do
                       for NUM_MEM in ${NUM_MEM_SET[@]}; do
                         for NUM_DDR_XP in ${NUM_DDR_XP_SET[@]}; do
                              for NUM_DDR_Side in ${NUM_DDR_SIDE_SET[@]}; do
#                              echo "DDR XP:${NUM_DDR_XP} Side:${NUM_DDR_Side}"
                              if [[ $NUM_DDR_Side > $NUM_DDR_XP ]]; then
                                  continue #continue
                              fi
                              echo "DDR XP:${NUM_DDR_XP} Side:${NUM_DDR_Side}"
                              if [[ $NUM_MEM < $NUM_DDR_XP ]]; then
                                 echo " $NUM_MEM < $NUM_DDR_XP "
                                 continue #continue [2]
                              fi
                              echo "-------- Graph_NUMMEM(${NUM_MEM})_DDRXP(${NUM_DDR_XP}_DDRSide${NUM_DDR_Side}) ----------------"


             OUTPUT_PREFIX="NETWORK${NETWORK}_LW${LINKWIDTH}_LL${LINK_LAT}_RL${ROUTER_LAT}_VC${VC_PER_VNET}"
             OUTPUT_DIR="${OUTPUT_ROOT}/${OUTPUT_PREFIX}/WS${WKSET}_Core${NUMCPUS}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_MEM${NUM_MEM}_MEMLOC${NUM_DDR_XP}Side${NUM_DDR_Side}_INTERLV${MultiCoreAddrMode}_SNFTBE${SNF_TBE}_DMT${DMT}_TRANS${TRANS}_NUMLOAD${NUM_LOAD}" 
             echo ${OUTPUT_DIR}
 
           grep -E "^[[:space:]]+[0-9]+: system\.ruby\.network\.int_links[0-9]+\.buffers[0-9]+" ${OUTPUT_DIR}/debug.trace > ${OUTPUT_DIR}/link.log
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
 fi

