import sys, os
# Ensure project root is on PYTHONPATH to import `app`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
import logging

from app.agent.graph import build_langgraph


def test_build_langgraph_includes_custom_mcp_prompt(monkeypatch):
    # Capture prompt argument passed to create_react_agent
    captured = {}

    def fake_create_react_agent(model, tools, *, prompt=None, checkpointer=None, name=None, debug=None):
        captured['prompt'] = prompt
        return 'fake_agent'

    # Monkeypatch the create_react_agent used in graph
    monkeypatch.setattr('app.agent.graph.create_react_agent', fake_create_react_agent)
    # Monkeypatch get_github_mcp_tools to avoid Docker call
    monkeypatch.setattr('app.agent.graph.get_github_mcp_tools', lambda: [])

    graph = build_langgraph(facade=None)  # facade not used for prompt injection
    # Verify the custom instruction prompt is included
    prompt = captured.get('prompt')
    assert prompt is not None, "Prompt was not passed to create_react_agent"
    assert "You are a GitHub assistant with access to GitHub MCP tools" in prompt
    assert "call the get_file_contents tool" in prompt


@pytest.mark.parametrize("user_input,expected_intent", [
    ("Provide a summary of pytorch/pytorch", "github_research"),
    ("Show me the weather", "needs_clarification"),
])
def test_detect_intent_override(monkeypatch, user_input, expected_intent):
    # Test the keyword override in detect_intent
    # Use a dummy model that won't be called
    class DummyModel:
        def invoke(self, messages):
            # Return a dummy JSON intent
            from langchain_core.messages import AIMessage
            return AIMessage(content='{"intent": "chit_chat"}')

    from app.agent.nodes import Nodes
    nodes = Nodes(model=DummyModel(), facade=None)
    intent = nodes.detect_intent(user_input)
    assert intent == expected_intent
