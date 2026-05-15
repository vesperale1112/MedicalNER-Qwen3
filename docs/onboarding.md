# 项目交接说明

> 如果你已经拿到 GPU 服务器，直接看 `docs/gpu_training.md`。那份文档是按“从服务器空环境到跑完 pro_cot_858 训练”的执行顺序写的。

## 一句话总结

用 Gemini API 从 DSM-5 精神障碍文本中自动抽取知识图谱，把抽取结果当训练数据，用 QLoRA 微调 Qwen3-8B，让 Qwen 自己也能做知识图谱抽取。

**用大模型（Gemini）造数据 → 用数据训小模型（Qwen）。**

---

## 知识图谱 Schema

目标是从精神障碍的医学文本中抽取结构化的实体和关系，输出 JSON 格式的知识图谱。

**10 类实体节点：**

| label | 说明 | 主要属性 |
|-------|------|----------|
| Disease | 疾病（DSM-5） | DSM-5 Code, Subtype, Course Requirements, Comorbidity Types, Prognosis Factors |
| Symptom | 核心/伴随症状 | Symptom Description, Occurrence Frequency, Severity Description |
| Diagnostic Criteria | 诊断标准 | Required Core Symptoms, Functional Impairment Requirements, Exclusion Details |
| Disease (Differential) | 鉴别诊断 | DSM-5 Code, Core Features, Key Differentiation Points, Misdiagnosis Risk |
| Interview Tool | 访谈要点 | Key Inquiry Directions, Sample Interview Phrases, Follow-up Focus |
| Patient Information | 患者特征 | Age Group, Comorbidities, Special Conditions, Medication History |
| Medication | 药物 | Generic Name, Indications, Contraindications, Common Side Effects |
| Communication Method | 沟通策略 | Suitable Patient Type, Empathetic Phrases, Pitfalls to Avoid |
| Risk Information | 风险因素 | Risk Type, Alert Keywords, Emergency Intervention Steps |

**22 种关系类型**，覆盖疾病层级（subsumes, differentiates_from）、症状-疾病（is_core_symptom_of, precedes）、诊断三角（required_for_diagnosis_of, excludes_if_present）、用药（first_line_for, contraindicated_in）、风险（triggers_alert_when）等。

完整的 schema 定义在代码的 `SYSTEM_PROMPT` 常量中。

**输出格式示例：**

```json
{
  "entities": [
    {
      "id": "D1",
      "label": "Disease",
      "name": "Major Depressive Disorder",
      "properties": { "DSM-5 Code": "296.2x", "Subtype": "Unipolar" }
    },
    {
      "id": "S1",
      "label": "Symptom",
      "name": "Persistent depressed mood",
      "properties": { "Occurrence Frequency": "Daily", "Severity Description": "Most of the day" }
    }
  ],
  "relations": [
    {
      "source": "S1",
      "target": "D1",
      "relation_type": "Symptom–Disease",
      "relation_name": "Core Symptom Of",
      "relation": "is_core_symptom_of"
    }
  ]
}
```

---

## 整体流水线

```
原始精神障碍记录(JSON)
  │
  ▼  [01] Gemini API 抽取（带 CoT 推理）
  │
filtered JSON（质量过滤后）
  │
  ▼  [02] 转 ShareGPT 格式（<thinking> → <think> 标签规范化）
  │
LLaMA-Factory 训练数据
  │
  ▼  [03] QLoRA 微调 Qwen3-8B
  │
LoRA adapter 权重
  │
  ▼  [04] 对比评估（base Qwen vs adapter）
  │
评估报告
```

对应 `scripts/` 下 4 个编号脚本：

