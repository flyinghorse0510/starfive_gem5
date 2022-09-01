#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#include <string.h>

#define ASIZE  8096
#define STEP    128
#define ITERS     4

double arrA[ASIZE];
double arrB[ASIZE];

__attribute__ ((noinline,aligned(32))) 
double loop(int zero) {
  int i, iters;
  double t1;

  for(iters=zero; iters < ITERS; iters+=1) {
    for(i=zero; i < ASIZE; i+=1) {
      arrA[i]=arrA[i]*3.2 + arrB[i];
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

   volatile double a = t;
}
