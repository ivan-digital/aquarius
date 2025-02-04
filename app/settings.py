# app/settings.py
import os

TOKEN_FILE = "my_token.txt"


def get_github_token():
    """
    Get the stored GitHub token from a file or environment variable, etc.
    """
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def get_model_name_llama():
    # return "krith/qwen2.5-coder-32b-instruct-abliterated:IQ4_XS"
    return "deepseek-r1:70b"


def get_ollama_port():
    return 11434


def get_ollama_host():
    return f"http://localhost:{get_ollama_port()}"
