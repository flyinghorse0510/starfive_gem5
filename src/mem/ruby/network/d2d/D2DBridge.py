from m5.params import *
from m5.SimObject import SimObject
from m5.objects.ClockedObject import ClockedObject

class D2DBridge(ClockedObject):
    type = 'D2DBridge'
    cxx_header = "mem/ruby/network/d2d/D2DBridge.hh"
    cxx_class = 'gem5::ruby::D2DBridge'

    die_id    = Param.Int("Die Id")
    d2d_width = Param.Int("Die 2 die width")

    # Declare the message buffers
    reqOut = Param.MessageBuffer("")
    snpOut = Param.MessageBuffer("")
    rspOut = Param.MessageBuffer("")
    datOut = Param.MessageBuffer("")
    reqIn  = Param.MessageBuffer("")
    snpIn  = Param.MessageBuffer("")
    rspIn  = Param.MessageBuffer("")
    datIn  = Param.MessageBuffer("")

    d2dIn  = VectorResponsePort("Input from the NW side")
    d2dOut = VectorRequestPort("Output to the Bride side")