| 步骤 | 脚本 | 做什么 | 需要 |
|------|------|--------|------|
| 1 | `01_generate_cot_data.sh` | 调 Gemini API 抽取 KG，输出到 `data/generated/` | Gemini API Key |
| 2 | `02_convert_to_llamafactory.sh` | 转成 ShareGPT 对话格式，规范化 think 标签 | 步骤1的输出 |
| 3 | `03_train_lora.sh` | 调 `llamafactory-cli train` 跑 QLoRA | GPU + LLaMA-Factory |
| 4 | `04_compare_outputs.sh` | 加载 base/adapter 模型对比输出 | GPU + 训好的 adapter |

另外两个辅助脚本：
- `run_specific_pipeline.sh` — 串联步骤 1-3 一键跑
- `setup_modelarts_env.sh` — 华为 ModelArts 环境搭建（创建 conda 环境、装依赖、检查 CUDA/bf16/LLaMA-Factory）

---

## 核心代码

全在 `src/kg_lora/` 下，5 个 Python 文件。脚本用 `PYTHONPATH=src python3 -m kg_lora.<module>` 调用。

### generate_cot_data.py（~1250 行，数据生成）

直接用 `urllib` 调 Gemini REST API（没用 SDK），从每条精神障碍记录中抽取知识图谱。

**两种抽取模式：**
- `single_pass` — 短文本直接送 Gemini，超长的截断
- `chunk_merge` — 长文本切成重叠块，分别抽取后合并实体/关系，再调一次 Gemini 做修复（repair pass）

**两种 CoT 提示风格：**
- `specific` — 要求 Gemini 写**跟当前样本相关的**抽取决策（"这条文本最重要的疾病是X，Y没有抽取因为文本没明确提到"）。禁止写套话
- `template`（代码里也叫 standard）— 要求 Gemini 按**固定 6 步模板**写推理（"第一步识别疾病，第二步提取症状..."），每条样本结构差不多

**质量过滤：** 拒绝实体数 < 3 的样本和包含幽灵关系（relation 引用了不存在的实体 ID）的样本。

**实体去重键：** `(label, normalized_name)`；**关系去重键：** `(source, target, relation_type, relation_name, relation)` 五元组。

### convert_to_llamafactory.py（格式转换）

把生成结果转成 `[{messages: [{role: "system", content: ...}, {role: "user", content: ...}, {role: "assistant", content: ...}]}]` 的 ShareGPT 格式，并注册到 `data/llamafactory/dataset_info.json`。

**关键功能：** 将 Gemini 输出的 `<thinking>` 标签规范化为 Qwen3 原生的 `<think>` 标签（通过 `normalize_qwen_think_tags()` 函数）。也支持导出 chunk 级别的 traces 作为独立 SFT 样本。

### compare_qwen_outputs.py（评估对比）

逐个加载 base Qwen 和各 LoRA adapter 跑推理（为了省显存，一次只加载一个模型，跑完释放再加载下一个）。支持 4-bit/8-bit 量化加载。每个模型的输出单独存成一个 JSON 文件。

### analyze_compare_outputs.py / analyze_kg_outputs.py（统计分析）

对输出文件做汇总统计：实体数、关系数、有效 JSON 比例、空属性比例等。

---

## SYSTEM_PROMPT 同步问题

**这是最大的代码架构坑。** KG 的 schema（实体表、关系表、抽取指令）作为 `SYSTEM_PROMPT` 常量被**完整复制了三份**，分别在：

1. `generate_cot_data.py` — Gemini 生成时用
2. `convert_to_llamafactory.py` — 构造训练数据时用
3. `compare_qwen_outputs.py` — Qwen 推理评估时用

改 schema 必须同步改三处，否则训练数据和推理时用的 prompt 不一致。`HIGH_COVERAGE_REQUIREMENTS`、`COT_TEMPLATE_PROMPT`、`COT_SPECIFIC_PROMPT` 也是同样情况（前两个文件都有）。

---

## Think 标签的坑

Gemini 生成数据时用 `<thinking>`/`</thinking>` 标签包裹推理过程，但 Qwen3 的原生 thinking 标签是 `<think>`/`</think>`。

