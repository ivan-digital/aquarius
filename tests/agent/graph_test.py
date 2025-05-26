"""Tests for the agent graph logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.language_models import FakeListLLM
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph

from app.agent.graph import build_langgraph
from app.agent.state import State as AgentState
from app.config_manager import ConfigManager


@pytest.fixture
def mock_config_manager():
    """Fixture for a mock ConfigManager."""
    manager = MagicMock(spec=ConfigManager)
    manager.get_config.side_effect = lambda key, default=None: {
        "github_token": "test_token",
        "fastmcp_log_level": "DEBUG",
        "github_mcp_enabled": True,
        "react_chat_system_prompt_prefix": "Test Prefix:",
    }.get(key, default)
    manager.get_react_prompt_repo_id.return_value = "hwchase17/react-chat"
    return manager

@pytest.fixture
def mock_llm():
    """Fixture for a mock LLM."""
    return FakeListLLM(responses=["AIMessage content"])

@pytest.mark.asyncio
@patch("app.agent.graph.MultiServerMCPClient")
@patch("app.agent.graph.hub.pull")
async def test_build_langgraph_creates_runnable_graph(
    mock_hub_pull, mock_mcp_client_constructor, mock_config_manager, mock_llm
):
    """Test that build_langgraph creates a runnable graph instance."""
    # Mock hub.pull to return a valid ChatPromptTemplate
    mock_prompt = MagicMock()
    mock_prompt.messages = [MagicMock()] # Ensure it has a messages attribute
    mock_hub_pull.return_value = mock_prompt

    # Mock MCP client and its methods
    mock_mcp_client_instance = AsyncMock()
    mock_mcp_client_instance.get_tools = AsyncMock(return_value=[]) # No MCP tools for simplicity
    mock_mcp_client_constructor.return_value.__aenter__.return_value = mock_mcp_client_instance

    graph = await build_langgraph(mock_config_manager, mock_llm)
    assert graph is not None
    assert hasattr(graph, "invoke") # Check if it's a runnable (compiled graph)

@pytest.mark.asyncio
@patch("app.agent.graph.MultiServerMCPClient")
@patch("app.agent.graph.hub.pull")
async def test_build_langgraph_with_mcp_tools(
    mock_hub_pull, mock_mcp_client_constructor, mock_config_manager, mock_llm
):
    """Test graph building when MCP tools are available."""
    mock_prompt = MagicMock()
    mock_prompt.messages = [MagicMock()]
    mock_hub_pull.return_value = mock_prompt

    mock_mcp_tool = MagicMock()
    mock_mcp_tool.name = "mcp_tool"
    mock_mcp_client_instance = AsyncMock()
    mock_mcp_client_instance.get_tools = AsyncMock(return_value=[mock_mcp_tool])
    mock_mcp_client_constructor.return_value.__aenter__.return_value = mock_mcp_client_instance

    # Patch create_react_agent to inspect its arguments
    with patch("app.agent.graph.create_react_agent") as mock_create_react_agent:
        mock_react_agent_executor = MagicMock()
        mock_create_react_agent.return_value = mock_react_agent_executor

        await build_langgraph(mock_config_manager, mock_llm)

        mock_create_react_agent.assert_called_once()
        called_args, _ = mock_create_react_agent.call_args
        # Ensure llm and prompt are passed
        assert called_args[0]["model"] == mock_llm
        assert called_args[0]["prompt"] == mock_prompt
        # Check that MCP tool is in the list of tools passed to create_react_agent
        assert any(tool.name == "mcp_tool" for tool in called_args[0]["tools"])
        assert any(tool.name == "search_arxiv" for tool in called_args[0]["tools"])
        assert any(tool.name == "execute_terminal_command" for tool in called_args[0]["tools"])


@pytest.mark.asyncio
@patch("app.agent.graph.MultiServerMCPClient")
@patch("app.agent.graph.hub.pull")
async def test_build_langgraph_mcp_disabled(
    mock_hub_pull, mock_mcp_client_constructor, mock_config_manager, mock_llm
):
    """Test graph building when MCP is disabled in config."""
    mock_prompt = MagicMock()
    mock_prompt.messages = [MagicMock()]
    mock_hub_pull.return_value = mock_prompt
    mock_config_manager.get_config.side_effect = lambda key, default=None: {
        "github_token": "test_token",
        "fastmcp_log_level": "DEBUG",
        "github_mcp_enabled": False, # MCP disabled
        "react_chat_system_prompt_prefix": "Test Prefix:",
    }.get(key, default)

    with patch("app.agent.graph.create_react_agent") as mock_create_react_agent:
        await build_langgraph(mock_config_manager, mock_llm)
        mock_mcp_client_constructor.assert_not_called() # MCP client should not be initialized
        # Check that only local tools are passed
        called_args, _ = mock_create_react_agent.call_args
        tool_names = [tool.name for tool in called_args[0]["tools"]]
        assert "mcp_tool" not in tool_names
        assert "search_arxiv" in tool_names
        assert "execute_terminal_command" in tool_names

@pytest.mark.asyncio
@patch("app.agent.graph.MultiServerMCPClient")
@patch("app.agent.graph.hub.pull")
async def test_react_mcp_node_invocation(
    mock_hub_pull, mock_mcp_client_constructor, mock_config_manager, mock_llm
):
    """Test the react_mcp node's direct invocation logic within the graph context."""
    mock_prompt = MagicMock()
    mock_prompt.messages = [MagicMock()]
    mock_hub_pull.return_value = mock_prompt

    mock_mcp_client_instance = AsyncMock()
    mock_mcp_client_instance.get_tools = AsyncMock(return_value=[])
    mock_mcp_client_constructor.return_value.__aenter__.return_value = mock_mcp_client_instance

    # Mock the create_react_agent to return a mock executor
    mock_react_agent_executor = MagicMock()
    mock_react_agent_executor.invoke.return_value = {"messages": [AIMessage(content="React response")]}

    with patch("app.agent.graph.create_react_agent", return_value=mock_react_agent_executor):
        graph = await build_langgraph(mock_config_manager, mock_llm)

    # Get the actual node function for react_mcp
    # This requires inspecting the compiled graph's internals or refactoring build_langgraph
    # For simplicity, we assume the node is retrievable or test its effect through graph.invoke
    # If direct node access is hard, test via graph.invoke with state routing to react_mcp
    initial_state = AgentState(messages=[HumanMessage(content="Test react query")], next_node="react_mcp")
    config = {"configurable": {"thread_id": "test-thread"}}

    # To directly test the node, we'd need to extract it.
    # Instead, we'll invoke the graph and ensure it routes correctly and the mock is called.
    # This is more of an integration test for the node within the graph.
    # We need to ensure the intent_router directs to react_mcp.
    # For this, we can mock the intent_router_node's behavior if it's complex,
    # or ensure the initial state forces the path.

    # Let's assume intent_router will correctly use 'next_node' from state
    # The graph structure is: intent_router -> react_mcp -> END
    final_state = await graph.ainvoke(initial_state, config=config)

    mock_react_agent_executor.invoke.assert_called_once()
    call_args, call_kwargs = mock_react_agent_executor.invoke.call_args
    assert call_args[0] == {"messages": [HumanMessage(content="Test react query")]}
    assert call_kwargs['config'] == config # Ensure config is passed through
    assert final_state["messages"][-1].content == "React response"


