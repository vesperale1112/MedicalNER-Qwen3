# GPU 服务器训练手册

这份文档只讲一件事：拿到一台 GPU Linux 服务器后，如何用当前主数据集训练 Qwen3-8B LoRA。

当前应该训练的数据集是：

```text
LLaMA-Factory dataset name: pro_cot_001_858_complete_schema0413
Dataset file: data/llamafactory/pro_cot_001_858_complete_llamafactory.json
Source generation file: data/generated/gemini_split/pro_cot_001_858_complete_schema0413.json
```

不要先跑 Gemini 数据生成。858 条训练数据已经提交到仓库里了。

## 当前仓库状态

截至 commit `2087450`，数据已经准备好，但训练入口还没有完全同步到新数据集：

- `data/llamafactory/dataset_info.json` 只注册了 `pro_cot_001_858_complete_schema0413`
- `configs/llamafactory/qwen3_8b_lora_cot_specific.yaml` 仍指向旧的 `kg_cot_specific_614`
- `scripts/03_train_lora.sh specific` 仍检查旧文件 `data/llamafactory/kg_cot_specific_614.json`
- 如果文件是从 Windows/WSL 拷过去的，shell 脚本可能是 CRLF 换行，Linux bash 会报语法错误

所以最稳的做法是：新建一份 `pro858` 专用训练 YAML，然后直接调用 `llamafactory-cli train`。

## 服务器要求

最低建议：

- Linux
- Python 3.10
- NVIDIA GPU，支持 bf16
- 显存：24 GB 是比较紧的下限；48 GB 更稳
- 磁盘：至少预留 80-150 GB，用于模型缓存和 checkpoint
- 能访问 Hugging Face 或服务器已有 `Qwen/Qwen3-8B` 缓存

当前配置是 4-bit QLoRA、`cutoff_len: 16384`、per-device batch size 1、gradient accumulation 8。若 24 GB 显存 OOM，优先把 `cutoff_len` 降到 `12288` 或 `8192`。

## 1. 拉代码并检查数据

```bash
cd ~/workspace
git clone <REPO_URL> MedicalNER-Qwen3
cd MedicalNER-Qwen3

git log --oneline -n 3
git status --short

jq 'keys' data/llamafactory/dataset_info.json
jq 'length' data/llamafactory/pro_cot_001_858_complete_llamafactory.json
grep -R "<thinking>" data/llamafactory/pro_cot_001_858_complete_llamafactory.json && echo "BAD: old tags found" || echo "OK: no old thinking tags"
```

期望看到：

- `dataset_info.json` 里有 `pro_cot_001_858_complete_schema0413`
- 数据文件长度是 `858`
- 没有 `<thinking>` 标签

## 2. 修复 shell 脚本换行

如果是在 Linux 上正常 `git clone`，通常不需要这一步。但如果脚本报 `syntax error near unexpected token $'in\r'`，说明文件是 CRLF。

检查：

```bash
file scripts/03_train_lora.sh
bash -n scripts/03_train_lora.sh
```

修复：

```bash
dos2unix scripts/*.sh scripts/gemini/*.py src/kg_lora/*.py configs/llamafactory/*.yaml
```

如果服务器没有 `dos2unix`：

```bash
perl -pi -e 's/\r$//' scripts/*.sh scripts/gemini/*.py src/kg_lora/*.py configs/llamafactory/*.yaml
```

再验证：

```bash
bash -n scripts/03_train_lora.sh
python3 -m py_compile src/kg_lora/*.py scripts/gemini/*.py
```

## 3. 搭环境

### ModelArts

仓库已有 ModelArts helper：

```bash
cd ~/workspace/llc/MedicalNER-Qwen3
ENV_PREFIX=/cache/llc/KG bash scripts/setup_modelarts_env.sh
source /home/ma-user/miniconda3/bin/activate /cache/llc/KG
export PYTHONNOUSERSITE=1
```

### 普通 GPU 服务器

```bash
cd ~/workspace/MedicalNER-Qwen3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
export PYTHONNOUSERSITE=1
```

验证：

```bash
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda:", torch.version.cuda)
print("cuda available:", torch.cuda.is_available())
print("bf16 supported:", torch.cuda.is_bf16_supported() if torch.cuda.is_available() else None)
PY

llamafactory-cli version
nvidia-smi
```

