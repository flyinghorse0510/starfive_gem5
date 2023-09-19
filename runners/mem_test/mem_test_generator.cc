#include <fstream>
#include <iostream>
#include <string>
#include <unistd.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <cstdio>
#include <random>
#include <pybind11/pybind11.h>
#include "mem_test_generator.hh"



namespace MemTest {
    bool test_generator(const std::string& path, int rowCount) {
        int fd = open_data_file(path.c_str());
        if (fd < 0) {
            fprintf(stderr, "Failed to create data file! FilePath ==> %s\n", path.c_str());
            return false;
        }

        DirectedMemTestEntry dataEntry = {};
        ssize_t dataEntryLength = sizeof(dataEntry);
        fprintf(stdout, "Data Entry Length: %lu\n", dataEntryLength);

        uint8_t cmdList[2] = {static_cast<uint8_t>(Command::ReadReq), static_cast<uint8_t>(Command::WriteReq)};
        for (int i = 0; i < rowCount; i++) {
            dataEntry.paddr++;
            dataEntry.memCmd = cmdList[i%2];
            dataEntry.blkSize = i % MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE + 1;
            dataEntry.data[i%MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE]++;
            if (!write_binary_entry(fd, dataEntry)) {
                fprintf(stderr, "Failed to write data file! Iteration ==> %d\n", i);
                close_data_file(fd);
                return false;
            }
        }

        return close_data_file(fd);
    }

    bool generate_seq2_mem_test(
        const std::string& path,
        uint64_t numPeers,
        uint64_t blockSize,
        uint64_t workingSet,
        uint64_t blockStrideBits,
        unsigned int percentReads,
        uint64_t baseAddr,
        bool addrInterleavedOrTiled,
        bool randomizeAcc
    ) {
        // fprintf(stderr, "per CPU working set not block aligned, workingSet=%lu, num_peers=%lu, blockSize=%lu\n", workingSet, numPeers, blockSize);
        if (workingSet % (numPeers*blockSize) != 0) {
            fprintf(stderr, "per CPU working set not block aligned, workingSet=%lu, num_peers=%lu, blockSize=%lu\n", workingSet, numPeers, blockSize);
            return false;
        }

        int fd = open_data_file(path.c_str());
        if (fd < 0) {
            fprintf(stderr, "Failed to create data file! FilePath ==> %s\n", path.c_str());
            return false;
        }

        // Special variables
        static unsigned int TESTER_PRODUCER_IDX;
        MEM_TEST_REQ_BLK_TYPE writeSyncDataBase = 0x8f1;

        // Create random engine
        std::random_device rDev;
        std::mt19937 rEngine(rDev());
        std::uniform_int_distribution<std::mt19937::result_type> rIntDist(0, 100);

        DirectedMemTestEntry dataEntry = {};
        dataEntry.blkSize = sizeof(MEM_TEST_REQ_BLK_TYPE);
        ssize_t dataEntryLength = sizeof(dataEntry);
        fprintf(stdout, "Data Entry Length: %lu\n", dataEntryLength);

        uint64_t numPerCPUWorkingBlocks = (workingSet / (numPeers*blockSize));
        for (unsigned int id = 0; id < numPeers; id++) {
            for (unsigned int i = 0; i < numPerCPUWorkingBlocks; i++) {
                // Access Address
                uint64_t effectiveBlockAddr = (addrInterleavedOrTiled) ? (baseAddr+(numPeers*i)+id) : (baseAddr+(numPerCPUWorkingBlocks*id)+i);
                if (blockStrideBits > 0) {
                    effectiveBlockAddr = effectiveBlockAddr<<blockStrideBits;
                }
                uint64_t effectiveAddr = effectiveBlockAddr<<(static_cast<uint64_t>(std::log2(blockSize)));
                dataEntry.paddr = effectiveAddr;

                unsigned cmdChoice = rIntDist(rEngine);
                bool isRead = (cmdChoice <= percentReads) ? true : false;
                if (isRead) {
                    // ReadReq
                    dataEntry.memCmd = Command::ReadReq;
                } else {
                    // WriteReq
                    dataEntry.memCmd = Command::WriteReq;
                }

                // Sync Data
                *(reinterpret_cast<MEM_TEST_REQ_BLK_TYPE*>(dataEntry.data)) = (TESTER_PRODUCER_IDX << 8) + (writeSyncDataBase++);

                if (!write_binary_entry(fd, dataEntry)) {
                    fprintf(stderr, "Failed to write data file! id ==> %u, i ==> %u\n", id, i);
                }
            }
        }

        return true;
    }

    int open_data_file(const char* path) {
        return open(path, O_RDWR | O_TRUNC | O_CREAT, S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH);
    }

    bool close_data_file(int fd) {
        return (close(fd) == 0);
    }

    bool write_binary_entry(int fd, const DirectedMemTestEntry& entry) {
        ssize_t entryLength = sizeof(entry);
        ssize_t writeLength = write(fd, reinterpret_cast<const void*>(&entry), entryLength);
        return (entryLength == writeLength);
    }
}

namespace py = pybind11;
PYBIND11_MODULE(mem_test_generator, m) {
    m.doc() = "StarFive gem5 MemTest data generator";

    m.def("test_generator", &MemTest::test_generator, py::arg("path") = "./mem_test/data/mem_test_data.bin", py::arg("rowCount") = 1000);
    m.def("generate_seq2_mem_test", &MemTest::generate_seq2_mem_test,
        py::arg("path"),
        py::arg("numPeers") = 1,
        py::arg("blockSize") = 64,
        py::arg("workingSet") = 1024,
        py::arg("blockStrideBits") = 0,
        py::arg("percentReads") = 50,
        py::arg("baseAddr") = 0x0,
        py::arg("addrInterleavedOrTiled") = false,
        py::arg("randomizeAcc") = false
    );
}