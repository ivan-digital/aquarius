import pytest

# Mark all tests in this file as unit tests (fast with mocking)
pytestmark = pytest.mark.unit
import os
from unittest.mock import Mock, patch, MagicMock
from app.agent.llm_client import LLMClient
from app.config_manager import ConfigManager


class TestLLMClient:
    """Test cases for LLMClient."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get.side_effect = lambda key, default=None: {
            "test_mode": False,
            "llm_model": "qwen3:32b",
            "llm_base_url": "http://localhost:11434",
            "timeouts": {"llm_request": 300}
        }.get(key, default)
        return config_manager

    @patch('app.agent.llm_client.ChatOllama')
    def test_llm_client_initialization_production_mode(self, mock_chat_ollama, mock_config_manager):
        """Test LLMClient initialization in production mode."""
        mock_ollama_instance = Mock()
        mock_chat_ollama.return_value = mock_ollama_instance
        
        client = LLMClient(mock_config_manager)
        
        assert client.config_manager == mock_config_manager
        assert client._llm == mock_ollama_instance
        
        # Verify ChatOllama was called with correct parameters
        mock_chat_ollama.assert_called_once_with(
            model="qwen3:32b",
            base_url="http://localhost:11434",
            timeout=300
        )

    @patch('app.agent.llm_client.ChatOllama')
    def test_llm_client_initialization_test_mode(self, mock_chat_ollama, mock_config_manager):
        """Test LLMClient initialization in test mode."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "test_mode": True,
            "llm_model": "qwen3:32b",
            "llm_base_url": "http://localhost:11434",
            "timeouts": {"llm_request": 300}
        }.get(key, default)
        
        mock_ollama_instance = Mock()
        mock_chat_ollama.return_value = mock_ollama_instance
        
        client = LLMClient(mock_config_manager)
        
        # In test mode, should use qwen3:8b as default
        mock_chat_ollama.assert_called_once_with(
            model="qwen3:8b",
            base_url="http://localhost:11434",
            timeout=300
        )

    @patch('app.agent.llm_client.ChatOllama')
    @patch.dict(os.environ, {'TEST_LLM_MODEL': 'custom-test-model'})
    def test_llm_client_with_test_model_env_var(self, mock_chat_ollama, mock_config_manager):
        """Test LLMClient initialization with TEST_LLM_MODEL environment variable."""
        mock_ollama_instance = Mock()
        mock_chat_ollama.return_value = mock_ollama_instance
        
        client = LLMClient(mock_config_manager)
        
        # Should use the TEST_LLM_MODEL env var
        mock_chat_ollama.assert_called_once_with(
            model="custom-test-model",
            base_url="http://localhost:11434",
            timeout=300
        )

    @patch('app.agent.llm_client.ChatOllama')
    @patch.dict(os.environ, {'TEST_LLM_MODEL': 'custom-test-model'})
    def test_llm_client_test_mode_with_env_var(self, mock_chat_ollama, mock_config_manager):
        """Test LLMClient in test mode with TEST_LLM_MODEL environment variable."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "test_mode": True,
            "llm_model": "qwen3:32b",
            "llm_base_url": "http://localhost:11434",
            "timeouts": {"llm_request": 300}
        }.get(key, default)
        
        mock_ollama_instance = Mock()
        mock_chat_ollama.return_value = mock_ollama_instance
        
        client = LLMClient(mock_config_manager)
        
        # Even in test mode, TEST_LLM_MODEL env var should take precedence
        mock_chat_ollama.assert_called_once_with(
            model="custom-test-model",
            base_url="http://localhost:11434",
            timeout=300
        )

    @patch('app.agent.llm_client.ChatOllama')
    def test_llm_client_with_default_values(self, mock_chat_ollama):
        """Test LLMClient initialization with default config values."""
        mock_config_manager = Mock()
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "test_mode": False,
        }.get(key, default)
        
        mock_ollama_instance = Mock()
        mock_chat_ollama.return_value = mock_ollama_instance
        
        client = LLMClient(mock_config_manager)
        
        # Should use default values
        mock_chat_ollama.assert_called_once_with(
            model="llama3",  # Default model
            base_url="http://host.docker.internal:11434",  # Default base URL
            timeout=300  # Default timeout
        )

    @patch('app.agent.llm_client.ChatOllama')
    def test_llm_client_with_custom_timeout(self, mock_chat_ollama, mock_config_manager):
        """Test LLMClient initialization with custom timeout."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "test_mode": False,
            "llm_model": "qwen3:32b",
            "llm_base_url": "http://localhost:11434",
            "timeouts": {"llm_request": 600}
        }.get(key, default)
        
        mock_ollama_instance = Mock()
        mock_chat_ollama.return_value = mock_ollama_instance
        
        client = LLMClient(mock_config_manager)
        
        mock_chat_ollama.assert_called_once_with(
            model="qwen3:32b",
            base_url="http://localhost:11434",
            timeout=600
        )

    @patch('app.agent.llm_client.ChatOllama')
    def test_llm_client_initialization_failure(self, mock_chat_ollama, mock_config_manager):
        """Test LLMClient initialization when ChatOllama fails."""
        mock_chat_ollama.side_effect = Exception("Failed to connect to Ollama")
        
        with pytest.raises(Exception, match="Failed to connect to Ollama"):
            LLMClient(mock_config_manager)

    @patch('app.agent.llm_client.ChatOllama')
    def test_llm_property_returns_instance(self, mock_chat_ollama, mock_config_manager):
        """Test that llm property returns the initialized instance."""
        mock_ollama_instance = Mock()
        mock_chat_ollama.return_value = mock_ollama_instance
        
        client = LLMClient(mock_config_manager)
        
        assert client.llm == mock_ollama_instance

    def test_llm_property_raises_when_not_initialized(self, mock_config_manager):
        """Test that llm property raises error when LLM not initialized."""
        client = LLMClient.__new__(LLMClient)  # Create instance without calling __init__
        client.config_manager = mock_config_manager
        client._llm = None
        
        with pytest.raises(ValueError, match="LLM not initialized"):
            _ = client.llm

    @patch('app.agent.llm_client.ChatOllama')
    def test_llm_client_docker_base_url(self, mock_chat_ollama, mock_config_manager):
        """Test LLMClient with Docker-specific base URL."""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "test_mode": False,
            "llm_model": "qwen3:32b",
            "llm_base_url": "http://host.docker.internal:11434",  # Docker URL
            "timeouts": {"llm_request": 300}
        }.get(key, default)
        
        mock_ollama_instance = Mock()
        mock_chat_ollama.return_value = mock_ollama_instance
        
        client = LLMClient(mock_config_manager)
        
        mock_chat_ollama.assert_called_once_with(
            model="qwen3:32b",
            base_url="http://host.docker.internal:11434",
            timeout=300
        )
