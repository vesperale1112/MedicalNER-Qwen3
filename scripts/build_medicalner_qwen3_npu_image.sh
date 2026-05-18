#!/usr/bin/env bash
# 在 SZAIC 调试机（szaic-hpc-debug-0003）上构建 MedicalNER-Qwen3 NPU 镜像。
#
# 做的事：
#   1. 从公共共享存储拷昇腾 FlashAttention patch 到 docker/ 构建上下文
#   2. docker build
#   3. 如果传了 --push，docker push 到 hub.szaic.com 内部仓库
#
# 用法：
#   bash scripts/build_medicalner_qwen3_npu_image.sh              # 只构建本地镜像
#   bash scripts/build_medicalner_qwen3_npu_image.sh --push       # 构建并推送
#   IMAGE_TAG=v1.1 bash scripts/build_medicalner_qwen3_npu_image.sh --push
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

TEAM="${TEAM:-wumengyue}"
IMAGE_NAME="${IMAGE_NAME:-xiranwang-medicalner-qwen3}"
IMAGE_TAG="${IMAGE_TAG:-v1.0}"
IMAGE_FULL="hub.szaic.com/sjtu/sjtu_${TEAM}-${IMAGE_NAME}:${IMAGE_TAG}"

FA_PATCH_SRC="${FA_PATCH_SRC:-/aistor/sjtu/hpc_stor01/public/ascend_patch/npu_flash_attn.py}"
FA_PATCH_DST="${ROOT_DIR}/docker/npu_flash_attn.py"

PUSH=0
for arg in "$@"; do
    case "${arg}" in
        --push) PUSH=1 ;;
        -h|--help)
            sed -n '2,18p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
        *)
            echo "unknown arg: ${arg}" >&2
            exit 1
            ;;
    esac
done

echo "===== Build context ====="
echo "ROOT_DIR    : ${ROOT_DIR}"
echo "IMAGE_FULL  : ${IMAGE_FULL}"
echo "FA_PATCH_SRC: ${FA_PATCH_SRC}"
echo "FA_PATCH_DST: ${FA_PATCH_DST}"
echo "PUSH        : ${PUSH}"
echo

if [[ ! -f "${FA_PATCH_SRC}" ]]; then
    echo "ERROR: FA patch not found at ${FA_PATCH_SRC}" >&2
    echo "       本机不是 SZAIC 调试机，或共享存储未挂载。" >&2
    echo "       手动把文件拷到 ${FA_PATCH_DST} 后再次运行。" >&2
    exit 1
fi
cp "${FA_PATCH_SRC}" "${FA_PATCH_DST}"
echo "copied FA patch -> ${FA_PATCH_DST}"

echo "===== docker build ====="
docker build \
    -t "${IMAGE_FULL}" \
    -f "${ROOT_DIR}/docker/Dockerfile" \
    "${ROOT_DIR}/docker"

echo
echo "===== docker images ====="
docker images | head -n 1
docker images | grep "sjtu_${TEAM}-${IMAGE_NAME}" || true

if [[ "${PUSH}" -eq 1 ]]; then
    echo
    echo "===== docker push ====="
    docker push "${IMAGE_FULL}"
fi

echo
echo "done. image = ${IMAGE_FULL}"
