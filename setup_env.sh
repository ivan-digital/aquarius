#!/bin/zsh
# Aquarius Environment Setup Script
# Installs all dependencies for integration tests and local development
# Usage: source ./setup_env.sh OR ./setup_env.sh

set -e

# 1. Install Homebrew if not present
if ! command -v brew &>/dev/null; then
  echo "Homebrew not found. Installing..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

echo "[1/6] Homebrew is installed."

# 2. Install chromedriver
if ! command -v chromedriver &>/dev/null; then
  echo "Installing chromedriver..."
  brew install chromedriver
else
  echo "chromedriver already installed."
fi

# Remove quarantine attribute to avoid trust prompt on macOS
if [[ "$(uname)" == "Darwin" ]]; then
  chromedriver_path="$(which chromedriver)"
  if [[ -n "$chromedriver_path" ]]; then
    echo "Removing quarantine attribute from chromedriver..."
    xattr -d com.apple.quarantine "$chromedriver_path" || true
  fi
fi

# 3. Install Poetry
if ! command -v poetry &>/dev/null; then
  echo "Installing Poetry..."
  brew install poetry
else
  echo "Poetry already installed."
fi

# 4. Install Python dependencies
poetry install

echo "[4/6] Python dependencies installed."

# 5. Install Ollama (if not present)
if ! command -v ollama &>/dev/null; then
  echo "Installing Ollama..."
  brew install ollama
else
  echo "Ollama already installed."
fi

echo "[5/6] Ollama is installed."

# 6. Pull required Ollama models
ollama pull qwen3:8b || true
ollama pull qwen3:32b || true

echo "[6/6] Ollama models pulled."

echo "Aquarius environment setup complete!"
