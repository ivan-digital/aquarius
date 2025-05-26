# Aquarius

Aquarius is a GitHub-focused AI assistant using a LangGraph ReAct agent, Ollama LLM backend, and Gradio interface for natural language GitHub repository exploration.

## Quickstart

### 1. Environment Setup

To install all required dependencies (chromedriver, Poetry, Ollama, and models), run:

```sh
./setup_env.sh
```

This script will:

- Install Homebrew (if missing)
- Install chromedriver (for Selenium tests)
- Install Poetry (for Python dependency management)
- Install all Python dependencies
- Install Ollama (for LLM backend)
- Download required Ollama models (`qwen3:8b`, `qwen3:32b`)

See `docs/requirements.md` for more details.

### 2. Running the Application

To start the main application locally:

```sh
poetry run python app/main.py
```

Or with Docker:

```sh
docker-compose -f docker-compose.app.yml up --build
```

### 3. Running Tests

The project uses unit tests with mocking to ensure code quality while maintaining fast test execution.

#### Running Unit Tests

```sh
# Run all unit tests (default)
poetry run pytest

# Run specific test files or patterns
poetry run pytest tests/unit/agent/test_facade.py
poetry run pytest "tests/unit/**/test_*.py"

# Run with verbose output
poetry run pytest -v

# See all available options
poetry run pytest --help
```

This will run all the unit tests in the project. The tests are organized to mirror the project structure under `tests/unit/`.

All tests use mocks instead of actual external services, making them:
- Fast and reliable
- Independent of external services
- Suitable for CI/CD pipelines

See `pytest.ini` for configuration details.

---

For more information, see the `docs/` directory.
