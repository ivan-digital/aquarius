import pytest

# Mark all tests in this file as unit tests (fast with mocking)
pytestmark = pytest.mark.unit
import os
import tempfile
import yaml
from unittest.mock import patch

from app.config_manager import ConfigManager


class TestConfigManager:
    """Test ConfigManager functionality according to simplified requirements."""

    def test_config_manager_initialization_with_valid_files(self):
        """Test ConfigManager loads config and keys files correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test config files
            config_data = {
                "llm_model": "qwen3:32b",
                "llm_base_url": "http://localhost:11434",
                "llm_temperature": 0.1
            }
            keys_data = {
                "github_token": "test_token_123"
            }
            
            config_file = os.path.join(temp_dir, "config.yaml")
            keys_file = os.path.join(temp_dir, "keys.yaml")
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            with open(keys_file, 'w') as f:
                yaml.dump(keys_data, f)
            
            # Test initialization
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                config_manager = ConfigManager()
                
                assert config_manager.get("llm_model") == "qwen3:32b"
                assert config_manager.get("github_token") == "test_token_123"

    def test_config_manager_missing_config_file(self):
        """Test ConfigManager raises error when config file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                with pytest.raises(FileNotFoundError):
                    ConfigManager()

    def test_config_manager_missing_keys_file_optional(self):
        """Test ConfigManager handles missing optional keys file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_data = {"llm_model": "qwen3:8b"}
            config_file = os.path.join(temp_dir, "config.yaml")
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                config_manager = ConfigManager()
                
                assert config_manager.get("llm_model") == "qwen3:8b"
                assert config_manager.get("github_token") is None

    def test_config_manager_environment_variable_override(self):
        """Test ConfigManager respects environment variable overrides."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_data = {"llm_base_url": "http://localhost:11434"}
            config_file = os.path.join(temp_dir, "config.yaml")
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                with patch.dict(os.environ, {"LLM_BASE_URL": "http://override:8080"}):
                    config_manager = ConfigManager()
                    assert config_manager.get("llm_base_url") == "http://override:8080"

    def test_config_manager_test_mode_environment(self):
        """Test ConfigManager handles test mode from environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.yaml")
            with open(config_file, 'w') as f:
                yaml.dump({}, f)
            
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                with patch.dict(os.environ, {"TEST_MODE": "true"}):
                    config_manager = ConfigManager()
                    assert config_manager.get("test_mode") is True

    def test_config_manager_llm_model_environment_override(self):
        """Test ConfigManager respects LLM_MODEL environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_data = {"llm_model": "qwen3:32b"}
            config_file = os.path.join(temp_dir, "config.yaml")
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                with patch.dict(os.environ, {"LLM_MODEL": "qwen3:8b"}):
                    config_manager = ConfigManager()
                    assert config_manager.get("llm_model") == "qwen3:8b"

    def test_config_manager_github_token_fallback(self):
        """Test ConfigManager falls back to environment for GitHub token."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.yaml")
            with open(config_file, 'w') as f:
                yaml.dump({}, f)
            
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_456"}):
                    config_manager = ConfigManager()
                    assert config_manager.get("github_token") == "env_token_456"

    def test_config_manager_default_values(self):
        """Test ConfigManager returns default values when key not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.yaml")
            with open(config_file, 'w') as f:
                yaml.dump({}, f)
            
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                config_manager = ConfigManager()
                
                assert config_manager.get("nonexistent_key") is None
                assert config_manager.get("nonexistent_key", "default_value") == "default_value"

    def test_config_manager_keys_priority_over_config(self):
        """Test ConfigManager prioritizes keys file over config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_data = {"llm_model": "config_model"}
            keys_data = {"llm_model": "keys_model"}
            
            config_file = os.path.join(temp_dir, "config.yaml")
            keys_file = os.path.join(temp_dir, "keys.yaml")
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            with open(keys_file, 'w') as f:
                yaml.dump(keys_data, f)
            
            with patch('os.path.dirname') as mock_dirname:
                mock_dirname.return_value = temp_dir
                config_manager = ConfigManager()
                
                assert config_manager.get("llm_model") == "keys_model"
