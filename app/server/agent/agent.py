from typing import Annotated
from typing_extensions import TypedDict

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from app.server.agent.facade import ToolsFacade
from app.server.agent.llm_client import LLMClient


class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_langgraph(llm_client: LLMClient, facade: ToolsFacade):
    """
    Build a LangGraph that:
      - Has a chatbot node calling llm_client.chat_with_tools
      - Has 2 ToolNodes: one for 'search' tools, one for 'code' tools
      - Routes to the correct node depending on LLM usage
      - Has a 'human_approval_node' to break out of loops / get clarification
    """
    graph_builder = StateGraph(State)

    ###########################################################################
    # 1. Chatbot node (unchanged)
    ###########################################################################

    def chatbot_node(state: State) -> dict:
        """
        Node that calls your LLM with the entire set of Tools.
        We transform each message in state['messages'] into a dict or string
        as required by llm_client.chat_with_tools(...).
        """
        print("\n[chatbot_node] Entering chatbot_node...")
        print(f"[chatbot_node] Current state messages: {state['messages']}")

        chat_msgs = []
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                chat_msgs.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                chat_msgs.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                chat_msgs.append({"role": "system", "content": msg.content})
            else:
                # If you're using a custom message class, adapt accordingly
                chat_msgs.append({"role": "user", "content": str(msg)})

        result = llm_client.chat_with_tools(messages=chat_msgs, tools=facade.tools)

        # Log the content returned by your LLM
        print(f"[chatbot_node] LLM returned: {result['content']}")

        # Return a new AIMessage
        new_state = {
            "messages": [AIMessage(content=result["content"])]
        }
        print(f"[chatbot_node] Exiting chatbot_node, new state: {new_state}")
        return new_state

    ###########################################################################
    # 2. "Human approval" node for manual intervention
    ###########################################################################

    def human_approval_node_fn(state: State) -> dict:
        """
        A node that indicates we need a human to review the conversation
        and provide clarifications if the system is stuck in a loop or ambiguous.
        """
        print("\n[human_approval_node] Entering human_approval_node...")

        # In a real system, you might store state in a DB, send an email/Slack alert, etc.
        # For now, we just provide a placeholder AIMessage:
        return {
            "messages": [
                AIMessage(content=(
                    "I'm stuck or need clarification. "
                    "Please provide more context or restate your request."
                ))
            ]
        }

    ###########################################################################
    # 3. Search / Code tool nodes (unchanged placeholders)
    ###########################################################################

    def search_node_fn(state: State) -> dict:
        print("\n[search_node] Entering search_node...")
        return {
            "messages": [AIMessage(content="Search tool result placeholder")]
        }

    def code_node_fn(state: State) -> dict:
        print("\n[code_node] Entering code_node...")
        return {
            "messages": [AIMessage(content="Code tool result placeholder")]
        }

    # Create optional tool-wrappers (if you need them)
    search_node = ToolNode(tools=facade.search_tools)
    code_node = ToolNode(tools=facade.code_tools)

    ###########################################################################
    # 4. Add all nodes to the graph
    ###########################################################################

    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("search_node", search_node)
    graph_builder.add_node("code_node", code_node)
    graph_builder.add_node("human_approval_node", human_approval_node_fn)

    ###########################################################################
    # 5. The routing logic
    ###########################################################################

    def choose_next_node(state: State) -> str:
        """
        Examines the last message's content to see whether it refers to a search or code tool,
        or if it is empty/ambiguous and needs human approval.
        """
        print("\n[choose_next_node] Deciding next node...")
        if not state["messages"]:
            print("[choose_next_node] No messages, defaulting to 'chatbot'")
            return "chatbot"

        last_msg = state["messages"][-1]
        last_content = last_msg.content.strip() if last_msg.content else ""
        print(f"[choose_next_node] Last message: {last_content}")

        # Detect empty or obviously stuck content
        if not last_content:
            print("[choose_next_node] Empty LLM response or no content. Going to 'human_approval_node'.")
            return "human_approval_node"

        # Example: If LLM is repeatedly requesting more context or is stuck
        if "not sufficient" in last_content.lower() or "please provide more context" in last_content.lower():
            print("[choose_next_node] LLM repeated confusion. Going to 'human_approval_node'.")
            return "human_approval_node"

        # Check for search triggers
        if any(keyword in last_content
               for keyword in ["redditSearcher", "googleSearcher", "arxivSearch", "githubSearchEnrich"]):
            print("[choose_next_node] Found a search keyword, going to 'search_node'")
            return "search_node"

        # Check for code triggers
        if "executePython" in last_content:
            print("[choose_next_node] Found a code command, going to 'code_node'")
            return "code_node"

        # Otherwise, stay in chatbot
        print("[choose_next_node] No special tool command, staying in 'chatbot'")
        return "chatbot"

    # From chatbot, choose next node based on last message
    graph_builder.add_conditional_edges(
        source="chatbot",
        path=choose_next_node
    )

    ###########################################################################
    # 6. Add edges for the rest of the flow
    ###########################################################################

    # Once we do 'search_node' or 'code_node', return to chatbot
    graph_builder.add_edge("search_node", "chatbot")
    graph_builder.add_edge("code_node", "chatbot")

    # If we go to 'human_approval_node', after a human clarifies (i.e. new HumanMessage),
    # we can return to chatbot again.
    graph_builder.add_edge("human_approval_node", "chatbot")

    # Also allow chatbot to remain in chatbot on subsequent runs
    graph_builder.add_edge("chatbot", "chatbot")

    # Entry point is 'chatbot'
    graph_builder.set_entry_point("chatbot")

    ###########################################################################
    # 7. Compile the graph with memory-based checkpoints
    ###########################################################################

    memory = MemorySaver()
    graph = graph_builder.compile(
        checkpointer=memory,
        # We'll interrupt before using tools, same as your original code
        interrupt_before=["search_node", "code_node", "human_approval_node"]
    )
    return graph
