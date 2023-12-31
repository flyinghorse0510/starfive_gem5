/*
 * Copyright (c) 2019-2021 ARM Limited
 * All rights reserved.
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 1999-2008 Mark D. Hill and David A. Wood
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "mem/ruby/network/MessageBuffer.hh"

#include <cassert>

#include "base/cprintf.hh"
#include "base/logging.hh"
#include "base/random.hh"
#include "base/stl_helpers.hh"
#include "debug/RubyQueue.hh"
#include "mem/ruby/system/RubySystem.hh"

#include "typeinfo"
#include "mem/ruby/protocol/CHIRequestMsg.hh"
#include "mem/ruby/protocol/CHIResponseMsg.hh"
#include "mem/ruby/protocol/CHIDataMsg.hh"
#include "mem/ruby/protocol/MemoryMsg.hh"
#include "mem/ruby/slicc_interface/RubyRequest.hh"
#include "debug/MsgBufDebug.hh"
#include "debug/TxnTrace.hh"
#include "debug/TxnLink.hh"
#include <set>
#include <regex>

namespace gem5
{

namespace ruby
{

using stl_helpers::operator<<;

MessageBuffer::MessageBuffer(const Params &p)
    : SimObject(p), m_stall_map_size(0), m_max_size(p.buffer_size),
    m_max_dequeue_rate(p.max_dequeue_rate), m_dequeues_this_cy(0),
    m_time_last_time_size_checked(0),
    m_time_last_time_enqueue(0), m_time_last_time_pop(0),
    m_last_arrival_time(0), m_strict_fifo(p.ordered),
    m_randomization(p.randomization),
    m_allow_zero_latency(p.allow_zero_latency),
    m_routing_priority(p.routing_priority),
    ADD_STAT(m_not_avail_count, statistics::units::Count::get(),
             "Number of times this buffer did not have N slots available"),
    ADD_STAT(m_msg_count, statistics::units::Count::get(),
             "Number of messages passed the buffer"),
    ADD_STAT(m_buf_msgs, statistics::units::Rate<
                statistics::units::Count, statistics::units::Tick>::get(),
             "Average number of messages in buffer"),
    ADD_STAT(m_retry_msgs, statistics::units::Count::get(),
             "Number of retry message"), 
    ADD_STAT(m_stall_time, statistics::units::Tick::get(),
             "Total number of ticks messages were stalled in this buffer"),
    ADD_STAT(m_stall_count, statistics::units::Count::get(),
             "Number of times messages were stalled"),
    ADD_STAT(m_avg_stall_time, statistics::units::Rate<
                statistics::units::Tick, statistics::units::Count>::get(),
             "Average stall ticks per message"),
    ADD_STAT(m_occupancy, statistics::units::Rate<
                statistics::units::Ratio, statistics::units::Tick>::get(),
             "Average occupancy of buffer capacity")
{
    m_msg_counter = 0;
    m_consumer = NULL;
    m_size_last_time_size_checked = 0;
    m_size_at_cycle_start = 0;
    m_stalled_at_cycle_start = 0;
    m_msgs_this_cycle = 0;
    m_priority_rank = 0;

    m_stall_msg_map.clear();
    m_input_link_id = 0;
    m_vnet_id = 0;

    m_buf_msgs = 0;
    m_stall_time = 0;

    m_dequeue_callback = nullptr;

    // stats
    m_not_avail_count
        .flags(statistics::nozero);

    m_msg_count
        .flags(statistics::nozero);

    m_buf_msgs
        .flags(statistics::nozero);

    m_retry_msgs
        .flags(statistics::nozero);

    m_stall_count
        .flags(statistics::nozero);

    m_avg_stall_time
        .flags(statistics::nozero | statistics::nonan);

    m_occupancy
        .flags(statistics::nozero);

    m_stall_time
        .flags(statistics::nozero);

    if (m_max_size > 0) {
        m_occupancy = m_buf_msgs / m_max_size;
    } else {
        m_occupancy = 0;
    }

    m_avg_stall_time = m_stall_time / m_msg_count;
}

unsigned int
MessageBuffer::getSize(Tick curTime)
{
    if (m_time_last_time_size_checked != curTime) {
        m_time_last_time_size_checked = curTime;
        m_size_last_time_size_checked = m_prio_heap.size();
    }

    return m_size_last_time_size_checked;
}

bool
MessageBuffer::areNSlotsAvailable(unsigned int n, Tick current_time)
{

    // fast path when message buffers have infinite size
    if (m_max_size == 0) {
        return true;
    }

    // determine the correct size for the current cycle
    // pop operations shouldn't effect the network's visible size
    // until schd cycle, but enqueue operations effect the visible
    // size immediately
    unsigned int current_size = 0;
    unsigned int current_stall_size = 0;

    if (m_time_last_time_pop < current_time) {
        // no pops this cycle - heap and stall queue size is correct
        current_size = m_prio_heap.size();
        current_stall_size = m_stall_map_size;
    } else {
        if (m_time_last_time_enqueue < current_time) {
            // no enqueues this cycle - m_size_at_cycle_start is correct
            current_size = m_size_at_cycle_start;
        } else {
            // both pops and enqueues occured this cycle - add new
            // enqueued msgs to m_size_at_cycle_start
            current_size = m_size_at_cycle_start + m_msgs_this_cycle;
        }

        // Stall queue size at start is considered
        current_stall_size = m_stalled_at_cycle_start;
    }

    // now compare the new size with our max size
    if (current_size + current_stall_size + n <= m_max_size) {
        return true;
    } else {
        DPRINTF(RubyQueue, "n: %d, current_size: %d, heap size: %d, "
                "m_max_size: %d\n",
                n, current_size + current_stall_size,
                m_prio_heap.size(), m_max_size);

        // DPRINTF(TxnTrace, "MessageBufferContents: %s\n",getMsgBufferContents());
        m_not_avail_count++;
        return false;
    }
}

const Message*
MessageBuffer::peek() const
{
    DPRINTF(RubyQueue, "Peeking at head of queue. Buffer size: %d.\n",m_prio_heap.size());
    const Message* msg_ptr = m_prio_heap.front().get();
    assert(msg_ptr);

    DPRINTF(RubyQueue, "Message: %s\n", (*msg_ptr));
    return msg_ptr;
}

// FIXME - move me somewhere else
Tick
random_time()
{
    Tick time = 1;
    time += random_mt.random(0, 3);  // [0...3]
    if (random_mt.random(0, 7) == 0) {  // 1 in 8 chance
        time += 100 + random_mt.random(1, 15); // 100 + [1...15]
    }
    return time;
}

std::string denseDst(const NetDest &n) {
    return n.getAllDestStr();
}

void
MessageBuffer::txntrace_print(MsgPtr message, \
                              const gem5::Tick& arrival_time, \
                              const bool arrivalOrDep)
{

    const std::type_info& msg_type = typeid(*(message.get()));

    // use regex to choose the port_name we want to print
    std::string port_name = name();
    // char link_info[50] = "\0";

    // if this line is reqRdy, skip this line
    if(port_name.find("reqRdy") != std::string::npos){
        return;
    } else if (port_name.find("snpRdy") != std::string::npos) {
        return;
    }
 
    // else we always print this line
    // zhiang: we added txSeqNum to CHI protocol msgs so that can print txSeqNum
    uint64_t txSeqNum = 0; 
    if (msg_type == typeid(RubyRequest)){
        const RubyRequest* msg = dynamic_cast<RubyRequest*>(message.get());
        txSeqNum = msg->getRequestPtr()->getReqInstSeqNum();
        std::string reqtor = "Seq";
        RubyRequestType const &typ = msg->getType();
        DPRINTF(TxnTrace, "txsn: %#018x, type: %s, isArrival: %d, addr: %#x, reqtor: %s, dest: %s\n", 
            txSeqNum,
            typ,
            arrivalOrDep,
            msg->getPhysicalAddress(),
            reqtor,
            std::string("---"));
        assert(txSeqNum != 0); // txsn should not be 0
        assert(msg->getRequestPtr() != nullptr); // requestPtr should not be nullptr
    }
    else if(msg_type == typeid(CHIRequestMsg)){
        const CHIRequestMsg* msg = dynamic_cast<CHIRequestMsg*>(message.get());
        txSeqNum = msg->gettxSeqNum();
        NetDest dst = msg->getDestination();
        MachineID const & reqtor = msg->getrequestor();
        CHIRequestType const & typ = msg->gettype();
        DPRINTF(TxnTrace, "txsn: %#018x, type: %s, isArrival: %d, addr: %#x, reqtor: %s, bufferSize: %d, dest: %s\n", 
            txSeqNum,
            typ,
            arrivalOrDep,
            msg->getaddr(),
            reqtor,
            getSize(curTick()),
            denseDst(dst));
    }
    else if (msg_type == typeid(CHIResponseMsg)){
        const CHIResponseMsg* msg = dynamic_cast<CHIResponseMsg*>(message.get());
        txSeqNum = msg->gettxSeqNum();
        MachineID const & reqtor = msg->getresponder();
        NetDest dst = msg->getDestination();
        CHIResponseType const & typ = msg->gettype();
        DPRINTF(TxnTrace, "txsn: %#018x, type: %s, isArrival: %d, addr: %#x, reqtor: %s, bufferSize: %d, dest: %s\n", 
            txSeqNum,
            typ,
            arrivalOrDep,
            msg->getaddr(),
            reqtor,
            getSize(curTick()),
            denseDst(dst));
    }
    else if (msg_type == typeid(CHIDataMsg)){
        const CHIDataMsg* msg = dynamic_cast<CHIDataMsg*>(message.get());
        NetDest dst = msg->getDestination();
        MachineID const & reqtor = msg->getresponder();
        txSeqNum = msg->gettxSeqNum();
        CHIDataType const & typ = msg->gettype();
        DPRINTF(TxnTrace, "txsn: %#018x, type: %s, isArrival: %d, addr: %#x, reqtor: %s, bufferSize: %d, dest: %s\n", 
            txSeqNum,
            typ,
            arrivalOrDep,
            msg->getaddr(),
            reqtor,
            getSize(curTick()),
            denseDst(dst));
    }
    else if (msg_type == typeid(MemoryMsg)){
        const MemoryMsg* msg = dynamic_cast<MemoryMsg*>(message.get());
        std::string reqtor = "Memory";
        txSeqNum = msg->gettxSeqNum();
        MemoryRequestType const & typ = msg->getType();
        DPRINTF(TxnTrace, "txsn: %#018x, type: %s, isArrival: %d, addr: %#x, bufferSize: %d, dest: %s\n", 
            txSeqNum,
            typ,
            arrivalOrDep,
            msg->getaddr(),
            getSize(curTick()),
            reqtor);
    }
}

void
MessageBuffer::enqueue(MsgPtr message, Tick current_time, Tick delta)
{
    // record current time incase we have a pop that also adjusts my size
    if (m_time_last_time_enqueue < current_time) {
        m_msgs_this_cycle = 0;  // first msg this cycle
        m_time_last_time_enqueue = current_time;
    }

    m_msg_counter++;
    m_msgs_this_cycle++;

    // Calculate the arrival time of the message, that is, the first
    // cycle the message can be dequeued.
    panic_if((delta == 0) && !m_allow_zero_latency,
           "Delta equals zero and allow_zero_latency is false during enqueue");
    Tick arrival_time = 0;

    // random delays are inserted if the RubySystem level randomization flag
    // is turned on and this buffer allows it
    if ((m_randomization == MessageRandomization::disabled) ||
        ((m_randomization == MessageRandomization::ruby_system) &&
          !RubySystem::getRandomization())) {
        // No randomization
        arrival_time = current_time + delta;
    } else {
        // Randomization - ignore delta
        if (m_strict_fifo) {
            if (m_last_arrival_time < current_time) {
                m_last_arrival_time = current_time;
            }
            arrival_time = m_last_arrival_time + random_time();
        } else {
            arrival_time = current_time + random_time();
        }
    }

    // Check the arrival time
    assert(arrival_time >= current_time);
    if (m_strict_fifo) {
        if (arrival_time < m_last_arrival_time) {
            panic("FIFO ordering violated: %s name: %s current time: %d "
                  "delta: %d arrival_time: %d last arrival_time: %d\n",
                  *this, name(), current_time, delta, arrival_time,
                  m_last_arrival_time);
        }
    }

    // If running a cache trace, don't worry about the last arrival checks
    if (!RubySystem::getWarmupEnabled()) {
        m_last_arrival_time = arrival_time;
    }

    // compute the delay cycles and set enqueue time
    Message* msg_ptr = message.get();
    assert(msg_ptr != NULL);

    assert(current_time >= msg_ptr->getLastEnqueueTime() &&
           "ensure we aren't dequeued early");

    msg_ptr->updateDelayedTicks(current_time);
    msg_ptr->setLastEnqueueTime(arrival_time);
    msg_ptr->setMsgCounter(m_msg_counter);

    // Insert the message into the priority heap
    m_prio_heap.push_back(message);
    push_heap(m_prio_heap.begin(), m_prio_heap.end(), std::greater<MsgPtr>());
    // Increment the number of messages statistic
    m_buf_msgs++;

    assert((m_max_size == 0) ||
           ((m_prio_heap.size() + m_stall_map_size) <= m_max_size));

    DPRINTF(RubyQueue, "Enqueue arrival_time: %lld, delta:%lld, Message: %s\n",
            arrival_time, delta, *(message.get()));

    profileRetry(message);

    // zhiang: print the txntrace message
    txntrace_print(message, arrival_time, true);
    // Schedule the wakeup
    assert(m_consumer != NULL);
    m_consumer->scheduleEventAbsolute(arrival_time);
    m_consumer->storeEventInfo(m_vnet_id);
}

Tick
MessageBuffer::dequeue(Tick current_time, bool decrement_messages)
{
    DPRINTF(RubyQueue, "Popping\n");
    assert(isReady(current_time));

    // get MsgPtr of the message about to be dequeued
    MsgPtr message = m_prio_heap.front();

    // get the delay cycles
    message->updateDelayedTicks(current_time);
    Tick delay = message->getDelayedTicks();

    // record previous size and time so the current buffer size isn't
    // adjusted until schd cycle
    if (m_time_last_time_pop < current_time) {
        m_size_at_cycle_start = m_prio_heap.size();
        m_stalled_at_cycle_start = m_stall_map_size;
        m_time_last_time_pop = current_time;
        m_dequeues_this_cy = 0;
    }
    ++m_dequeues_this_cy;

    pop_heap(m_prio_heap.begin(), m_prio_heap.end(), std::greater<MsgPtr>());
    m_prio_heap.pop_back();
    if (decrement_messages) {
        // Record how much time is passed since the message was enqueued
        m_stall_time += curTick() - message->getLastEnqueueTime();
        m_msg_count++;

        // If the message will be removed from the queue, decrement the
        // number of message in the queue.
        m_buf_msgs--;
        txntrace_print(message, curTick(), false);
    }

    // if a dequeue callback was requested, call it now
    if (m_dequeue_callback) {
        m_dequeue_callback();
    }

    return delay;
}

std::string MessageBuffer::getCHITypeStr(const MsgPtr& message) {
    const std::type_info& msg_type = typeid(*(message.get()));
    if (msg_type==typeid(CHIRequestMsg)) {
        const CHIRequestMsg* msg = dynamic_cast<CHIRequestMsg*>(message.get());
        return CHIRequestType_to_string(msg->gettype());
    } else if (msg_type==typeid(CHIResponseMsg)) {
        const CHIResponseMsg* msg = dynamic_cast<CHIResponseMsg*>(message.get());
        return CHIResponseType_to_string(msg->gettype());
    } else if (msg_type==typeid(CHIDataMsg)) {
        const CHIDataMsg* msg = dynamic_cast<CHIDataMsg*>(message.get());
        return CHIDataType_to_string(msg->gettype());
    } else {
        return std::string("NonCHIMessage");
    }
}

void
MessageBuffer::registerDequeueCallback(std::function<void()> callback)
{
    m_dequeue_callback = callback;
}

void
MessageBuffer::unregisterDequeueCallback()
{
    m_dequeue_callback = nullptr;
}

void
MessageBuffer::clear()
{
    m_prio_heap.clear();

    m_msg_counter = 0;
    m_time_last_time_enqueue = 0;
    m_time_last_time_pop = 0;
    m_size_at_cycle_start = 0;
    m_stalled_at_cycle_start = 0;
    m_msgs_this_cycle = 0;
}

void
MessageBuffer::recycle(Tick current_time, Tick recycle_latency)
{
    DPRINTF(RubyQueue, "Recycling.\n");
    assert(isReady(current_time));
    MsgPtr node = m_prio_heap.front();
    pop_heap(m_prio_heap.begin(), m_prio_heap.end(), std::greater<MsgPtr>());

    Tick future_time = current_time + recycle_latency;
    node->setLastEnqueueTime(future_time);

    m_prio_heap.back() = node;
    push_heap(m_prio_heap.begin(), m_prio_heap.end(), std::greater<MsgPtr>());
    m_consumer->scheduleEventAbsolute(future_time);
}

void
MessageBuffer::reanalyzeList(std::list<MsgPtr> &lt, Tick schdTick)
{
    while (!lt.empty()) {
        MsgPtr m = lt.front();
        assert(m->getLastEnqueueTime() <= schdTick);

        m_prio_heap.push_back(m);
        push_heap(m_prio_heap.begin(), m_prio_heap.end(),
                  std::greater<MsgPtr>());

        m_consumer->scheduleEventAbsolute(schdTick);

        DPRINTF(RubyQueue, "Requeue arrival_time: %lld, Message: %s\n",
            schdTick, *(m.get()));

        lt.pop_front();
    }
}

void
MessageBuffer::reanalyzeMessages(Addr addr, Tick current_time)
{
    DPRINTF(RubyQueue, "ReanalyzeMessages %#x\n", addr);
    assert(m_stall_msg_map.count(addr) > 0);

    //
    // Put all stalled messages associated with this address back on the
    // prio heap.  The reanalyzeList call will make sure the consumer is
    // scheduled for the current cycle so that the previously stalled messages
    // will be observed before any younger messages that may arrive this cycle
    //
    m_stall_map_size -= m_stall_msg_map[addr].size();
    assert(m_stall_map_size >= 0);
    reanalyzeList(m_stall_msg_map[addr], current_time);
    m_stall_msg_map.erase(addr);
}

void
MessageBuffer::reanalyzeAllMessages(Tick current_time)
{
    DPRINTF(RubyQueue, "ReanalyzeAllMessages\n");

    //
    // Put all stalled messages associated with this address back on the
    // prio heap.  The reanalyzeList call will make sure the consumer is
    // scheduled for the current cycle so that the previously stalled messages
    // will be observed before any younger messages that may arrive this cycle.
    //
    for (StallMsgMapType::iterator map_iter = m_stall_msg_map.begin();
         map_iter != m_stall_msg_map.end(); ++map_iter) {
        m_stall_map_size -= map_iter->second.size();
        assert(m_stall_map_size >= 0);
        reanalyzeList(map_iter->second, current_time);
    }
    m_stall_msg_map.clear();
}

void
MessageBuffer::stallMessage(Addr addr, Tick current_time)
{
    DPRINTF(RubyQueue, "Stalling due to %#x\n", addr);
    assert(isReady(current_time));
    assert(getOffset(addr) == 0);
    MsgPtr message = m_prio_heap.front();

    // Since the message will just be moved to stall map, indicate that the
    // buffer should not decrement the m_buf_msgs statistic
    dequeue(current_time, false);

    //
    // Note: no event is scheduled to analyze the map at a later time.
    // Instead the controller is responsible to call reanalyzeMessages when
    // these addresses change state.
    //
    (m_stall_msg_map[addr]).push_back(message);
    m_stall_map_size++;
    m_stall_count++;

}

bool
MessageBuffer::hasStalledMsg(Addr addr) const
{
    return (m_stall_msg_map.count(addr) != 0);
}

void
MessageBuffer::deferEnqueueingMessage(Addr addr, MsgPtr message)
{
    DPRINTF(RubyQueue, "Deferring enqueueing message: %s, Address %#x\n",
            *(message.get()), addr);
    (m_deferred_msg_map[addr]).push_back(message);
}

void
MessageBuffer::enqueueDeferredMessages(Addr addr, Tick curTime, Tick delay)
{
    assert(!isDeferredMsgMapEmpty(addr));
    std::vector<MsgPtr>& msg_vec = m_deferred_msg_map[addr];
    assert(msg_vec.size() > 0);

    // enqueue all deferred messages associated with this address
    for (MsgPtr m : msg_vec) {
        enqueue(m, curTime, delay);
    }

    msg_vec.clear();
    m_deferred_msg_map.erase(addr);
}

bool
MessageBuffer::isDeferredMsgMapEmpty(Addr addr) const
{
    return m_deferred_msg_map.count(addr) == 0;
}

void
MessageBuffer::profileRetry(MsgPtr message)
{
    const std::type_info& msg_type = typeid(*(message.get()));
    if(msg_type == typeid(CHIResponseMsg)) {
         const CHIResponseMsg* msg = dynamic_cast<CHIResponseMsg*>(message.get());
         CHIResponseType const & typ = msg->gettype();
         if(CHIResponseType_RetryAck == typ)
             m_retry_msgs++;
    }
}

void
MessageBuffer::print(std::ostream& out) const
{
    ccprintf(out, "[MessageBuffer: ");
    if (m_consumer != NULL) {
        ccprintf(out, " consumer-yes ");
    }

    // std::vector<MsgPtr> copy(m_prio_heap);
    // std::sort_heap(copy.begin(), copy.end(), std::greater<MsgPtr>());
    // ccprintf(out, "%s] %s", copy, name());
    ccprintf(out, "%s", name());
}

std::string MessageBuffer::getMsgBufferContents() const {
    /**
     * Print the Head of the message
     */
    std::vector<MsgPtr> copy(m_prio_heap);
    std::sort_heap(copy.begin(), copy.end(), std::greater<MsgPtr>());
    std::stringstream ss;
    unsigned count = 0;
    unsigned buf_size = 1; // copy.size();
    ss << "[";
    for (auto &msgptr : copy) {
        const std::type_info& msg_type = typeid(*(msgptr.get()));
        if (msg_type == typeid(RubyRequest)) {
            const RubyRequest* msg = dynamic_cast<RubyRequest*>(msgptr.get());
            ss << "addr: 0x" << std::hex << msg->getLineAddress() 
               << "|RubyRequest";
            if (count < (buf_size-1)) {
                ss << ", ";
            }
        } else if (msg_type == typeid(CHIRequestMsg)) {
            const CHIRequestMsg* msg = dynamic_cast<CHIRequestMsg*>(msgptr.get());
            NetDest net_dest = msg->getDestination();
            ss << "addr: 0x" << std::hex << msg->getaddr();
            ss << std::dec << "|" << msg->gettype()
               << "|" << msg->getrequestor()
               << "-->" << denseDst(net_dest)
               << "|" << msg->getallowRetry();
            if (count < (buf_size-1)) {
                ss << ", ";
            }
        } else if (msg_type == typeid(CHIResponseMsg)) {
            const CHIResponseMsg* msg = dynamic_cast<CHIResponseMsg*>(msgptr.get());
            ss << "addr: 0x" << std::hex << msg->getaddr()
               << "|" << msg->gettype();
            if (count < (buf_size-1)) {
                ss << ", ";
            }

        } else if (msg_type == typeid(CHIDataMsg)) {
            const CHIDataMsg* msg = dynamic_cast<CHIDataMsg*>(msgptr.get());
            ss << "addr: 0x" << std::hex << msg->getaddr()
               << "|" << msg->gettype();
            if (count < (buf_size-1)) {
                ss << ", ";
            }

        } else {
            ss << "undefined:";
            if (count < (buf_size-1)) {
                ss << ", ";
            }
        }
        count++;
        break;
    }
    ss << "]";
    return ss.str();
}

