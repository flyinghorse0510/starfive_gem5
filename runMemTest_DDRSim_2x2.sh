#!/bin/bash

Help() {
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|s|h]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     Run1 (MemTest)."
   echo "s     Run2 (IsoMemTest)."
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
        s) RUN2="yes"
           ;;
    esac
done

WORKSPACE="${HOME}/Desktop"
GEM5_DIR=$(pwd) 
ISA="RISCV" 
CCPROT="CHI" 
NUMCPUS=4 
NUMDIRS=1
NUM_LLC_BANK=4 
LLC_BANK_SIZE="1MiB"


if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/gem5.opt --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN2" != "" ]; then
    OUTPUT_DIR="${WORKSPACE}/DDRTest_memTest_${NUMCPUS}CPU"
    $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.opt \
        -d ${OUTPUT_DIR} \
        ${GEM5_DIR}/configs/example/ruby_mem_test.py \
        --num-dirs=${NUMDIRS} \
        --num-l3caches=${NUM_LLC_BANK} \
        --l3_size=${LLC_BANK_SIZE} \
        --network=simple \
        --topology=CustomMesh \
        --chi-config=${GEM5_DIR}/configs/example/noc_config/2x2.py \
        --ruby \
        --maxloads=5000 \
        --mem-size="16GB" \
        --num-cpus=${NUMCPUS} \
        --mem-type=DDR4_3200_8x8 \
        --addr-mapping="RoRaBaBg1CoBg0Co53Dp" \
        --disable-gclk-set

    #--debug-flags=WSWS --debug-file=memctrldebug.trace \ --disable-ref \
    #grep -rwI -e 'system\.ruby\.hnf\.cntrl' $OUTPUT_DIR/debug.trace > $OUTPUT_DIR/debug.hnf.trace
fi
