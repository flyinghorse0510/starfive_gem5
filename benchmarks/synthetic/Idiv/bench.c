#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>

#define ASIZE  8096
#define STEP    128
#define ITERS     1000

double arrA[ASIZE];
double arrB[ASIZE];

__attribute__ ((noinline)) 
void loop(int iters) {

    while(iters > 0)
    {
      __asm__ __volatile__("div a4, a4, a7"); 
      __asm__ __volatile__("div a6, a6, a7"); 
      __asm__ __volatile__("div t0, t0, a7"); 
      __asm__ __volatile__("div t1, t1, a7"); 
      __asm__ __volatile__("div t2, t2, a7"); 
      __asm__ __volatile__("div t3, t3, a7"); 
      __asm__ __volatile__("div t4, t4, a7"); 
      __asm__ __volatile__("div t4, t4, a7"); 
      __asm__ __volatile__("div t5, t5, a7"); 
      __asm__ __volatile__("div t6, t6, a7"); 
      iters--;
    }
}

int main(int argc, char* argv[]) {
   #ifdef ENABLE_GEM5
  m5_dump_reset_stats(0,0);
  #endif
 
   loop(ITERS); 
   #ifdef ENABLE_GEM5
    m5_dump_reset_stats(0,0);
    #endif

}
