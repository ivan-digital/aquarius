import pytest
from flask import json
from app.server.routes import app
from app.server.chat import ChatService


def test_chat_route_basics(monkeypatch):
    # Ensure Flask app responds with proper structure
    app.testing = True

    # Monkeypatch ChatService.process_message to return a known reply
    fake_reply = "Fake reply"
    fake_history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": fake_reply}]
    monkeypatch.setattr(ChatService, 'process_message', lambda self, uid, msg: (fake_reply, fake_history))

    with app.test_client() as client:
        response = client.post('/chat', json={"user_id": "user1", "message": "Hello"})
        assert response.status_code == 200
        data = response.get_json()
        assert 'assistant_reply' in data
        assert data['assistant_reply'] == fake_reply
        assert 'messages' in data
        assert data['messages'] == fake_history


def test_summary_request_fallback(monkeypatch):
    # Test that a summary request returns the fallback message when no real GitHub MCP is available
    cs = ChatService()
    reply, history = cs.process_message("test_user", "Provide a summary of pytorch/pytorch")
    assert isinstance(reply, str)
    # Expect fallback for now
    assert "I am not equipped to handle this task" in reply
    # History should include user message and assistant reply
    roles = [m['role'] for m in history]
    assert 'user' in roles
    assert 'assistant' in roles
