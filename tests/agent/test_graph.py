import pytest
from unittest.mock import patch, MagicMock

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph # Added import
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.graph import build_langgraph, State # Assuming State is accessible or can be mocked
from app.agent.facade import ToolsFacade
# Mock configManager before it's used by app.agent.graph
# This is a common pattern for mocking module-level singletons
config_manager_mock = MagicMock()
config_manager_mock.config = {
    "model_name": "test_model",
    "intent_to_node_mapping": {
        "greeting": "chatbot",
        "mcp_task": "react_mcp",
        "time_query": "time"
    },
    "fallback_node_name": "clarify"
}

# Patch configManager where it's imported in app.agent.graph
# Adjust the path 'app.agent.graph.configManager' if it's imported differently
# e.g., 'app.config_manager.configManager' if imported from the root of config_manager.py
# For this example, assuming 'from app.config_manager import configManager' in graph.py
# Or, if it's 'import app.config_manager', then 'app.config_manager.configManager'
# Based on the provided graph.py, it's 'from app.config_manager import configManager'
# So the path to patch is 'app.agent.graph.configManager'

@patch('app.agent.graph.configManager', new=config_manager_mock)
@patch('app.agent.graph.ChatOllama')
@patch('app.agent.graph.Nodes')
@patch('app.agent.graph.get_github_mcp_tools')
@patch('app.agent.graph.create_react_agent')
def test_build_langgraph_returns_state_graph(
    mock_create_react_agent,
    mock_get_github_mcp_tools,
    mock_nodes_class,
    mock_chat_ollama,
):
    """Test that build_langgraph successfully returns a CompiledStateGraph instance."""
    # Setup mocks
    mock_chat_ollama.return_value = MagicMock()
    mock_nodes_instance = MagicMock()
    mock_nodes_class.return_value = mock_nodes_instance
    
    # Correctly mock the tool to have a .name attribute
    mock_tool = MagicMock()
    mock_tool.name = 'get_file_contents'
    mock_get_github_mcp_tools.return_value = [mock_tool] 
    mock_create_react_agent.return_value = MagicMock() # This will be the 'react_mcp' handler

    graph = build_langgraph()
    assert isinstance(graph, CompiledStateGraph), "build_langgraph should return a CompiledStateGraph instance"
    # print("Test test_build_langgraph_returns_state_graph PASSED") # Removed print

@patch('app.agent.graph.configManager', new=config_manager_mock)
@patch('app.agent.graph.ChatOllama')
@patch('app.agent.graph.Nodes')
@patch('app.agent.graph.get_github_mcp_tools')
@patch('app.agent.graph.create_react_agent')
def test_build_langgraph_initializes_tools_facade(
    mock_create_react_agent,
    mock_get_github_mcp_tools,
    mock_nodes_class,
    mock_chat_ollama,
):
    """Test that ToolsFacade is initialized if not provided."""
    mock_chat_ollama.return_value = MagicMock()
    mock_nodes_instance = MagicMock()
    mock_nodes_class.return_value = mock_nodes_instance
    
    # Correctly mock the tool to have a .name attribute
    mock_tool = MagicMock()
    mock_tool.name = 'get_file_contents'
    mock_get_github_mcp_tools.return_value = [mock_tool]
    mock_create_react_agent.return_value = MagicMock()

    # Patch ToolsFacade within the scope of this test or ensure it's globally mocked if necessary
    with patch('app.agent.graph.ToolsFacade') as mock_tools_facade_class:
        mock_tools_facade_instance = MagicMock()
        mock_tools_facade_class.return_value = mock_tools_facade_instance
        
        build_langgraph(facade=None)
        mock_tools_facade_class.assert_called_once()

        mock_tools_facade_class.reset_mock()
        provided_facade = ToolsFacade() # Or MagicMock(spec=ToolsFacade)
        build_langgraph(facade=provided_facade)
        mock_tools_facade_class.assert_not_called() # Should not be called if facade is provided
    # print("Test test_build_langgraph_initializes_tools_facade PASSED") # Removed print

