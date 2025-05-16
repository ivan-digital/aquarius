import logging
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt.chat_agent_executor import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from app.agent.facade import ToolsFacade
from app.agent.mcp.github_server import get_github_mcp_tools
from app.agent.nodes import Nodes
from app.agent.state import State
from app.config_manager import configManager

# Configure module-level logger
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def build_langgraph(facade: ToolsFacade = None) -> StateGraph:
    logger.debug("Starting build_langgraph with ToolsFacade: %s", facade)
    # If no facade provided, initialize default ToolsFacade
    if facade is None:
        facade = ToolsFacade()

    # Initialize LLM and nodes
    model_name = configManager.config.get("model_name")
    logger.debug("Loading ChatOllama model: %s", model_name)
    llm = ChatOllama(model=model_name)
    nodes = Nodes(llm, facade)
    logger.debug("Nodes initialized: %s", nodes)
    
    mcp_tools = get_github_mcp_tools()
    # Custom prompt to instruct the agent on how to summarize GitHub repos
    mcp_prompt = (
        "You are a GitHub assistant with access to GitHub MCP tools. "
        "When the user asks for a summary of a repository in the form 'Provide a summary of owner/repo', "
        "you MUST call the get_file_contents tool with the repository owner, repo name, and path 'README.md'. "
        "After fetching the README content, provide a concise summary of that content. "
        "For other GitHub requests, use the appropriate MCP tools."
    )
    react_mcp = create_react_agent(
        model = llm,
        tools = mcp_tools,
        prompt = mcp_prompt,
        checkpointer = MemorySaver(),
        name = "react_mcp",
        debug = True,
    )
    # Ensure react_mcp is callable; wrap stubs returning non-callable
    if not callable(react_mcp):
        logger.debug("react_mcp agent is not callable, wrapping into dummy handler")
        def _dummy_react_mcp(state):
            return {"messages": []}
        react_mcp = _dummy_react_mcp
    # Wrap react_mcp to ensure it returns an AIMessage when no messages are produced
    from langchain_core.messages import AIMessage
    orig_react_mcp = react_mcp
    def react_mcp_wrapped(*args, **kwargs) -> dict:
        # Attempt to call stub or real react_mcp with state and optional config
        try:
            result = orig_react_mcp(*args, **kwargs)
        except TypeError:
            # Try calling with state and config signature
            state = args[0] if len(args) > 0 else None
            config = args[1] if len(args) > 1 else {}
            result = orig_react_mcp(state, config)
        # Ensure any node failure still results in an AIMessage
        messages = result.get("messages", []) or []
        if not messages:
            return {
                "messages": [AIMessage(content="I am not equipped to handle this task with the functions at my disposal.")],
                "state_updates": {}
            }
        return result
    react_mcp = react_mcp_wrapped
    logger.debug("Created react_mcp agent with %d MCP tools", len(mcp_tools))
    # Build the state graph
    gb = StateGraph(State)
    logger.debug("StateGraph instance created")

    # Add nodes
    for node_name, handler in [
        ("chatbot", nodes.chatbot_node),
        ("profile_node", nodes.profile_node),
        ("clarify", nodes.human_node),
        ("react_mcp", react_mcp),
        ("time", nodes.time_node),
        ("end", nodes.end_node_fn)
    ]:
        gb.add_node(node_name, handler)
        logger.debug("Added node '%s' with handler %s", node_name, handler)

    # Routing function with detailed logging
    def intent_router(state: State) -> str:
        last = state["messages"][-1]

        if isinstance(last, HumanMessage):
            logger.info("Graph saw user message: %s", last.content)

        # Check if the last AI message indicates a tool failure from a previous node
        if len(state["messages"]) > 1:
            second_last = state["messages"][-2]
            # Check if the AI's last message is a generic failure message
            if isinstance(second_last, HumanMessage) and isinstance(last, AIMessage) and \
               "I am not equipped to handle this task" in last.content:
                # Log the failure and route to 'end' to prevent looping
                logger.debug(f"Previous node failed to handle: '{second_last.content.strip()}'. Routing to 'end'.")
                return "end"

        if isinstance(last, AIMessage):
            logger.debug("Last message is AIMessage('%s'), routing to 'end'", last.content)
            return "end"

        intent = nodes.detect_intent(last.content.strip())
        
        # Get intent-to-node mapping from config
        intent_to_node_mapping = configManager.config.get("intent_to_node_mapping", {})
        fallback_node = configManager.config.get("fallback_node_name", "clarify")
        
        target_node = intent_to_node_mapping.get(intent, fallback_node)
        
        logger.debug(
            "Detected intent '%s' for message '%s', routing to node '%s'",
            intent, last.content.strip(), target_node
        )
        return target_node

    # Set entry and finish points
    gb.set_conditional_entry_point(intent_router)
    gb.set_finish_point("end")
    logger.debug("Entry and finish points configured")

    # Loop all nodes back to router
    for node_name in [
        "chatbot",
        "profile_node",
        "clarify",
        "react_mcp",
        "time"
    ]:
        gb.add_conditional_edges(node_name, intent_router)
        logger.debug("Added conditional edge from '%s' back to router", node_name)
    # 'end' is the finish point and should not route back to intent_router

    # Compile the graph
    graph = gb.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["clarify", "end"]
    )
    logger.debug("Compiled StateGraph: %s", graph)
    return graph