如果 `torch.cuda.is_available()` 是 `False`，不要开始训练，先修 CUDA / 驱动 / PyTorch 环境。

## 4. 设置缓存路径

模型下载和训练缓存不要放到很小的系统盘。推荐显式设置：

```bash
export KG_CACHE_ROOT=${KG_CACHE_ROOT:-$PWD/.cache}
export HF_HOME=${HF_HOME:-$KG_CACHE_ROOT/huggingface}
export TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE:-$HF_HOME/hub}
export HF_DATASETS_CACHE=${HF_DATASETS_CACHE:-$HF_HOME/datasets}
export HUGGINGFACE_HUB_CACHE=${HUGGINGFACE_HUB_CACHE:-$HF_HOME/hub}
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-$KG_CACHE_ROOT}
export TMPDIR=${TMPDIR:-$KG_CACHE_ROOT/tmp}
export MPLCONFIGDIR=${MPLCONFIGDIR:-$KG_CACHE_ROOT/matplotlib}
mkdir -p "$HF_HOME" "$TRANSFORMERS_CACHE" "$HF_DATASETS_CACHE" "$TMPDIR" "$MPLCONFIGDIR" models/adapters
```

ModelArts 上可以把 `KG_CACHE_ROOT` 指到 `/cache/llc/KG-cache` 之类的高速盘。

## 5. 新建 pro858 训练配置

不要直接覆盖 v1 的 `specific` / `standard` 配置。新建一份：

```bash
cp configs/llamafactory/qwen3_8b_lora_cot_specific.yaml \
  configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml
```

编辑 `configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml`，至少改这两行：

```yaml
dataset: pro_cot_001_858_complete_schema0413
output_dir: models/adapters/qwen3-8b-cot-pro858
```

建议最终配置保持这些关键值：

```yaml
model_name_or_path: Qwen/Qwen3-8B
quantization_bit: 4
quantization_method: bitsandbytes
stage: sft
finetuning_type: lora
lora_rank: 8
lora_target: all
dataset_dir: data/llamafactory
dataset: pro_cot_001_858_complete_schema0413
template: qwen3
cutoff_len: 16384
val_size: 0.10
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
learning_rate: 1.0e-4
num_train_epochs: 3.0
bf16: true
save_steps: 10
eval_steps: 10
load_best_model_at_end: true
metric_for_best_model: eval_loss
greater_is_better: false
output_dir: models/adapters/qwen3-8b-cot-pro858
```

如果 24 GB 显存 OOM，只改：

```yaml
cutoff_len: 12288
```

还 OOM 再降到：

```yaml
cutoff_len: 8192
```

## 6. 先跑 smoke training

第一次上新机器，不要直接跑完整训练。复制一份 smoke 配置：

```bash
cp configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml \
  configs/llamafactory/qwen3_8b_lora_cot_pro858_smoke.yaml
```

把 smoke 配置改成：

```yaml
max_samples: 64
num_train_epochs: 1.0
save_steps: 5
eval_steps: 5
output_dir: models/adapters/qwen3-8b-cot-pro858-smoke
overwrite_output_dir: true
```

然后跑：

```bash
if grep -q "<thinking>" data/llamafactory/pro_cot_001_858_complete_llamafactory.json; then
  echo "BAD: old <thinking> tags found"
  false
fi
llamafactory-cli train configs/llamafactory/qwen3_8b_lora_cot_pro858_smoke.yaml
```

Smoke 通过的标准：

- 能加载 `Qwen/Qwen3-8B`
- 能加载 `pro_cot_001_858_complete_schema0413`
- 能开始训练并打印 loss
- 没有 CUDA OOM
- `models/adapters/qwen3-8b-cot-pro858-smoke/` 下有训练输出

## 7. 跑完整训练

```bash
if grep -q "<thinking>" data/llamafactory/pro_cot_001_858_complete_llamafactory.json; then
  echo "BAD: old <thinking> tags found"
  false
fi
llamafactory-cli train configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml
```

按当前默认配置估算：

- 总样本：858
- 验证集：约 86
- 训练样本：约 772
- 等效 batch size：8
- 每 epoch：约 96 optimizer steps
- 3 epochs：约 290 optimizer steps
- 每 10 steps eval + checkpoint：约 29 个 checkpoint

产物会在：

```text
models/adapters/qwen3-8b-cot-pro858/
```

## 8. 中断后恢复

查看已有 checkpoint：