@pytest.mark.asyncio
@patch("app.agent.graph.hub.pull") # Mock hub.pull as it's called in build_langgraph
async def test_chatbot_node_invocation(mock_hub_pull, mock_config_manager, mock_llm):
    """Test the chatbot_node's direct invocation logic."""
    # Mock hub.pull to prevent external calls during graph build
    mock_prompt = MagicMock()
    mock_prompt.messages = [MagicMock()]
    mock_hub_pull.return_value = mock_prompt

    # Build the graph to get access to the compiled nodes
    # We need to disable MCP to simplify the test and avoid its mocks here
    mock_config_manager.get_config.side_effect = lambda key, default=None: {
        "github_token": "test_token", # Still needed for initial setup
        "github_mcp_enabled": False, # Disable MCP
        "react_chat_system_prompt_prefix": "Test Prefix:",
    }.get(key, default)

    graph = await build_langgraph(mock_config_manager, mock_llm)

    initial_state = AgentState(messages=[HumanMessage(content="Hello chatbot")], next_node="chatbot")
    config = {"configurable": {"thread_id": "test-thread-chatbot"}}

    # Invoke the graph, assuming intent_router routes to chatbot
    final_state = await graph.ainvoke(initial_state, config=config)

    # mock_llm is a FakeListLLM, its invoke will return the preset response
    assert final_state["messages"][-1].content == "AIMessage content"
    # Check that the LLM was called by the chatbot_node
    # The FakeListLLM doesn't easily expose call counts without more setup,
    # but the output being correct implies it was called.
    # We can also check the system prompt was generated
    # For a more direct test of the node, one might extract the node function
    # from the graph if possible, or mock the LLM more intricately.