- `convert_to_llamafactory.py` 会自动把 `<thinking>` 替换成 `<think>`
- `03_train_lora.sh` 启动训练前会**检查数据集中是否残留 `<thinking>` 标签**，如果有会报错拒绝训练
- 如果你手动准备训练数据，一定要确保用的是 `<think>` 不是 `<thinking>`

---

## 仓库里已经有的数据

> **2026-05-07 数据集大换血**：旧的 specific 614 / standard 635 被归档进 `version1/`，新的 858 条完整 pro_cot 数据集成为主用训练数据。详情见 `reports/gemini_generation_status_20260507.md`。

### 当前主用数据（v2）

| 文件 | 说明 |
|------|------|
| `data/raw/mental_disorders_20251125_165535.json` | 原始精神障碍记录（858 条，输入数据） |
| `data/generated/gemini_split/pro_cot_001_858_complete_schema0413.json` | Gemini Pro CoT 生成结果，**完整 858 条，0 失败** |
| `data/generated/gemini_split/flash3_structure_001_858_complete_schema0413.json` | Gemini Flash 结构抽取，完整 858 条 |
| `data/generated/gemini_split/pro_structure_*.json` | Gemini Pro 结构抽取，**进行中 449/858**（被 Pro 每日配额卡住） |
| `data/llamafactory/pro_cot_001_858_complete_llamafactory.json` | **新的训练数据集**：858 条 ShareGPT 样本，已用 `<think>` 标签 |
| `data/llamafactory/dataset_info.json` | 当前只注册了 `pro_cot_001_858_complete_schema0413` |
| `data/samples/sample_eval_cases.json` | 评估样本（5 条，覆盖短/中/长文本） |
| `data/samples/sample_eval_cases_expanded.json` | 5 条评估样本的扩展版本 |

**新数据集的 CoT 风格变了**（看 prompt 实测）：要求 `<think>` 里写不超过 6 步的简洁推理，think 中位 **1953 字符**、输出中位 **4096 字符**、think/output 比值约 **0.48** —— 比 v1（specific 0.12 / standard 0.06）高一个数量级，预期能修复之前评估里 adapter 输出空 think 的问题。

### 归档数据（v1，仅作对比保留）

放在 `data/llamafactory/version1/` 和 `data/generated/version1/`：

| 文件 | 说明 |
|------|------|
| `data/llamafactory/version1/kg_cot_specific_614.json` | 旧的 specific CoT 训练集（614 条） |
| `data/llamafactory/version1/kg_cot_standard_635.json` | 旧的 standard CoT 训练集（635 条） |
| `data/llamafactory/version1/dataset_info.json` | v1 时代的注册文件（含旧数据集名） |
| `data/generated/version1/0413_cot_specific_614_12000_8000.json` | v1 specific 原始生成结果 |
| `data/generated/version1/0413_cot_standard_635_12000_8000.json` | v1 standard 原始生成结果 |

**不在仓库里的：** 模型权重（adapter）、评估输出（`outputs/`）。

生成数据文件名中的数字含义：`0413_cot_specific_614_12000_8000` → 4月13日生成，specific 风格，614 条有效样本，max_input_chars=12000，max_output_tokens=8000；`pro_cot_001_858_complete_schema0413` → Gemini Pro 模型，CoT 风格，覆盖 1-858 全量，schema 版本 0413。

---

## v1 specific/standard vs v2 pro_cot_858

仓库里有两代生成数据，新 vs 旧的差别：

| | v1 specific | v1 standard | **v2 pro_cot_858（当前）** |
|---|---|---|---|
| 生成模型 | Gemini Flash | Gemini Flash | **Gemini Pro** |
| 推理风格 | 针对当前样本写抽取决策 | 固定 6 步模板 | 不超过 6 步的简洁 think |
| 有效样本数 | 614 | 635 | **858（全量，0 失败）** |
| think 中位长度 | 588 字符 | 256 字符 | **1953 字符** |
| think/output 比值 | 0.12 | 0.06 | **~0.48** |

