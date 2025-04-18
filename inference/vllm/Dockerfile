# vllm image for rtx5090 sm_120 Blackwell architecture
FROM nvcr.io/nvidia/pytorch:25.03-py3

ENV MAX_JOBS=16
ENV NVCC_THREADS=4
ENV FLASHINFER_ENABLE_AOT=0
ENV USE_CUDA=1
ENV CUDA_HOME=/usr/local/cuda
ENV TORCH_CUDA_ARCH_LIST='12.0+PTX'
ENV CCACHE_DIR=/root/.ccache

RUN apt-get update && apt-get install -y --no-install-recommends \
    kmod \
    git \
    cmake \
    ccache \
    python3-pip \
    python3-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip
RUN pip3 install bitsandbytes
RUN git clone --recursive https://github.com/flashinfer-ai/flashinfer.git /workspace/flashinfer
WORKDIR /workspace/flashinfer
RUN pip3 install -e . -v

RUN git clone https://github.com/vllm-project/vllm.git /workspace/vllm
WORKDIR /workspace/vllm
RUN python3 use_existing_torch.py

RUN pip3 install --no-cache-dir -r requirements/build.txt
RUN pip3 install --no-cache-dir setuptools_scm
RUN python3 setup.py develop

RUN pip3 install --no-cache-dir \
    transformers \
    accelerate \
    huggingface_hub

COPY scripts/run.sh /workspace/run.sh
EXPOSE 8000
CMD ["python3", "/workspace/run.sh"]