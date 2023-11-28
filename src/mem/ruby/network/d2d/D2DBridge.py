from m5.params import *
from m5.SimObject import SimObject
from m5.objects.ClockedObject import ClockedObject

class D2DBridge(ClockedObject):
    type = 'D2DBridge'
    cxx_header = "mem/ruby/network/d2d/D2DBridge.hh"
    cxx_class = 'gem5::ruby::D2DBridge'

    # Die Ids
    src_die_id = Param.Int("Source die Id")
    dst_die_id = Param.UInt16("Dest die Id")

    # D2D link parameters
    d2d_width = Param.Int("d2d width")
    d2d_traversal_latency = Param.Int(1, "d2d traversal latency in cycles")

    # CHI node on the die side
    chi_d2d_cntrl     = Param.D2DNode_Controller("Attached CHI node on the NW side that will generate CHI packets")

    # D2D side message buffer
    d2d_incoming_link = Param.MessageBuffer("")
    d2d_outgoing_link = Param.MessageBuffer("")

    # Weighted RR arbiter weights for each channels
    wrr_weights = VectorParam.Int([1,1,1,2],"Weighted RR arbiter weights [req,snp,rsp,dat]")