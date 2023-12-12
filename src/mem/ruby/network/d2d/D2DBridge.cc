
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
#include <numeric>
#include <limits>
#include <utility>
#include <typeinfo>

#include "params/D2DBridge.hh"
#include "sim/clocked_object.hh"
#include "mem/ruby/common/Consumer.hh"
#include "mem/ruby/common/TypeDefines.hh"
#include "mem/ruby/network/d2d/D2DBridge.hh"
#include "mem/ruby/network/d2d/D2DMsg.hh"
#include "mem/ruby/protocol/D2DCrMsg.hh"
#include "mem/ruby/protocol/D2DNode_Controller.hh"
#include "params/D2DNode_Controller.hh"
#include "debug/RubyD2DStr5.hh"

namespace gem5
{

	namespace ruby
	{

		void CHIPort::setConsumer(D2DBridge* bridge) {
			buffer->setConsumer(bridge);
		}

		uint32_t CHIPort::getMinTransmissibleData(Tick curTick) const {
			assert(curTick >= m_time_last_time_d2dbits_sent);
			uint32_t min_Transmissible_size = 0; // Minimum Transmissible size, if the message can be split
			if (curTick > m_time_last_time_d2dbits_sent) {
				min_Transmissible_size = getRdyMsgSize(curTick, true);
			} else {
				if (getRdyMsgSize(curTick, true) > m_d2dbits_sent_this_cyc) {
					min_Transmissible_size = getRdyMsgSize(curTick, true) - m_d2dbits_sent_this_cyc;
				}
			}
			return min_Transmissible_size;
		}

		void CHIPort::resetServiceCount(Tick curTick) {
			m_total_service_rcvd_d2dbits = 0;
			m_time_service_start = curTick;
		}

		void CHIPort::incrementServiceCount(uint32_t serviceCountBits) {
			m_total_service_rcvd_d2dbits += serviceCountBits;
		}

		double CHIPort::getServiceShare(Tick curTick, uint32_t total_share) const {
			assert(curTick >= m_time_service_start);
			return ((static_cast<double>(m_total_service_rcvd_d2dbits))/(static_cast<double>(total_share)));
		}

		uint32_t CHIPort::getMaxTransmissibleDataBits(Tick curTick, uint32_t d2d_rem_bw) const {
			uint32_t ret = 0;
			switch(m_vnet_id) {
				case 0 : 
				case 1 : 
				case 2 : {
						 ret = getRdyMsgSize(curTick, false);
						 if (d2d_rem_bw >= ret) {
							 return ret;
						 } else {
							 return 0;
						 }
						 break;
					 }
				case 3 : {
						 int32_t  r2 = d2d_rem_bw - dat_control_bits;
						 if (r2 > 0) {
							 uint32_t r3 = d2d_rem_bw - dat_control_bits;
							 uint32_t num_bytes = r3/8 ;
							 return (num_bytes*8 + dat_control_bits);
						 } else {
							 return 0;
						 }
						 break;
					 }
			}
		}

		Tick CHIPort::dequeue(Tick current_time) {
			assert(buffer);
			buffer->dequeue(current_time,true);
		}

		const Message* CHIPort::scheduleMsgForD2D(Tick curTick,\
				uint32_t& d2d_rem_bw,\
				bool& can_consume_bw,\
				bool& can_deq) {
			assert(curTick >= m_time_last_time_d2dbits_sent);
			if (hasTransmissibleData(curTick, d2d_rem_bw)) {
				uint32_t max_Transmissible_data_bits = getMaxTransmissibleDataBits(curTick, d2d_rem_bw);
				assert(max_Transmissible_data_bits > 0);
				can_consume_bw = true;
				d2d_rem_bw = d2d_rem_bw - max_Transmissible_data_bits;
				if (curTick > m_time_last_time_d2dbits_sent) {
					m_time_last_time_d2dbits_sent = curTick;
					m_d2dbits_sent_this_cyc = max_Transmissible_data_bits;
				} else {
					m_d2dbits_sent_this_cyc += max_Transmissible_data_bits;
				}
				if (!hasTransmissibleData(curTick, d2d_rem_bw)) {
					can_deq = true;
				}
				incrementServiceCount(max_Transmissible_data_bits);
			}
			if (can_deq) {
				return buffer->peek();
			} else {
				return nullptr;
			}
		}

