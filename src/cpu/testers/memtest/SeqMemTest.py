# Copyright (c) 2015, 2021 Arm Limited
# All rights reserved.
#
# The license below extends only to copyright in the software and shall
# not be construed as granting a license to any other intellectual
# property including but not limited to intellectual property relating
# to a hardware implementation of the functionality of the software
# licensed hereunder.  You may use the software subject to the license
# terms below provided that you ensure that this notice is replicated
# unmodified and in its entirety in all distributions of the software,
# modified or unmodified, in source code or in binary form.
#
# Copyright (c) 2005-2007 The Regents of The University of Michigan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from m5.params import *
from m5.proxy import *

from m5.objects.ClockedObject import ClockedObject

class SeqMemTest(ClockedObject):
    type = 'SeqMemTest'
    cxx_header = "cpu/testers/memtest/seqmemtest.hh"
    cxx_class = 'gem5::SeqMemTest'

    # Interval of packet injection, the size of the memory range
    # touched, and an optional stop condition
    interval = Param.Cycles(1, "Interval between request packets")
    size = Param.Unsigned(4194304, "Size of memory region to use (bytes)")
    base_addr_1 = Param.Addr(0x0, "Start of the first testing region")
    
    mod_stream_triad = Param.Bool(False, "Generate Stream TRIAD like Mem requestes. 2 independent loads, 1 dependent stores")
    
    working_set = Param.Addr(1024, "Working set(bytes). Must be a multiple of cache line size")
    max_loads = Param.Counter(1, "Number of loads to execute before exiting")
    #percent_reads = Param.Percent(65, "Percentage reads")
    percent_reads = Param.Percent(100, "Percentage reads")
    addr_intrlvd_or_tiled = Param.Bool(False,"If true the address partitioning across CPUs is interleaved [0,N,2N;1,N+1,2N+1;...]. Otherwise Tiled [0:N-1,N:2N-1]")

    num_cpus = Param.Counter(1, "Total number of CPUs")
    num_producers = Param.Counter(1, "Number of (write) producers")

    # Determine how often to print progress messages and what timeout
    # to use for checking progress of both requests and responses
    progress_interval = Param.Counter(1000000,
        "Progress report interval (in accesses)")
    progress_check = Param.Cycles(5000000, "Cycles before exiting " \
                                      "due to lack of progress")

    port = RequestPort("Port to the memory system")
    system = Param.System(Parent.any, "System this tester is part of")

    # Add the ability to supress error responses on functional
    # accesses as Ruby needs this
    suppress_func_errors = Param.Bool(False, "Suppress panic when "\
                                            "functional accesses fail.")
