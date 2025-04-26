# Aquarius

Aquarius is an intelligent code assistant that combines a chat interface with local LLM inference to help you explore, document, and interact with Python code repositories. It provides flexible search and code execution tools.

---

## Features

- **Agent-Based Architecture**  
  Utilizes a LangGraph state machine to manage conversation flow.

- **Intent Routing**  
  Classifies user queries into `search`, `code`, or `chit_chat` and routes them accordingly.

- **Integrated Tools**  
  Provides built-in tools:
  - `redditSearcher` for Reddit queries
  - `googleSearcher` for Google Custom Search
  - `arxivSearch` for academic papers
  - `githubSearchEnrich` for GitHub repository insights
  - `executePython` for sandboxed Python code execution

- **Memory & Context**  
  Employs a MemorySaver checkpointer to maintain conversational history and state.

- **Flask API & Gradio UI**  
  Enables chat via a RESTful `/chat` endpoint and an interactive Gradio interface.
  In this repo I include [LLM inference docker container](inference/README.md) with vLLM, prometheus and grafana.

---

## Project Structure

```
aquarius/
├── app/
│   ├── agent/                # Agent logic, tools and nodes
│   ├── server/               # Flask routes and file processor
│   ├── ui.py                 # Gradio chat UI integration
│   └── config_manager.py     # YAML configuration loader
├── main.py                   # Entry point (API + UI)
├── pyproject.toml            # Poetry project file
├── config.yaml               # LLM and API keys configuration
└── README.md
```

---

## Requirements

- Python **3.11**
- [Poetry](https://python-poetry.org/) for dependency management
- A running Ollama LLM instance (configured in `config.yaml`)
- API credentials for search tools (Google, GitHub, Reddit) if you plan to use external searches

---

## Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ivan-digital/aquarius.git
   cd aquarius
   ```
2. **Install dependencies**
   ```bash
   poetry install
   ```
3. **Configure**  
   Create `config.yaml` and fill in your:
   - `model_name` &rarr; Ollama model ID
   - `google_key`, `google_cx` &rarr; Google Custom Search credentials
   - `github_token` &rarr; GitHub API token
   - `reddit_secret` &rarr; Reddit API client secret
   - Optional: `browser` for Selenium WebDriver

---

## Running the Application

Start both the API and UI together:

```bash
poetry run python main.py
```

- **Flask API** on `http://127.0.0.1:5000`
- **Gradio UI** served at `0.0.0.0:7860` (default)


---

## Contributing

Contributions are welcome! Please fork the repo and submit pull requests for enhancements or bug fixes.

---

## License

This project is licensed under the [MIT License](LICENSE).

