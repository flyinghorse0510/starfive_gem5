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

class DieNodeDistribution(object):
    """
        Mapping from CPU to corresponding
        dieId
    """
    _on_die_map = dict()
    _num_dies   = 4
    
    @classmethod
    def get_die_id(cls, node_id):
        return cls._on_die_map.get(node_id, -1)
    
    @classmethod
    def setup_die_map(cls, num_dies):
        cls._num_dies = num_dies
        cls._on_die_map = dict([(k, k % cls._num_dies) for k in range(100)])

class DieCPUDistribution(DieNodeDistribution):
    pass

class DieHADistribution(DieNodeDistribution):
    pass

class DieD2DDistribution(DieNodeDistribution):
    pass

class DieSNFDistribution(DieNodeDistribution):
    pass

class DieHNFDistribution(DieNodeDistribution):
    pass

class NoC_Params(CHI_config.NoC_Params):
    num_rows = 4
    num_cols = 4

# Specialization of nodes to define bindings for each CHI node type
# needed by CustomMesh.
# The default types are defined in CHI_Node and their derivatives in
# configs/ruby/CHI_config.py

class CHI_RNF(CHI_config.CHI_RNF):
    class NoC_Params(CHI_config.CHI_RNF.NoC_Params):
        die_plcmnt_map = dict({
            0: list(range(16)),
            1: list(range(16)),
            2: list(range(16)),
            3: list(range(16))
        })

class CHI_HNF(CHI_config.CHI_HNF):
    class NoC_Params(CHI_config.CHI_HNF.NoC_Params):
        die_plcmnt_map = dict({
            0: list(range(16)),
            1: list(range(16)),
            2: list(range(16)),
            3: list(range(16))
        })

class CHI_HNF_Snoopable(CHI_config.CHI_HNF_Snoopable):
    class NoC_Params(CHI_config.CHI_HNF_Snoopable.NoC_Params):
        die_plcmnt_map = dict({
            0: list(range(16)),
            1: list(range(16)),
            2: list(range(16)),
            3: list(range(16))
        })

class CHI_D2DNode(CHI_config.CHI_D2DNode):
    class NoC_Params(CHI_config.CHI_D2DNode.NoC_Params):
        die_plcmnt_map = dict({
            0: [7,14],
            1: [7,14],
            2: [7,14],
            3: [7,14]
        })

class CHI_HA(CHI_config.CHI_HA):
    class NoC_Params(CHI_config.CHI_HA.NoC_Params):
        die_plcmnt_map = dict({
            0: [5],
            1: [5],
            2: [5],
            3: [5]
        })

class CHI_SNF_MainMem(CHI_config.CHI_SNF_MainMem):
    class NoC_Params(CHI_config.CHI_SNF_MainMem.NoC_Params):
        die_plcmnt_map = dict({
            0: [3],
            1: [3],
            2: [3],
            3: [3]
        })

class CHI_SNF_BootMem(CHI_config.CHI_SNF_BootMem):
    class NoC_Params(CHI_config.CHI_SNF_BootMem.NoC_Params):
        die_plcmnt_map = dict({
            0: [13],
            1: [13],
            2: [13],
            3: [13]
        })

class CHI_MN(CHI_config.CHI_MN):
    class NoC_Params(CHI_config.CHI_MN.NoC_Params):
        die_plcmnt_map = dict({
            0: [11],
            1: [11],
            2: [11],
            3: [11]
        })


class CHI_RNI_DMA(CHI_config.CHI_RNI_DMA):
    class NoC_Params(CHI_config.CHI_RNI_DMA.NoC_Params):
        die_plcmnt_map = dict({
            0: [14],
            1: [14],
            2: [14],
            3: [14]
        })

class CHI_RNI_IO(CHI_config.CHI_RNI_IO):
    # Used in FS mode
    class NoC_Params(CHI_config.CHI_RNI_IO.NoC_Params):
        die_plcmnt_map = dict({
            0: [12],
            1: [12],
            2: [12],
            3: [12]
        })
