#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>

#define ASIZE 2048
#define STEP  1024
#define ITERS   16

int arr[ASIZE];

__attribute__ ((noinline,aligned(32)))
int loop(int zero) {
  int t = 0,i,iter;
  for(iter=0; iter < ITERS; ++iter) {
    for(i=zero; i < STEP; ++i) {
      arr[i]=i; 
    }
    t+=arr[ASIZE-1-zero];
  }
  return t;
}

int main(int argc, char* argv[]) {
   argc&=10000;
memset(arr, 0, sizeof(arr));
   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   int t=loop(argc); 
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile int a = t;
}
