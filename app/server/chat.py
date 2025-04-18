# app/server/chat.py

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.graph import build_langgraph
from app.agent.facade import ToolsFacade

class ChatService:
    def __init__(self):
        self.tools_facade = ToolsFacade()
        self.graph = build_langgraph(self.tools_facade)

    def _serialize_messages(self, messages):
        serialized = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                role = "assistant"
                content = msg.content
            elif isinstance(msg, HumanMessage):
                role = "user"
                content = msg.content
            elif isinstance(msg, SystemMessage):
                role = "system"
                content = msg.content
            else:
                role = "unknown"
                content = str(msg)
            serialized.append({"role": role, "content": content})
        return serialized

    def process_message(self, user_id: str, message: str):
        input_data = {"messages": [HumanMessage(content=message)]}
        config = {"configurable": {"thread_id": user_id}}

        final_state = self.graph.invoke(input_data, config=config)
        all_messages = final_state["messages"] or []

        # Find the last assistant message
        assistant_msgs = [m for m in all_messages if isinstance(m, AIMessage)]
        if assistant_msgs:
            reply = assistant_msgs[-1].content
        else:
            reply = "No assistant response found."

        return reply, self._serialize_messages(all_messages)

    def get_history(self, user_id: str):
        state = self.graph.checkpointer.load_checkpoint(user_id)
        if not state:
            return []
        return self._serialize_messages(state.get("messages", []))