#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>

#define ASIZE 2048
#define STEP   128
#define ITERS 4096

__attribute__ ((noinline,aligned(32)))
int loop(int zero) {
  int t1 = 1 +zero;

  int i;
  for(i=zero; i < ITERS; i+=1) {
    t1*=t1;
  }
  return t1;
}

int main(int argc, char* argv[]) {
   argc&=10000;
   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   int t=loop(argc); 
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile int a = t;
}
