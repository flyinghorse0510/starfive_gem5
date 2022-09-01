#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>

#define ASIZE 8192
#define STEP   128


float arr[ASIZE];
float arr1[ASIZE];
float arr2[ASIZE];
float arr3[ASIZE];
float arr4[ASIZE];
float arr5[ASIZE];
float arr6[ASIZE];
float arr7[ASIZE];
float arr8[ASIZE];
float arr9[ASIZE];

__attribute__ ((noinline,aligned(32))) 
float loop3(int zero) {
  float f = 0;
  for(int i = 0; i < ASIZE; i+=1) {
    int ind=i&(STEP-1);
    arr1[ind]=i;
    arr2[ind]=i;
    arr3[ind]=i;
    arr4[ind]=i;
    arr5[ind]=i;
    arr6[ind]=i;
    arr7[ind]=i;
    arr8[ind]=i;
    arr9[ind]=i;
    //f=f*f*f*f*f*f*f*f*f*f*f;
  }
  return f;
}

int main(int argc, char* argv[]) {
   argc&=10000;
   //loop0(argc);
   //loop1(argc);
   //loop2(argc);
   memset(arr1, 6.3, sizeof(arr1));
   memset(arr2, 6.3, sizeof(arr2));
   memset(arr3, 6.3, sizeof(arr3));
   memset(arr4, 6.3, sizeof(arr4));
   memset(arr5, 6.3, sizeof(arr5));
   memset(arr6, 6.3, sizeof(arr6));
   memset(arr7, 6.3, sizeof(arr7));
   memset(arr8, 6.3, sizeof(arr8));
   memset(arr9, 6.3, sizeof(arr9));

   #ifdef ENABLE_GEM5
m5_reset_stats(0,0);
#endif
 
   float f =loop3(argc);
   #ifdef ENABLE_GEM5
m5_dump_stats(0,0);
#endif

   volatile float a = f;
}
