import pytest

# Mark all tests in this file as unit tests (fast with mocking)
pytestmark = pytest.mark.unit
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.agent.graph import build_github_react_agent


class TestGraphModule:
    """Test cases for simplified graph module - GitHub ReAct agent creation."""

    @pytest.fixture
    def mock_config_manager(self):
        """Mock ConfigManager for testing."""
        config_manager = Mock()
        config_manager.get.side_effect = lambda key, default=None: {
            "llm_model": "qwen3:8b",  # Explicitly use lightweight model for tests
            "llm_base_url": "http://localhost:11434",
            "llm_temperature": 0.1
        }.get(key, default)
        return config_manager

    @patch('app.agent.graph.create_react_agent')
    def test_build_github_react_agent(self, mock_create_react, mock_config_manager):
        """Test that GitHub ReAct agent is created correctly with proper configuration."""
        mock_llm = Mock()
        mock_agent = Mock()
        mock_create_react.return_value = mock_agent
        
        # Create GitHub-specific tools
        mock_tools = [
            Mock(name="github_search_repositories", description="Search for GitHub repositories"),
            Mock(name="github_get_repository", description="Get details about a GitHub repository"),
            Mock(name="github_list_commits", description="List commits in a GitHub repository")
        ]

        result = build_github_react_agent(mock_config_manager, mock_llm, mock_tools)

        mock_create_react.assert_called_once()
        
        # Verify LLM and tools were passed to create_react_agent
        call_args = mock_create_react.call_args
        assert call_args[1]['model'] == mock_llm
        assert call_args[1]['tools'] == mock_tools
        
        # Verify we're using a checkpoint saver for state persistence
        assert 'checkpointer' in call_args[1]
        
        # Verify the result is our mock agent
        assert result == mock_agent

    @patch('app.agent.graph.create_react_agent')
    def test_build_agent_with_empty_tools(self, mock_create_react, mock_config_manager):
        """Test that agent can be built with empty tools list."""
        mock_llm = Mock()
        mock_agent = Mock()
        mock_create_react.return_value = mock_agent

        result = build_github_react_agent(mock_config_manager, mock_llm, [])

        mock_create_react.assert_called_once()
        call_args = mock_create_react.call_args
        assert call_args[1]['tools'] == []
        assert result == mock_agent

    @patch('app.agent.graph.create_react_agent')
    def test_build_agent_handles_creation_error(self, mock_create_react, mock_config_manager):
        """Test that agent creation error is handled gracefully."""
        mock_llm = Mock()
        mock_create_react.side_effect = Exception("Agent creation failed")

        with pytest.raises(Exception):
            # The function should raise an exception when creation fails
            build_github_react_agent(mock_config_manager, mock_llm, [])

    def test_system_prompt_includes_github_context(self, mock_config_manager):
        """Test that the system prompt includes GitHub-specific context focusing on repository exploration."""
        mock_llm = Mock()
        mock_tools = []
        
        with patch('app.agent.graph.create_react_agent') as mock_create_react:
            build_github_react_agent(mock_config_manager, mock_llm, mock_tools)
            
            # Verify system prompt was used and contains all required GitHub context
            call_args = mock_create_react.call_args
            state_modifier = call_args[1]['state_modifier']
            
            # Check for essential GitHub-focused assistant components
            assert "GitHub assistant" in state_modifier
            assert "repositories" in state_modifier
            assert "GitHub tools" in state_modifier
            
            # Check for specific capabilities mentioned in the prompt
            assert "explore GitHub repositories" in state_modifier
            assert "analyze code" in state_modifier or "analyze repository" in state_modifier
            assert "recent changes" in state_modifier or "recent commits" in state_modifier
            
            # Ensure the prompt doesn't mention non-GitHub features
            assert "database" not in state_modifier.lower()
            assert "web search" not in state_modifier.lower()
            assert "chat" not in state_modifier.lower() or "chat with repository" in state_modifier.lower()

    @patch('app.agent.graph.create_react_agent')
    def test_react_agent_pattern_used(self, mock_create_react, mock_config_manager):
        """Test that the ReAct agent pattern is specifically used (Reasoning and Acting)."""
        mock_llm = Mock()
        mock_agent = Mock()
        mock_create_react.return_value = mock_agent
        
        build_github_react_agent(mock_config_manager, mock_llm, [])
        
        # Verify create_react_agent was called (not other agent types)
        mock_create_react.assert_called_once()
        
        # Check that essential ReAct pattern components are being passed
        call_args = mock_create_react.call_args[1]
        assert 'model' in call_args  # LLM for reasoning
        assert 'tools' in call_args  # Tools for acting
        
        # Verify no complex routing or state machines are used
        with patch('langgraph.graph.StateGraph', create=True) as mock_state_graph:
            build_github_react_agent(mock_config_manager, mock_llm, [])
            mock_state_graph.assert_not_called()
