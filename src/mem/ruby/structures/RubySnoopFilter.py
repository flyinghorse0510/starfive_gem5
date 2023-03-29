

from m5.params import *
from m5.proxy import *
from m5.objects.ReplacementPolicies import *
from m5.SimObject import SimObject

class RubySnoopFilter(SimObject):
    type = 'RubySnoopFilter'
    cxx_class = 'gem5::ruby::SnoopFilter'
    cxx_header = "mem/ruby/structures/SnoopFilter.hh"

    size = Param.Int(4, "Number of Entries");
    assoc = Param.Int(2, "Associativity");
    start_index_bit = Param.Int(6, "index start, default 6 for 64-byte line");
    allow_infinite_entries = Param.Bool(False,"Allow infinite entries, incase of an ideal snoopfilter");