**v1 评估结论**（`reports/qwen_compare_analysis_report.md`，5 样本对比 base vs v1 adapter）：
- 两个 v1 adapter 的 JSON 都能稳定解析，实体/关系覆盖度也比 base 高（specific 13.0 entity / standard 15.2 entity vs base 7.0）
- 但两者训出来后 `<think>` 都是空的 —— 因为 v1 的 think/output 比值太低，监督信号几乎全在 JSON 上
- specific 偏保守、standard 偏结构化，各自有语义错配问题

v2 设计上正是冲着 think 监督信号不够这一点改的，能不能跑出非空 think + 高质量 JSON 还需要训完才知道。

---

## 训练配置细节

训练配置文件在 `configs/llamafactory/` 下，三个 YAML：

| 配置 | 数据集名（YAML 里写的） | cutoff_len |
|------|------------------------|------------|
| `qwen3_8b_lora_cot_specific.yaml` | `kg_cot_specific_614` | 16384 |
| `qwen3_8b_lora_cot_standard.yaml` | `kg_cot_standard_635` | 16384 |
| `qwen3_8b_lora_sft.yaml` | `kg_ner_sft` | 4096 |

> ⚠️ **配置/脚本和当前数据集不一致（commit 2087450 后未同步）。** 三个 YAML 还指向 v1 数据集名，`scripts/03_train_lora.sh` 也还在硬编码检查 `data/llamafactory/kg_cot_specific_614.json` —— 这两个名字目前都没在 `data/llamafactory/dataset_info.json` 里注册了，直接跑会报 `Missing training dataset`。下一节会给出具体怎么改。

**共同配置：**
- 基座模型：`Qwen/Qwen3-8B`（base 版，不是 Instruct——华为 HF 镜像上没有 Instruct 版）
- 微调方式：QLoRA（4-bit bitsandbytes 量化 + LoRA rank 8 + target all 线性层）
- 计算精度：bf16
- 学习率：1e-4，cosine schedule
- batch：per_device=1，gradient_accumulation=8（等效 batch_size=8）
- epochs：3

**CoT 配置额外特点（specific 和 standard 共有）：**
- 频繁 checkpoint：每 10 步 eval + 保存（给 ~600 条数据大约产生 ~20 个 checkpoint）
- `save_total_limit: 30` 防磁盘爆满
- `load_best_model_at_end: true`，按 eval_loss 选最优 checkpoint
- `val_size: 0.10`（10% 验证集）
- `warmup_ratio: 0.03`

**缓存路径：** 训练脚本把 HuggingFace cache 全部指向 `.cache/` 目录。可通过 `KG_CACHE_ROOT` 或 `HF_HOME` 环境变量覆盖。

---

## 环境搭建

### 依赖

`requirements.txt` 固定了 `torch==2.6.0`（兼容 CUDA 12.x），并且**已包含 `llamafactory[metrics]==0.9.3`**，所以 `pip install -r requirements.txt` 就能装好所有依赖。

