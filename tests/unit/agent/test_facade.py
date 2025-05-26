import pytest

# Mark all tests in this file as unit tests (fast with mocking)
pytestmark = pytest.mark.unit
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.agent.facade import AgentFacade
from app.server.models import AgentResponse

# Mock classes for langchain_core.messages to avoid depending on the actual package
class MockMessage:
    def __init__(self, content="", type="unknown"):
        self.content = content
        self.type = type

class MockAIMessage(MockMessage):
    def __init__(self, content="", tool_calls=None):
        super().__init__(content=content, type="ai")
        self.tool_calls = tool_calls or []

class MockHumanMessage(MockMessage):
    def __init__(self, content=""):
        super().__init__(content=content, type="human")


class TestAgentFacade:
    """Test cases for AgentFacade - simplified GitHub ReAct agent."""

    @pytest.mark.asyncio
    async def test_facade_initialization(self, mock_config_manager):
        """Test that AgentFacade initializes correctly."""
        facade = AgentFacade(config_manager=mock_config_manager)
        
        assert facade.config_manager == mock_config_manager
        assert facade._github_token is None
        assert hasattr(facade, '_initialization_lock')
        
    @pytest.mark.asyncio
    @patch('app.agent.facade.LLMClient')
    @patch('app.agent.facade.MultiServerMCPClient')
    async def test_invoke_creates_agent_on_first_use(self, mock_mcp_client, mock_llm_client, mock_config_manager):
        """Test that agent is created on first invoke call."""
        # Setup mocks
        mock_llm = Mock()
        mock_llm_instance = Mock()
        mock_llm_instance.llm = mock_llm
        mock_llm_client.return_value = mock_llm_instance

        # Mock MCP client and tools
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.list_tools.return_value = []
        mock_mcp_client.return_value = mock_mcp_instance

        # Mock agent response with proper message structure
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                MockHumanMessage(content="Tell me about microsoft/vscode"),
                MockAIMessage(content="Repository summary completed.")
            ]
        }

        facade = AgentFacade(config_manager=mock_config_manager)

        with patch('app.agent.facade.create_react_agent', return_value=mock_agent):
            result = await facade.invoke("test_user", "Tell me about microsoft/vscode")

            assert isinstance(result, AgentResponse)
            assert result.success
            assert "Repository summary completed" in result.message

    @pytest.mark.asyncio
    @patch('app.agent.facade.LLMClient')
    async def test_invoke_handles_github_queries(self, mock_llm_client, mock_config_manager):
        """Test that facade handles GitHub repository queries."""
        mock_llm = Mock()
        mock_llm_instance = Mock()
        mock_llm_instance.llm = mock_llm
        mock_llm_client.return_value = mock_llm_instance
        
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [MockAIMessage(content="The repository has 3 recent commits with bug fixes and new features.")]
        }

        facade = AgentFacade(config_manager=mock_config_manager)
        
        with patch('app.agent.facade.create_react_agent', return_value=mock_agent):
            result = await facade.invoke("test_user", "What are the recent changes in owner/repo?")
            
            assert isinstance(result, AgentResponse)
            assert result.success
            assert "recent commits" in result.message
            assert "bug fixes" in result.message

    @pytest.mark.asyncio
    @patch('app.agent.facade.LLMClient')
    @patch('app.agent.facade.MultiServerMCPClient')
    async def test_invoke_handles_timeout(self, mock_mcp_client, mock_llm_client, mock_config_manager):
        """Test that invoke handles timeout gracefully."""
        mock_llm = Mock()
        mock_llm_instance = Mock()
        mock_llm_instance.llm = mock_llm
        mock_llm_client.return_value = mock_llm_instance

        # Mock MCP client and tools
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.list_tools.return_value = []
        mock_mcp_client.return_value = mock_mcp_instance

        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = asyncio.TimeoutError()
        
        facade = AgentFacade(config_manager=mock_config_manager)
        
        with patch('app.agent.facade.create_react_agent', return_value=mock_agent):
            result = await facade.invoke("test_user", "Test query")
            
            assert isinstance(result, AgentResponse)
            assert not result.success
            assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_close_resources_cleans_up(self, mock_config_manager):
        """Test that close_resources properly cleans up."""
        facade = AgentFacade(config_manager=mock_config_manager)
        
        # Since the facade now uses per-request clients, close_resources should clear the github token
        facade._github_token = "test_token"
        
        await facade.close_resources()
        
        assert facade._github_token is None

    @pytest.mark.asyncio
    async def test_start_initializes_basic_setup(self, mock_config_manager):
        """Test that start method initializes basic setup."""
        facade = AgentFacade(config_manager=mock_config_manager)
        
        with patch.object(facade, '_initialize_basic_setup_if_needed', new_callable=AsyncMock) as mock_init:
            await facade.start()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_closes_resources(self, mock_config_manager):
        """Test that stop method closes resources."""
        facade = AgentFacade(config_manager=mock_config_manager)
        
        with patch.object(facade, 'close_resources', new_callable=AsyncMock) as mock_close:
            await facade.stop()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_per_request_llm_client(self, mock_config_manager):
        """Test that per-request LLM client is created correctly."""
        facade = AgentFacade(config_manager=mock_config_manager)
        
        with patch('app.agent.facade.LLMClient') as mock_llm_client:
            mock_instance = Mock()
            mock_llm_client.return_value = mock_instance
            
            result = await facade._create_per_request_llm_client()
            
            assert result == mock_instance
            mock_llm_client.assert_called_once_with(config_manager=mock_config_manager)

    @pytest.mark.asyncio
    async def test_create_per_request_mcp_client_without_token(self, mock_config_manager):
        """Test that MCP client creation returns empty tools when no GitHub token."""
        facade = AgentFacade(config_manager=mock_config_manager)
        facade._github_token = None
        
        result = await facade._create_per_request_mcp_client()
        
        assert result == (None, [])

    @pytest.mark.asyncio
    async def test_generate_error_response(self, mock_config_manager):
        """Test error response generation."""
        facade = AgentFacade(config_manager=mock_config_manager)
        
        with patch.object(facade, '_create_per_request_llm_client') as mock_create_llm:
            # Return None to trigger the hardcoded fallback message
            mock_create_llm.return_value = None
            
            result = await facade._generate_error_response("Test error", "Test message")
            
            # Should use fallback error message
            assert "technical issue" in result.lower()
            assert "try rephrasing" in result.lower()
