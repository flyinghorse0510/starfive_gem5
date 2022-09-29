
from ruby import CHI_config

# CustomMesh parameters for a 4x4 mesh. Routers will have the following layout:
#
# 0 ---  1 ---  2 --- 3
# |      |      |     |
# 4 ---  5 ---  6 --- 7
# |      |      |     |
# 8 ---  9 ---  10 --- 11
# |      |      |     |
# 12 --- 13 --- 14 --- 15
#
# Default parameter are configs/ruby/CHI_config.py
#
class NoC_Params(CHI_config.NoC_Params):
    num_rows = 4
    num_cols = 4

# Specialization of nodes to define bindings for each CHI node type
# needed by CustomMesh.
# The default types are defined in CHI_Node and their derivatives in
# configs/ruby/CHI_config.py

class CHI_RNF(CHI_config.CHI_RNF):
    class NoC_Params(CHI_config.CHI_RNF.NoC_Params):
        router_list = list(range(16))

class CHI_HNF(CHI_config.CHI_HNF):
    class NoC_Params(CHI_config.CHI_HNF.NoC_Params):
        router_list = list(range(16))

class CHI_SNF_MainMem(CHI_config.CHI_SNF_MainMem):
    class NoC_Params(CHI_config.CHI_SNF_MainMem.NoC_Params):
        router_list = [14]

class CHI_SNF_BootMem(CHI_config.CHI_SNF_BootMem):
    class NoC_Params(CHI_config.CHI_SNF_BootMem.NoC_Params):
        router_list = [13]

class CHI_MN(CHI_config.CHI_MN):
    class NoC_Params(CHI_config.CHI_MN.NoC_Params):
        router_list = [3,7,11,15]

class CHI_RNI_DMA(CHI_config.CHI_RNI_DMA):
    class NoC_Params(CHI_config.CHI_RNI_DMA.NoC_Params):
        router_list = [12,13,14]

class CHI_RNI_IO(CHI_config.CHI_RNI_IO):
    # Used in FS mode
    class NoC_Params(CHI_config.CHI_RNI_IO.NoC_Params):
        router_list = [12,13,14]
