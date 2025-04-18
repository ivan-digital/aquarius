rem docker build -t vllm-bnb .
rem docker run --gpus all -it -p 8000:8000 vllm-bnb

docker run --gpus all -it  -v "C:/Users/Administrator/PycharmProjects/aquarius/inference/vllm/scripts:/workspace/scripts"  -p 8000:8000  vllm-bnb /workspace/scripts/run.sh