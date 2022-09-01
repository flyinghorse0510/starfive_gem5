#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#define ASIZE 65536
#define STEP   128
#define ITERS   32

int arr[ASIZE];

__attribute__ ((noinline,aligned(32)))
int loop(int zero) {
  int t = 0,i,iter;
  for(iter=zero; iter < ITERS; ++iter) {
    for(i=iter; i < ASIZE; i+=1024) {
      t += arr[i+0*128];
      t += arr[i+1*128];
      t += arr[i+2*128];
      t += arr[i+3*128];
      t += arr[i+4*128];
      t += arr[i+4*128+1];
      t += arr[i+6*128];
      t += arr[i+6*128+1];
    }
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
