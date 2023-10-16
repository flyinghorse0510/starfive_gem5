
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

#ifndef __MEM_RUBY_NETWORK_D2DNODE_HH__
#define __MEM_RUBY_NETWORK_D2DNODE_HH__

#include <iostream>
#include <string>
#include <vector>

#include "mem/ruby/common/Consumer.hh"
#include "mem/ruby/common/TypeDefines.hh"

namespace gem5
{

namespace ruby
{

class NetDest;
class MessageBuffer;
class SimpleNetwork;

class D2DNode : public ClockedObject, public Consumer {

    public:
        D2DNode(const Params &p);
        void init();
        void resetStats();
        void regStats();
        ~D2DNode();

        void wakeup();
        void print(std::ostream& out);
    
    private:
        uint32_t m_die_id;

        struct CHIPort {
            uint32_t message_size;
            uint32_t vnet_id;
            MessageBuffer* buffer;
            CHIPort(uint32_t message_size, \
                    uint32_t vnet_id, \
                    MessageBuffer* buffer) 
                : message_size(message_size),
                  vnet_id(vnet_id), 
                  buffer(buffer) {}
        };

       /**
        * Indexed by vnet 
        * 0: req
        * 1: snp
        * 2: rsp
        * 3: dat
        */
        std::vector<CHIPort> m_chi_in;

        std::vector<CHIPort> m_chi_out;

        struct CXSPort {

            uint32_t message_size;

            MessageBuffer* buffer;
        };

        CXSPort m_cxs_in;

        CXSPort m_cxs_out;

        uint32_t m_chi_req_width;
        
        uint32_t m_chi_snp_width;
        
        uint32_t m_chi_rsp_width;
        
        uint32_t m_chi_dat_width;
        
        uint32_t m_cxs_width;

        std::vector<int> m_pending_message_count;

};

D2DNode::D2DNode(const Params &p) 
    : ClockedObject(p), 
      Consumer(this),
      m_die_id(p.die_id),
      m_chi_req_width(87),
      m_chi_snp_width(101),
      m_chi_rsp_width(67),
      m_chi_dat_width(610),
      m_cxs_width(512)
    {
        m_chi_in = {
            CHIPort(m_chi_req_width, 0, p.reqIn),
            CHIPort(m_chi_snp_width, 1, p.snpIn),
            CHIPort(m_chi_rsp_width, 2, p.rspIn),
            CHIPort(m_chi_dat_width, 3, p.datIn)
        };

        m_chi_out = {
            CHIPort(m_chi_req_width, 0, p.reqOut),
            CHIPort(m_chi_snp_width, 1, p.snpOut),
            CHIPort(m_chi_rsp_width, 2, p.rspOut),
            CHIPort(m_chi_dat_width, 3, p.datOut)
        };

}

}
}

#endif /* __MEM_RUBY_NETWORK_D2DNODE_HH__ */