#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#include <string.h>

#define ASIZE  8192
#define STEP    128
#define ITERS     2

float arrA[ASIZE];
float arrB[ASIZE];

__attribute__ ((noinline,aligned(32)))
float loop(int zero) {
  int i, iters;
  float t1;

  for(iters=zero; iters < ITERS; iters+=1) {
    for(i=zero; i < ASIZE; i+=1) {
      arrA[i]=arrA[i]*3.2f + arrB[i];
    }
    t1+=arrA[ASIZE-1];
  }

  return t1;
}

int main(int argc, char* argv[]) {
   memset(arrA, 6, sizeof(arrA));
   memset(arrB, 8, sizeof(arrB));
   argc&=10000;
   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   int t=loop(argc); 
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile float a = t;
}