		uint32_t CHIPort::getRdyMsgSize(Tick curTick, bool minTransmissible) const {
			/**
			 * Aggregate the size of
			 * all the waiting messages, ready
			 * for transmissions. Guard it to 
			 * avoid multiple aggregations in 
			 * the same tick.
			 */
			uint32_t ret = 0;
			switch(m_vnet_id) {
				case 0 : 
				case 1 : 
				case 2 : { // req,snp,rsp message sizes are always fixed
						 assert(buffer);
						 if (buffer->isReady(curTick)) {
							 ret = message_size;
						 } else {
							 ret = 0;
						 }
						 break;
					 }
				case 3: { // dat message depends upon the byte enables
						assert(buffer);
						if (buffer->isReady(curTick)) {
							if (minTransmissible) {
								auto msgptr = buffer->peek();
								assert(typeid(*msgptr) == typeid(CHIDataMsg));
								const CHIDataMsg* msg = dynamic_cast<const CHIDataMsg*>(msgptr);
								const WriteMask& wmask = msg->getbitMask();
								/**
								 * The additional dat_control_bits includes the
								 * byte enables (64 bits) and other
								 * control bits
								 */
								ret = 8*(wmask.count()) + dat_control_bits;
							} else {
								ret = 8 + dat_control_bits;
							}
						} else {
							ret = 0;
						}
					}
			}
			return ret;
		}

		bool CHIPort::hasTransmissibleData(Tick curTick, uint32_t d2d_rem_bw) const {
			return ((getMinTransmissibleData(curTick) <= d2d_rem_bw) && (getMinTransmissibleData(curTick) > 0));
		}

		bool CHIPort::hasRdyData(Tick curTick) const {
			return (getMinTransmissibleData(curTick) > 0);
		}

		void D2DPort::setConsumer(D2DBridge* bridge) {
			buffer->setConsumer(bridge);
		}

		void D2DPort::send(Tick curTick, const MsgPtrVec& msgptrvec, Tick delta) {
			assert(buffer->areNSlotsAvailable(1,curTick)); // Credits based flow control so credits is assumed to avail when trying to send
			panic_if(msgptrvec.size() <= 0, "Trying to extract chi flits from empty d2d flits\n");
			MsgPtr d2dmsg = std::make_shared<D2DMsg>(curTick, msgptrvec);
			buffer->enqueue(d2dmsg,curTick,delta);
		}

		void D2DPort::extractCHIMessages(Tick curTick, std::vector<std::vector<MsgPtr>> &in_msg_d2d_chi) {

			while (buffer->isReady(curTick)) {
				const Message* in_msg = buffer->peek();
				const std::type_info& msg_type = typeid(*in_msg);

				assert(msg_type == typeid(D2DMsg));

				const D2DMsg* in_msg_d2d = dynamic_cast<const D2DMsg*>(in_msg);

				in_msg_d2d->extractCHIMessages(curTick, in_msg_d2d_chi);

				buffer->dequeue(curTick);
			}
		}

		int D2DBridge::MAX_VNETS = 4;

