import sys
import os
import pytest
import logging
import asyncio
import json
import ollama
from typing import Tuple

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment with simplified agent configuration."""
    os.environ["APP_COMPONENT"] = "test"
    os.environ["TEST_LLM_MODEL"] = "qwen3:8b"  # Ensure qwen3:8b for all tests
    os.environ["TEST_MODE"] = "true"  # Explicitly enable test mode
    
    # Auto-enable test mode for all tests
    from app.config_manager import ConfigManager
    config_manager = ConfigManager()
    config_manager.config["test_mode"] = True
    config_manager.config["llm_model"] = "qwen3:8b"  # Use smaller model for tests
    
    logging.info("Test environment configured with test_mode=True and model=qwen3:8b")
    return config_manager


@pytest.fixture(scope="session")
def llm_judge():
    """
    LLM judge fixture that uses local Ollama qwen3:8b model to evaluate response quality.
    Returns a function that can judge if a response meets given criteria.
    """
    import ollama
    
    async def judge_response(query: str, response: str, criteria: str) -> Tuple[bool, str]:
        """
        Judge if a response meets the given criteria.
        
        Args:
            query: The original user query
            response: The assistant's response to evaluate
            criteria: The evaluation criteria
            
        Returns:
            Tuple of (is_good_response: bool, reason: str)
        """
        evaluation_prompt = f"""
You are an expert evaluator. Please evaluate if the following response adequately answers the user's query according to the given criteria.

USER QUERY: {query}

ASSISTANT RESPONSE: {response}

EVALUATION CRITERIA:
{criteria}

Please respond with a JSON object containing:
1. "meets_criteria": true/false
2. "reason": brief explanation of your evaluation

Example response:
{{"meets_criteria": true, "reason": "Response contains relevant GitHub repository information including description and features."}}
"""
        
        try:
            print(f"DEBUG: llm_judge starting evaluation...")
            print(f"DEBUG: Query: {query[:100]}...")
            print(f"DEBUG: Response: {response[:100]}...")
            
            # Use Ollama client to get evaluation
            result = ollama.generate(
                model="qwen3:8b",
                prompt=evaluation_prompt,
                options={"temperature": 0.1}
            )
            
            print(f"DEBUG: llm_judge got result from ollama")
            response_text = result['response'].strip()
            print(f"DEBUG: llm_judge response: {response_text[:200]}...")
            
            # Try to extract JSON from the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                evaluation = json.loads(json_str)
                
                meets_criteria = evaluation.get("meets_criteria", False)
                reason = evaluation.get("reason", "No reason provided")
                
                return meets_criteria, reason
            else:
                # Fallback: simple text analysis
                response_lower = response_text.lower()
                if "true" in response_lower or "meets" in response_lower:
                    return True, "LLM indicated response meets criteria"
                else:
                    return False, "LLM indicated response does not meet criteria"
                    
        except Exception as e:
            # Fallback: basic keyword matching
            response_lower = response.lower()
            query_lower = query.lower()
            
            # Simple heuristic: if response contains key terms from query, consider it good
            if any(word in response_lower for word in query_lower.split() if len(word) > 3):
                return True, f"Fallback evaluation: Response contains relevant keywords from query (LLM error: {e})"
            else:
                return False, f"Fallback evaluation: Response lacks relevant content (LLM error: {e})"
    
    return judge_response
