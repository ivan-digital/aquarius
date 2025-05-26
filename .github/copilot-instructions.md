# Aquarius Custom Copilot Instructions

This file provides custom instructions for GitHub Copilot in the Aquarius project. These guidelines will be included in every chat request.

## 0. Primary Objective
**MAIN GOAL**: Maintain the Aquarius project with high code quality, ensuring all tests run properly with comprehensive test coverage. The GitHub-focused AI assistant should work reliably with simple, straightforward implementations. Tests should never be skipped - they must be implemented correctly and pass reliably. The test suite is critical for project quality assurance.

## 0.1. Performance and Flow Expectations
- **Response Time**: It is acceptable for LLM responses to take around 60 seconds, and the whole agent flow could be even longer as it may contain several individual LLM calls.
- **Simplicity First**: Keep the flow simple without unnecessary bypasses or fallbacks. Prefer straightforward implementations over complex conditional logic.
- **No Complex Error Handling**: Avoid intricate fallback chains or error recovery mechanisms. Simple error messages and clean failures are preferred over complex retry logic.

## 1. Project Overview
- **Project Context**: GitHub-focused AI assistant using LangGraph ReAct agent, Ollama LLM backend, and Gradio interface for natural language GitHub repository exploration.
- **Architecture**: Simplified ReAct agent using LangGraph's `create_react_agent` with GitHub MCP tools integration.
- **Current Status**: All tests passing (32 tests, 4 appropriately skipped when GITHUB_TOKEN not available), simple error handling implemented, no complex fallback mechanisms.
- **System Requirements**: See `docs/requirements.md` for detailed technical specifications and use cases.
- **Ollama Models**:
    - Services typically run with `qwen3:32b`.
    - Tests are typically run against `qwen3:8b`.

## 2. Development Environment
- **Setup & Dependencies**: Use Poetry. To set up the local development environment or update dependencies, modify `pyproject.toml` as needed and run `poetry install`. This installs all dependencies, including development ones.
- **Docker Builds**: Note that `Dockerfile` typically uses `poetry install --no-dev` for production images.

## 3. Coding Standards & Best Practices
- **Pythonic Idioms**: Use Pythonic idioms (PEP 8/PEP 484).
- **Type Hints**: Provide type hints for all public functions and methods.
- **Import Ordering**: Maintain import ordering: standard library, third-party, local modules.
- **Comments**: Strictly avoid adding comments to the code during edits.
- **Class Length**: Limit class definitions to 700 lines; if absolutely necessary, the maximum is 1000 lines.
- **Simplified Architecture**: The project now uses a simple ReAct agent instead of complex intent routing. All interactions are GitHub-focused.

## 3.1. Simplified Agent Architecture
- **Single ReAct Agent**: Uses LangGraph's `create_react_agent` for straightforward GitHub interactions following ReAct (Reasoning and Acting) pattern.
- **GitHub MCP Tools**: Only GitHub MCP tools are integrated via Model Context Protocol servers (`ghcr.io/github/github-mcp-server`).
- **AgentFacade**: Simplified to manage only GitHub MCP client lifecycle and ReAct agent creation.
- **No Complex Routing**: Removed complex intent detection, multiple node types, and conditional routing - all queries go directly to the ReAct agent.
- **Natural Language Interface**: Users interact via Gradio web interface using natural language to explore GitHub repositories, get summaries, and analyze recent changes.
- **Lifecycle Management**: Ensure GitHub MCP client remains active during tool execution to prevent `ClosedResourceError`.

## 4. Project Structure
- **Folder Organization**:
    - `app/`: Core directory for the AI assistant's application logic. This includes:
        - Server components (Flask API)
        - UI components (Gradio)
        - Configuration modules
        - Simplified agent logic in `app/agent/` (facade.py, graph.py)
    - `inference/`: Docker setups, notebooks, and monitoring configs for LLM inference.
    - `tests/`: Unit tests mirroring source structure.
    - `debug/`: Debug scripts and troubleshooting utilities. **ALL debug scripts must be placed in this directory to maintain project organization.** Never place debug scripts in the root directory or any other location.

## 5. Running the Project & Tests
- **Running the Application Locally**: The main application is primarily located within the `app/` directory. To start it locally, navigate to the project root and execute `poetry run python app/main.py`. Ensure all dependencies are installed using `poetry install`.
- **Running the Application with Docker**: The application within `app/` can also be run using Docker. Utilize `docker-compose -f docker-compose.app.yml up --build` from the project root for this. This is useful for testing containerized deployments of the main application.
- **Test Structure & Execution**: Tests are organized in a unit test-only approach for optimal development workflow:
  - **Unit Tests**: Fast tests with mocking - `poetry run pytest`
  - **Test Directory Structure**: Tests mirror the application structure under `tests/unit/` for better organization and maintainability
  - **Mocking Strategy**: All external services and dependencies are mocked to ensure tests are fast, reliable and isolated
- **Test Execution Policy**: Always run tests from the terminal only. VS Code's test integration has been disabled due to reliability issues. Use `poetry run pytest` for all test execution.

## 6. Specific Component Guidelines
- **Gradio UI (`ui.py`)**: Use existing component patterns and callbacks; keep interfaces minimal and well-documented.
- **Flask Routes (`server/routes.py`)**: Use `@app.route`, consistent JSON schemas, and proper error handling.

## 7. Documentation
- **Docstrings**: Always include concise docstrings for new modules, functions, and classes.
- **Unit Tests**: Write unit tests alongside any new logic; follow pytest conventions and naming.
- **External Libraries**: For significant external libraries utilized in the project, create or update Markdown (.md) files in the `docs/` folder. These files should summarize key classes, functions, and usage patterns relevant to their application within this project, sourcing information from official online documentation.

## 8. Troubleshooting & Learning
- **Error Handling**: When encountering errors or working with unfamiliar frameworks/libraries, prioritize searching official documentation and reliable internet resources to understand and resolve issues.
- **Test Failure Analysis Workflow**:
  1. **Import Errors**: Check `poetry install` completion and module paths
  2. **Missing Fixtures**: Verify fixture definitions in `conftest.py` files
  3. **Mock Issues**: Ensure mocks match actual function signatures
  4. **Async Issues**: Verify `@pytest.mark.asyncio` and `await` keywords
  5. **Docker/Testcontainers**: Check service startup and port availability
  6. **Environment Variables**: Verify required env vars are set
  7. **File Paths**: Ensure test files can locate application modules

## 9. Problem Solving Strategy
- Address issues and test failures systematically, one at a time. Verify each fix with a test run before moving to the next problem.
- **Test Fix Protocol**:
  1. Run failing test individually: `poetry run pytest path/to/test.py::test_function -v`
  2. Analyze error type and traceback
  3. Fix root cause (imports, mocks, async, etc.)
  4. Verify fix: `poetry run pytest path/to/test.py::test_function`
  5. Run related tests to check for regressions
  6. Run full suite when all fixes complete