#!/usr/bin/env bash
# 在 NPU 容器内部运行的训练入口（被 scripts/submit_medicalner_qwen3_pro858_npu.sh
# 提交的 vc 任务调用，也可在调试机的容器里直接 bash 这一行手动跑）。
#
# 期望已经在镜像 hub.szaic.com/sjtu/sjtu_wumengyue-medicalner-qwen3:* 内，
# 共享存储已自动挂载，项目根目录在 /aistor/sjtu/hpc_stor01/home/wangxiran/projects/MedicalNER-Qwen3。
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/aistor/sjtu/hpc_stor01/home/wangxiran/projects/MedicalNER-Qwen3}"
CONFIG_YAML="${CONFIG_YAML:-configs/llamafactory/qwen3_8b_lora_cot_pro858_npu.yaml}"
DATASET_JSON="${DATASET_JSON:-data/llamafactory/pro_cot_001_858_complete_llamafactory.json}"

cd "${PROJECT_DIR}"

# 缓存路径放共享存储，别落到容器临时目录
KG_CACHE_ROOT="${KG_CACHE_ROOT:-${PROJECT_DIR}/.cache}"
export HF_HOME="${HF_HOME:-${KG_CACHE_ROOT}/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HOME}/hub}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-${HF_HOME}/datasets}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${KG_CACHE_ROOT}}"
# 不要把 TMPDIR 放共享存储：multiprocessing 清理 pymp-* 时会撞共享 FS 的
# .__dpc* 影子文件，Device or resource busy / Directory not empty。
export TMPDIR="${TMPDIR:-/tmp}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${KG_CACHE_ROOT}/matplotlib}"
mkdir -p "${HF_HOME}" "${TRANSFORMERS_CACHE}" "${HF_DATASETS_CACHE}" \
         "${MPLCONFIGDIR}" models/adapters
mkdir -p "${TMPDIR}" 2>/dev/null || true

export PYTHONNOUSERSITE=1
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
# 单卡训练时 LLaMA-Factory 直接走单进程；多卡时设 FORCE_TORCHRUN=1 由其自动 torchrun
export FORCE_TORCHRUN="${FORCE_TORCHRUN:-0}"

echo "===== Runtime Info ====="
hostname
date
echo "PROJECT_DIR : ${PROJECT_DIR}"
echo "CONFIG_YAML : ${CONFIG_YAML}"
echo "DATASET_JSON: ${DATASET_JSON}"
echo "ASCEND_VISIBLE_DEVICES   = ${ASCEND_VISIBLE_DEVICES:-<unset>}"
echo "ASCEND_RT_VISIBLE_DEVICES= ${ASCEND_RT_VISIBLE_DEVICES:-<unset>}"
echo "FORCE_TORCHRUN           = ${FORCE_TORCHRUN}"
which python3
which llamafactory-cli
npu-smi info || true

python3 - <<'PY'
import torch
print("torch:", torch.__version__)
try:
    import torch_npu
    print("torch_npu:", getattr(torch_npu, "__version__", "unknown"))
    print("torch_npu.npu.device_count():", torch_npu.npu.device_count())
except Exception as e:
    print("torch_npu import failed:", e)
if hasattr(torch, "npu"):
    print("torch.npu.is_available():", torch.npu.is_available())
    print("torch.npu.device_count():", torch.npu.device_count())
PY

# Qwen3 模板要求训练数据是 <think> 而不是 Gemini 风格的 <thinking>
if grep -q "<thinking>" "${DATASET_JSON}" || grep -q "</thinking>" "${DATASET_JSON}"; then
    echo "ERROR: ${DATASET_JSON} contains <thinking> tags. Qwen3 training requires <think> tags." >&2
    exit 1
fi

echo "===== Training YAML ====="
sed -n '1,220p' "${CONFIG_YAML}"

echo "===== Start llamafactory-cli train ====="
llamafactory-cli train "${CONFIG_YAML}"

echo "===== Training finished ====="
date
