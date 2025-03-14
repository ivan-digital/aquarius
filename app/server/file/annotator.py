import json
import time

from ollama import Client

class LLMCodeAnnotator:
    """
    Processes code files by reading their entire content and sending it
    to an LLM for summarization & classification using an Ollama-based LLMService.
    """

    RESPONSE_SCHEME = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "classification": {"type": "string"}
        },
        "required": ["summary", "classification"]
    }

    PROMPT_TEMPLATE = (
        "You are an AI that analyzes code.\n"
        "Given the following class definition, provide:\n"
        "1) A short summary in your own words (the 'essence' and functionality).\n"
        "2) A classification from the set: ['build_system', 'configuration_files', 'scripts', 'code', 'other'].\n\n"
        "Class definition:\n"
        "{}\n\n"
        "Return JSON following this response scheme:\n"
        "{}"
    )

    def __init__(self, llm_service):
        """
        :param llm_service: An instance of LLMService configured with the Ollama client.
        """
        self.llm_service = llm_service

    def process_files(self, file_path):
        start = time.time()
        try:
            with open(file_path, 'r') as f:
                file_content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

        prompt = self.PROMPT_TEMPLATE.format(file_content, self.RESPONSE_SCHEME)

        llm_response = self.llm_service.completion(prompt)
        return {
                "file": file_path,
                "code": file_content,
                "summary": llm_response.get("summary", ""),
                "classification": llm_response.get("classification", "other"),
                "executed_s": (time.time() - start)
            }