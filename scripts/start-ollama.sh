#!/usr/bin/env bash
#
# start_llm.sh: Simple script to start Ollama with a given model,
#               ensuring the model is pulled and the default port is free.

set -euo pipefail

MODEL_ID="${1:-krith/qwen2.5-coder-32b-instruct-abliterated:IQ4_XS}"
TIMEOUT="${2:-60}"
PORT=11434

echo "Model ID: ${MODEL_ID}"
echo "Timeout (seconds): ${TIMEOUT}"

#######################################
# 1) Check if model is installed; if not, pull it
#######################################
echo "Checking if model '${MODEL_ID}' is already installed..."
if ! ollama show "${MODEL_ID}" &>/dev/null; then
  echo "Model '${MODEL_ID}' not found locally. Pulling..."
  ollama pull "${MODEL_ID}"
  echo "Model '${MODEL_ID}' successfully pulled."
else
  echo "Model '${MODEL_ID}' is already installed."
fi

#######################################
# 2) Check if port is busy; if yes, kill processes
#######################################
echo "Checking if port ${PORT} is free..."
PIDS=$(lsof -t -i :"${PORT}" -sTCP:LISTEN 2>/dev/null || true)
if [[ -n "${PIDS}" ]]; then
  echo "Port ${PORT} is in use by PID(s): ${PIDS}"
  echo "Killing process(es) on port ${PORT}..."
  for pid in ${PIDS}; do
    kill -9 "${pid}"
  done
  echo "Freed port ${PORT}."
else
  echo "Port ${PORT} is free."
fi

#######################################
# 3) Start Ollama server
#######################################
echo "Starting Ollama server with model '${MODEL_ID}'..."
ollama serve
OLLAMA_PID=$!

echo "Ollama started (PID: ${OLLAMA_PID}). Waiting for readiness..."
START_TIME=$(date +%s)

#######################################
# 4) Wait until server is ready or times out
#######################################
while true; do
  # Quick attempt to hit the /generate endpoint
  if curl -s -X POST "http://localhost:${PORT}/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": \"ping\", \"model\": \"${MODEL_ID}\"}" \
        >/dev/null; then
    echo "LLM server is up and running!"
    break
  fi

  CURRENT_TIME=$(date +%s)
  if ((CURRENT_TIME - START_TIME >= TIMEOUT)); then
    echo "Timeout waiting for LLM to start."
    kill -9 "${OLLAMA_PID}"
    exit 1
  fi

  sleep 2
done

echo "Ready to use LLM. (PID: ${OLLAMA_PID})"