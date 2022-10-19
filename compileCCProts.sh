#!/bin/bash

CCPROTS=("CHI")
for ccprot in ${CCPROTS[@]}; do
    echo "Building ${ccprot}"
    scons build/RISCV_${ccprot}/gem5.opt --default=RISCV PROTOCOL=${ccprot} -j`nproc`
done