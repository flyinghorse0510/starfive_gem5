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
      __asm__ __volatile__("addi a4, a4, 1"); 
      __asm__ __volatile__("addi a6, a6, 1"); 
      __asm__ __volatile__("addi t0, t0, 1"); 
      __asm__ __volatile__("addi t1, t1, 1"); 
      __asm__ __volatile__("addi t2, t2, 1"); 
      __asm__ __volatile__("addi t3, t3, 1"); 
      __asm__ __volatile__("addi t4, t4, 1"); 
      __asm__ __volatile__("addi t4, t4, 1"); 
      __asm__ __volatile__("addi t5, t5, 1"); 
      __asm__ __volatile__("addi t6, t6, 1"); 
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
