# 
# 
# 128-Bits Alignment
#
# Low <===================== 128 bits (Little Endian) =====================> High
# |<-------- 64 bits -------->|<- 8 bits ->|<- 8 bits ->|<------ 48 bits ------>|
#         Address(paddr)        Memcmd(42)    BlockSize   ExtraData(6 x uint8_t)
#            uint64_t            uint8_t       uint8_t          uint8_t[6]
# 
# 

def customize_generator(dataGenParser) -> bool:
    dataGenParser.add_argument("--output_path", type=str, default="")
    dataGenParser.add_argument("--output_file", type=str, default="mem_test_data.bin")
    dataGenParser.add_argument("--num_cpus", type=int, default=1)
    dataGenParser.add_argument("--num_dmas", type=int, default=0)
    dataGenParser.add_argument("--block_size", type=int, default=64)
    dataGenParser.add_argument("--working_set", type=int, default=1024)
    dataGenParser.add_argument("--block_stride_bits", type=int, default=0)
    dataGenParser.add_argument("--percent_reads", type=int, default=50)
    dataGenParser.add_argument("--base_addr", type=int, default=0x0)
    dataGenParser.add_argument("--row_count", type=int, default=1000)
    dataGenParser.add_argument("--addr_intrlvd_or_tiled", action='store_true')
    dataGenParser.add_argument("--randomize_acc", action='store_true')
    dataGenParser.add_argument("-t", "-T", "--target", dest="target", nargs="+", default=["seq2"])
    dataGenParser.set_defaults(addr_intrlvd_or_tiled=False)
    dataGenParser.set_defaults(randomize_acc=False)
    return True
    
def test_generator(options) -> bool:
    from build import mem_test_generator
    print("Begin generating [TEST_GENERATOR]")
    ret = mem_test_generator.test_generator(options.path, options.row_count)
    if ret:
        print("[TEST_GENERATOR] generated successfully ==> %s" %(options.path))
    else:
        print("[TEST_GENERATOR] generated with ERROR ==> %s" %(options.path))
    
    return ret

def generate_seq2_mem_test(options) -> bool:
    from build import mem_test_generator
    print("Begin generating [SEQ2_MEM_TEST]")
    options.num_peers = options.num_cpus + options.num_dmas
    ret = mem_test_generator.generate_seq2_mem_test(
        path = options.path, 
        numPeers = options.num_peers, 
        blockSize = options.block_size, 
        workingSet = options.working_set,
        blockStrideBits = options.block_stride_bits,
        percentReads = options.percent_reads,
        baseAddr = options.base_addr,
        addrInterleavedOrTiled = options.addr_intrlvd_or_tiled,
        randomizeAcc = options.randomize_acc
    )
    if ret:
        print("[SEQ2_MEM_TEST] generated successfully ==> %s" %(options.path))
    else:
        print("[SEQ2_MEM_TEST] generated with ERROR ==> %s" %(options.path))
    
    return ret
    

genCmdDict = {
    "test": test_generator,
    "seq2": generate_seq2_mem_test
}

def generate(options):
    # Generate test
    for i in range(len(options.target)):
        genCmdDict[options.target[i]](options)
    