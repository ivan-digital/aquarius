from typing import Annotated
from typing_extensions import TypedDict

# LangGraph imports
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Represents the state containing the conversation messages."""
    messages: Annotated[list, add_messages]


# Define a system prompt that embodies the agent’s personality.
SYSTEM_PROMPT = """
You are a friendly, upbeat AI assistant named Frankie.
You love chatting with humans, even if they only say a quick "hi" or "hey".
Respond with warmth, curiosity, and friendliness.
You can:
	1.	Search external resources for information.
	2.	Execute Python code in a sandbox.
Only use these capabilities if truly needed. 
"""


def build_langgraph(llm_client, facade):
    """
    Build a LangGraph that:
      - Has a chatbot node calling llm_client.chat_with_tools
      - Has 2 ToolNodes: one for 'search' tools, one for 'code' tools
      - Routes to the correct node depending on usage
      - Has a 'human_approval_node' to break out of loops / get clarification
      - Uses memory-based checkpoints
    """
    graph_builder = StateGraph(State)

    ###########################################################################
    # 1. Chatbot node
    ###########################################################################

    def chatbot_node(state: State) -> dict:
        """
        Calls your LLM with the entire set of Tools, *plus* a system prompt
        that defines the agent's personality and style.
        """
        print("\n[chatbot_node] Entering chatbot_node...")
        print(f"[chatbot_node] Current state messages: {state['messages']}")

        # 1. Start with a system message that gives the agent personality
        chat_msgs = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # 2. Add user / assistant messages from the conversation
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                chat_msgs.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                chat_msgs.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                chat_msgs.append({"role": "system", "content": msg.content})
            else:
                chat_msgs.append({"role": "user", "content": str(msg)})

        # 3. Call the LLM (tools can be used if the assistant triggers them)
        result = llm_client.chat_with_tools(
            messages=chat_msgs,
            tools=facade.tools
        )

        # Log and return
        print(f"[chatbot_node] LLM returned: {result['content']}")
        new_state = {
            "messages": [AIMessage(content=result["content"])]
        }
        print(f"[chatbot_node] Exiting chatbot_node, new state: {new_state}")
        return new_state

    ###########################################################################
    # 2. Human approval node
    ###########################################################################

    def human_approval_node_fn(state: State) -> dict:
        """
        A node for manual intervention if the system is truly stuck or needs
        explicit user clarification.
        """
        print("\n[human_approval_node] Entering human_approval_node...")
        return {
            "messages": [
                AIMessage(content=(
                    "I'm stuck or need clarification. "
                    "Please provide more context or restate your request."
                ))
            ]
        }

    ###########################################################################
    # 3. Search / Code tool nodes (basic placeholders or direct usage)
    ###########################################################################

    # If you want to handle these “manually,” you can do so.
    # Or just define them via ToolNode so they can be called automatically
    # when the LLM says "use search tool" or "use code tool."

    search_node = ToolNode(tools=facade.search_tools)
    code_node = ToolNode(tools=facade.code_tools)

    ###########################################################################
    # 4. Add these nodes to the graph
    ###########################################################################

    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("search_node", search_node)
    graph_builder.add_node("code_node", code_node)
    graph_builder.add_node("human_approval_node", human_approval_node_fn)

    ###########################################################################
    # 5. Routing logic
    ###########################################################################

    def choose_next_node(state: State) -> str:
        """
        Examines the last message's content and decides the next node.
        Adjust the logic as you prefer, e.g. how to detect usage
        of code or search commands.
        """
        print("\n[choose_next_node] Deciding next node...")

        if not state["messages"]:
            print("[choose_next_node] No messages, default to 'chatbot'.")
            return "chatbot"

        last_msg = state["messages"][-1]
        last_content = (last_msg.content or "").strip().lower()

        # If truly empty, optionally route to human approval or stay in chatbot
        if not last_content:
            print("[choose_next_node] Empty response, let's stay in 'chatbot'.")
            return "chatbot"

        # If the LLM explicitly calls out for certain tools:
        if "redditsearcher" in last_content or "googlesearcher" in last_content \
                or "arxivsearch" in last_content or "githubsearchenrich" in last_content:
            print("[choose_next_node] Found a search keyword, going to 'search_node'")
            return "search_node"

        if "executepython" in last_content:
            print("[choose_next_node] Found a code command, going to 'code_node'")
            return "code_node"

        # If the LLM repeatedly says it's stuck or wants more context,
        # you could route to human_approval_node. For example:
        # if "not sufficient" in last_content or "need more context" in last_content:
        #     return "human_approval_node"

        # Otherwise, remain in normal chatbot
        print("[choose_next_node] No special tool usage, staying in 'chatbot'")
        return "chatbot"

    # From chatbot, go to the chosen node
    graph_builder.add_conditional_edges(
        source="chatbot",
        path=choose_next_node
    )

    ###########################################################################
    # 6. Additional edges
    ###########################################################################

    # After search_node or code_node, return to chatbot
    graph_builder.add_edge("search_node", "chatbot")
    graph_builder.add_edge("code_node", "chatbot")

    # If we ever go to human_approval_node, the user can clarify or fix the conversation,
    # then we route back to chatbot afterward.
    graph_builder.add_edge("human_approval_node", "chatbot")

    # Also allow chatbot to remain in chatbot on subsequent runs
    graph_builder.add_edge("chatbot", "chatbot")

    # Entry point is always chatbot
    graph_builder.set_entry_point("chatbot")

    ###########################################################################
    # 7. Compile the graph with memory-based checkpoints
    ###########################################################################

    memory = MemorySaver()
    graph = graph_builder.compile(
        checkpointer=memory,
        interrupt_before=["search_node", "code_node", "human_approval_node"]
    )

    return graph
