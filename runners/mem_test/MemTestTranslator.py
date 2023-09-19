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

def customize_translator(dataTransParser) -> bool:
    return True

def translate_binary(binFilePath: str = "", textFilePath: str = "") -> bool:
    from build import mem_test_translator
    return mem_test_translator.translate_binary(binFilePath, textFilePath)