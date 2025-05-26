import logging
from typing import List
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.tools import BaseTool
from langgraph.prebuilt.chat_agent_executor import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from app.config_manager import ConfigManager

logger = logging.getLogger(__name__)


def build_github_react_agent(
    config_manager: ConfigManager,
    llm: BaseLanguageModel,
    tools: List[BaseTool]
) -> object:
    """
    Build a simple ReAct agent for GitHub interactions.
    This replaces the complex graph routing with a straightforward ReAct agent.
    """
    logger.info(f"Building GitHub ReAct agent with {len(tools)} tools")
    
    # System prompt for GitHub assistant
    system_prompt = (
        "You are a helpful GitHub assistant. You can help users explore GitHub repositories, "
        "analyze code, check recent changes, and answer questions about repository content. "
        "Use the available GitHub tools to fetch information when needed. "
        "When you have enough information to answer the user's question, provide a clear and helpful response."
    )
    
    try:
        agent = create_react_agent(
            model=llm,
            tools=tools,
            checkpointer=MemorySaver(),
            state_modifier=system_prompt
        )
        logger.info("GitHub ReAct agent built successfully")
        return agent
    except Exception as e:
        logger.error(f"Error building GitHub ReAct agent: {e}", exc_info=True)
        raise


def build_langgraph_with_config(
    config_manager: ConfigManager,
    llm: BaseLanguageModel,
    tools: List[BaseTool]
) -> object:
    """Backward compatibility wrapper for the simplified agent."""
    return build_github_react_agent(config_manager, llm, tools)


def get_graph(
    config_manager: ConfigManager,
    llm: BaseLanguageModel,
    tools: List[BaseTool]
) -> object:
    """
    Get the graph/agent for the conversation.
    This is the main entry point used by the facade.
    """
    return build_github_react_agent(config_manager, llm, tools)
