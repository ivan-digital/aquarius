# vLLM + OpenTelemetry + Prometheus
FROM nvcr.io/nvidia/pytorch:25.03-py3

ENV MAX_JOBS=16 \
    NVCC_THREADS=4 \
    FLASHINFER_ENABLE_AOT=0 \
    USE_CUDA=1 \
    CUDA_HOME=/usr/local/cuda \
    TORCH_CUDA_ARCH_LIST='12.0+PTX' \
    CCACHE_DIR=/root/.ccache \
    # --- OpenTelemetry / Prometheus ---
    OTEL_SERVICE_NAME=vllm-api \
    OTEL_METRICS_EXPORTER=prometheus \
    OTEL_TRACES_EXPORTER=none \
    OTEL_EXPORTER_PROMETHEUS_HOST=0.0.0.0 \
    OTEL_EXPORTER_PROMETHEUS_PORT=9464

RUN apt-get update && apt-get install -y --no-install-recommends \
        kmod git cmake ccache python3-pip python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip
RUN pip3 install bitsandbytes \
    opentelemetry-distro \
    opentelemetry-exporter-prometheus \
    opentelemetry-instrumentation-fastapi \
    opentelemetry-instrumentation-asgi

RUN git clone --recursive https://github.com/flashinfer-ai/flashinfer.git /workspace/flashinfer
WORKDIR /workspace/flashinfer
RUN pip3 install -e . -v

RUN git clone https://github.com/vllm-project/vllm.git /workspace/vllm
WORKDIR /workspace/vllm
RUN python3 use_existing_torch.py
RUN pip3 install --no-cache-dir -r requirements/build.txt
RUN pip3 install --no-cache-dir setuptools_scm
RUN python3 setup.py develop

RUN pip3 install --no-cache-dir transformers accelerate huggingface_hub

COPY scripts/run.sh /workspace/run.sh
EXPOSE 8000 9464
CMD [ "/workspace/run.sh" ]