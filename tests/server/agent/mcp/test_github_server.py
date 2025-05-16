import pytest
import asyncio
import logging

from app.agent.mcp.github_server import get_github_mcp_tools
from langchain_mcp_adapters.client import MultiServerMCPClient

class DummyClient:
    def __init__(self, servers):
        self.servers = servers
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    def get_tools(self):
        # Return dummy tools list
        return ["dummy_tool1", "dummy_tool2"]

@pytest.fixture(autouse=True)
def patch_mcp_client(monkeypatch):
    # Patch the MultiServerMCPClient to use DummyClient
    monkeypatch.setattr(
        "app.agent.mcp.github_server.MultiServerMCPClient",
        lambda servers: DummyClient(servers)
    )

def test_get_github_mcp_tools_returns_dummy_tools(caplog):
    caplog.set_level(logging.DEBUG)
    tools = get_github_mcp_tools()
    assert isinstance(tools, list)
    assert tools == ["dummy_tool1", "dummy_tool2"]
    # Ensure debug logs contain server config
    assert "GitHub MCP server configuration" in caplog.text
    assert "Fetched GitHub MCP tools" in caplog.text
