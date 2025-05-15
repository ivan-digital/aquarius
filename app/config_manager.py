import os
import yaml


class ConfigManager:
    """
    A helper class to load and manage configuration from a YAML file.
    Expected YAML format:
      llm_endpoint: "http://localhost:11434"
      model_name: "your_model_name_here"
    """

    def __init__(self, config_file="/config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found.")
        with open(self.config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config

    def get(self, key, default=None):
        return self.config.get(key, default)


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
configManager = ConfigManager(os.path.join(PROJECT_DIR, "../config.yaml"))
