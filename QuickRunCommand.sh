#!/bin/bash

# workingset=(32 64 128 256 512 768 1024 1120 1184 1600 2048 3840 4096 5120 6400 8000 8192 9600 10240 16384 32768 40000 65536 80000 131072 262144 1048576)
workingset=(256)
# workingset=(11200000 11380000 11560000 11740000 11920000 12100000 12280000 12460000 12640000 12820000)
#workingset=(4000000 4180000 4360000 4540000 4720000 4900000 5080000 5260000 5440000 5620000 5800000 5980000 6160000 6340000 6520000 6700000 6880000 7060000 7240000 7420000 7600000 7780000 7960000 8140000 8320000 8500000 8680000 8860000 9040000 9220000 9400000 9580000 9760000 9940000 10120000 10300000 10480000 10660000 10840000 11020000 11200000 11380000 11560000 11740000 11920000 12100000 12280000 12460000 12640000 12820000)
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
OUTPUT_DIR="${WORKSPACE}/04_gem5dump/FixedStride_"
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
            --debug-flags=RubyCHIDebugStr5,RubyGenerated  --debug-file=debug.trace \
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

# echo "Parsing the address trace"
# python3 ProcessCHIDebugTrace.py --dump-dir ${OUTPUT_DIR}
