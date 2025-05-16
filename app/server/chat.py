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
        # Rebuild the graph to pick up any stubs or updated configurations
        self.graph = build_langgraph(self.tools_facade)
        input_data = {"messages": [HumanMessage(content=message)]}
        config = {"configurable": {"thread_id": user_id}}
        # Execute the graph, fallback gracefully on recursion errors
        try:
            final_state = self.graph.invoke(input_data, config=config)
        except Exception as e:
            from langgraph.errors import GraphRecursionError
            if isinstance(e, GraphRecursionError):
                fallback = "I am not equipped to handle this task with the functions at my disposal."
                history = [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": fallback}
                ]
                return fallback, history
            raise

        # Process messages from final graph state
        all_messages = final_state["messages"] or []

        # Find the last assistant message, excluding end-node marker
        end_marker = "(Conversation ended.)"
        meaningful_msgs = [m for m in all_messages if isinstance(m, AIMessage) and m.content != end_marker]
        if meaningful_msgs:
            reply = meaningful_msgs[-1].content
        else:
            reply = "No assistant response found."

        return reply, self._serialize_messages(all_messages)

    def get_history(self, user_id: str):
        state = self.graph.checkpointer.load_checkpoint(user_id)
        if not state:
            return []
        return self._serialize_messages(state.get("messages", []))