#include <fstream>
#include <iostream>
#include <string>
#include <unistd.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <cstdio>
#include <pybind11/pybind11.h>
#include <inttypes.h>

#include "mem_test_translator.hh"

namespace MemTest {

    bool translate_binary(const std::string& binaryPath, const std::string& textPath) {
        int binFd = open_data_file(binaryPath.c_str());
        if (binFd < 0) {
            fprintf(stderr, "Failed to open binary file! Binary data path ==> %s\n", binaryPath.c_str());
            return false;
        }
        int textFd = create_data_file(textPath.c_str());
        if (textFd < 0) {
            close_data_file(binFd);
            fprintf(stderr, "Failed to create text file! Text data path ==> %s\n", textPath.c_str());
            return false;
        }

        ssize_t binaryFileLength = get_file_length(binFd);
        ssize_t binaryEntryLength = sizeof(DirectedMemTestEntry);
        if (binaryFileLength == 0) {
            close_data_file(binFd);
            close_data_file(textFd);
            fprintf(stderr, "Failed to get binary file info!\n");
            return false;
        }
        if (binaryFileLength % binaryEntryLength != 0) {
            close_data_file(binFd);
            close_data_file(textFd);
            fprintf(stderr, "Binary data entry length misalignment! Total Length ==> %lu, Entry Length ==> %lu\n", binaryFileLength, binaryEntryLength);
            return false;
        }

        long long numEntry = binaryFileLength / binaryEntryLength;
        fprintf(stdout, "Begin binary file translation: %s ==> %s ...\n", binaryPath.c_str(), textPath.c_str());
        DirectedMemTestEntry dataEntry = {};
        bool ret = false;
        for (long long i = 0; i < numEntry; i++) {
            ret = read_binary_entry(binFd, dataEntry);
            if (!ret) {
                fprintf(stderr, "Read binary entry failed! Iteration: %llu\n", i);
            }
            ret = write_text_entry(textFd, dataEntry);
            if (!ret) {
                fprintf(stderr, "Write text entry failed! Iteration: %llu\n", i);
            }
        }

        close_data_file(binFd);
        close_data_file(textFd);

        fprintf(stdout, "Finish translation!\n");
        return true;
    }

    bool read_binary_entry(int fd, DirectedMemTestEntry& entry) {
        ssize_t readLength = read(fd, reinterpret_cast<void*>(&entry), sizeof(entry));
        if (readLength != sizeof(entry)) {
            return false;
        }
        return true;
    }

    bool write_text_entry(int fd, const DirectedMemTestEntry& entry) {
        char buffer[sizeof(entry)*16] = {};
        ssize_t length = snprintf(buffer, sizeof(entry)*16-1, "%#018lx,%s,%" PRIu8 ",", entry.paddr, cmdStrArray[entry.memCmd], entry.blkSize);
        for (int i = 0; i < MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE; i++) {
            snprintf(buffer+length+5*i, sizeof(entry)*16 - 1 - length - 5*i ,"%#04x,", entry.data[i]);
        }
        snprintf(buffer+length+5*MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE, sizeof(entry)*16 - 1 - length - 5*MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE, "\n");
        ssize_t totalLength = length + 5*MEM_TEST_ENTRY_MAX_REQ_BLK_SIZE + 1;
        ssize_t writeLength = write(fd, reinterpret_cast<void*>(buffer), totalLength);
        if (writeLength != totalLength) {
            return false;
        }
        return true;
    }
    

    int create_data_file(const char* path) {
        return open(path, O_RDWR | O_TRUNC | O_CREAT, S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH);
    }

    int open_data_file(const char* path) {
        return open(path, O_RDONLY);
    }

    bool close_data_file(int fd) {
        return (close(fd) == 0);
    }

    ssize_t get_file_length(int fd) {
        struct stat fileInfo;
        int ret = fstat(fd, &fileInfo);
        if (ret < 0) {
            return 0;
        }
        return fileInfo.st_size;
    }
}

namespace py = pybind11;
PYBIND11_MODULE(mem_test_translator, m) {
    m.doc() = "StarFive gem5 MemTest data translator";

    m.def("translate_binary", &MemTest::translate_binary, py::arg("binaryPath"), py::arg("textPath"));

}