bool MessageBuffer::targetBufferName(const std::string target_str) const {
    std::string port_name = name();
    if (port_name.find(target_str) != std::string::npos) {
        return true;
    }
    return false;
}


bool
MessageBuffer::isReady(Tick current_time) const
{
    assert(m_time_last_time_pop <= current_time);
    bool can_dequeue = (m_max_dequeue_rate == 0) ||
                       (m_time_last_time_pop < current_time) ||
                       (m_dequeues_this_cy < m_max_dequeue_rate);
    bool is_ready = (m_prio_heap.size() > 0) &&
                   (m_prio_heap.front()->getLastEnqueueTime() <= current_time);
    // DPRINTF(TxnTrace,"can_dequeue: %d, is_ready: %d\n",can_dequeue,is_ready);
    if (!can_dequeue && is_ready) {
        // Make sure the Consumer executes next cycle to dequeue the ready msg
        m_consumer->scheduleEvent(Cycles(1));
    }
    return can_dequeue && is_ready;
}

Tick
MessageBuffer::readyTime() const
{
    if (m_prio_heap.empty())
        return MaxTick;
    else
        return m_prio_heap.front()->getLastEnqueueTime();
}

uint32_t
MessageBuffer::functionalAccess(Packet *pkt, bool is_read, WriteMask *mask)
{
    DPRINTF(RubyQueue, "functional %s for %#x\n",
            is_read ? "read" : "write", pkt->getAddr());

    uint32_t num_functional_accesses = 0;

    // Check the priority heap and write any messages that may
    // correspond to the address in the packet.
    for (unsigned int i = 0; i < m_prio_heap.size(); ++i) {
        Message *msg = m_prio_heap[i].get();
        if (is_read && !mask && msg->functionalRead(pkt))
            return 1;
        else if (is_read && mask && msg->functionalRead(pkt, *mask))
            num_functional_accesses++;
        else if (!is_read && msg->functionalWrite(pkt))
            num_functional_accesses++;
    }

    // Check the stall queue and write any messages that may
    // correspond to the address in the packet.
    for (StallMsgMapType::iterator map_iter = m_stall_msg_map.begin();
         map_iter != m_stall_msg_map.end();
         ++map_iter) {

        for (std::list<MsgPtr>::iterator it = (map_iter->second).begin();
            it != (map_iter->second).end(); ++it) {

            Message *msg = (*it).get();
            if (is_read && !mask && msg->functionalRead(pkt))
                return 1;
            else if (is_read && mask && msg->functionalRead(pkt, *mask))
                num_functional_accesses++;
            else if (!is_read && msg->functionalWrite(pkt))
                num_functional_accesses++;
        }
    }

    return num_functional_accesses;
}

// Arka: get the Message Type string representation
std::string getMsgTypeStr(const MsgPtr &message) {
  std::stringstream ss;
  const std::type_info& msg_type = typeid(*(message.get()));
  if (msg_type == typeid(RubyRequest)) {
    ss << "RubyRequest";
  } else if (msg_type == typeid(CHIRequestMsg)) {
    const CHIRequestMsg* msg = dynamic_cast<CHIRequestMsg*>(message.get());
    CHIRequestType const &typ = msg->gettype();
    ss << typ;
  } else if (msg_type == typeid(CHIResponseMsg)) {
    const CHIResponseMsg* msg = dynamic_cast<CHIResponseMsg*>(message.get());
    CHIResponseType const &typ = msg->gettype();
    ss << typ;
  } else if (msg_type == typeid(CHIDataMsg)) {
    const CHIDataMsg* msg = dynamic_cast<CHIDataMsg*>(message.get());
    CHIDataMsg const &typ = msg->gettype();
    ss << typ;
  } else {
    ss << "Uidentified";
  }
  return ss.str();
}

} // namespace ruby
} // namespace gem5
