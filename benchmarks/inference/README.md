# 用当前 semantic 模型生成 benchmark 预测

这个入口复用 `agent/run_semantic_pipeline.py` 的两阶段抽取：实体 LoRA → 实体表 → 关系 LoRA → 程序校验和组装图。它只把每篇的 `text` 送入模型；即使输入文件带参考图，也不会把参考实体或关系送入模型。模型在一个进程中加载一次；每篇的窗口可以成批生成。

## 对应哪一版训练

本地 Git 历史中，最近一轮训练实验截至 2026-10-19。最终保留的组合是：

- 实体：`entity_short_complete_lr1e4_r16_e2`，推理选 `short_source`；
- 关系：`relation_short_canonical_complete_lr1e4_r16_e2`，推理选 `short_canonical`；
- 源文本窗口 2400 字符，重叠最多 400 字符；默认输入上限 8192 token、输出上限 4096 token。

这些是本脚本的默认值。后续 DPO24 自由文本关系 F1 未超过原 SFT，标签加权 SFT 的提升很小，最终记录均保留原组合。证据见 [训练轮次最终选择](../../docs/audits/20261019-round2/round-closeout.json)和 [DPO24 最终结果](../../docs/audits/20261019-round3/DPO24-RESULT.zh.md)。仓库中 11 月 16 日提交更新了数据、schema 和 benchmark 示例，并不是同一模型的新训练记录。上述历史分数来自反复使用的银标 tune，不是独立盲测。

## 需要准备

1. 本地 Qwen3-8B 基座目录，包含模型权重、配置及 tokenizer，且与训练时基座配置和 tokenizer 匹配。
2. 上述实体和关系 LoRA 各自的完整目录，保留 `adapter_model.safetensors`、`adapter_config.json` 和对应的 `training_manifest.json`。询问训练负责人时，请明确要上述两个 **SFT** 模型及各自的训练记录；旧版整图 JSON LoRA、分类器或 DPO 权重不能直接当作这对模型。
3. 支持 BF16 的 CUDA GPU，以及 [agent/requirements.txt](../../agent/requirements.txt) 对应的 PyTorch、Transformers、PEFT 环境。原加载器当前直接使用 CUDA，不能把这个入口直接当作 Ascend NPU 推理。

仓库中的 `models/adapters/qwen3-8b-cot-pro858` 属于旧路线，并不等同于上面两个 semantic adapter。本地当前没有找到这两个 semantic 权重，因此这里还没有做真实模型推理。

原加载器会核对训练记录中的协议、阶段、基座配置/tokenizer 和 adapter 信息。Windows 工作区如果仅将协议文件的 LF 换行为 CRLF，本入口会在两个训练记录都匹配 LF 内容时兼容这一差异，不修改源文件；其他协议差异仍由原加载器拒绝。请保留训练目录原有文件。

## 运行

在仓库根目录运行，将路径替换成实际位置：

```bash
python benchmarks/inference/run_semantic.py \
  --input benchmarks/datasets/kg_40/dhy_pilot.json \
  --run-dir benchmarks/runs/semantic_kg40 \
  --base-model /path/to/Qwen3-8B \
  --entity-adapter /path/to/entity_short_complete_lr1e4_r16_e2 \
  --relation-adapter /path/to/relation_short_canonical_complete_lr1e4_r16_e2
```

`--run-dir` 必须是不存在的新目录。成功加载后会生成 `predictions.json`，并在每篇结束时更新；`sources/` 保存实际输入，`traces/` 保存原始模型输出、解析与失败信息，均可能含原文。若某篇生成不完整，该篇标为 `failed`、图为 `null`，不会把部分图当作完整预测。模型或权重加载失败会在创建运行目录之前退出。结构化 ICD 输入仍走原有确定性解析，无需模型；它的结果不是模型预测。

可按硬件调整 `--batch-size`（默认 4，控制同一篇内的窗口批次），也可设置 `--timeout-seconds`（每篇生成时限）。`--max-input-tokens`、`--max-new-tokens`、`--short-chars` 和两个 variant 也可修改；切换 variant 时须与相应 adapter 的训练记录一致。当前实现逐篇处理，虽然窗口批量调用，但不同文章之间不合并批次；批次组成与历史实验可能不同，不能保证逐字复现历史结果。

输入需是 `medicalner-benchmark-v1` JSON，每篇至少包含唯一字符串 `id` 和非空 `text`；现有参考文件和导入后的 MDIEC 文件均符合该基本格式。使用参考文件作为输入时，脚本仅取 `id` 和 `text`，不读取参考图进行推理。

## 评分和解释

```bash
python benchmarks/benchmark.py evaluate \
  --reference benchmarks/datasets/kg_40/dhy_pilot.json \
  --predictions benchmarks/runs/semantic_kg40/predictions.json \
  --tasks graph --include-errors \
  --output benchmarks/runs/semantic_kg40_metrics.json
```

预测文件直接适配现有评分器；`graph` 比较名称、类型及有向关系。对于自由文本，如果实体阶段 trace 提供正文位置，预测还声明 `ner`：位置来自原解析器对实体 mention 的所有原文匹配，可能包含多余出现位置。只有参考也提供同一坐标系的 mention 才能评分 NER。概念 ID 和关系的具体 mention 端点不由本模型提供，因此不声明 `nel`、`m_re` 或 `c_re`。若成功样本中包含结构化 ICD 等没有实体阶段位置的输入，本次结果只声明 `graph`。

当前模型使用 [`agent/semantic/protocol.py`](../../agent/semantic/protocol.py) 的训练本体，不会自动切换到 11 月的 v3.2 schema；它与治疗文献试标、MDIEC 等数据的标签未必一致。要解释分数，须先核对本体、输入和参考标注，明确未映射类别。`dhy_pilot.json` 是单人未仲裁试标，不是独立金标。

无权重检查：

```bash
python -m unittest discover -s benchmarks/inference -p 'test_*.py' -v
python -m unittest discover -s benchmarks/tests -v
```
