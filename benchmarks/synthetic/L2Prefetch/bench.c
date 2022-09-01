#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#include <stdlib.h>     /* malloc, free, rand */


#define ITERS    1
//#define LEN   131072
#define LEN   65536


struct ll {
  struct ll* _next;
  char arr[48];
} __attribute__((aligned(64)));

struct ll list[LEN];

__attribute__ ((noinline,aligned(32)))
int loop(int zero,struct ll* n) {
  int t = 0,iter;
  for(iter=0; iter < ITERS; ++iter) {
    struct ll* cur =n;
    while( (cur!=NULL)) {
      //t+=cur->val;
      cur=cur->_next;
    }
  }
  return t;
}

int main(int argc, char* argv[]) {
   argc&=10000;
   struct ll *n, *cur;

   int i;
   n=malloc(sizeof(struct ll));
   cur=n;
   for(i=0;i<LEN-1;++i) {
	 list[i]._next = &list[i+1];
   }

   list[LEN-1]._next=NULL;

   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   int t=loop(argc, &list[0]);
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile int a = t;
}
