import json
import re
import time
from typing import Dict, Any, Optional, Union, Literal, TypeVar
from ollama import Client

JsonSchemaValue = Dict[str, Any]
T = TypeVar('T')


class LLMClient:
    """
    Service for interacting with an LLM via the Ollama client.
    """

    def __init__(self, config):
        self.endpoint = config["llm_endpoint"]
        self.model_name = config["model_name"]
        self.client = Client(host=self.endpoint)

    def completion(
            self,
            prompt: str,
            _format: Optional[Union[Literal['', 'json'], JsonSchemaValue]] = None,
    ) -> dict:
        """
        Sends the prompt along with a JSON schema so that the model returns
        structured output. Returns a dict with keys 'summary' and 'classification'.
        """
        start = time.time()
        response = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            format=_format
        )
        text = response.get("response", "")
        parsed = self._extract_json(text)
        parsed["execution"] = time.time() - start
        return parsed

    def _extract_json(self, text: str) -> dict:
        """
        Extracts the JSON object from the response text.
        First, it searches for a block delimited by ```json ... ```
        If not found, it falls back to extracting the text from the first '{'
        to the last '}'.
        """
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                json_str = text[start:end + 1]
            else:
                return {}
        try:
            return json.loads(json_str)
        except Exception as e:
            print("Error parsing extracted JSON:", e)
            return {}

    def chat_with_tools(self, messages, tools):
        response = self.client.chat(model=self.model_name, messages=messages, tools=tools)
        print(response)
        if hasattr(response, "message") and hasattr(response.message, "tool_calls") and response.message.tool_calls:
            for tool_call in response.message.tool_calls:
                tool_name = tool_call.function.name
                arguments = tool_call.function.arguments
                matched_tool = next(
                    (tool for tool in tools if getattr(tool, '__name__', None) == tool_name),
                    None
                )
                if matched_tool:
                    try:
                        tool_result = matched_tool(**arguments)
                    except Exception as e:
                        tool_result = f"Error executing tool '{tool_name}': {e}"
                    return {
                        "role": "assistant",
                        "content": f"Tool {tool_name} execution result: {tool_result}"
                    }
        else:
            return {"content": response.message.content, "role": response.message.role}
