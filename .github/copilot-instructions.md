# Aquarius Custom Copilot Instructions

This file provides custom instructions for GitHub Copilot in the Aquarius project. These guidelines will be included in every chat request.

- Project context: Python 3.11, Poetry, Flask REST API, Gradio UI, LangGraph-based agent, local Ollama inference.
- Use Pythonic idioms (PEP 8/PEP 484), type hints for all public functions and methods.
- Manage dependencies with Poetry: if adding a package, update `pyproject.toml` and run `poetry install`.
- Follow existing folder structure:
  - `app/` for server, UI, and config modules.
  - `agent/` for conversation logic, prompts, and search/code tools.
  - `inference/` for Docker setups, notebooks, and monitoring configs.
  - `tests/` for unit tests mirroring source structure.
- For Gradio UI (`ui.py`): use existing component patterns and callbacks; keep interfaces minimal and well-documented.
- For Flask routes (`server/routes.py`): use `@app.route`, consistent JSON schemas, and proper error handling.
- Always include concise docstrings for new modules, functions, and classes.
- Write unit tests alongside any new logic; follow pytest conventions and naming.
- Maintain import ordering: standard library, third-party, local modules.
- When suggesting config snippets for `config.yaml`, include placeholders and comments describing each key.
- Avoid adding placeholder or non-meaningful comments to the code. Focus on comments that explain complex logic or decisions.
