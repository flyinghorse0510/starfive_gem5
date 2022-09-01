#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>

#define ASIZE 2048
#define STEP   128
#define ITERS   20

__attribute__ ((noinline,aligned(32)))
int rec(int i){
  if(i==0) return 0;
  if(i==1) return 1;
  if(i<1024) {
    return rec(i-1)+rec(i/2);
  } else {
    return 5;
  }
}

__attribute__ ((noinline,aligned(32)))
int loop(int zero) {
  int t = 0,i,iter;
  for(iter=0; iter < ITERS; ++iter) {
    t+=rec(iter*8);
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
