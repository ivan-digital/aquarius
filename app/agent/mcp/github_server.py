# app/agent/mcp/github_server.py

import logging
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient
from app.config_manager import configManager

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def get_github_mcp_tools():
    """
    Spins up a single GitHub MCP server (via Docker) and returns
    the list of loaded tools for use in a react agent.
    """
    github_token = configManager.config.get("github_token")
    mcp_servers = {
        "github": {
            "transport": "stdio",
            "command": "docker",
            "args": [
                "run", "-i", "--rm",
                "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                "ghcr.io/github/github-mcp-server"
            ],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
                "FASTMCP_LOG_LEVEL": "DEBUG"
            },
        }
    }

    async def _fetch():
        async with MultiServerMCPClient(mcp_servers) as client:
            return client.get_tools()

    loop = asyncio.new_event_loop()
    try:
        tools = loop.run_until_complete(_fetch())
    finally:
        loop.close()

    logger.info("Loaded %d GitHub-MCP tools", len(tools))
    return tools