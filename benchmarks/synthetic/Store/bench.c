#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>

#define ASIZE  8096
#define STEP    128
#define ITERS     1000

int arrA[ASIZE];
int arrB[ASIZE];

__attribute__ ((noinline)) 
void loop(int iters) {

    while(iters > 0)
    {
      __asm__ __volatile__("la a4, arrA"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
      __asm__ __volatile__("sw t0, (a4)"); 
      __asm__ __volatile__("sw t1, 4(a4)"); 
      __asm__ __volatile__("sw t2, 8(a4)"); 
      __asm__ __volatile__("sw t3, 12(a4)"); 
      __asm__ __volatile__("sw t4, 16(a4)"); 
      __asm__ __volatile__("sw t5, 20(a4)"); 
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
