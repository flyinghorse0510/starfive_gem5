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

        uint32_t dat_control_bits; // [TODO]: Make it a class variable

        double m_wrr_weight; // [TODO]: Make it a class variable

        uint32_t m_d2dbits_sent_this_cyc; // Bits sents through d2d this cyc

        Tick m_time_last_time_d2dbits_sent;

        uint32_t m_total_service_rcvd_d2dbits;

        Tick m_time_service_start;

        uint32_t getRdyMsgSize(Tick curTick, bool minTransmissible) const;

        uint32_t getMaxTransmissibleDataBits(Tick curTick, uint32_t d2d_rem_bw) const;

        void incrementServiceCount(uint32_t serviceCountBits);

    public:
        CHIPort() : D2DBridgePort(0, nullptr),
            m_vnet_id(1),
            dat_control_bits(98),
            m_wrr_weight(0.0),
            m_d2dbits_sent_this_cyc(0),
            m_time_last_time_d2dbits_sent(0),
            m_total_service_rcvd_d2dbits(0),
            m_time_service_start(0) {}

        CHIPort(uint32_t message_size, \
                uint32_t vnet_id, \
                MessageBuffer* buffer, \
                double wrr_weight) 
            : D2DBridgePort(message_size, buffer),
              m_vnet_id(vnet_id),
              dat_control_bits(98),
              m_wrr_weight(wrr_weight),
              m_d2dbits_sent_this_cyc(0),
              m_time_last_time_d2dbits_sent(0),
              m_total_service_rcvd_d2dbits(0),
              m_time_service_start(0) {}
        
        void setConsumer(D2DBridge* bridge) override;

        int32_t getVnetId() const { return m_vnet_id; }

        uint32_t getMinTransmissibleData(Tick curTick) const;

        bool hasTransmissibleData(Tick curTick, uint32_t d2d_rem_bw) const;
        
        bool hasRdyData(Tick curTick) const;

        Tick dequeue(Tick current_time);

        bool enqueue(MsgPtr message, Tick curTick, Tick delta);

        const Message* scheduleMsgForD2D(Tick curTick,\
                                    uint32_t& d2d_rem_bw,\
									bool& can_send,\
									bool& can_deq);

        void resetServiceCount(Tick curTick);

        double getServiceShare(Tick curTick, uint32_t total_share) const;
};

class D2DPort : public D2DBridgePort {
    
    public:
        D2DPort() : D2DBridgePort(0, nullptr) {}

        D2DPort(uint32_t message_size, \
                MessageBuffer* buffer)
            : D2DBridgePort(message_size, buffer) {
                panic_if(buffer->params().buffer_size > 0,"%s: D2D ports have credit based flow control\n",buffer->name());
            }
        
        void setConsumer(D2DBridge* bridge) override;

        void send(Tick curTick, const MsgPtrVec& msgptrvec, Tick delta);

        void extractCHIMessages(Tick curTick, std::vector<std::vector<MsgPtr>> &chi_msg_from_d2d);

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

        void print(std::ostream& out) const {
            out << "[D2DBridge("
                << m_src_die_id << ","
                << m_dst_die_id << ")]";
        };

    private:
        static int MAX_VNETS;

        uint32_t m_src_die_id;
        
        uint32_t m_dst_die_id;

        std::vector<int> m_wrr_weights;

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

        MessageBuffer* m_d2d_cr_in;

        MessageBuffer* m_nw_cr_in;  // Credit recvd from D2DNode CHI controller. Which is a part of the NW or die

        MessageBuffer* m_d2d_cr_out;

        uint32_t m_pending_current_bw;   // How many bits can be sent in current tick

        const uint32_t m_max_d2d_bw;    // max d2d bw in bits

        const uint32_t m_d2d_traversal_latency; // d2d traversal latency

        Tick m_time_pending_current_bw;  // Time guard for m_pending_current_bw

        uint32_t m_active_cy_count;      // The number of cy when an a d2d flit is sent across

        uint32_t m_active_cy_count_share; // The number of cy when an a d2d flit is sent across mod the total weight

        uint32_t m_active_d2dbits_sent; // Total d2d bits sent out

        Tick m_time_last_time_active_cy_count; // Last time m_active_cy_count was updated

        std::vector<uint32_t> m_prio; // Priority of each of the channels

		MsgPtrVec m_chi_d2d_flits_out; // Flits selected for d2d link traversal

        Tick m_time_last_time_d2d_out_sent; // Tick when last time sent out a d2d flit

		std::vector<std::vector<MsgPtr>> m_chi_d2d_flits_in; // Sorted as per vnet

        Tick m_time_last_time_d2d_in_rcvd; // Tick when last time recvd a d2d flit from th m_d2d_in
        
        uint32_t m_num_credits; // Number of credits we have currently for transfer

        const uint32_t m_max_num_credits;

        Tick m_time_last_time_inc_credits; // Last time I recvd credits from peer d2d bridge

        Tick m_time_last_time_dec_credits; // Last time I consumed (send a D2DFlit) credits

        Tick m_time_last_time_rcvd_credits_from_nw; // Last time I recvd a credit from the NW side. TODO is this guard reqd

        void incCredits(Tick curTick);

        void decCredits(Tick curTick);

        void updateCredits(Tick cur_tick);

        bool noCHIChannelTransmissible(Tick curTick, uint32_t d2d_rem_bw) const;
        
        bool atleast1CHIChannelHasRdyData(Tick curTick) const;

        bool incrementActiveCyCount(bool can_send, Tick curTick);

        void updatePriorities(bool can_send, Tick curTick);

        void reEvaluateCHIPriorities(Tick curTick);

        void recvD2DMsg(Tick curTick);

        void sendCHIToNetwork(Tick curTick);

        void sendCHIOutTxBuffer(Tick curTick);

        void sendCreditsOut(Tick curTick);

        void storeCHIOutTxBuffer(Tick curTick, const Message* msg, uint32_t vnet_id);

        void clearCHIOutTxBuffer(Tick curTick);

        bool hasCredits(Tick curTick) const;
};

}
}
#endif /* __MEM_RUBY_NETWORK_D2DNODE_HH__ */
