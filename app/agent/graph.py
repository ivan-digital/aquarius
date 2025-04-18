import logging
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt.chat_agent_executor import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from app.agent.facade import ToolsFacade
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

def build_langgraph(facade: ToolsFacade) -> StateGraph:
    logger.debug("Starting build_langgraph with ToolsFacade: %s", facade)

    # Initialize LLM and nodes
    model_name = configManager.config.get("model_name")
    logger.debug("Loading ChatOllama model: %s", model_name)
    llm = ChatOllama(model=model_name)
    nodes = Nodes(llm, facade)
    logger.debug("Nodes initialized: %s", nodes)

    # Create React agents for search and code
    react_search = create_react_agent(
        model=llm,
        tools=facade.search_tools,
        checkpointer=MemorySaver(),
        name="react_search",
        debug=True,
    )
    logger.debug("Created react_search agent with tools: %s", facade.search_tools)

    react_code = create_react_agent(
        model=llm,
        tools=facade.code_tools,
        checkpointer=MemorySaver(),
        name="react_code",
        debug=True,
    )
    logger.debug("Created react_code agent with tools: %s", facade.code_tools)

    # Build the state graph
    gb = StateGraph(State)
    logger.debug("StateGraph instance created")

    # Add nodes
    for node_name, handler in [
        ("chatbot", nodes.chatbot_node),
        ("profile_node", nodes.profile_node),
        ("clarify", nodes.human_node),
        ("react_search", react_search),
        ("react_code", react_code),
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

        if isinstance(last, AIMessage):
            logger.debug("Last message is AIMessage('%s'), routing to 'end'", last.content)
            return "end"
        intent = nodes.detect_intent(last.content.strip())
        mapping = {
            "search": "react_search",
            "code": "react_code",
            "chit_chat": "chatbot",
            "profile": "profile_node",
            "time": "time"
        }
        target = mapping.get(intent, "clarify")
        logger.debug(
            "Detected intent '%s' for message '%s', routing to '%s'",
            intent, last.content.strip(), target
        )
        return target

    # Set entry and finish points
    gb.set_conditional_entry_point(intent_router)
    gb.set_finish_point("end")
    logger.debug("Entry and finish points configured")

    # Loop all nodes back to router
    for node_name in [
        "chatbot",
        "profile_node",
        "clarify",
        "react_search",
        "react_code",
        "time",
        "end"
    ]:
        gb.add_conditional_edges(node_name, intent_router)
        logger.debug("Added conditional edge from '%s' back to router", node_name)

    # Compile the graph
    graph = gb.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["clarify", "end"]
    )
    logger.debug("Compiled StateGraph: %s", graph)
    return graph
