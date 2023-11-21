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

    # CHI side ports
    reqOut = RequestPort("CHI Outgoing")
    snpOut = RequestPort("CHI Outgoing")
    rspOut = RequestPort("CHI Outgoing")
    datOut = RequestPort("CHI Outgoing")
    reqIn  = ResponsePort("CHI Incoming")
    snpIn  = ResponsePort("CHI Incoming")
    rspIn  = ResponsePort("CHI Incoming")
    datIn  = ResponsePort("CHI Incoming")

    # D2D side ports
    d2dIn  = ResponsePort("D2D Outgoing")
    d2dOut = RequestPort("D2D Incoming")

    # Activating Buffers
    chi_d2d_cntrl   = Param.RubyController("External node")

    # def connectOtherDie(self,options,other):
    #     other.d2dOut = MessageBuffer(buffer_size=2,
    #                                  max_dequeue_rate=1,
    #                                  ordered=True,
    #                                  randomization='ruby_system')
    #     self.d2dIn   = other.d2dOut