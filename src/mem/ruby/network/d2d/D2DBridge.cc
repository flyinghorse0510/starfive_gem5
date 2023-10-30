
/*
 * The D2DLink models the connections/protocols
 * between multiple dies. As an example, for
 * Starlink-2.0 each die uses a CHI protocol to 
 * communicate amongst on-chip agents (HNF, RNFs)
 * etc. And a special node, the D2D node is connected
 * to the mesh, which fwds traffic to a different node
 * The D2D node uses a protocol like CXS to communicate
 * amongst multiple dies.
 */


#include <iostream>
#include <string>
#include <vector>

#include "params/D2DBridge.hh"
#include "sim/clocked_object.hh"
#include "mem/ruby/common/Consumer.hh"
#include "mem/ruby/common/TypeDefines.hh"
#include "mem/ruby/network/d2d/D2DBridge.hh"

namespace gem5
{

namespace ruby
{

D2DBridge::D2DBridge(const Params &p) 
    : ClockedObject(p), 
      Consumer(this),
      m_die_id(p.die_id)
    {
        m_chi_in = {
            CHIPort(87, 0, p.reqIn),
            CHIPort(101, 1, p.snpIn),
            CHIPort(67, 2, p.rspIn),
            CHIPort(610, 3, p.datIn)
        };

        m_chi_out = {
            CHIPort(87, 0, p.reqOut),
            CHIPort(101, 1, p.snpOut),
            CHIPort(67, 2, p.rspOut),
            CHIPort(610, 3, p.datOut)
        };

        // for (auto ) {

        // } 

}

void D2DBridge::init() {}

void D2DBridge::resetStats() {}

void D2DBridge::regStats() {}

void D2DBridge::wakeup() {}

D2DBridge::~D2DBridge() {}

}
}
