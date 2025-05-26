# app/agent/llm_client.py
import logging
import os
from app.config_manager import ConfigManager
from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseLanguageModel

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Manages the instantiation of the Language Model.
    """
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._llm: BaseLanguageModel | None = None
        self._initialize_llm()

    def _initialize_llm(self):
        """Initializes the LLM based on configuration."""
        effective_model_name: str
        
        # Check for test mode first
        test_mode = self.config_manager.get("test_mode", False)
        test_model_env = os.getenv("TEST_LLM_MODEL")
        
        if test_mode:
            # In test mode, prefer TEST_LLM_MODEL env var, fallback to qwen3:8b
            if test_model_env:
                effective_model_name = test_model_env
                logger.info(f"LLMClient: Test mode enabled, using model from TEST_LLM_MODEL: {effective_model_name}")
            else:
                effective_model_name = "qwen3:8b"  # Always use qwen3:8b as default for tests
                logger.info(f"LLMClient: Test mode enabled, using default test model: {effective_model_name}")
        else:
            # Normal production mode
            if test_model_env:
                effective_model_name = test_model_env
                logger.info(f"LLMClient: Using LLM model from TEST_LLM_MODEL env var: {effective_model_name}")
            else:
                effective_model_name = self.config_manager.get("llm_model", "llama3") # Default if not in config
                logger.info(f"LLMClient: Using LLM model from config ('llm_model') or default: {effective_model_name}")

        ollama_base_url = self.config_manager.get("llm_base_url", "http://host.docker.internal:11434")
        
        # Get timeout configuration
        llm_timeout = self.config_manager.get("timeouts", {}).get("llm_request", 300)
        
        logger.info(f"LLMClient: Loading ChatOllama model: {effective_model_name} from {ollama_base_url} with {llm_timeout}s timeout")
        
        try:
            self._llm = ChatOllama(
                model=effective_model_name, 
                base_url=ollama_base_url,
                timeout=llm_timeout  # Add explicit timeout
            )
            logger.info(f"LLMClient: ChatOllama model '{effective_model_name}' initialized successfully.")
        except Exception as e:
            logger.error(f"LLMClient: Failed to initialize ChatOllama model '{effective_model_name}': {e}", exc_info=True)
            # Potentially raise an error or handle fallback if critical
            raise

    @property
    def llm(self) -> BaseLanguageModel:
        """Returns the initialized LLM instance."""
        if self._llm is None:
            logger.error("LLMClient: LLM not initialized. Call _initialize_llm or check constructor.")
            raise ValueError("LLM not initialized. Cannot provide LLM instance.")
        return self._llm