@patch('app.agent.graph.configManager', new=config_manager_mock)
@patch('app.agent.graph.ChatOllama')
@patch('app.agent.graph.Nodes') 
@patch('app.agent.graph.get_github_mcp_tools')
@patch('app.agent.graph.create_react_agent')
@patch('app.agent.graph.StateGraph') 
def test_build_langgraph_registers_nodes_and_configures_graph_structure(
    mock_state_graph_class, 
    mock_create_react_agent,
    mock_get_github_mcp_tools,
    mock_nodes_class, 
    mock_chat_ollama,
):
    """Test that build_langgraph registers nodes, sets entry/finish points, and edges."""
    mock_chat_ollama.return_value = MagicMock()
    mock_nodes_instance = MagicMock() 
    mock_nodes_class.return_value = mock_nodes_instance
    
    # Correctly mock the tool to have a .name attribute
    mock_tool = MagicMock()
    mock_tool.name = 'get_file_contents'
    mock_get_github_mcp_tools.return_value = [mock_tool]
    mock_react_mcp_agent_instance = MagicMock(name="react_mcp_agent_instance")
    mock_create_react_agent.return_value = mock_react_mcp_agent_instance

    mock_graph_instance = MagicMock(spec=StateGraph) 
    mock_state_graph_class.return_value = mock_graph_instance 

    build_langgraph()

    # 1. Test Node Registration
    expected_node_handlers = {
        "chatbot": mock_nodes_instance.chatbot_node,
        "profile_node": mock_nodes_instance.profile_node,
        "clarify": mock_nodes_instance.human_node,
        "time": mock_nodes_instance.time_node,
        "end": mock_nodes_instance.end_node_fn,
        "react_mcp": None  # Special handling as it's a wrapped function
    }
    
    assert mock_graph_instance.add_node.call_count == len(expected_node_handlers)

    for call_args in mock_graph_instance.add_node.call_args_list:
        node_name, handler_called = call_args[0]
        assert node_name in expected_node_handlers, f"Unexpected node added: {node_name}"
        assert callable(handler_called), f"Handler for node '{node_name}' is not callable."
        
        if node_name == "react_mcp":
            # Check that the original agent creation was called, as its result is wrapped.
            mock_create_react_agent.assert_called_once()
        else:
            assert handler_called == expected_node_handlers[node_name], \
                f"Incorrect handler for node '{node_name}'."

    # 2. Test Entry Point
    assert mock_graph_instance.set_conditional_entry_point.call_count == 1
    entry_point_handler = mock_graph_instance.set_conditional_entry_point.call_args[0][0]
    assert callable(entry_point_handler), "Entry point handler must be callable."

    # 3. Test Finish Point
    mock_graph_instance.set_finish_point.assert_called_once_with("end")

    # 4. Test Conditional Edges
    # Nodes that loop back to the router
    nodes_with_conditional_edges = ["chatbot", "profile_node", "clarify", "react_mcp", "time"]
    assert mock_graph_instance.add_conditional_edges.call_count == len(nodes_with_conditional_edges)
    
    for node_name in nodes_with_conditional_edges:
        # Check that add_conditional_edges was called for this node_name,
        # with the entry_point_handler (intent_router) as the conditional function.
        mock_graph_instance.add_conditional_edges.assert_any_call(node_name, entry_point_handler)
    
    # 5. Test Graph Compilation
    mock_graph_instance.compile.assert_called_once()


