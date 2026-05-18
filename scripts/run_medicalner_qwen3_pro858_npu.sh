#!/bin/bash
set -euo pipefail

cd /aistor/sjtu/hpc_stor01/home/wangxiran/MedicalNER-Qwen3

export PYTHONNOUSERSITE=1
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
PY

which llamafactory-cli
npu-smi info || true

# --- Optional: Apply NPU FlashAttention patch ---
NPU_FA_PATCH=/aistor/sjtu/hpc_stor01/public/ascend_patch/npu_flash_attn.py
LLAMAFACTORY_SRC=/opt/LLaMA-Factory

if [[ -f "$NPU_FA_PATCH" ]]; then
    echo "===== Applying NPU FlashAttention patch ====="
    TARGET_DIR="$LLAMAFACTORY_SRC/src/llamafactory/model/model_utils"
    if [[ -d "$TARGET_DIR" ]]; then
        cp "$NPU_FA_PATCH" "$TARGET_DIR/npu_flash_attn.py"

        LOADER="$LLAMAFACTORY_SRC/src/llamafactory/model/loader.py"
        if [[ -f "$LOADER" ]] && ! grep -q "npu_flash_attn" "$LOADER"; then
            sed -i '/^from \.model_utils\./a from .model_utils.npu_flash_attn import patch_npu_flash_attn' "$LOADER"
            sed -i 's/\(patch_config(.*)\)/\1\n    patch_npu_flash_attn()/' "$LOADER"
            echo "NPU FA patch applied"
        else
            echo "NPU FA patch already present or loader.py not found"
        fi
    fi
else
    echo "INFO: NPU FA patch not found at $NPU_FA_PATCH, using default SDPA"
fi

echo "===== Training YAML ====="
sed -n '1,60p' configs/llamafactory/qwen3_8b_lora_cot_pro858_npu.yaml

echo "===== Start training ====="
llamafactory-cli train configs/llamafactory/qwen3_8b_lora_cot_pro858_npu.yaml

echo "===== Training finished ====="
date
