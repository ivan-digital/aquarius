import pytest
from flask import json
from app.server.routes import app
from app.agent.graph import build_langgraph
from langchain_core.messages import AIMessage, HumanMessage

@pytest.fixture(autouse=True)
def stub_graph(monkeypatch):
    # Create a fake react_mcp node that returns a dummy summary
    def fake_create_react_agent(model, tools, *, prompt=None, checkpointer=None, name=None, debug=None):
        # Return a callable that simulates a react_mcp agent
        def fake_agent_node(state, config):
            # state['messages'] contains [HumanMessage]
            user_msg = state['messages'][-1]
            # Respond with a dummy summary
            summary = f"Summary of {user_msg.content.split()[-1]}"
            return {"messages": [AIMessage(content=summary)]}
        return fake_agent_node

    # Stub get_github_mcp_tools to avoid Docker call
    monkeypatch.setattr('app.agent.graph.get_github_mcp_tools', lambda: [])
    monkeypatch.setattr('app.agent.graph.create_react_agent', fake_create_react_agent)
    # Also force detect_intent to route to react_mcp
    from app.agent.nodes import Nodes
    monkeypatch.setattr(Nodes, 'detect_intent', lambda self, text: 'github_research')

    # Rebuild graph to apply stubs
    from app.server.chat import ChatService
    ChatService().graph = build_langgraph(None)
    yield


def test_chat_summary_end_to_end(monkeypatch):
    app.testing = True
    with app.test_client() as client:
        message = "Provide a summary of owner/repo"
        resp = client.post('/chat', json={"user_id": "u1", "message": message})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['assistant_reply'] == f"Summary of {message.split()[-1]}"
        # History should include assistant message
        roles = [m['role'] for m in data['messages']]
        assert 'assistant' in roles
