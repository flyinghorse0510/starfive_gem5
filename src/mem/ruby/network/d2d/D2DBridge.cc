
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

void CHIPort::setConsumer(D2DBridge* bridge) {
    buffer->setConsumer(bridge);
}

void D2DPort::setConsumer(D2DBridge* bridge) {
    buffer->setConsumer(bridge);
}

D2DBridge::D2DBridge(const Params &p)
    : ClockedObject(p), 
      Consumer(this),
      m_src_die_id(p.src_die_id),
      m_dst_die_id(p.dst_die_id),
      m_chid2d_cntrl(dynamic_cast<D2DNode_Controller *>(p.chi_d2d_cntrl)) {
        
        m_chi_in = {
          CHIPort(87,0,m_chid2d_cntrl->params().bridge_reqOut),
          CHIPort(61,0,m_chid2d_cntrl->params().bridge_snpOut),
          CHIPort(30,0,m_chid2d_cntrl->params().bridge_rspOut),
          CHIPort(610,0,m_chid2d_cntrl->params().bridge_datOut),
        };

        m_chi_out = {
          CHIPort(87,0,m_chid2d_cntrl->params().bridge_reqIn),
          CHIPort(61,0,m_chid2d_cntrl->params().bridge_snpIn),
          CHIPort(30,0,m_chid2d_cntrl->params().bridge_rspIn),
          CHIPort(610,0,m_chid2d_cntrl->params().bridge_datIn),
        };

        m_d2d_in = D2DPort(512, p.d2d_incoming_link);

        m_d2d_out = D2DPort(512, p.d2d_outgoing_link);
    }

void D2DBridge::init() {
  for (auto it = m_chi_in.begin(); it != m_chi_in.end(); it++) {
    it->setConsumer(this);
  }

  m_d2d_in.setConsumer(this);
}

void D2DBridge::resetStats() {}

void D2DBridge::regStats() {
  ClockedObject::regStats();
}

void D2DBridge::wakeup() {
  panic_if("%s: wakeup not implemented\n",name());
}

D2DBridge::~D2DBridge() {}

}
}