		D2DBridge::D2DBridge(const Params &p) : ClockedObject(p), 
		Consumer(this), 
		m_max_d2d_bw(p.d2d_width),
		m_d2d_traversal_latency(p.d2d_traversal_latency),
		m_src_die_id(p.src_die_id),
		m_dst_die_id(p.dst_die_id),
		m_wrr_weights(p.wrr_weights),
		m_pending_current_bw(p.d2d_width),
		m_time_pending_current_bw(0),
		m_active_cy_count(0),
		m_active_cy_count_share(0),
		m_active_d2dbits_sent(0),
		m_time_last_time_active_cy_count(0),
		m_time_last_time_d2d_out_sent(0),
		m_time_last_time_d2d_in_rcvd(0),
		m_prio({3,2,1,0}),
		m_chid2d_cntrl(p.chi_d2d_cntrl),
		m_chi_d2d_flits_in({}),
		m_chi_d2d_flits_out({}),
		m_num_credits(p.d2d_max_credits),
		m_max_num_credits(p.d2d_max_credits),
		m_time_last_time_inc_credits(0),
		m_time_last_time_dec_credits(0),
		m_d2d_cr_in(p.d2d_incoming_cr_link),
		m_d2d_cr_out(p.d2d_outgoing_cr_link),
		m_nw_cr_in(m_chid2d_cntrl->params().d2dnode_crdOut) {
			m_chi_in = {
				CHIPort(87,0,m_chid2d_cntrl->params().d2dnode_reqOut,m_wrr_weights[0]),
				CHIPort(61,1,m_chid2d_cntrl->params().d2dnode_snpOut,m_wrr_weights[1]),
				CHIPort(30,2,m_chid2d_cntrl->params().d2dnode_rspOut,m_wrr_weights[2]),
				CHIPort(610,3,m_chid2d_cntrl->params().d2dnode_datOut,m_wrr_weights[3]),
			};
			m_chi_out = {
				CHIPort(87,0,m_chid2d_cntrl->params().d2dnode_reqIn,m_wrr_weights[0]),
				CHIPort(61,1,m_chid2d_cntrl->params().d2dnode_snpIn,m_wrr_weights[1]),
				CHIPort(30,2,m_chid2d_cntrl->params().d2dnode_rspIn,m_wrr_weights[2]),
				CHIPort(610,3,m_chid2d_cntrl->params().d2dnode_datIn,m_wrr_weights[3]),
			};
			assert(m_chi_in.size() == 4);
			assert(m_wrr_weights.size() >= m_chi_in.size());
			m_d2d_in = D2DPort(512, p.d2d_incoming_link);
			m_d2d_out = D2DPort(512, p.d2d_outgoing_link);
			for (int vnet_id = 0; vnet_id < MAX_VNETS; vnet_id++) {
				m_chi_d2d_flits_in.push_back({});
			}
		}

		void D2DBridge::init() {
			for (auto it = m_chi_in.begin(); it != m_chi_in.end(); it++) {
				it->setConsumer(this);
			}
			m_d2d_in.setConsumer(this);
			m_nw_cr_in->setConsumer(this);
			m_d2d_cr_in->setConsumer(this);
		}

		void D2DBridge::resetStats() {}

		void D2DBridge::regStats() {
			ClockedObject::regStats();
		}

		void D2DBridge::updateCredits(Tick curTick) {
			if (curTick > m_time_pending_current_bw) {
				m_time_pending_current_bw = curTick;
				if (hasCredits(curTick)) {
					m_pending_current_bw = m_max_d2d_bw;
				}
			}
		}

		bool D2DBridge::noCHIChannelTransmissible(Tick curTick, uint32_t d2d_rem_bw) const {
			for (auto it = m_chi_in.begin(); it != m_chi_in.end(); it++) {
				if (it->hasTransmissibleData(curTick, d2d_rem_bw)) {
					return false;
				}
			}
			return true;
		}

		bool D2DBridge::atleast1CHIChannelHasRdyData(Tick curTick) const {
			for (auto it = m_chi_in.begin(); it != m_chi_in.end(); it++) {
				if (it->hasRdyData(curTick)) {
					return true;
				}
			}
			return false;
		}

