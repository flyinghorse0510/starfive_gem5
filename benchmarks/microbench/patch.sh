#!/bin/bash
sed -i '1s/^/#ifdef ENABLE_GEM5\n#include <gem5\/m5ops.h>\n#endifi\n/' */bench.c
sed -i 's/m5_dump_stats(0,0);/#ifdef ENABLE_GEM5\nm5_dump_stats(0,0);\n#endif\n/g' */bench.c
sed -i 's/m5_reset_stats(0,0);/#ifdef ENABLE_GEM5\nm5_reset_stats(0,0);\n#endif\n/g' */bench.c
