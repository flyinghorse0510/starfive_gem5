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
      __asm__ __volatile__("fdiv.s f1, f2, f3");
      __asm__ __volatile__("fdiv.s f4, f4, f5");
      __asm__ __volatile__("fdiv.s f1, f2, f3");
      __asm__ __volatile__("fdiv.s f4, f4, f5");
      __asm__ __volatile__("fdiv.s f1, f2, f3");
      __asm__ __volatile__("fdiv.s f4, f4, f5");
      __asm__ __volatile__("fdiv.s f1, f2, f3");
      __asm__ __volatile__("fdiv.s f4, f4, f5");
      __asm__ __volatile__("fdiv.s f1, f2, f3");
      __asm__ __volatile__("fdiv.s f4, f4, f5");
      __asm__ __volatile__("fdiv.s f1, f2, f3");
      __asm__ __volatile__("fdiv.s f4, f4, f5");
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