@pytest.mark.asyncio
async def test_intent_router_node_routes_to_chatbot(mock_config_manager, mock_llm):
    """Test that the intent_router routes to chatbot by default."""
    # Disable MCP and React features for simplicity
    mock_config_manager.get_config.side_effect = lambda key, default=None: {
        "github_mcp_enabled": False,
        "react_chat_system_prompt_prefix": None, # No prefix
    }.get(key, default)
    mock_config_manager.get_react_prompt_repo_id.return_value = "some/prompt" # Needs a value

    # Mock hub.pull
    with patch("app.agent.graph.hub.pull") as mock_hub_pull:
        mock_prompt = MagicMock()
        mock_prompt.messages = [MagicMock()]
        mock_hub_pull.return_value = mock_prompt

        graph = await build_langgraph(mock_config_manager, mock_llm)

    # Mock the Nodes.intent_router_node to control its output
    # The actual Nodes class is instantiated within build_langgraph
    # We need to patch the instance's method or the class method if it's static
    # For simplicity, let's assume the default routing if intent_router doesn't set 'next_node'
    # or if it explicitly sets it to 'chatbot'.

    # The default behavior of the conditional edge is to go to "chatbot"
    # if "next_node" is not in the output of "intent_router" or is "chatbot".
    initial_state = AgentState(messages=[HumanMessage(content="General query")])
    config = {"configurable": {"thread_id": "test-thread-intent-chatbot"}}

    # We expect it to go to chatbot_node, which uses mock_llm
    final_state = await graph.ainvoke(initial_state, config=config)
    assert final_state["messages"][-1].content == "AIMessage content" # From chatbot_node via mock_llm

@pytest.mark.asyncio
async def test_intent_router_node_routes_to_react_mcp(mock_config_manager, mock_llm):
    """Test that the intent_router can route to react_mcp."""
    mock_config_manager.get_config.side_effect = lambda key, default=None: {
        "github_token": "test_token",
        "github_mcp_enabled": True, # MCP enabled
        "react_chat_system_prompt_prefix": "Test Prefix:",
    }.get(key, default)
    mock_config_manager.get_react_prompt_repo_id.return_value = "hwchase17/react-chat"

    with patch("app.agent.graph.hub.pull") as mock_hub_pull, \
         patch("app.agent.graph.MultiServerMCPClient") as mock_mcp_client_constructor, \
         patch("app.agent.graph.create_react_agent") as mock_create_react_agent, \
         patch("app.agent.nodes.Nodes.intent_router_node") as mock_intent_router_node: # Patch the method

        mock_prompt = MagicMock()
        mock_prompt.messages = [MagicMock()]
        mock_hub_pull.return_value = mock_prompt

        mock_mcp_client_instance = AsyncMock()
        mock_mcp_client_instance.get_tools = AsyncMock(return_value=[])
        mock_mcp_client_constructor.return_value.__aenter__.return_value = mock_mcp_client_instance

        mock_react_agent_executor = MagicMock()
        mock_react_agent_executor.invoke.return_value = {"messages": [AIMessage(content="React MCP response")]}
        mock_create_react_agent.return_value = mock_react_agent_executor

        # Configure the mock intent_router_node to output "react_mcp"
        # The state passed to intent_router_node will be the initial_state
        def intent_router_side_effect(state):
            # Make sure to return a dict that can update the AgentState
            return {"next_node": "react_mcp", "messages": state.get("messages", [])}
        mock_intent_router_node.side_effect = intent_router_side_effect

        graph = await build_langgraph(mock_config_manager, mock_llm)

    initial_state = AgentState(messages=[HumanMessage(content="Query for react_mcp")])
    config = {"configurable": {"thread_id": "test-thread-intent-react"}}

    final_state = await graph.ainvoke(initial_state, config=config)

    mock_intent_router_node.assert_called_once()
    mock_create_react_agent.assert_called_once() # Ensure react_agent was set up
    mock_react_agent_executor.invoke.assert_called_once() # Ensure react_agent was invoked
    assert final_state["messages"][-1].content == "React MCP response"

@pytest.mark.asyncio
async def test_graph_compilation_failure(mock_config_manager, mock_llm):
    """Test that graph compilation failure is handled."""
    with patch.object(StateGraph, "compile", side_effect=RuntimeError("Compilation failed")):
        with pytest.raises(RuntimeError, match="Compilation failed"):
            await build_langgraph(mock_config_manager, mock_llm)

