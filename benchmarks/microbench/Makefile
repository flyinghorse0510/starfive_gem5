DIRS = $(dir $(wildcard */))

.PHONY: default all $(DIRS)

ifndef GEM5_HOME
	$(error GEM5_HOME is not set)
endif

default: PARENT = default
default: $(DIRS) 

all: PARENT = all
all: $(DIRS)

X86: PARENT = X86
X86: $(DIRS)

ARM: PARENT = ARM
ARM: $(DIRS)

RISCV_GEM5: PARENT = RISCV_GEM5
RISCV_GEM5: $(DIRS)

RISCV_RTL: PARENT = RISCV_RTL
RISCV_RTL: $(DIRS)

$(DIRS):
	$(MAKE) $(PARENT) -C $@

clean:
	rm -f */bench.X86
	rm -f */bench.ARM
	rm -f */bench.RISCV_GEM5
	rm -f */bench.RISCV_RTL
	rm -f */randArr.h 
