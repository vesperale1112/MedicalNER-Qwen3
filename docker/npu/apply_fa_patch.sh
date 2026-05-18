#!/bin/bash
set -euo pipefail

NPU_FA_PATCH=/aistor/sjtu/hpc_stor01/public/ascend_patch/npu_flash_attn.py
LLAMAFACTORY_SRC=/opt/LLaMA-Factory

if [[ ! -f "$NPU_FA_PATCH" ]]; then
    echo "ERROR: NPU FA patch not found at $NPU_FA_PATCH"
    exit 1
fi

cp "$NPU_FA_PATCH" "$LLAMAFACTORY_SRC/src/llamafactory/model/model_utils/npu_flash_attn.py"

LOADER="$LLAMAFACTORY_SRC/src/llamafactory/model/loader.py"
if ! grep -q "npu_flash_attn" "$LOADER"; then
    sed -i '/^from \.model_utils\./a from .model_utils.npu_flash_attn import patch_npu_flash_attn' "$LOADER"
    sed -i '/patch_config(/a\    patch_npu_flash_attn()' "$LOADER"
    echo "NPU FA patch applied successfully"
else
    echo "NPU FA patch already present"
fi
