#!/bin/bash
set -euo pipefail

cd /hpc_stor03/sjtu_home/xiran.wang/MedicalNER-Qwen3

export PYTHONNOUSERSITE=1
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/hpc_stor03/sjtu_home/xiran.wang/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=$HF_HOME/hub
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

echo "===== Model files ====="
ls -lh /hpc_stor03/sjtu_home/xiran.wang/models/Qwen3-8B | head -n 30

echo "===== YAML ====="
sed -n '1,220p' configs/llamafactory/qwen3_8b_lora_cot_pro858_smoke_1step.yaml

echo "===== Start smoke training ====="
CUDA_VISIBLE_DEVICES=0 llamafactory-cli train \
  configs/llamafactory/qwen3_8b_lora_cot_pro858_smoke_1step.yaml

echo "===== Smoke training finished ====="
date
