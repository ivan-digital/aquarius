#!/usr/bin/env bash

set -e

python -m vllm.entrypoints.api_server \
  --model deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B \
  --host 0.0.0.0 \
  --port 8000 \
  --trust-remote-code \
  --dtype bfloat16 \
  --quantization bitsandbytes
