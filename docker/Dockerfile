# MedicalNER-Qwen3 镜像（昇腾 NPU）
#
# 基础镜像已经带好匹配的 CANN / torch / torch_npu / MindSpeed，
# 不要在这里重装 torch、torch_npu 或 CUDA 版的 flash-attn / bitsandbytes。
#
# 构建上下文期望包含 docker/ 目录下的 Dockerfile、requirements-npu.txt、
# apply_npu_fa_patch.sh 以及 npu_flash_attn.py（从
# /aistor/sjtu/hpc_stor01/public/ascend_patch/npu_flash_attn.py 拷过来，
# scripts/build_medicalner_qwen3_npu_image.sh 会自动做这一步）。
FROM hub.szaic.com/sjtu-base/sjtu_base-pytorch-for-ascend:cann8.2rc1-torch2.6.0-py3.10

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONNOUSERSITE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_ENDPOINT=https://hf-mirror.com

RUN sed -i -r 's@(archive|security|ports)\.ubuntu\.com@mirrors.aliyun.com@g' /etc/apt/sources.list 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
         git vim wget curl ca-certificates sudo tmux screen jq less \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --upgrade pip setuptools wheel

# Python 依赖（不要在这里写 torch / torch_npu / bitsandbytes / flash-attn）
COPY requirements-npu.txt /tmp/requirements-npu.txt
RUN pip install -r /tmp/requirements-npu.txt

# 应用昇腾 FlashAttention patch 到 pip 安装好的 llamafactory
# 条件已经满足：torch 2.6.0 / torch_npu 2.6.0 >= 2.3.1，
# Qwen3 + LLaMA-Factory 在 flash_attn: auto 下走 PyTorch 原生
# scaled_dot_product_attention，正是 patch 钩住的入口。
COPY npu_flash_attn.py /opt/ascend_patch/npu_flash_attn.py
COPY apply_npu_fa_patch.sh /opt/ascend_patch/apply_npu_fa_patch.sh
RUN chmod +x /opt/ascend_patch/apply_npu_fa_patch.sh \
    && /opt/ascend_patch/apply_npu_fa_patch.sh

WORKDIR /workspace
