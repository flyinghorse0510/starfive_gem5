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

ISA="RISCV"
CCPROT="CHI"

if [ "$BUILD" != "" ]; then
    echo "Start building"
    scons build/${ISA}_${CCPROT}/gem5.opt --default=RISCV PROTOCOL=${CCPROT} -j`nproc`
fi

ITERCOUNTS=(10 100 1000 10000)
if [ "$RUN" != "" ]; then
    for n in ${ITERCOUNTS[@]} ; do
        OUTPUT_DIR="${WORKSPACE}/04_gem5dump/STREAM_1C_no_roi_$n"
        mkdir -p ${OUTPUT_DIR}
        echo "Running no roi"
        $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.opt \
            -d $OUTPUT_DIR \
            ${GEM5_DIR}/configs/example/Starlink2.0_4x4intradie.py \
            --size-ws=64 \
            --num-dirs=1 \
            --no-roi \
            --num-l3caches=16 \
            --num-iters=$n \
            --network=simple \
            --topology=CustomMesh \
            --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
            --ruby \
            --mem-size="4GB"

        OUTPUT_DIR="${WORKSPACE}/04_gem5dump/STREAM_1C_$n"
        mkdir -p ${OUTPUT_DIR}
        echo "Running roi"
        $GEM5_DIR/build/${ISA}_${CCPROT}/gem5.opt \
            -d $OUTPUT_DIR \
            ${GEM5_DIR}/configs/example/Starlink2.0_4x4intradie.py \
            --size-ws=64 \
            --num-dirs=1 \
            --num-l3caches=16 \
            --num-iters=$n \
            --network=simple \
            --topology=CustomMesh \
            --chi-config=${GEM5_DIR}/configs/example/noc_config/Starlink2.0_4x4Mesh.py \
            --ruby \
            --mem-size="4GB"
    done
fi