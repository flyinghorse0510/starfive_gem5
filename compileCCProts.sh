#!/bin/bash

#CCPROTS=("MI_example" "MESI_Two_Level" "MESI_Three_Level" "MOESI_hammer" "MOESI_CMP_token" "MOESI_AMD_Base" "CHI")

CCPROTS=("CHI")
for ccprot in ${CCPROTS[@]}; do
    echo "Building ${ccprot}"
    scons build/RISCV_${ccprot}/gem5.opt --default=RISCV PROTOCOL=${ccprot} -j`nproc`
done