```bash
find models/adapters/qwen3-8b-cot-pro858 -maxdepth 1 -type d -name 'checkpoint-*' | sort -V | tail
```

如果最后一个是 `checkpoint-120`，编辑 YAML：

```yaml
resume_from_checkpoint: models/adapters/qwen3-8b-cot-pro858/checkpoint-120
```

然后重新跑：

```bash
llamafactory-cli train configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml
```

恢复成功后，训练日志里应该能看到从 checkpoint 继续，而不是从 step 0 开始。

## 9. 训练后评估

当前 `scripts/04_compare_outputs.sh` 还只认识 `specific_adapter` 和 `standard_adapter`。不改脚本也能评估 pro858：把 pro858 adapter 暂时作为 `specific_adapter` 传给 Python 模块。

```bash
EVAL_PREFIX="outputs/pro858_eval_$(date +%Y%m%d_%H%M%S)"

PYTHONPATH=src python3 -m kg_lora.compare_qwen_outputs \
  --data data/raw/mental_disorders_20251125_165535.json \
  --samples data/samples/sample_eval_cases_expanded.json \
  --base-model Qwen/Qwen3-8B \
  --specific-adapter models/adapters/qwen3-8b-cot-pro858 \
  --standard-adapter models/adapters/qwen3-8b-cot-pro858 \
  --models base_qwen,specific_adapter \
  --load-in-4bit \
  --output "$EVAL_PREFIX"

PYTHONPATH=src python3 -m kg_lora.analyze_compare_outputs --input "${EVAL_PREFIX}_base_qwen.json"
PYTHONPATH=src python3 -m kg_lora.analyze_compare_outputs --input "${EVAL_PREFIX}_specific_adapter.json"
```

重点看：

- JSON 是否能稳定解析
- entity / relation 数量是否合理
- `<think>` 是否非空
- 是否出现明显语义错配，例如把核心症状连成 `Excludes If Present`
- 是否把限定词过度拆成实体

## 10. 常见问题

### `Missing training dataset`

原因通常是 YAML 里的 `dataset:` 和 `data/llamafactory/dataset_info.json` 不一致。

检查：

```bash
jq 'keys' data/llamafactory/dataset_info.json
rg '^dataset:' configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml
```

应该是：

```yaml
dataset: pro_cot_001_858_complete_schema0413
```

### `syntax error near unexpected token $'in\r'`

这是 CRLF 换行。执行：

```bash
dos2unix scripts/*.sh
```

### CUDA OOM

优先降 `cutoff_len`：

```yaml
cutoff_len: 12288
```

还不行就：

```yaml
cutoff_len: 8192
```

不要第一反应改 LoRA rank 或学习率；先保住训练能跑。

### 下载模型太慢或无法访问 Hugging Face

把 `model_name_or_path` 改成服务器上的本地模型目录，例如：

```yaml
model_name_or_path: /cache/models/Qwen3-8B
```

目录里需要有 tokenizer、config、model shard 等 Hugging Face 格式文件。

### 训练跑完但没有最终 adapter

检查：

```bash
find models/adapters/qwen3-8b-cot-pro858 -maxdepth 2 -type f | sort | tail -50
```

如果只有 checkpoint，没有根目录最终文件，通常是训练中断或保存策略问题。可以用最佳 checkpoint 目录作为 adapter 路径评估。

## 推荐执行顺序

最短可靠路径：

```bash
# 1. 环境
source .venv/bin/activate  # 或 source /home/ma-user/miniconda3/bin/activate /cache/llc/KG
export PYTHONNOUSERSITE=1

# 2. 验证
bash -n scripts/03_train_lora.sh
python3 -m py_compile src/kg_lora/*.py scripts/gemini/*.py
jq 'length' data/llamafactory/pro_cot_001_858_complete_llamafactory.json
llamafactory-cli version
nvidia-smi

# 3. 创建 pro858 配置
cp configs/llamafactory/qwen3_8b_lora_cot_specific.yaml configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml
# 手动把 dataset/output_dir 改成 pro858

# 4. smoke run
cp configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml configs/llamafactory/qwen3_8b_lora_cot_pro858_smoke.yaml
# 手动把 max_samples/epochs/output_dir 改成 smoke
llamafactory-cli train configs/llamafactory/qwen3_8b_lora_cot_pro858_smoke.yaml

# 5. full run
llamafactory-cli train configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml
```
