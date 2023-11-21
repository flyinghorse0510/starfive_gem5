from m5.params import *
from m5.SimObject import SimObject
from m5.objects.ClockedObject import ClockedObject

class D2DBridge(ClockedObject):
    type = 'D2DBridge'
    cxx_header = "mem/ruby/network/d2d/D2DBridge.hh"
    cxx_class = 'gem5::ruby::D2DBridge'

    # Die Ids
    src_die_id = Param.Int("Source die Id")
    dst_die_id = Param.Int("Dest die Id")

    d2d_width = Param.Int("Die 2 die width")

    # CHI node on the die side
    chi_d2d_cntrl     = Param.RubyController("Attached CHI node on the NW side that will generate CHI packets")

    # D2D side message buffer
    d2d_incoming_link = Param.MessageBuffer("")
    d2d_outgoing_link = Param.MessageBuffer("")