### 本地环境

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 只跑训练不需要填 GEMINI_API_KEY
```

### ModelArts（华为云）

```bash
cd ~/workspace/llc/MedicalNER-Qwen3
ENV_PREFIX=/cache/llc/KG bash scripts/setup_modelarts_env.sh
source /home/ma-user/miniconda3/bin/activate /cache/llc/KG
export PYTHONNOUSERSITE=1
cp .env.example .env
```

`setup_modelarts_env.sh` 做的事：创建/修复 conda 环境 → 装 pip 依赖 → 检查 torch/CUDA/bf16 → 检查 llamafactory-cli。

`PYTHONNOUSERSITE=1` 是为了防止 ModelArts 的 `~/.local` 下安装的旧版包干扰。

---

## 环境变量

在 `.env` 里配置（参考 `.env.example`）：

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `GEMINI_API_KEY` | Gemini 数据生成（只跑训练不需要） | 无 |
| `BASE_MODEL` | Qwen 基座模型 | `Qwen/Qwen3-8B` |
| `SPECIFIC_ADAPTER` | specific adapter 路径 | `models/adapters/qwen3-8b-cot-specific` |
| `STANDARD_ADAPTER` | standard adapter 路径 | `models/adapters/qwen3-8b-cot-standard` |
| `KG_DATA_PATH` | 原始数据路径 | `data/raw/mental_disorders_20251125_165535.json` |
| `KG_OUTPUT_ROOT` | 输出根目录 | `outputs` |
| `KG_CACHE_ROOT` | HuggingFace 缓存根目录 | `.cache` |

---

## 常用命令

### 直接开始训练（数据已在仓库）

```bash
PYTHONNOUSERSITE=1 bash scripts/03_train_lora.sh specific   # 训练 specific adapter
PYTHONNOUSERSITE=1 bash scripts/03_train_lora.sh standard   # 训练 standard adapter
```

### 烟雾测试 Gemini 生成

```bash
# 在 .env 填入 GEMINI_API_KEY 后
MAX_SAMPLES=3 WORKERS=1 bash scripts/01_generate_cot_data.sh
```

### 完整数据生成

```bash
COT_STYLE=specific WORKERS=4 bash scripts/01_generate_cot_data.sh
```

### 格式转换

```bash
bash scripts/02_convert_to_llamafactory.sh \
  data/generated/cot_filtered_merged.json \
  kg_cot_specific_614 \
  specific
```

### 评估对比

```bash
bash scripts/04_compare_outputs.sh
```

### 直接运行 Python 模块

```bash
PYTHONPATH=src python3 -m kg_lora.generate_cot_data --help
PYTHONPATH=src python3 -m kg_lora.convert_to_llamafactory --help
PYTHONPATH=src python3 -m kg_lora.compare_qwen_outputs --help
PYTHONPATH=src python3 -m kg_lora.analyze_compare_outputs --input <path>
PYTHONPATH=src python3 -m kg_lora.analyze_kg_outputs --input <path>
```

### 一键跑完生成+转换+训练

```bash
bash scripts/run_specific_pipeline.sh data/raw/mental_disorders_20251125_165535.json
```

---

## 目录结构

```
├── configs/llamafactory/        3 个 LLaMA-Factory 训练 YAML
├── data/
│   ├── raw/                     原始精神障碍记录（已提交）
│   ├── generated/               Gemini CoT 生成输出（已提交 0413 批次）
│   ├── llamafactory/            ShareGPT 训练数据 + dataset_info.json（已提交）
│   └── samples/                 评估样本（5 条）
├── models/adapters/             训好的 LoRA adapter（不提交）
├── outputs/                     评估输出（不提交）
├── reports/                     分析报告
├── scripts/                     Shell 入口脚本
├── src/kg_lora/                 Python 模块（5 个文件）
├── docs/                        文档
├── requirements.txt             Python 依赖（含 LLaMA-Factory）
└── .env.example                 环境变量模板
```

---

## 当前状态（2026-05-10）

**已完成：**
- v1 数据生成流程（specific 614 / standard 635）已跑通并归档到 `version1/`
- v1 已做过 5 样本 base vs adapter 评估（`reports/qwen_compare_analysis_report.md`），结论是 LoRA 有效但 think 输出全空
- v2 数据生成升级到 Gemini Pro，**858 条全量 CoT 已完成**并提交，think/output 比值大幅提升
- v2 数据已转好 ShareGPT 格式、用 `<think>` 标签、注册进 `dataset_info.json`
- ModelArts 环境搭建脚本就绪、训练配置基本成熟（4-bit QLoRA / rank 8 / target all / cosine LR / 频繁 eval+checkpoint）

**未完成 / 阻塞中：**
- Gemini Pro structure 抽取还在跑，被每日配额卡在 449/858（不影响 CoT 训练，是另一条数据线）
- v2 的训练配置和入口脚本还指向 v1 文件名，**直接跑训练会失败**（详见下一节）
- v2 还没训过，更没评估过

---

## 下一步：开始训练新的 858 数据集

走的是「用 v2 pro_cot_858 训」这条路。机器还没就绪，先在本地把配置改好提交，到 GPU 上 pull 下来直接跑。

### Step 1：改一份新的训练配置（不要原地改 v1 的）

建议**新建** `configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml`，复制 `qwen3_8b_lora_cot_specific.yaml` 然后改两行：

```yaml
dataset: pro_cot_001_858_complete_schema0413   # 改这里：和 dataset_info.json 一致
output_dir: models/adapters/qwen3-8b-cot-pro858  # 改这里：避免和 v1 adapter 路径混
```

其它字段（cutoff_len: 16384、rank 8、bf16、save_steps: 10、val_size: 0.10、3 epochs）保持不变。新数据集 858 条 + 10% 验证 → 大约 772 训练样本，等效 batch 8，每 epoch ~96 step，3 epoch ~290 step，按 save_steps=10 会产生 ~29 个 checkpoint，刚好在 `save_total_limit: 30` 容量内。

### Step 2：给 03_train_lora.sh 加一个 pro858 入口

`scripts/03_train_lora.sh` 第 23-41 行的 `case` 里加一支，例如：

```bash
pro858)
  CONFIG="configs/llamafactory/qwen3_8b_lora_cot_pro858.yaml"
  DATASET_JSON="data/llamafactory/pro_cot_001_858_complete_llamafactory.json"
  ;;
