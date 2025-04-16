import unittest
from unittest.mock import MagicMock
import json

from app.agent import LLMClient


class DummyFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class DummyToolCall:
    def __init__(self, function):
        self.function = function

class DummyResponse:
    def __init__(self, tool_calls=None, response=""):
        self.tool_calls = tool_calls if tool_calls is not None else []
        self.response = response

# Define a dummy tool function to be used in the tests.
def dummy_tool(arg1):
    return "dummy tool output"

class TestLLMClient(unittest.TestCase):
    def setUp(self):
        # Create a dummy configuration for the LLMClient.
        config = {
            "llm_endpoint": "http://dummy-endpoint",
            "model_name": "dummy-model"
        }
        self.llm_service = LLMClient(config)
        # Replace the actual Ollama client with a MagicMock to control responses.
        self.llm_service.client = MagicMock()

    def test_completion_with_valid_json(self):
        # Prepare a dummy JSON response wrapped in a markdown code block.
        json_payload = {"summary": "Test summary", "classification": "Test classification"}
        json_response = json.dumps(json_payload)
        response_text = f"Some intro text ```json\n{json_response}\n``` some trailing text."
        self.llm_service.client.generate.return_value = {"response": response_text}

        # Call the completion method.
        result = self.llm_service.completion("Test prompt")

        # Assert that the parsed output matches the dummy payload.
        self.assertEqual(result.get("summary"), "Test summary")
        self.assertEqual(result.get("classification"), "Test classification")
        self.assertIn("execution", result)
        self.assertIsInstance(result["execution"], float)

    def test_chat_with_tools(self):
        # Create an initial messages list.
        messages = [{"role": "user", "content": "Please call dummy tool"}]

        # Set up a dummy tool call that should trigger the dummy_tool function.
        dummy_func = DummyFunction("dummy_tool", {"arg1": "value1"})
        dummy_tool_call = DummyToolCall(dummy_func)
        # Simulate a chat response that first returns a tool call...
        response_with_tool = DummyResponse(tool_calls=[dummy_tool_call])
        # ... and then a final response with no tool calls.
        response_final = DummyResponse(tool_calls=[], response="final response")

        # Configure the client's chat method to return these responses in order.
        self.llm_service.client.chat.side_effect = [response_with_tool, response_final]

        # Call chat_with_tools with a max_rounds value that ensures we process both responses.
        final_response = self.llm_service.chat_with_tools(messages, tools=[dummy_tool], max_rounds=2)

        # Verify that a tool message was appended to the messages list.
        tool_messages = [msg for msg in messages if msg["role"] == "tool" and msg["name"] == "dummy_tool"]
        self.assertTrue(len(tool_messages) > 0)
        self.assertEqual(tool_messages[0]["content"], "dummy tool output")

        # Verify that the final response returned is the one with no tool_calls.
        self.assertEqual(final_response, response_final)

if __name__ == "__main__":
    unittest.main()