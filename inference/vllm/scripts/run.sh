#!/usr/bin/env bash
set -e

exec opentelemetry-instrument \
  --metrics_exporter prometheus \
  --service_name "${OTEL_SERVICE_NAME:-vllm-api}" \
  vllm serve deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B \
        --host 0.0.0.0 \
        --port 8000 \
        --trust-remote-code \
        --dtype bfloat16 \
        --quantization bitsandbytes
