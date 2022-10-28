#!/bin/bash

# workingset=(1024 2048 4096 5120 6144 8192 10240 12288 14336 16384 25600 49152 65536 98304 131072 147456 262144 327680 655360 1048576)
workingset=(1024)

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
OUTPUT_DIR="${WORKSPACE}/04_gem5dump/STREAM_"
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