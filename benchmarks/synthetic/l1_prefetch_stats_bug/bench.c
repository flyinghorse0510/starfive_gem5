#ifdef ENABLE_GEM5
#include <gem5/m5ops.h>
#endif
#include <stdio.h>

#define ASIZE  35000
#define STEP 8
#define ITERS     1

int arrA[ASIZE];
//double arrB[ASIZE];

//__attribute__ ((noinline,aligned(32)))
//void init_data(){
//	int i;
//	for( i=0 ; i<ASIZE ; i++ ){
//		arrA[i] = i;
//	}
//}	

__attribute__ ((noinline,aligned(32))) 
int loop(int iters) {

	int i,t=0;
	for( i=0 ; i<ASIZE ; i=i+STEP ){
		t += arrA[i];
		//printf("%d\n",i);
	}

	return t;
}

int main(int argc, char* argv[]) {
	
	//init_data();

	#ifdef ENABLE_GEM5
 	m5_reset_stats(0,0);
	#endif
 
	int t = loop(ITERS); 

	#ifdef ENABLE_GEM5
	m5_dump_stats(0,0);
	#endif

	volatile result = t;

}
