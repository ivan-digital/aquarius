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
    if not github_token:
        logger.error("GitHub token is not set in configManager.config['github_token']")
        raise RuntimeError("Missing GitHub token for MCP server initialization")

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
    logger.debug("GitHub MCP server configuration: %s", mcp_servers)

    async def _fetch():
        logger.debug("Starting async fetch of GitHub MCP tools")
        async with MultiServerMCPClient(mcp_servers) as client:
            logger.debug("MultiServerMCPClient started, fetching tools...")
            return client.get_tools()

    loop = asyncio.new_event_loop()
    try:
        logger.debug("Running event loop %s to fetch GitHub MCP tools", loop)
        tools = loop.run_until_complete(_fetch())
        logger.debug("Fetched GitHub MCP tools: %s", tools)
    except Exception as e:
        logger.error("Error initializing GitHub MCP server or fetching tools: %s", e)
        raise
    finally:
        loop.close()

    logger.info("Loaded %d GitHub-MCP tools", len(tools))
    return tools