#!/bin/bash
set -euo pipefail

cd /hpc_stor03/sjtu_home/xiran.wang/MedicalNER-Qwen3

export PYTHONNOUSERSITE=1
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/hpc_stor03/sjtu_home/xiran.wang/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=$HF_HOME/hub
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TRANSFORMERS_CACHE=$HF_HOME/hub
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "===== Runtime Info ====="
hostname
date
which python
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("cuda version:", torch.version.cuda)
print("gpu count:", torch.cuda.device_count())
PY
which llamafactory-cli
nvidia-smi || true

echo "===== Training YAML ====="
sed -n '1,220p' configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml

echo "===== Start training via scripts/03_train_lora.sh ====="
bash scripts/03_train_lora.sh pro858

echo "===== Training finished ====="
date
