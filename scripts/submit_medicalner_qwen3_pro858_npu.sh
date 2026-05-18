#!/usr/bin/env bash
# 在 SZAIC 调试机上把 pro858 训练任务提交到 NPU 队列 pdgpu-sjtu-ai。
#
# 默认 1 NPU（NPU:CPU:MEM = 1:20:120），按 SZAIC 规范资源配比申请。
# 想加大资源就传环境变量：
#   NPU=4 CPU=80 MEM=480G bash scripts/submit_medicalner_qwen3_pro858_npu.sh
#   NPU=8 CPU=160 MEM=960G bash scripts/submit_medicalner_qwen3_pro858_npu.sh
#
# 镜像必须先 docker push 到内部仓库（计算节点拉不到调试机本地镜像）：
#   bash scripts/build_medicalner_qwen3_npu_image.sh --push
set -euo pipefail

TEAM="${TEAM:-wumengyue}"
USERNAME="${USERNAME:-wangxiran}"
QUEUE="${QUEUE:-pdgpu-sjtu-ai}"
IMAGE_NAME="${IMAGE_NAME:-medicalner-qwen3}"
IMAGE_TAG="${IMAGE_TAG:-v1.0}"
IMAGE_FULL="${IMAGE_FULL:-hub.szaic.com/sjtu/sjtu_${TEAM}-${IMAGE_NAME}:${IMAGE_TAG}}"

NPU="${NPU:-1}"
CPU="${CPU:-20}"
MEM="${MEM:-120G}"

PROJECT_DIR="${PROJECT_DIR:-/aistor/sjtu/hpc_stor01/home/${USERNAME}/projects/MedicalNER-Qwen3}"
RUN_SCRIPT="${RUN_SCRIPT:-${PROJECT_DIR}/scripts/run_medicalner_qwen3_pro858_npu.sh}"
LOG_DIR="${LOG_DIR:-${PROJECT_DIR}/logs}"
LOG_PATH="${LOG_PATH:-${LOG_DIR}/pro858_npu.JOB.log}"

mkdir -p "${LOG_DIR}"

if [[ ! -f "${RUN_SCRIPT}" ]]; then
    echo "ERROR: run script not found: ${RUN_SCRIPT}" >&2
    echo "       共享存储里的项目目录是不是 ${PROJECT_DIR}？" >&2
    exit 1
fi

# slurm.pl 风格要求日志路径里包含 JOB
if [[ "${LOG_PATH}" != *JOB* ]]; then
    echo "ERROR: LOG_PATH 必须包含字符串 JOB，当前是 ${LOG_PATH}" >&2
    exit 1
fi

echo "===== Submit summary ====="
echo "QUEUE     : ${QUEUE}"
echo "IMAGE     : ${IMAGE_FULL}"
echo "NPU:CPU:M : ${NPU} : ${CPU} : ${MEM}"
echo "PROJECT   : ${PROJECT_DIR}"
echo "RUN       : ${RUN_SCRIPT}"
echo "LOG       : ${LOG_PATH}"
echo

# 多 NPU 时让 LLaMA-Factory 走 torchrun（同一 task 内多进程）
FORCE_TORCHRUN=0
if (( NPU > 1 )); then
    FORCE_TORCHRUN=1
fi

set -x
vc submit \
    -p "${QUEUE}" \
    -i "${IMAGE_FULL}" \
    -g "${NPU}" \
    -c "${CPU}" \
    -m "${MEM}" \
    -e "PROJECT_DIR=${PROJECT_DIR}" \
    -e "HF_ENDPOINT=https://hf-mirror.com" \
    -e "PYTHONNOUSERSITE=1" \
    -e "FORCE_TORCHRUN=${FORCE_TORCHRUN}" \
    JOB=1:1 "${LOG_PATH}" \
    --cmd "bash ${RUN_SCRIPT}"
set +x

cat <<EOF

提交完成。查看状态和日志：
  vc list
  vc list -j <JOBID>
  tail -f ${LOG_PATH/JOB/1}
EOF
