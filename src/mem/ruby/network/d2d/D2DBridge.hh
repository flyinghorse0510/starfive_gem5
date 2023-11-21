#ifndef __MEM_RUBY_NETWORK_D2DNODE_HH__
#define __MEM_RUBY_NETWORK_D2DNODE_HH__

#include "sim/clocked_object.hh"
#include "mem/ruby/common/Consumer.hh"
#include "mem/ruby/common/TypeDefines.hh"
#include "mem/ruby/network/d2d/D2DBridge.hh"
#include "mem/ruby/protocol/D2DNode_Controller.hh"
#include "params/D2DBridge.hh"

namespace gem5
{

namespace ruby
{

class NetDest;
class MessageBuffer;
class SimpleNetwork;

class D2DBridgePort {

    protected:
        uint32_t message_size;

        MessageBuffer* buffer;

    public:
        D2DBridgePort(uint32_t message_size, MessageBuffer* buffer) 
            : message_size(message_size) ,
              buffer(buffer) {}

        virtual void setConsumer(D2DBridge* bridge) = 0;
};

class CHIPort : public D2DBridgePort {
    private:
        int32_t m_vnet_id;

    public:
        CHIPort() : D2DBridgePort(0, nullptr) {
            m_vnet_id = -1;
        }

        CHIPort(uint32_t message_size, \
                uint32_t vnet_id, \
                MessageBuffer* buffer) 
            : D2DBridgePort(message_size, buffer) {
                m_vnet_id = vnet_id;
            }
        
        void setConsumer(D2DBridge* bridge) override;
};

class D2DPort : public D2DBridgePort {
    
    public:
        D2DPort() : D2DBridgePort(0, nullptr) {}

        D2DPort(uint32_t message_size, \
                MessageBuffer* buffer)
            : D2DBridgePort(message_size, buffer) {}
        
        void setConsumer(D2DBridge* bridge) override;

};

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
        uint32_t m_src_die_id;
        
        uint32_t m_dst_die_id;

        D2DNode_Controller* m_chid2d_cntrl;

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

        D2DPort m_d2d_in;
        
        D2DPort m_d2d_out;

        std::vector<int> m_pending_message_count;
};

}
}
#endif /* __MEM_RUBY_NETWORK_D2DNODE_HH__ */
