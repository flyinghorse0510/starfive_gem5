#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#include <stdlib.h>     /* malloc, free, rand */


#define ITERS    1
//#define LEN   524288
//#define LEN   131072
#define LEN   65536
#define LEN_ARR 1048576 


int drain_arr[LEN_ARR];

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

   int i;
	printf("Size of struct : %d\n", sizeof(struct ll));

	//int offsetArr[2] = {2, 3};
	int offsetArr[4] = {-1, 3, -1, 4};

	i = 0;
	while(i < LEN)
	{
		for(int j = 0; j < 4; j++)
		{
			int nextIndex = i + offsetArr[j];
			list[i]._next = &list[nextIndex];
			i = nextIndex; 
		}
	}

	list[i]._next = NULL;


   //for(i=0;i<LEN-1;++i) {
   //  list[i]._next = &list[i+1];
   //}

   //list[LEN-1]._next=NULL;
	volatile int z;
	for(int k = 0; k < LEN_ARR; k++)
	{
		z += drain_arr[k];
	}

   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   int t=loop(argc, &list[0]);
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile int a = t;
}
