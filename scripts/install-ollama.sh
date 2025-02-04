#!/usr/bin/env bash

set -e  # Exit immediately on error

echo "===== Checking for Homebrew installation ====="
if ! command -v brew &> /dev/null; then
  echo "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "Homebrew is already installed."
fi

echo
echo "===== Configuring Homebrew in your shell ====="
# Determine CPU architecture (Apple Silicon or Intel)
arch_name="$(uname -m)"

if [ "$arch_name" = "arm64" ]; then
  # Apple Silicon (M1, M2, etc.)
  if [ -x "/opt/homebrew/bin/brew" ]; then
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
else
  # Intel
  if [ -x "/usr/local/bin/brew" ]; then
    echo 'eval "$(/usr/local/bin/brew shellenv)"' >> "$HOME/.zprofile"
    eval "$(/usr/local/bin/brew shellenv)"
  fi
fi

echo
echo "===== Updating Homebrew ====="
brew update

echo
echo "===== Tapping Ollama repository ====="
brew tap ollama/tap || true

echo
echo "===== Installing Ollama ====="
brew install ollama/tap/ollama

echo
echo "===== Installation complete! ====="
echo "Open a new terminal OR run the following command in this shell to refresh your environment:"
if [ "${arch_name}" = "arm64" ]; then
  echo '    eval "$(/opt/homebrew/bin/brew shellenv)"'
else
  echo '    eval "$(/usr/local/bin/brew shellenv)"'
fi
echo
echo "You can now use Ollama by running:  ollama"