		void D2DBridge::wakeup() {
			/**
			 * The wakeup is called when
			 * 1. Consumer tagged message buffer, 
			 *    have ready messages. Note that,
			 *    the MessageBuffer.isReady can 
			 *    still be false, if it has a finite
			 *    deq rate per clock cycle.
			 * 2. The wakeup schedules another wakeup in
			 *    a later clock cycle
			 * 
			 * Which means in a single tick
			 * 
			 * 1. Multiple wakeups can happen and is quite common
			 * 2. 
			 */


			/**
			 * Sweep through all the CHI channels.
			 * 1. If the channel is ready
			 * 2. And the top message fits in remaining D2D flit
			 * 3. Packetize and send
			 */

			updateCredits(clockEdge());

			uint32_t d2d_rem_bw = m_pending_current_bw;

			bool can_consume_bw = false;

			bool can_deq        = false;

			uint32_t k = 0; // [TODO] Output of Design a configurable arbitration policy

			clearCHIOutTxBuffer(clockEdge());

			// Sweep through each CHI channel and extract transmissible packets
			DPRINTF(RubyD2DStr5,"CrCount = %d\n",getNumCredits(clockEdge()));

			while(atleast1CHIChannelHasRdyData(clockEdge())) {

				auto vnet_id = m_prio[k];

				// Fast path, if the channel does not have any ready data
				if (!m_chi_in[vnet_id].hasRdyData(clockEdge())) {
					k = (k+1)%(m_chi_in.size());
					continue;
				}

				panic_if(!hasCredits(clockEdge()),"Ran out of credits\n");

				if(noCHIChannelTransmissible(clockEdge(), d2d_rem_bw)) {
					scheduleEvent(Cycles(1));
					break;
				}

				auto b = m_chi_in[vnet_id].scheduleMsgForD2D(clockEdge(), 
						d2d_rem_bw, 
						can_consume_bw,
						can_deq);

				if (can_consume_bw && can_deq) {
					// Buffer it before sending out
					storeCHIOutTxBuffer(clockEdge(),b,vnet_id);
				}
				k = (k+1)%(m_chi_in.size()); // [TODO] Output of Design a configurable arbitration policy
			}

			panic_if(!can_consume_bw && can_deq, "BW not consumed but can deq from CHI message\n");

			updatePriorities(can_consume_bw, clockEdge());

			m_pending_current_bw = d2d_rem_bw;

			sendCHIOutTxBuffer(clockEdge(),can_consume_bw, can_deq);

			sendCreditsOut(clockEdge());

			recvCredits(clockEdge());

			// Extract message from the incoming d2d links
			recvD2DMsg(clockEdge());

			sendCHIToNetwork(clockEdge());

		}

		void D2DBridge::recvD2DMsg(Tick curTick) {
			if (curTick > m_time_last_time_d2d_in_rcvd) {
				m_time_last_time_d2d_in_rcvd = curTick;
				m_d2d_in.extractCHIMessages(clockEdge(), m_chi_d2d_flits_in);
			}
		}

		void D2DBridge::sendCHIToNetwork(Tick curTick) {
			bool schedule_next_wakeup = false;
			for (int vnet_id = 0; vnet_id < MAX_VNETS; vnet_id++) {
				if ( m_chi_d2d_flits_in[vnet_id].size() > 0 ) {
					MsgPtr message = m_chi_d2d_flits_in[vnet_id].front();
					schedule_next_wakeup = m_chi_out[vnet_id].enqueue(message, clockEdge(), Cycles(1));
					pop_heap(m_chi_d2d_flits_in[vnet_id].begin(), m_chi_d2d_flits_in[vnet_id].end(), std::greater<MsgPtr>());
					m_chi_d2d_flits_in[vnet_id].pop_back();
				}
			}
			if (schedule_next_wakeup) {
				scheduleEvent(Cycles(1));
			}
		}

		void D2DBridge::clearCHIOutTxBuffer(Tick curTick) {
			/**
			 * Ensure that
			 * m_chi_d2d_flits_out contain all
			 * the transmissible flits in the
			 * current clock cycle only
			 */
			if (curTick > m_time_last_time_d2d_out_sent) {
				m_time_last_time_d2d_out_sent = curTick;
				m_chi_d2d_flits_out.clear();
			}
		}

		void D2DBridge::storeCHIOutTxBuffer(Tick curTick, const Message* b, uint32_t vnet_id) {
			assert(b);
			panic_if(curTick != m_time_last_time_d2d_out_sent,"Tmp CHI flit buffer contains stale data from the previous cycles");
			m_chi_d2d_flits_out.push_back(std::make_pair(vnet_id, b->clone()));
			m_chi_in[vnet_id].dequeue(curTick);
		}

		void D2DBridge::sendCHIOutTxBuffer(Tick curTick,  bool can_consume_bw, bool can_deq) {
			if (can_consume_bw) {
				if (can_deq) {
					panic_if(m_chi_d2d_flits_out.size() <= 0,"can_send asserted but m_chi_d2d_flits_out is empty\n");
					panic_if(curTick != m_time_last_time_d2d_out_sent,"Tmp CHI flit buffer contains stale data from the previous cycles");
					m_d2d_out.send(curTick, m_chi_d2d_flits_out, cyclesToTicks(Cycles(m_d2d_traversal_latency)));
				}
				decCredits(curTick);
			}
		}