@patch('app.agent.graph.configManager', new=config_manager_mock)
@patch('app.agent.graph.ChatOllama')
@patch('app.agent.graph.Nodes')
@patch('app.agent.graph.get_github_mcp_tools')
@patch('app.agent.graph.create_react_agent')
@patch('app.agent.graph.StateGraph')
def test_intent_router_logic(
    mock_state_graph_class,
    mock_create_react_agent,
    mock_get_github_mcp_tools,
    mock_nodes_class,
    mock_chat_ollama,
):
    """Test the logic of the intent_router function."""
    mock_chat_ollama.return_value = MagicMock()
    mock_nodes_instance = MagicMock()
    mock_nodes_class.return_value = mock_nodes_instance
    mock_get_github_mcp_tools.return_value = [MagicMock(name='get_file_contents')]
    mock_create_react_agent.return_value = MagicMock() 

    mock_graph_instance = MagicMock(spec=StateGraph)
    mock_state_graph_class.return_value = mock_graph_instance

    build_langgraph()

    assert mock_graph_instance.set_conditional_entry_point.call_count == 1
    intent_router_func = mock_graph_instance.set_conditional_entry_point.call_args[0][0]
    assert callable(intent_router_func)

    # Test cases: (state_messages_list, mocked_detected_intent, expected_node_name)
    test_cases = [
        ([HumanMessage(content="Hello")], "greeting", "chatbot"),
        ([HumanMessage(content="Summarize repo")], "mcp_task", "react_mcp"),
        ([HumanMessage(content="What time is it?")], "time_query", "time"),
        ([HumanMessage(content="Unknown query")], "unknown_intent", "clarify"), # Fallback
        ([AIMessage(content="I did something.")], None, "end"), # AIMessage routes to end
        # Tool failure: Human asks, AI says "I am not equipped..."
        ([HumanMessage(content="Do X"), AIMessage(content="I am not equipped to handle this task")], None, "end"),
        # Normal conversation flow then AI message
        ([HumanMessage(content="Hi"), AIMessage(content="Hello back!")], None, "end"),
    ]

    for messages_list, mocked_intent, expected_node in test_cases:
        current_state: State = {"messages": messages_list}
        
        # Configure mock for nodes.detect_intent for this specific case
        # It's only called if the last message is HumanMessage and not a tool failure.
        should_call_detect_intent = False
        if isinstance(messages_list[-1], HumanMessage):
            # Check for the specific tool failure pattern that bypasses intent detection
            is_tool_failure = (
                len(messages_list) > 1 and
                isinstance(messages_list[-2], HumanMessage) and
                isinstance(messages_list[-1], AIMessage) and # This condition is actually for the *next* state
                                                            # The router sees the HumanMessage first.
                                                            # Let's adjust the logic for when detect_intent is called.
                                                            # The router logic:
                                                            # 1. Checks for tool failure (Human, then AI "not equipped")
                                                            # 2. Checks if last is AIMessage
                                                            # 3. If last is HumanMessage, calls detect_intent
                "I am not equipped to handle this task" in messages_list[-1].content
            ) # This tool failure check is on the *current* last message if it's an AI one.

            # If the *current last message* is Human, detect_intent is called.
            mock_nodes_instance.detect_intent.return_value = mocked_intent
            should_call_detect_intent = True
        
        # If the state represents a situation *after* a tool failure message from AI,
        # the last message would be that AI message.
        is_post_tool_failure_ai_message = (
            isinstance(messages_list[-1], AIMessage) and
            "I am not equipped to handle this task" in messages_list[-1].content and
            len(messages_list) > 1 and isinstance(messages_list[-2], HumanMessage)
        )

        actual_node_returned = intent_router_func(current_state)
        assert actual_node_returned == expected_node

        if should_call_detect_intent and not is_post_tool_failure_ai_message and expected_node != "end":
             # detect_intent is called if last message is Human and it doesn't immediately lead to 'end'
             # due to some other prior condition (which isn't the case for HumanMessage inputs here before detect_intent).
            mock_nodes_instance.detect_intent.assert_called_with(messages_list[-1].content.strip())
        
        mock_nodes_instance.detect_intent.reset_mock() # Reset for the next iteration

# More tests will be added here for node registration, router logic, etc.
