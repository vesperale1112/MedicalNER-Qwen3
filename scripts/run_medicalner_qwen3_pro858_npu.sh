#!/bin/bash
set -euo pipefail

cd /aistor/sjtu/hpc_stor01/home/wangxiran/projects/MedicalNER-Qwen3

LLAMAFACTORY_HOME=/aistor/sjtu/hpc_stor01/home/wangxiran/LLaMA-Factory

export PYTHONNOUSERSITE=1
export PYTHONPATH="$LLAMAFACTORY_HOME/src:${PYTHONPATH:-}"
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/aistor/sjtu/hpc_stor01/home/wangxiran/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=$HF_HOME/hub
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TRANSFORMERS_CACHE=$HF_HOME/hub

mkdir -p "$HF_HOME" "$HUGGINGFACE_HUB_CACHE" "$HF_DATASETS_CACHE" models/adapters

echo "===== Runtime Info ====="
hostname
date
which python

python - <<'PY'
import torch
import torch_npu
print("torch:", torch.__version__)
print("torch_npu:", getattr(torch_npu, "__version__", "unknown"))
print("npu available:", torch.npu.is_available() if hasattr(torch, "npu") else False)
print("npu count:", torch.npu.device_count() if hasattr(torch, "npu") else 0)

import llamafactory
print("llamafactory location:", llamafactory.__file__)
PY

npu-smi info || true

echo "===== Training YAML ====="
sed -n '1,60p' configs/llamafactory/qwen3_8b_lora_cot_pro858_npu.yaml

echo "===== Start training ====="
python -m llamafactory.cli train configs/llamafactory/qwen3_8b_lora_cot_pro858_npu.yaml

echo "===== Training finished ====="
date
