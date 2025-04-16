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
  1. Search external resources for information.
  2. Execute Python code in a sandbox.
Only use these capabilities if truly needed.
"""

# Prompt for intent classification
INTENT_PROMPT = """
You are an intent-classification AI.
Given the user's message, classify it into exactly one of the following categories:
1. "chit_chat" for greetings, small talk, or normal conversation
2. "search" if the user or you need to search external data (Google, GitHub, etc.)
3. "code" if the user or you are requesting Python code execution
4. "other" if none of the above apply

Return your answer as valid JSON with this format:
{
  "intent": "<chit_chat or search or code or other>"
}
Be concise and do not add extra keys.
"""


def build_langgraph(llm_client, facade):
    """
    Build a LangGraph that:
      - Has a chatbot node calling llm_client.chat_with_tools
      - Has 2 ToolNodes: one for 'search' tools, one for 'code' tools
      - Routes to the correct node based on an LLM-based intent classifier
      - Has a 'human_approval_node' for manual fixes/clarification
      - Has an 'end_node' so we don't loop forever after the assistant replies
      - Uses memory-based checkpoints
    """

    graph_builder = StateGraph(State)

    # -------------------------------------------------------------------------
    # 0. Helper: detect_intent
    # -------------------------------------------------------------------------
    def detect_intent(llm_client, user_message: str) -> str:
        """
        Uses the LLM to classify the message into 'chit_chat', 'search', 'code', or 'other'.
        """
        # Construct a prompt that includes INTENT_PROMPT + the user's message
        prompt = f"{INTENT_PROMPT}\nUser message: {user_message}\n"
        # We'll assume llm_client.completion returns a dict with the LLM text in 'response' or as parsed JSON.
        response_data = llm_client.completion(prompt, _format='json')
        # Expected to have a structure like {"intent": "chit_chat", "execution": 0.23, ...}
        intent = response_data.get("intent", "other")
        return intent

    # -------------------------------------------------------------------------
    # 1. Chatbot node
    # -------------------------------------------------------------------------
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
                # Fallback
                chat_msgs.append({"role": "user", "content": str(msg)})

        # 3. Call the LLM (tools can be used if the assistant triggers them)
        result = llm_client.chat_with_tools(
            messages=chat_msgs,
            tools=facade.all_tools
        )

        # Log and return
        print(f"[chatbot_node] LLM returned: {result['content']}")
        new_state = {
            "messages": [AIMessage(content=result["content"])]
        }
        print(f"[chatbot_node] Exiting chatbot_node, new state: {new_state}")
        return new_state

    # -------------------------------------------------------------------------
    # 2. Human approval node
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 3. Search / Code tool nodes
    # -------------------------------------------------------------------------
    search_node = ToolNode(tools=facade.search_tools)
    code_node = ToolNode(tools=facade.code_tools)

    # -------------------------------------------------------------------------
    # 4. End node
    # -------------------------------------------------------------------------
    def end_node_fn(state: State) -> dict:
        """
        Simple node that indicates conversation is done.
        Typically, you wouldn't even call the LLM here; just finalize.
        """
        print("\n[end_node] Entering end_node...")
        return {
            "messages": [
                AIMessage(content="(Conversation ended. No new user input.)")
            ]
        }

    # -------------------------------------------------------------------------
    # 5. Add nodes to the graph
    # -------------------------------------------------------------------------
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("search_node", search_node)
    graph_builder.add_node("code_node", code_node)
    graph_builder.add_node("human_approval_node", human_approval_node_fn)
    graph_builder.add_node("end_node", end_node_fn)

    # -------------------------------------------------------------------------
    # 6. Routing logic with LLM-based intent detection
    # -------------------------------------------------------------------------
    def choose_next_node(state: State) -> str:
        """
        Examines the last message, uses the LLM to classify intent if from user,
        or ends if the last message was from the assistant (meaning no new user input).
        """
        print("\n[choose_next_node] Deciding next node...")

        if not state["messages"]:
            print("[choose_next_node] No messages, go to 'chatbot'.")
            return "chatbot"

        last_msg = state["messages"][-1]

        # If the last message is from the assistant, we assume no new user input => end
        if isinstance(last_msg, AIMessage):
            print("[choose_next_node] Last message from assistant => end_node.")
            return "end_node"

        # Otherwise, the last message is from the user => detect intent
        last_content = (last_msg.content or "").strip()
        if not last_content:
            print("[choose_next_node] Empty user message => chatbot or end. Let's do chatbot.")
            return "chatbot"

        # 1) Use our helper to detect the intent
        intent = detect_intent(llm_client, last_content)
        print(f"[choose_next_node] Detected intent: '{intent}'")

        # 2) Route based on intent
        if intent == "search":
            return "search_node"
        elif intent == "code":
            return "code_node"
        elif intent == "chit_chat":
            return "chatbot"
        else:
            # 'other' => normal chatbot or maybe human approval
            return "chatbot"

    # Connect the chatbot => choose_next_node
    graph_builder.add_conditional_edges(source="chatbot", path=choose_next_node)

    # -------------------------------------------------------------------------
    # 7. Additional edges
    # -------------------------------------------------------------------------
    # After search_node or code_node, we go back to chatbot so the LLM can answer
    graph_builder.add_edge("search_node", "chatbot")
    graph_builder.add_edge("code_node", "chatbot")

    # If we ever go to human_approval_node, the user can clarify
    # then we route back to chatbot afterward.
    graph_builder.add_edge("human_approval_node", "chatbot")

    # We have an end node that doesn't go anywhere.
    # If you do want to continue from end_node, you can add an edge to chatbot.
    # graph_builder.add_edge("end_node", "chatbot")  # Typically not added if truly final.

    # Entry point is always chatbot
    graph_builder.set_entry_point("chatbot")

    # -------------------------------------------------------------------------
    # 8. Compile the graph with memory-based checkpoints
    # -------------------------------------------------------------------------
    memory = MemorySaver()
    graph = graph_builder.compile(
        checkpointer=memory,
        interrupt_before=["search_node", "code_node", "human_approval_node", "end_node"]
    )

    return graph