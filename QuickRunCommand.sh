#!/bin/bash

# workingset=(1024 2048 4096 5120 6144 8192 10240 14336 16384 32768 65536 131072 262144 393216 10485766)
# workingset=(1048576 4194304 8388608 16777216 33554432 67108864)
#workingset=(2048 8192 16384)
#workingset=(2048)

#workingset=(2048)


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
GEM5_DIR=$(pwd)
OUTPUT_DIR="${WORKSPACE}/04_gem5Dump/HAS0.5"
ISA="RISCV"
CCPROT="CHI"


l1d_size="32KiB"
l1i_size="32KiB"
l2_size="64KiB"
l3_size="16KiB" #"256KiB"
l1d_assoc=8
l1i_assoc=8
l2_assoc=8
l3_assoc=16
NUM_LLC=16


NUM_ITER=4 #16 #800  #32 #16
NUM_CPU=4 #16

#WS=2048*${NUM_CPU}

workingset=(524288) #(32768) #
prefix="PDCP_20230201"
#prefix="MultiThread"


if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/gem5.opt --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

if [ "$RUN" != "" ]; then
    for i in ${workingset[@]} ; do
        mkdir -p $OUTPUT_DIR$i
        echo "Start running with $i working set size"
        $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.opt \
            --debug-flags=PseudoInst --debug-file=debug.trace \
            -d "${OUTPUT_DIR}_${prefix}_Core${NUM_CPU}_Iter${NUM_ITER}_L1${l1d_size}_L2${l2_size}_L3${l3_size}_WS${i}" \
            ${GEM5_DIR}/configs/example/Starlink2.0_intradie.py \
            --rate-style \
            --size-ws=$i \
            --l1d_size=${l1d_size}\
            --l1i_size=${l1i_size}\
            --l2_size=${l2_size}\
            --l3_size=${l3_size}\
            --l1d_assoc=${l1d_assoc}\
            --l1i_assoc=${l1i_assoc}\
            --l2_assoc=${l2_assoc}\
            --l3_assoc=${l3_assoc}\
            --num-dirs=1 \
            --use-o3 \
            --num-l3caches=${NUM_LLC} \
            --num-iters=${NUM_ITER} \
            --network=simple \
            --topology=CustomMesh \
            --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
            --ruby \
            --mem-size="4GB" \
            --num-cpus=${NUM_CPU}
    done
fi
            # --rate-style 
            # --debug-flags=PseudoInst --debug-file=debug.trace 
# --debug-flags=RubyCHIDebugStr5,RubyGenerated  --debug-file=debug.trace 
>>>>>>>>> Temporary merge branch 2
