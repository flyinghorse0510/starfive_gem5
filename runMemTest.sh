#!/bin/bash

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
while getopts "hbrs" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) RUN1="yes"
           ;;
    esac
done

export WORKSPACE="$(pwd)/output"
export GEM5_DIR=$(pwd)
export ISA="RISCV"
export CCPROT="CHI"
export NUMCPUS=4

buildType="gem5.debug"
l1d_size="32KiB"
l1i_size="32KiB"
l2_size="64KiB"
l3_size="16KiB" #"1024KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16
NETWORK="simple" #"garnet" #"simple"

DMT_Config=(False)
NUM_CPU_SET=(1 2) # = #2 #4 #16
WKSET=524288 #(32768) #

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/${buildType} --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN1" != "" ]; then
    OUTPUT_DIR="${WORKSPACE}/04_gem5dump/HAS0.5_4x4_BW"
    mkdir -p $OUTPUT_DIR
    for DMT in ${DMT_Config[@]}; do
       for NUMCPUS in ${NUM_CPU_SET[@]}; do
         
        $GEM5_DIR/build/${ISA}_${CCPROT}/${buildType} \
          --debug-flags=SeqMemLatTest --debug-file=debug.trace \
          -d "${OUTPUT_DIR}/${prefix}_Core${NUMCPUS}_DMT${DMT}" \
          ${GEM5_DIR}/configs/example/seq_ruby_mem_test.py \
          --num-dirs=1 \
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
          --maxloads=5000 \
          --mem-size="16GB" \
          --size-ws=${WKSET} \
          --mem-type=DDR4_3200_8x8 \
          --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
          --mem-test-type='bw_test' \
          --disable-gclk-set \
          --enable-DMT=False \
          --num-cpus=${NUMCPUS} \
          --num-producers=1
      grep -rwI -e 'system\.cpu0' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu0.trace
      grep -rwI -e 'system\.cpu1' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.cpu1.trace
     done
   done
fi
