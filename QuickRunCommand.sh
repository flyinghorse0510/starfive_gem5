#!/bin/bash

# workingset=(1024 2048 4096 5120 6144 8192 10240 14336 16384 32768 65536 131072 262144 393216 10485766)
workingset=(1048576 4194304 8388608 16777216 33554432 67108864)
# workingset=(64)

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

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/gem5.debug --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN" != "" ]; then
    for i in ${workingset[@]} ; do
        mkdir -p $OUTPUT_DIR$i
        echo "Start running with $i working set size"
        $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.opt \
            -d $OUTPUT_DIR$i \
            ${GEM5_DIR}/configs/example/Starlink2.0_4x4intradie.py \
            --no-roi \
            --rate-style \
            --size-ws=$i \
            --num-dirs=1 \
            --num-l3caches=16 \
            --num-iters=10000 \
            --network=simple \
            --topology=CustomMesh \
            --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
            --ruby \
            --mem-size="4GB" \
            --num-cpus=16 &
    done
    wait
fi


# echo "Parsing the address trace"
# python3 ProcessCHIDebugTrace.py --dump-dir ${OUTPUT_DIR}
