# services/llm_client.py

import json
import time

import requests

# Adjust if "get_ollama" no longer exists:
# from app.settings import get_ollama_host, get_model_name
from app.settings import get_ollama_host, get_model_name_llama

class LlmClient:
    def __init__(self):
        # Use the functions that actually exist:
        self.endpoint = get_ollama_host()  # e.g. "http://localhost:11411"
        self.model_name = get_model_name_llama()
        self.system_prompt = "You are Software Engineer Assistant"

    def generate(self, messages):
        system_prompt = self.system_prompt
        prompt_parts = []
        start = time.time()
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                # If you want to override the system prompt, capture it
                system_prompt = content
            else:
                prompt_parts.append(f"{role.title()}: {content}")

        # Join them into a single text prompt for Ollama
        prompt_str = "\n".join(prompt_parts)

        payload = {
            "model": self.model_name,
            "format":  {
            "type": "object",
                "properties": {
                    "thoughts": {
                    "type": "string"
                },
                "response": {
                    "type": "string"
                }
            },
                "required": [
                    "thoughts",
                    "response"
                ]
            },
            "system": system_prompt,
            "prompt": prompt_str,
            "stream": False,
            "options": {
                    "temperature": 0.2,
                    "top_p": 0.3
                }
            }

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            self.endpoint + "/api/generate",
            data=json.dumps(payload),
            headers=headers,
        )
        print(f"LLM call executed in {(time.time() - start)} s")


        if response.status_code == 200:
            data = json.loads(response.json().get("response", ""))
            print(f"LLM response: {data}")
            #if len(data.get("thoughts", "")) < 30:
            #    print(messages)
            return {
                "thoughts": data.get("thoughts", ""),
                "response": data.get("response", "")
            }
        else:
            return {
                "error": f"Failed to get response: {response.status_code}",
                "details": response.text
            }

    def generate_single(self, prompt_text: str):
        """
        Helper method for the single-string (non-chat) usage.
        Wraps the user prompt string into a list of messages for `generate_chat`.
        """
        messages = [
            {"role": "system", "content": "You are Software Engineer."},
            {"role": "user", "content": prompt_text}
        ]
        return self.generate(messages)