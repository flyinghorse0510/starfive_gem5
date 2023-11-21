
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
#include "mem/ruby/protocol/D2DNode_Controller.hh"
#include "params/D2DNode_Controller.hh"

namespace gem5
{

namespace ruby
{

D2DBridge::D2DBridge(const Params &p)
    : ClockedObject(p), 
      Consumer(this),
      m_src_die_id(p.src_die_id),
      m_dst_die_id(p.dst_die_id) {
        const auto chi_d2d_cntrl_ptr = dynamic_cast<D2DNode_Controller *>(p.chi_d2d_cntrl);
        const auto chid_d2d_cntr_params_ptr = reinterpret_cast<const D2DNode_ControllerParams &>(chi_d2d_cntrl_ptr->params());
        
        m_chi_in = {
          CHIPort(87,0,chid_d2d_cntr_params_ptr.reqIn),
          CHIPort(61,0,chid_d2d_cntr_params_ptr.snpIn),
          CHIPort(30,0,chid_d2d_cntr_params_ptr.rspIn),
          CHIPort(610,0,chid_d2d_cntr_params_ptr.reqIn),
        };

        m_chi_out = {
          CHIPort(87,0,chid_d2d_cntr_params_ptr.reqOut),
          CHIPort(61,0,chid_d2d_cntr_params_ptr.snpOut),
          CHIPort(30,0,chid_d2d_cntr_params_ptr.rspOut),
          CHIPort(610,0,chid_d2d_cntr_params_ptr.reqOut),
        };

    }

void D2DBridge::init() {}

void D2DBridge::resetStats() {}

void D2DBridge::regStats() {}

void D2DBridge::wakeup() {}

D2DBridge::~D2DBridge() {}

}
}
