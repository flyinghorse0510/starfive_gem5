/**
 * Copyright Starfive Pvt Ltd 2023
 */

#ifndef __D2DMsg_HH__
#define __D2DMsg_HH__

#include <iostream>

#include "mem/ruby/slicc_interface/RubySlicc_Util.hh"

#include "mem/ruby/protocol/Message.hh"
namespace gem5
{

	namespace ruby
	{

		class D2DMsg :  public Message
		{
			public:

				static int NUM_VNETS;

				D2DMsg(Tick curTime) : Message(curTime), m_msgptrvec({}) {}
				D2DMsg(const D2DMsg&) = default;
				D2DMsg &operator=(const D2DMsg&) = default;
				D2DMsg(const Tick curTime, const MsgPtrVec& local_msgptrvec)
					: Message(curTime)
				{
					panic_if(local_msgptrvec.size() <= 0, "Trying to extract chi flits from empty d2d flits\n");

					m_msgptrvec = local_msgptrvec;
				}
				MsgPtr
					clone() const
					{
						return std::shared_ptr<Message>(new D2DMsg(*this));
					}
				// Const accessors methods for each field
				/** \brief Const accessor method for msgptrvec field.
				 *  \return msgptrvec field
				 */
				const MsgPtrVec&
					getmsgptrvec() const
					{
						return m_msgptrvec;
					}
				// Non const Accessors methods for each field
				/** \brief Non-const accessor method for msgptrvec field.
				 *  \return msgptrvec field
				 */
				MsgPtrVec&
					getmsgptrvec()
					{
						return m_msgptrvec;
					}
				// Mutator methods for each field
				/** \brief Mutator method for msgptrvec field */
				void
					setmsgptrvec(const MsgPtrVec& local_msgptrvec)
					{
						m_msgptrvec = local_msgptrvec;
					}
				void print(std::ostream& out) const;

				void extractCHIMessages(Tick curTick, std::vector<std::vector<MsgPtr>> &) const;

				//private:
				/** A D2D message */
				MsgPtrVec m_msgptrvec;
		};

		const std::string demangle(const std::type_info& msg_type);

		inline ::std::ostream&
			operator<<(::std::ostream& out, const D2DMsg& obj)
			{
				obj.print(out);
				out << ::std::flush;
				return out;
			}

	} // namespace ruby
} // namespace gem5

#endif // __D2DMsg_HH__
