#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>
#include "randArr.h"

#define ASIZE 2048
#define STEP   128
#define ITERS   48

__attribute__ ((noinline,aligned(32)))
int loopy_helper(int i,int zero){
  return (i*2+zero)*3+(i+zero)*(i+zero);
}

__attribute__ ((noinline,aligned(32)))
int func_loopy(int i,int zero){
  int l,k=i;
  if(i<16) {
    return loopy_helper(i+4,zero);
  }
  for(l=i-16; l < i+zero; ++l) {
    k+=(k+l+randArr[l])&0x10101;
    randArr[l]=loopy_helper(k,zero);
  }
  return k;
}

__attribute__ ((noinline,aligned(32)))
int func_no_loopy(int i ){
  return (i+10+randArr[i])%16;
}

__attribute__ ((noinline,aligned(32)))
int loop(int zero) {
  int t = 0,i,iter;

  for(iter=zero; iter < ITERS; ++iter) {
    t+=func_loopy(iter,zero);
  }

  for(iter=zero; iter < ITERS; ++iter) {
    t+=func_no_loopy(iter);
  }

  return t;
}

int main(int argc, char* argv[]) {
   argc&=10000;
  #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
   int t=loop(argc); 
  #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif
   volatile int a = t;
}
