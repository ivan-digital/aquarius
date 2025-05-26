import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from app.config_manager import ConfigManager
from app.agent.llm_client import LLMClient
from app.agent.facade import AgentFacade


@pytest.fixture
def mock_config_data() -> Dict[str, Any]:
    """Mock configuration data for testing."""
    return {
        "llm_model": "qwen3:8b",
        "llm_base_url": "http://localhost:11434",
        "llm_temperature": 0.1,
        "llm_timeout": 120,
        "github_token": "test_token_123",
        "test_mode": True
    }


@pytest.fixture
def mock_config_manager(mock_config_data: Dict[str, Any]) -> Mock:
    """Mock ConfigManager for testing."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.get.side_effect = lambda key, default=None: mock_config_data.get(key, default)
    return config_manager


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = Mock()
    llm.ainvoke = AsyncMock(return_value=Mock(content="Mock response"))
    llm.invoke = Mock(return_value=Mock(content="Mock response"))
    return llm


@pytest.fixture
def mock_tools():
    """Mock GitHub tools for testing."""
    tool = Mock()
    tool.name = "github_search_repositories"
    tool.description = "Search GitHub repositories"
    tool.args_schema = Mock()
    return [tool]


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = AsyncMock()
    client.list_tools.return_value = []
    client.get_tools.return_value = []
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
async def agent_facade(mock_config_manager):
    """Create AgentFacade instance for testing."""
    facade = AgentFacade(config_manager=mock_config_manager)
    yield facade
    # Cleanup
    if hasattr(facade, '_mcp_manager') and facade._mcp_manager:
        try:
            await facade._mcp_manager.__aexit__(None, None, None)
        except:
            pass


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_github_response():
    """Mock GitHub API response data."""
    return {
        "repositories": [
            {
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "description": "A test repository",
                "stars": 100,
                "forks": 50
            }
        ],
        "commits": [
            {
                "sha": "abc123",
                "message": "Fix bug in authentication",
                "author": "test-user",
                "date": "2025-05-25T10:00:00Z"
            }
        ]
    }


@pytest.fixture
def mock_gradio_interface():
    """Mock Gradio interface for testing."""
    interface = Mock()
    interface.launch = Mock()
    interface.close = Mock()
    return interface


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    with patch.dict(os.environ, {
        "TEST_MODE": "true",
        "LLM_MODEL": "qwen3:8b",
        "LLM_BASE_URL": "http://localhost:11434"
    }):
        yield


@pytest.fixture(scope="session")
def mock_github_mcp_for_integration():
    """
    Mock GitHub MCP for integration tests to avoid Docker dependency issues.
    This fixture ensures API integration tests can run reliably.
    """
    from unittest.mock import Mock, AsyncMock
    
    # Create mock tools that simulate GitHub functionality
    mock_tools = []
    
    # Mock GitHub search tool
    search_tool = Mock()
    search_tool.name = "search_repositories"
    search_tool.description = "Search GitHub repositories"
    mock_tools.append(search_tool)
    
    # Mock file contents tool  
    file_tool = Mock()
    file_tool.name = "get_file_contents"
    file_tool.description = "Get file contents from repository"
    mock_tools.append(file_tool)
    
    # Mock commits tool
    commits_tool = Mock()
    commits_tool.name = "list_commits"
    commits_tool.description = "List repository commits"
    mock_tools.append(commits_tool)
    
    # Create mock MCP client
    mock_client = AsyncMock()
    mock_client.get_tools.return_value = mock_tools
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    # Create mock MCP manager  
    mock_manager = AsyncMock()
    mock_manager.__aenter__ = AsyncMock(return_value=mock_client)
    mock_manager.__aexit__ = AsyncMock(return_value=None)
    
    return {
        'client': mock_client,
        'manager': mock_manager,
        'tools': mock_tools
    }


@pytest.fixture
def mock_llm_with_github_responses():
    """Mock LLM with realistic GitHub-focused responses for more comprehensive testing."""
    llm = Mock()
    
    def create_response(content):
        response = Mock()
        response.content = content
        return response
    
    # Define responses based on query content
    response_map = {
        "hello": "Hello! I'm a GitHub-focused AI assistant. I can help you explore repositories, analyze code, check recent commits, and understand project structures. How can I assist you today?",
        "how are you": "I'm functioning well and ready to help with GitHub repository analysis! I have access to tools for searching repositories, reading files, and exploring project structures. What would you like to know about?",
        "microsoft/vscode": "The microsoft/vscode repository is the main repository for Visual Studio Code, Microsoft's popular open-source code editor. Here's what I found:\n\n**Repository Overview:**\n- **Stars:** ~150k+ stars\n- **Language:** TypeScript (primary), JavaScript, CSS\n- **Description:** Visual Studio Code combines the simplicity of a code editor with what developers need for their core edit-build-debug cycle.\n\n**Recent Activity:**\n- Active development with daily commits\n- Recent focus on performance improvements and new language features\n- Regular bug fixes and security updates",
        "tensorflow": "The tensorflow/tensorflow repository is Google's open-source machine learning framework. Here's the structure analysis:\n\n**Repository Structure:**\n- **Core Libraries:** `/tensorflow/core/` - Main C++ implementation\n- **Python API:** `/tensorflow/python/` - Python bindings and high-level APIs\n- **Documentation:** `/tensorflow/docs/` - API documentation and guides\n- **Tools:** `/tensorflow/tools/` - Build tools and utilities\n\nThe repository is well-organized with clear documentation and extensive testing infrastructure.",
        "default": "I understand you're asking about GitHub repositories. As a GitHub-focused assistant, I can help you explore repositories, analyze code, and understand project structures. Could you please specify a GitHub repository you'd like me to analyze?"
    }
    
    def mock_invoke(query_or_messages, **kwargs):
        # Handle both string queries and message lists
        if isinstance(query_or_messages, str):
            query = query_or_messages.lower()
        elif isinstance(query_or_messages, list) and len(query_or_messages) > 0:
            # Extract query from last message
            last_msg = query_or_messages[-1]
            if hasattr(last_msg, 'content'):
                query = last_msg.content.lower()
            else:
                query = str(last_msg).lower()
        else:
            query = "default"
        
        # Match query to appropriate response
        for key, response in response_map.items():
            if key in query:
                return create_response(response)
        
        return create_response(response_map["default"])
    
    llm.invoke = Mock(side_effect=mock_invoke)
    llm.ainvoke = AsyncMock(side_effect=mock_invoke)
    
    return llm

@pytest.fixture
def mock_agent_with_comprehensive_responses():
    """Mock agent that provides comprehensive GitHub-focused responses."""
    agent = Mock()
    
    def mock_invoke(state, **kwargs):
        messages = state.get('messages', [])
        if not messages:
            return {'messages': []}
        
        last_message = messages[-1]
        query = last_message.content.lower() if hasattr(last_message, 'content') else str(last_message).lower()
        
        # GitHub-focused responses
        if 'microsoft/vscode' in query or 'vscode' in query:
            response_content = "The microsoft/vscode repository is the main repository for Visual Studio Code. It's written primarily in TypeScript and has over 150k stars. Recent commits show active development focusing on performance improvements and new language features."
        elif 'tensorflow' in query:
            response_content = "The tensorflow/tensorflow repository is Google's machine learning framework. The repository structure includes core C++ libraries, Python APIs, documentation, and extensive tooling. It's a large, well-organized project with modular design."
        elif 'hello' in query:
            response_content = "Hello! I'm a GitHub-focused AI assistant. I can help you explore repositories, analyze code, check recent commits, and understand project structures."
        elif 'how are you' in query:
            response_content = "I'm functioning well and ready to help with GitHub repository analysis! I have access to tools for searching repositories and reading files."
        else:
            response_content = f"I understand you're asking about '{query}'. As a GitHub assistant, I can help with repository exploration and analysis. Please specify a GitHub repository."
        
        # Create mock AI message
        from langchain_core.messages import AIMessage
        response_message = AIMessage(content=response_content)
        
        return {'messages': messages + [response_message]}
    
    agent.invoke = Mock(side_effect=mock_invoke)
    agent.ainvoke = AsyncMock(side_effect=mock_invoke)
    
    return agent

@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for LLM operations with predictable responses."""
    client = Mock()
    
    def mock_generate(model, prompt, **kwargs):
        # Analyze prompt to return appropriate response
        prompt_lower = prompt.lower()
        
        if 'github' in prompt_lower and 'microsoft/vscode' in prompt_lower:
            response_text = "The microsoft/vscode repository contains Visual Studio Code source code. It's actively maintained with regular commits and has extensive TypeScript codebase."
        elif 'github' in prompt_lower and 'tensorflow' in prompt_lower:
            response_text = "The tensorflow/tensorflow repository is Google's machine learning framework with modular structure including core libraries, Python bindings, and comprehensive documentation."
        elif 'hello' in prompt_lower:
            response_text = "Hello! I'm ready to help with GitHub repository analysis and exploration."
        elif 'evaluation' in prompt_lower or 'criteria' in prompt_lower:
            # For LLM judge responses
            response_text = '{"meets_criteria": true, "reason": "Response contains relevant GitHub repository information and demonstrates system functionality."}'
        else:
            response_text = "I'm a GitHub-focused assistant ready to help with repository analysis."
        
        return {'response': response_text}
    
    client.generate = Mock(side_effect=mock_generate)
    return client
