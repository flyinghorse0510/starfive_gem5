#ifndef __MEM_RUBY_NETWORK_D2DNODE_HH__
#define __MEM_RUBY_NETWORK_D2DNODE_HH__

#include "sim/clocked_object.hh"
#include "mem/ruby/common/Consumer.hh"
#include "mem/ruby/common/TypeDefines.hh"
#include "mem/ruby/network/d2d/D2DBridge.hh"
#include "params/D2DBridge.hh"

namespace gem5
{

namespace ruby
{

class NetDest;
class MessageBuffer;
class SimpleNetwork;

class D2DBridge : public ClockedObject, public Consumer {

    public:
        PARAMS(D2DBridge);

        D2DBridge(const Params &p);
        void init();
        void resetStats();
        void regStats();
        ~D2DBridge();

        void wakeup();
        void print(std::ostream& out) const {};
    
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
        * Indexed by vnet.
        * Higher indices denote, higher
        * ids denote, higher priorities
        * 0: req
        * 1: snp
        * 2: rsp
        * 3: dat
        */
        std::vector<CHIPort> m_chi_in;
        std::vector<CHIPort> m_chi_out;

        struct D2DPort {
            uint32_t message_size;
            MessageBuffer* buffer;
        };

        // uint32_t m_chi_req_width;
        // uint32_t m_chi_snp_width;
        // uint32_t m_chi_rsp_width;
        // uint32_t m_chi_dat_width;
        // uint32_t m_d2d_width;

        std::vector<D2DPort> m_d2d_in;
        std::vector<D2DPort> m_d2d_out;

        std::vector<int> m_pending_message_count;
};

}
}
#endif /* __MEM_RUBY_NETWORK_D2DNODE_HH__ */
