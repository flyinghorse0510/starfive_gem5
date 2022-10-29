#!/bin/bash

Help()
{
   # Display Help
   echo "Run gem5 Starlink2.0 configurations."
   echo
   echo "Syntax: scriptTemplate [-b|r|h]"
   echo "options:"
   echo "h     Print this Help."
   echo "b     Build."
   echo "r     Run."
   echo
}

BUILD=""
RUN=""
while getopts "hbr" options; do
    case $options in
        h) Help
           exit;;
        b) BUILD="yes"
            ;;
        r) RUN="yes"
    esac
done

#/home/zhiguo.ge/ChipServer/Modeling/gem5_starlink2

WORKSPACE="${HOME}/ChipServer/Modeling"
GEM5_DIR="${WORKSPACE}/gem5_starlink2"
OUTPUT_DIR="${WORKSPACE}/04_gem5Dump/Starlink2.0_gem5_ubench"
ISA="RISCV"
CCPROT="CHI"
mkdir -p ${OUTPUT_DIR}

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/gem5.debug --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi


if [ "$RUN" != "" ]; then
    echo "Start running"
    $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.opt \
        -d $OUTPUT_DIR \
        ${GEM5_DIR}/configs/example/Starlink2.0_4x4intradie.py \
        --num-dirs=1 \
        --num-l3caches=16 \
        --network=simple \
        --topology=CustomMesh \
        --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
        --ruby \
        --mem-size="4GB" \
        --num-cpus=16
fi

# echo "Parsing the address trace"
# python3 ProcessCHIDebugTrace.py --dump-dir ${OUTPUT_DIR}