```

> 不要动 specific / standard / sft 三个分支 —— 那是 v1 的入口，留着以后做对比。

### Step 3：跑训练

ModelArts 上：

```bash
cd ~/workspace/llc/MedicalNER-Qwen3
ENV_PREFIX=/cache/llc/KG bash scripts/setup_modelarts_env.sh
source /home/ma-user/miniconda3/bin/activate /cache/llc/KG
export PYTHONNOUSERSITE=1

PYTHONNOUSERSITE=1 bash scripts/03_train_lora.sh pro858
```

本地 GPU 机：跳过 setup_modelarts，直接 `pip install -r requirements.txt` 后跑同样的命令。

显存：4-bit QLoRA + Qwen3-8B + cutoff_len 16384，单卡 24G 应该刚好够（v1 这套配置是这么定的），实测时如果 OOM 把 `cutoff_len` 临时降到 12288 试。

训练脚本启动前会 `grep <thinking>` 拒绝旧风格数据 —— 新数据集已经验证过没有 `<thinking>` 残留，会通过这个检查。

### Step 4：评估

训完之后：

```bash
# 在 .env 里加一行 PRO858_ADAPTER=models/adapters/qwen3-8b-cot-pro858
# 然后改 scripts/04_compare_outputs.sh 让它把这个 adapter 也加入对比
bash scripts/04_compare_outputs.sh
PYTHONPATH=src python3 -m kg_lora.analyze_compare_outputs --input outputs/...
```

重点要看的指标（参照 v1 报告的标准）：
1. JSON 可解析率（v1 adapter 是 5/5，新的应该不能比这差）
2. 实体/关系覆盖度（v1 是 13~15）
3. **`<think>` 是否非空** —— 这是 v2 设计要解决的核心问题
4. 抽取语义正确性（人工抽检：核心症状别错配、限定词别拆成实体）

### Step 5（可选）：v1 vs v2 消融

如果想对比新旧 CoT 风格，可以把 `version1/dataset_info.json` 里的两条 entry 合并回顶层 `dataset_info.json`，并把 `version1/kg_cot_specific_614.json` / `kg_cot_standard_635.json` 软链回顶层（或者改 YAML 的 `dataset_dir: data/llamafactory/version1`），这样原来的 `bash scripts/03_train_lora.sh specific|standard` 就能直接复用。