		bool CHIPort::enqueue(MsgPtr message, Tick curTick, Tick delta) {
			// Return true of can enqueue
			if (buffer->areNSlotsAvailable(1, curTick)) {
				buffer->enqueue(message, curTick, delta);
				return true;
			}
			return false;
		}

		bool D2DBridge::incrementActiveCyCount(bool can_consume_bw, Tick curTick) {
			bool reset_chi_service_counts = false;
			if (can_consume_bw) {
				uint32_t total_weight = static_cast<uint32_t>(std::accumulate(m_wrr_weights.begin(),m_wrr_weights.end(),0));
				assert(curTick >= m_time_last_time_active_cy_count);
				if (curTick != m_time_last_time_active_cy_count) {
					m_time_last_time_active_cy_count = curTick;
					if ((m_active_cy_count_share+1) == total_weight) {
						reset_chi_service_counts = true;
					}
					m_active_d2dbits_sent = (m_active_cy_count_share+1)*m_max_d2d_bw;
					m_active_cy_count_share = (m_active_cy_count_share+1) % total_weight;
					m_active_cy_count++;
				}
			}
			return reset_chi_service_counts;
		}

		void D2DBridge::reEvaluateCHIPriorities(Tick curTick) {
			std::vector<double> shares(m_chi_in.size(), 0.0);
			for (auto it = m_chi_in.begin(); it != m_chi_in.end(); it++) {
				shares[it->getVnetId()] = it->getServiceShare(curTick, m_active_d2dbits_sent);
			}
			std::sort(m_prio.begin(), m_prio.end(), [&shares](int i, int j){ return shares[i] < shares[j]; });
		}

		void D2DBridge::updatePriorities(bool can_consume_bw, Tick curTick) {
			bool reset_chi_service_counts = incrementActiveCyCount(can_consume_bw, curTick);
			reEvaluateCHIPriorities(curTick);
			if (reset_chi_service_counts) {
				for (auto it = m_chi_in.begin(); it != m_chi_in.end(); it++) {
					it->resetServiceCount(curTick);
				}
			}
		}

		void D2DBridge::recvCredits(Tick curTick) {
			// assert(m_time_last_time_inc_credits <= curTick);
			if ((curTick > m_time_last_time_inc_credits) && m_d2d_cr_in->isReady(curTick)){
				m_time_last_time_inc_credits = curTick;
				const D2DCrMsg *msg = dynamic_cast<const D2DCrMsg*>(m_d2d_cr_in->peek());
				panic_if(msg == nullptr,"Cannot cast to D2DCrMsg\n");
				if (m_num_credits < m_max_num_credits) {
					m_num_credits++;
				}
				m_d2d_cr_in->dequeue(curTick,true);
				DPRINTF(RubyD2DStr5,"D2DBridge Cr recvd incrementing\n");
			}
		}

		void D2DBridge::decCredits(Tick curTick) {
			assert(m_time_last_time_dec_credits <= curTick);
			if (curTick > m_time_last_time_dec_credits) {
				m_time_last_time_dec_credits = curTick;
				panic_if(m_num_credits <= 0,"Dec credits called with insufficient credits");
				m_num_credits--;
			}
		}

		void D2DBridge::sendCreditsOut(Tick curTick) {
			if (curTick > m_time_last_time_rcvd_credits_from_nw) {
				m_time_last_time_rcvd_credits_from_nw = curTick;
				if (m_nw_cr_in->isReady(curTick)) {
					MsgPtr credOut = std::make_shared<D2DCrMsg>(curTick);
					assert(m_d2d_cr_out->areNSlotsAvailable(1,curTick));
					m_d2d_cr_out->enqueue(credOut,curTick,0);
					m_nw_cr_in->dequeue(curTick,true);
					DPRINTF(RubyD2DStr5,"D2DNode-->D2DBridge Cr flow\n");
				}
			}
		}

		bool D2DBridge::hasCredits(Tick curTick) const {
			// [TODO]: Check if any Tick guards required
			return (m_num_credits > 0);
		}

		uint32_t D2DBridge::getNumCredits(Tick curTick) const {
			return m_num_credits;
		}

		D2DBridge::~D2DBridge() {}

	}
}