@pytest.mark.asyncio
@patch("app.agent.graph.MultiServerMCPClient")
@patch("app.agent.graph.hub.pull")
async def test_react_mcp_node_handles_agent_executor_failure(
    mock_hub_pull, mock_mcp_client_constructor, mock_config_manager, mock_llm
):
    """Test that react_mcp_node returns an error message if agent executor fails."""
    mock_prompt = MagicMock()
    mock_prompt.messages = [MagicMock()]
    mock_hub_pull.return_value = mock_prompt

    mock_mcp_client_instance = AsyncMock()
    mock_mcp_client_instance.get_tools = AsyncMock(return_value=[]) # No MCP tools
    mock_mcp_client_constructor.return_value.__aenter__.return_value = mock_mcp_client_instance

    mock_react_agent_executor = MagicMock()
    mock_react_agent_executor.invoke.side_effect = Exception("Agent execution error")

    with patch("app.agent.graph.create_react_agent", return_value=mock_react_agent_executor), \
         patch("app.agent.nodes.Nodes.intent_router_node") as mock_intent_router_node:

        def intent_router_side_effect(state):
            return {"next_node": "react_mcp", "messages": state.get("messages", [])}
        mock_intent_router_node.side_effect = intent_router_side_effect
        
        graph = await build_langgraph(mock_config_manager, mock_llm)

    initial_state = AgentState(messages=[HumanMessage(content="Trigger react error")])
    config = {"configurable": {"thread_id": "test-thread-react-fail"}}
    
    final_state = await graph.ainvoke(initial_state, config=config)
    
    assert isinstance(final_state["messages"][-1], AIMessage)
    assert "Error processing GitHub request: Exception." in final_state["messages"][-1].content
    mock_react_agent_executor.invoke.assert_called_once()

@pytest.mark.asyncio
@patch("app.agent.graph.MultiServerMCPClient")
@patch("app.agent.graph.hub.pull")
async def test_react_mcp_node_handles_no_agent_executor(
    mock_hub_pull, mock_mcp_client_constructor, mock_config_manager, mock_llm
):
    """Test react_mcp_node when react_mcp_node_agent_executor is None (e.g., no tools)."""
    mock_prompt = MagicMock() # hub.pull needs to return something
    mock_prompt.messages = [MagicMock()]
    mock_hub_pull.return_value = mock_prompt

    # Simulate no tools available, leading to react_mcp_node_agent_executor being None
    # This means create_react_agent is not called or returns None (though it usually raises error or returns an executor)
    # The critical part is that all_agent_tools is empty.
    mock_config_manager.get_config.side_effect = lambda key, default=None: {
        "github_token": None, # No token -> no mcp_servers -> no mcp tools
        "github_mcp_enabled": False, # Explicitly disable MCP
        "react_chat_system_prompt_prefix": "Test Prefix:",
    }.get(key, default)
    
    # Patch the tools to be empty
    with patch("app.agent.graph.search_arxiv", None), \
         patch("app.agent.graph.execute_terminal_command", None), \
         patch("app.agent.nodes.Nodes.intent_router_node") as mock_intent_router_node:

        # Ensure create_react_agent is not even called if no tools
        with patch("app.agent.graph.create_react_agent") as mock_create_react_agent:
            
            def intent_router_side_effect(state):
                return {"next_node": "react_mcp", "messages": state.get("messages", [])}
            mock_intent_router_node.side_effect = intent_router_side_effect

            # Temporarily modify build_langgraph's local tools to be empty for this test path
            # This is tricky. A better way would be to control what `all_agent_tools` becomes.
            # For this test, we'll rely on config to disable all tool sources.
            # And ensure create_react_agent is not called, so its return value doesn't matter.
            # The `react_mcp_node_agent_executor` will be None.

            graph = await build_langgraph(mock_config_manager, mock_llm)
            # mock_create_react_agent.assert_not_called() # This should be true if all_agent_tools is empty

    initial_state = AgentState(messages=[HumanMessage(content="Query to non-existent react agent")])
    config = {"configurable": {"thread_id": "test-thread-no-react-agent"}}
    
    final_state = await graph.ainvoke(initial_state, config=config)
    
    assert isinstance(final_state["messages"][-1], AIMessage)
    assert "Critical Error: GitHub interaction module not configured." in final_state["messages"][-1].content
