riscv64-unknown-elf-gcc \
    -O2 \
    -I./ -I${GEM5_HOME}/include \
    -DPREALLOCATE=1 -mcmodel=medany -static -std=gnu99 -O2 -ffast-math -fno-common -fno-builtin-printf -fno-tree-loop-distribute-patterns \
    -lm \
    -o dhrystone \
    dhrystone.c dhrystone_main.c ${GEM5_HOME}/util/m5/src/abi/riscv/m5op.S
