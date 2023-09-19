#ifndef _MEM_TEST_GENERATOR_HH_
#define _MEM_TEST_GENERATOR_HH_

#include "mem_test_data.hh"
#define MEM_TEST_REQ_BLK_TYPE uint16_t
namespace MemTest {

    bool test_generator(const std::string& path = "./mem_test/data/mem_test_data.bin", int rowCount = 1000);
    int open_data_file(const char* path);
    bool close_data_file(int fd);
    bool write_binary_entry(int fd, const DirectedMemTestEntry& entry);
    bool generate_seq2_mem_test(
        const std::string& path,
        uint64_t numPeers = 1,
        uint64_t blockSize = 64,
        uint64_t workingSet = 1024,
        uint64_t blockStrideBits = 0,
        unsigned int percentReads = 50,
        uint64_t baseAddr = 0x0,
        bool addrInterleavedOrTiled = false,
        bool randomizeAcc = false
    );
}

#endif