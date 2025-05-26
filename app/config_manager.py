import os
import yaml


class ConfigManager:
    """
    A helper class to load and manage configuration from YAML files.
    It loads a primary config file and an optional keys file.
    """

    def __init__(self, config_file="config.yaml", keys_file="keys.yaml"):
        # Determine the project root directory assuming this script is in app/
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.config_file = os.path.join(project_root, config_file)
        self.keys_file = os.path.join(project_root, keys_file)

        self.config = self._load_config(self.config_file)
        self.keys = self._load_config(self.keys_file, optional=True)

    def _load_config(self, file_path, optional=False):
        if not os.path.exists(file_path):
            if optional:
                return {}  # Return empty dict if optional file is not found
            raise FileNotFoundError(f"Configuration file '{file_path}' not found.")
        with open(file_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        return config_data if config_data is not None else {}  # Ensure {} if file is empty

    def get(self, key, default=None):
        # Check for environment variables for specific keys
        if key == "llm_base_url":
            env_value = os.getenv("LLM_BASE_URL")
            if env_value:
                return env_value
                
        # Check for test mode environment variable
        if key == "test_mode":
            test_mode = os.getenv("TEST_MODE")
            if test_mode:
                return test_mode.lower() == "true"
                
        # Check for LLM model override
        if key == "llm_model":
            # Priority 1: Environment variable
            model = os.getenv("LLM_MODEL")
            if model:
                return model
                
            # Priority 2: Use test model in test mode
            test_mode = os.getenv("TEST_MODE")
            if test_mode and test_mode.lower() == "true":
                return "qwen3:8b"
                
            # Priority 3: Use test model if test_mode config is true
            config_test_mode = self.config.get("test_mode", False)
            if config_test_mode:
                return "qwen3:8b"

        # Prioritize keys file, then config file
        value = self.keys.get(key, self.config.get(key, default))
        # Fallback to environment variable if key is github_token and not found
        if key == "github_token" and value is None:
            value = os.getenv("GITHUB_TOKEN", os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", default))
        return value
    
    def get_config(self, key, default=None):
        """
        Alias for get(), used by components expecting get_config interface.
        """
        return self.get(key, default)


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# configManager will now load both config.yaml and keys.yaml from the project root
configManager = ConfigManager(config_file="config.yaml", keys_file="keys.yaml")
