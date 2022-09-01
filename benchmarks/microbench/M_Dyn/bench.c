#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#include <stdlib.h>     /* malloc, free, rand */


#define AMULT 65536
#define ASIZE    32
#define AMASK (ASIZE-1)
#define ITERS  4096


int arr1[ASIZE*AMULT];
int arr2[ASIZE*AMULT];

__attribute__ ((noinline,aligned(32)))
int loop(int zero) {
  int acc1 = 1, count=0;
  int acc2 = 2;
 
  unsigned lfsr = 0xACE1u;
  unsigned lfsr2 = 0x0143u;

  do
  {
      /* taps: 16 14 13 11; feedback polynomial: x^16 + x^14 + x^13 + x^11 + 1 */
      lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u);    
      acc1 += arr1[(lfsr&AMASK)*AMULT];

      //printf("write %d, ",lfsr&AMASK);      

      lfsr2 = (lfsr2 >> 1) ^ (-(lfsr2 & 1u) & 0xB400u);
      acc2+=1;
      arr1[(lfsr2&AMASK)*AMULT]=acc2;
 
      //printf("read %d\n",lfsr&AMASK);      
  } while(++count < ITERS);
  //} while(lfsr != 0xACE1u);

  return acc1;
}


int main(int argc, char* argv[]) {
   argc&=10000;
memset(arr1, 0, sizeof(arr1));
memset(arr2, 0, sizeof(arr2));
   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   int t=loop(argc); 
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile int a = t;
}

