#!/bin/bash

workingset=(64 128 256 512 640 704 1024 1280 1408 1536 1600 1664 1792 2048 4096 8192 16384 32768 65536 131072 262144 524288 1048576 2097152 4194304 8388608 16777216)
# workingset=(64 128)


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

WORKSPACE="${HOME}/Desktop"
GEM5_DIR="${WORKSPACE}/gem5_starlink2.0"
OUTPUT_DIR="${WORKSPACE}/04_gem5dump/FixedStrideINTELConfig_"
ISA="RISCV"
CCPROT="CHI"

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/gem5.opt --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi


if [ "$RUN" != "" ]; then
    for i in ${workingset[@]} ; do
        mkdir -p ${OUTPUT_DIR}$i
        echo "Start running with $i working set size"
        $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.opt \
            -d $OUTPUT_DIR$i \
            ${GEM5_DIR}/configs/example/Starlink2.0_4x4intradie.py \
            --size-ws=$i \
            --num-dirs=1 \
            --num-l3caches=16 \
            --network=simple \
            --topology=CustomMesh \
            --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
            --ruby \
            --mem-size="4GB" \
            --num-cpus=16
    done
fi

# --debug-flags=RubyCHIDebugStr5,RubyGenerated  --debug-file=debug.trace 