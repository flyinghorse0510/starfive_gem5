/**
 * Copyright Starfive Pvt Ltd 2023
 */

#ifndef __D2DCrMsg_HH__
#define __D2DCrMsg_HH__

#include <iostream>

#include "mem/ruby/slicc_interface/RubySlicc_Util.hh"
#include "mem/ruby/protocol/Message.hh"

namespace gem5
{

	namespace ruby
	{
		class D2DCrMsg : public Message
        {
            public:
                D2DCrMsg(Tick curTick) : Message(curTick), m_cr_inc(true) {}

                D2DCrMsg(const D2DCrMsg&) = default;

                D2DCrMsg &operator=(const D2DCrMsg&) = default;

                MsgPtr clone() const { return std::shared_ptr<Message>(new D2DCrMsg(*this)); }

                void print(std::ostream& out) const {
                    out << "[D2DCrMsg: " << m_cr_inc <<"]\n";
                }
            
            private:
                bool m_cr_inc; // Just a placeholder not required

        };

        inline ::std::ostream& operator<<(::std::ostream& out, const D2DCrMsg& obj) {
            obj.print(out);
			out << ::std::flush;
			return out;
        }
	}

}

#endif /* __D2DCrMsg_HH__ */
