# Aquarius Requirements

## System Overview

Aquarius is a simplified GitHub-focused AI assistant that provides natural language interface for GitHub repository exploration and analysis.

## Core Components

### 1. LangGraph Agent Architecture
- **Framework**: Built using LangGraph's `create_react_agent` for straightforward ReAct (Reasoning and Acting) pattern
- **Agent Type**: Simple ReAct agent without complex intent routing or multiple node types
- **State Management**: Uses LangGraph's built-in `MemorySaver` for conversation history
- **Tools Integration**: GitHub MCP (Model Context Protocol) tools via Docker container

### 2. LLM Backend
- **Engine**: Ollama locally running models
- **Primary Model**: `qwen3:32b` for main operations
- **Test Model**: `qwen3:8b` for testing scenarios
- **Configuration**: Configurable via `keys.yaml` and `config.yaml`

### 3. User Interface
- **Framework**: Gradio web interface
- **Type**: Natural language chat interface
- **Accessibility**: Web-based, accessible via browser
- **Features**: Real-time conversation with the GitHub assistant

### 4. GitHub Integration
- **Method**: GitHub MCP Server via Docker (`ghcr.io/github/github-mcp-server`)
- **Authentication**: GitHub Personal Access Token
- **Tools**: Repository exploration, file content retrieval, structure analysis
- **Capabilities**: Read-only access to public and private repositories (based on token permissions)

## Primary Use Cases

### Repository Analysis
- **Summary Generation**: Provide comprehensive summaries of GitHub repositories
- **Recent Updates**: Analyze and summarize recent commits, pull requests, and releases
- **Code Exploration**: Navigate repository structure and examine file contents
- **Documentation Review**: Extract and summarize README files and documentation

### Natural Language Queries
Users can ask questions in natural language such as:
- "Give me a summary of the recent changes in [owner/repo]"
- "What are the main features of [repository]?"
- "Show me the structure of [repository]"
- "What's new in the latest release of [repository]?"
- "Explain what this repository does"

## Technical Requirements

### Dependencies
- Python 3.11+
- Poetry for dependency management
- Docker for GitHub MCP server
- Ollama for local LLM inference
- GitHub Personal Access Token

### Key Libraries
- `langchain-core`: Core LangChain functionality
- `langgraph`: Graph-based agent execution
- `langchain-mcp-adapters`: MCP integration
- `langchain-ollama`: Ollama LLM integration
- `gradio`: Web interface
- `flask`: API server (optional)

### Configuration
- `keys.yaml`: API keys and tokens
- `config.yaml`: Model and system configuration
- Environment variables for containerized deployment

## Architecture Principles

### Simplicity
- Single ReAct agent instead of complex routing
- Direct GitHub MCP integration
- Minimal configuration requirements

### Focus
- GitHub-specific functionality only
- Repository exploration and analysis
- Natural language interaction

### Scalability
- Docker-based MCP server deployment
- Configurable model backends
- Stateless agent design with persistent memory

## Output Format

The assistant provides responses in natural language with:
- **Bullet points** for structured information
- **Summaries** for repository overviews
- **Clear explanations** for technical content
- **Contextual information** about repositories and changes

## Testing Strategy

### Overall Approach
- **Mock-Based Unit Tests**: Core components tested with mocks to avoid external dependencies
- **LLM-Judged E2E Tests**: Two key integration tests (API & UI) with qwen3:8b as a response judge
- **Test Categories**: Facade, Graph, API, UI Integration, LLM Response Quality
- **Test Running**: Simplified with standard `pytest` commands via Poetry

### Unit Testing
- **Agent Facade Tests**: Validate initialization, GitHub query handling, timeouts, resource cleanup
- **Graph Tests**: Ensure correct ReAct agent creation with GitHub tools and system prompt
- **API Route Tests**: Verify API endpoints handle requests correctly with appropriate error responses
- **All unit tests use mocks** to avoid external dependencies and ensure fast, reliable execution

### Integration Testing
- **Two E2E tests with LLM judgment**:
  1. **API Integration**: Validates complete HTTP API responses for GitHub queries
  2. **UI Integration**: Validates Selenium-driven UI interaction with GitHub queries
- **LLM Judge**: Uses lightweight qwen3:8b model to evaluate response quality against specific criteria
- **Response Quality Criteria**: 
  - GitHub-focused content
  - Repository-specific information
  - Well-structured information
  - Appropriate level of detail

### Test Prerequisites
- Local Ollama instance running qwen3:8b model
- Valid GitHub token (for E2E tests only)
- Docker for GitHub MCP container (E2E tests only)
- Integration tests are skipped if prerequisites are not available

## Aquarius Test & Development Environment Setup

To ensure all integration tests and the application run reliably, follow these steps to set up your environment:

### 1. Automated Setup Script

Run the provided setup script to install all required dependencies (chromedriver, Poetry, Ollama, and models):

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

### 2. Manual Steps (if needed)

If you encounter issues, ensure the following are installed and available in your PATH:

- chromedriver
- poetry
- ollama

### 3. Running Tests

After setup, run all tests with:

```sh
poetry run pytest
```

### 4. Additional Notes

- Ensure `keys.yaml` contains a valid `github_token` for E2E tests.
- The Gradio UI and backend must be running for integration tests to pass.
- For Docker-based runs, see `docker-compose.app.yml`.

---

For more details, see `setup_env.sh` in the project root.

## Limitations

- Read-only GitHub access (no modifications)
- Dependent on GitHub token permissions
- Local Ollama model requirements
- Internet connectivity for GitHub API access
