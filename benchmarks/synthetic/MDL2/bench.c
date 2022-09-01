#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#include <stdlib.h>     /* malloc, free, rand */


#define ASIZE 2048
#define STEP   128
#define ITERS    1
#define LEN   2048

int arr[ASIZE];

struct ll {
  struct ll* _next;
  char padding[4096];
};

struct ll llarr[LEN];

__attribute__ ((noinline))
int loop(int zero,struct ll* n) {
  int t = 0,i,iter;
    struct ll* cur =n;
    while(cur!=NULL) {
      cur=cur->_next;
    }
  return t;
}

int main(int argc, char* argv[]) {
   argc&=10000;
   struct ll *n, *cur;

   int i;
   for(i=0;i<LEN-1;++i) {
       llarr[i]._next = &llarr[i+1];
   }

   llarr[LEN-1]._next=NULL;

   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   int t=loop(argc,llarr);
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile int a = t;
}
