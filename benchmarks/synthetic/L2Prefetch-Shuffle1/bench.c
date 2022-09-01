#include <stdlib.h>
#include "gem5/m5ops.h"

#define BUFFER_NUM_BITS						10
#define BUFFER_NUMBER						(1 << BUFFER_NUM_BITS)
unsigned char __attribute__((aligned(4096))) glbBuffer[4096 * BUFFER_NUMBER];
unsigned char * buffer0 = glbBuffer;

unsigned char * glbBuffers[BUFFER_NUMBER];

void initBuffers()
{
	int i;

	glbBuffers[0] = buffer0;
	for(i = 1; i < BUFFER_NUMBER; i++)
		glbBuffers[i] = glbBuffers[i - 1] + 4096;
	glbBuffers[0] = glbBuffers[1];
}

void init()
{
	unsigned int i;

	initBuffers();

	for(i = 0; i < 4096; i++)
		buffer0[i] = (unsigned char)(i * 1013);
}

__attribute__((noinline, aligned(32)))
void bufferCopy(unsigned int num0, unsigned int num1)
{
	unsigned int addr = 0, step = 1;
	unsigned short value = 0;
	int i;

	for(i = 0; i < 4096; i++)
	{
		unsigned int index = step & (BUFFER_NUMBER - 1);
		value += buffer0[addr] * buffer0[4095 - addr];
		glbBuffers[index][addr] = glbBuffers[BUFFER_NUMBER - 1 - index][value & 0xfff];
		addr = (addr + step + value) & 0xfff;
		step = (step + num0) % num1;
	}
}

void main(int argc, char * argv[])
{
	int base = 8;

#ifdef ENABLE_GEM5
	m5_reset_stats(0, 0);
#endif

	init();

	bufferCopy(base, 39 * base);

#ifdef ENABLE_GEM5
	m5_dump_stats(0, 0);
#endif

	volatile int a = 0;
}
