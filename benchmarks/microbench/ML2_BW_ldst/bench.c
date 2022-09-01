#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#include <stdlib.h>     /* malloc, free, rand */


#define ASIZE  65536
#define STEP     128
#define ITERS  65536
#define LEN     2048


typedef struct dude {
  int p1,p2,p3,p4;
} dude;


__attribute__ ((aligned(64)))
dude arr[ASIZE];
__attribute__ ((noinline,aligned(32)))
int loop(int zero) {
  int t = 0, count=0;

  unsigned lfsr = 0xACE1u;
  do
  {
      count++;
      /* taps: 16 14 13 11; feedback polynomial: x^16 + x^14 + x^13 + x^11 + 1 */
      lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u);    

      arr[lfsr].p4=lfsr + arr[lfsr].p1 + arr[lfsr].p2 + arr[lfsr].p3;

      //lfsr = lfsr + arr[lfsr].p1;

  } while(++count < ITERS);
  //} while(lfsr != 0xACE1u);

  return t;
}


int main(int argc, char* argv[]) {
   argc&=10000;
	for(int i =0; i < ASIZE; i++)
	{
		arr[i].p1 = 0;
		arr[i].p2 = 0;
		arr[i].p3 = 0;
		arr[i].p4 = 0;

	}
   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   int t=loop(argc); 
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile int a = t;
}

