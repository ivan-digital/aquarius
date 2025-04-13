import time
from typing import Dict, Any, Optional, Union, Literal, TypeVar

from ollama import Client

JsonSchemaValue = Dict[str, Any]
T = TypeVar('T')


def _extract_json(text: str) -> dict:
    """
    Extracts the JSON object from the response text.
    Searches for a block delimited by ```json ... ```; if not found,
    falls back to extracting from the first '{' to the last '}'.
    """
    import re
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
    import json
    try:
        return json.loads(json_str)
    except Exception as e:
        print("Error parsing extracted JSON:", e)
        return {}


class LLMClient:
    """
    Service for interacting with an LLM via Ollama.
    This wrapper uses the official Ollama client directly so that it
    integrates with your LangGraph setup.
    """

    def __init__(self, config: Dict[str, Any]):
        self.endpoint = config["llm_endpoint"]
        self.model_name = config["model_name"]
        # Directly instantiate the Ollama client.
        self.client = Client(host=self.endpoint)

    def completion(
        self,
        prompt: str,
        _format: Optional[Union[Literal['', 'json'], JsonSchemaValue]] = None,
    ) -> dict:
        """
        Sends a prompt along with an optional JSON schema so that the model returns
        structured output. Returns a dictionary that includes execution time.
        """
        start = time.time()
        response = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            format=_format
        )
        # Extract the "response" from the output and parse JSON.
        text = response.get("response", "")
        parsed = _extract_json(text)
        parsed["execution"] = time.time() - start
        return parsed

    def chat_with_tools(self, messages: list, tools: list) -> Dict[str, str]:
        """
        Sends a chat prompt with a list of messages and a set of tools.
        If the response includes tool calls, it will execute the matching tool.
        Otherwise, it returns the model's message.
        """

        ollama_tools = []
        for structured_tool in tools:
            schema_dict = structured_tool.args_schema.schema()

            tool_dict = {
                "name": structured_tool.name,
                "description": structured_tool.description,
                "function": {
                    "name": structured_tool.name,
                    "description": structured_tool.description,
                    "parameters": schema_dict
                }
            }
            ollama_tools.append(tool_dict)

        # Now pass the list of dictionaries to Ollama
        response = self.client.chat(
            model=self.model_name,
            messages=messages,
            tools=ollama_tools
        )

        # Manually handle calls if the model tries to invoke a tool
        if hasattr(response, "message") and getattr(response.message, "tool_calls", None):
            for tool_call in response.message.tool_calls:
                tool_name = tool_call.function.name
                arguments = tool_call.function.arguments

                # match the correct structured_tool
                matched_tool = next((t for t in tools if t.name == tool_name), None)
                if matched_tool:
                    try:
                        result = matched_tool.run(**arguments)
                    except Exception as e:
                        result = f"Error executing tool {tool_name}: {e}"

                    return {
                        "role": "assistant",
                        "content": f"Tool {tool_name} execution result: {result}"
                    }

        # Otherwise, return normal message
        return {
            "role": response.message.role,
            "content": response.message.content,
        }