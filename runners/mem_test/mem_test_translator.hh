#ifndef _MEM_TEST_TRANSLATOR_HH_
#define _MEM_TEST_TRANSLATOR_HH_

#include "mem_test_data.hh"

namespace MemTest {
    bool translate_binary(const std::string& binaryPath, const std::string& textPath);
    int create_data_file(const char* path);
    int open_data_file(const char* path);
    bool close_data_file(int fd);
    bool read_binary_entry(int fd, DirectedMemTestEntry& entry);
    bool write_text_entry(int fd, const DirectedMemTestEntry& entry);
    ssize_t get_file_length(int fd);
}

#endif