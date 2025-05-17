import logging
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.tools import render_text_description # Added import
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
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    force=True
)
logging.getLogger("langchain").setLevel(logging.DEBUG)
logging.getLogger("langgraph").setLevel(logging.DEBUG)

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
    
    all_mcp_tools = get_github_mcp_tools()
    mcp_tools = [tool for tool in all_mcp_tools if tool.name == 'get_file_contents']
    if not mcp_tools: 
        logger.error("Critical: 'get_file_contents' tool not found in MCP tools. Aborting react_mcp setup.")
    logger.info(f"Filtered MCP Tools provided to create_react_agent: {mcp_tools}") # Modified by Copilot
    
    # System message part of the prompt
    system_prompt_template_str = '''You are a helpful AI assistant with specialized tools for GitHub. Your primary goal is to assist users with GitHub-related tasks.\\\\n
When the user asks for a summary of a repository, for example: \'Provide a summary of owner/repo\', 
you MUST use the tool named \'get_file_contents\'. 
To use this tool, you need to provide the parameters: \'owner\', \'repo\', and \'path\'. 
For a repository summary, the \'path\' should always be \'README.md\'. 
After successfully calling the \'get_file_contents\' tool and receiving the content of README.md, 
you should then provide a concise summary of that content as your answer.\n
For other GitHub-related requests, analyze the request and use the most appropriate GitHub MCP tool available to you.\\\\n\\\\n
TOOLS:\n
------\n
{tools}\n\n
When you need to use a tool, you MUST respond *only* in the following format, stopping after Action Input. Do not add any other text or explanation:\n
```\n
Thought: Do I need to use a tool? Yes\n
Action: The action to take. Must be one of [{tool_names}]\n
Action Input: The input to the action. This MUST be a single-line JSON string that conforms to the tool\'s arguments schema. For example: {{{{"owner": "user", "repo": "name", "path": "file.md"}}}}\n
```\n
The system will then execute the tool and provide you with an Observation.\n\n
When you have a response to say to the Human, or if you do not need to use a tool (e.g., after receiving an Observation and being ready to answer), you MUST use the format:\n
```\n
Thought: Do I need to use a tool? No\n
Final Answer: [your response here]\n
```\n\n
Begin!'''

    # Manually format the system prompt string with tool descriptions
    rendered_tools_description = render_text_description(mcp_tools)
    tool_names_list = ", ".join([tool.name for tool in mcp_tools])

    formatted_system_prompt = system_prompt_template_str.format(
        tools=rendered_tools_description,
        tool_names=tool_names_list
    )

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(formatted_system_prompt), # Use pre-formatted string
        MessagesPlaceholder(variable_name="messages"),
    ])
    logger.debug(f"Prompt input variables: {prompt.input_variables}")

    react_mcp = create_react_agent(
        model = llm,
        tools = mcp_tools,
        prompt = prompt,  
        checkpointer = MemorySaver(),
        name = "react_mcp",
        debug = True,
    )
    logger.debug(f"Value returned by create_react_agent: {react_mcp}")
    logger.debug(f"Type of value returned by create_react_agent: {type(react_mcp)}")
    from langchain_core.messages import AIMessage
    orig_react_mcp = react_mcp
    
    def react_mcp_wrapped(*args, **kwargs) -> dict:
        logger.debug(f"Entering react_mcp_wrapped with args: {args}, kwargs: {kwargs}")
        current_state_dict: dict = args[0] 
        invoke_config = kwargs.get("config", {}) 

        agent_input = {"messages": current_state_dict["messages"]} 
        logger.debug(f"Invoking orig_react_mcp (CompiledStateGraph) with input: {agent_input} and config: {invoke_config}")

        try:
            result = orig_react_mcp.invoke(agent_input, config=invoke_config)
            logger.debug(f"orig_react_mcp (CompiledStateGraph) returned: {result}")
        except Exception as e:
            logger.error(f"Exception in orig_react_mcp.invoke call: {e}", exc_info=True)
            return {
                "messages": [AIMessage(content=f"Error processing request in react_mcp: {e}")]
            }

        messages = result.get("messages", []) if isinstance(result, dict) else []
        if not messages:
            logger.warning("No messages returned from orig_react_mcp.invoke. Result was: %s. Returning fallback message.", result)
            return {
                "messages": [AIMessage(content="I am not equipped to handle this task with the functions at my disposal.")]
            }
        
        logger.debug(f"react_mcp_wrapped returning result: {result}")
        # The result from the sub-graph should be a dict compatible with the main graph's State update
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
