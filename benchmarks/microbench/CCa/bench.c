#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>

#define ASIZE 2048
#define STEP   256
#define ITERS   32

__attribute__ ((noinline,aligned(32)))
int loop(int zero) {
  int t = 0,i,iter;
  for(iter=0; iter < ITERS; ++iter) {
    for(i=zero; i < STEP; i+=1) {
      if(i<zero)  {
        t+=3+3*t;
      } else {
        t-=1-5*t;
      }
    }
  }
  return t;
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
