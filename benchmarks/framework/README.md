# Benchmark 框架使用说明

入口是 [`benchmarks/benchmark.py`](../benchmark.py)，数据转换、评分和人工复核准备都只依赖 Python 标准库。以下命令均在仓库根目录执行。`--output` 要指定**尚不存在的文件**，避免覆盖已有数据。

## 评测范围

同一套评分器可以分别使用 `gold`（人工仲裁金标）、`silver`（模型银标）或 `pilot`（未仲裁试标）作为参考。类型由使用者根据数据来源声明；声明本身不会使银标变成金标。比较时应对每一种参考单独运行、分别报告。特别是银标一致性不等于临床正确率，未标出的关系也不能直接断定为不存在。

四层评分借鉴 GutBrainIE 的主要匹配单位：

| 参数 | 匹配条件 |
|---|---|
| `ner` | 同一部分、起止位置、原文片段及实体类型一致 |
| `nel` | NER 全部条件一致，且给定的 `concept_id` 一致 |
| `m_re` | 有向关系的两端原文提及文本、两端类型及关系标签一致；匹配键不含字符位置 |
| `c_re` | 有向关系的两端概念 ID、两端类型及关系标签一致 |
| `graph` | 本项目已有图的实体名称和类型，及有向关系的两端名称、类型和关系标签一致 |

`graph` 是实用的名称匹配诊断，**不是** NER、NEL、M-RE 或 C-RE。名称仅做 NFKC、大小写折叠和空白合并；类型、关系标签严格一致，不自动猜测同义词或把文章内节点 ID 当概念 ID。

这不是 GutBrainIE 官方评分器：这里按文档内精确键去重，未实现其重叠片段合并等官方预处理。使用其原生数据、标签与官方评测程序另行核验后，才能报告官方可比成绩。当前实现中，关系类别是“主体类型—关系—客体类型”，实体类别是实体类型；micro 汇总 TP/FP/FN，macro F1 对**参考中有支持样本**的类别求平均，预测独有类别仍计入 micro FP。分母为零时 P/R/F1 记为 0。报告包括总体、各类别和各文档计数，`--include-errors` 可加入逐项 FP/FN。

参考数据与预测数据必须各自声明能够提供的 `tasks`，评分器不会把缺少字符位置或概念 ID 的图误报成四层结果。所选任务的参考标注不完整时直接报错；预测中具体条目的字段无效时计 FP。预测缺失、失败或图结构无效时该文章按空预测处理，参考项保留为 FN；额外文章 ID、重复文章 ID、已提供但不一致的输入文本会报错。未在预测中提供原文时，报告的 `prediction_input_unverified` 会计数。**因此比较不同模型前仍需检查来源、样本、原文、schema 和实际模型输入是否一致。**

## 先运行虚构示例

示例仅用于检查接口，不含真实医学事实或人工金标。它有两篇文本，其中一篇没有关系；第一篇预测关系标签故意写错。

```bash
python benchmarks/benchmark.py evaluate \
  --reference benchmarks/examples/synthetic_reference.json \
  --predictions benchmarks/examples/synthetic_predictions.json \
  --tasks graph ner nel m_re c_re --include-errors \
  --output benchmarks/runs/synthetic_metrics.json
```

## 用本项目现有人工试标和模型图测试流程

导入器接受标注页导出或 `predictions/kg_pilot_20_gpt61sol.json` 这一类模型输出。它只保留数据原有信息，不从实体名推断 mention、offset 或 concept ID。若预测记录含 `input_used`，使用实际输入而不是较长的原始文本；这可能触发与参考文本不一致的错误，需要先确认比较是否公平。

以下仅用于验证流程：DHY 的结果是**单人试标、未仲裁**，不是最终金标；试标文章也不应冒充独立盲测。

```bash
python benchmarks/benchmark.py import-project \
  --input benchmarks/datasets/kg_pilot_20/annotations/MedicalNER_DHY_20articles_2026-10-22.json \
  --dataset-id pilot-dhy --kind pilot --output benchmarks/runs/pilot_dhy.json
python benchmarks/benchmark.py import-project \
  --input benchmarks/predictions/kg_pilot_20_gpt61sol.json \
  --dataset-id pilot-gpt --kind prediction --output benchmarks/runs/pilot_gpt.json
python benchmarks/benchmark.py evaluate \
  --reference benchmarks/runs/pilot_dhy.json --predictions benchmarks/runs/pilot_gpt.json \
  --tasks graph --include-errors --output benchmarks/runs/pilot_comparison.json
```

未来的独立人工金标、模型银标可各自转为本格式；图格式兼容时分别用 `--kind gold`、`--kind silver` 导入并分别评分。请固定同一批原文和本体标签，记录金标仲裁、银标来源、生成模型、数据版本及训练/测试隔离。不要将某个模型的训练银标直接当作该模型的独立测试集。对模型的完整性与质量不能仅由本脚本保证。

## 本地 MDIEC 公开语料

```bash
python benchmarks/benchmark.py import-mdiec \
  --input-dir benchmarks/datasets/public/mdiec/MDIEC \
  --output benchmarks/runs/mdiec_native.json
```

转换的是 946 份本地 BRAT 原生标注，保留其标签和有向 `Arg1 → Arg2`；支持 `ner` 和 `m_re`，**不提供**概念 ID。`.ann` 不是模型预测，本地没有论文的官方 train/dev/test 清单，不能把整包直接称为官方测试集或论文结果复现。MDIEC 和本项目的标签语义不完全一致；应使用原生标签训练/预测，或先制定并报告映射和未映射覆盖，不可直接强行混用。

转换器以 BRAT 的字符位置切片作为 mention 文本；遇到与 `.ann` 自带文本不一致的记录时，保留 `original_annotation_text` 并写到顶层 `import_issues`，供人工复核。本地已发现 1 处。关系按 M-RE 的提及文本/类型/标签去重后可能少于 BRAT 的原始关系行数，属于评分单位差异。

## 使用现有 semantic 模型入口

`agent/run_semantic_pipeline.py` 已提供单篇两阶段抽取接口。以下批处理适配只读取每篇的 `text`，不会向模型传参考图或正确实体；每篇调用一次现有 CLI，**每篇都会重新加载模型**，适合先小批量验证，跑大集合会较慢：

```bash
python benchmarks/benchmark.py run-semantic \
  --input benchmarks/runs/pilot_dhy.json --run-dir benchmarks/runs/semantic_pilot \
  --base-model /path/to/Qwen3-8B \
  --entity-adapter /path/to/semantic-entities \
  --relation-adapter /path/to/semantic-relations
python benchmarks/benchmark.py evaluate \
  --reference benchmarks/runs/pilot_dhy.json \
  --predictions benchmarks/runs/semantic_pilot/predictions.json \
  --tasks graph --output benchmarks/runs/semantic_pilot_metrics.json
```

适配器和 base 需满足现有入口的训练回执、协议及环境要求，详见 [`agent/README.md`](../../agent/README.md)。`--variant`、`--entity-variant`、`--short-chars` 和 `--timeout-seconds` 可按该入口设置。运行目录必须是新目录，其中保存输入文本、每篇结果、现有入口产生的 trace，以及每篇运行后更新的 `predictions.json`；这些文件可能含原文，注意保存位置。结构化 ICD 输入走原有确定性路径，可以不提供模型权重；自由文本则需要有效权重。

当前 semantic 最终图不含 span，但自由文本实体阶段的私有 trace 保留原文定位。批处理会从其中的 `filtered_entities` 复制 body anchors，在所有成功样本都具备该 trace 时额外声明 `ner`；已有解析器会为生成的 mention 查找原文中所有匹配位置，这一策略可能产生多余提及，需在解释实体分数时说明。它使用整个模型输入作为 `text` 部分；若参考数据按标题/摘要分别标注，须先统一位置坐标。结构化 ICD 路径没有实体阶段 trace，混合这类成功样本的批次只声明 `graph`，并在 `ner_unavailable_documents` 中列明。

模型没有提供稳定概念链接，关系输出也没有明确绑定具体 mention，因此不会据此声明 `nel`、`m_re` 或 `c_re`。现有入口另有需要单独提供可信标题来源的模式，这个批处理暂未接该模式；不要把参考答案当作标题输入。对当前本体和治疗摘要试标的 schema 差异也要先检查。

## 人工原文支持复核

此功能生成待人工填写的随机关系样本，不调用模型做医学判断。样本以“文档 + 本地图节点对 + 关系”为单位去重，`excluded_invalid_relations` 记录未能构造审核项的非法关系；该数量应与主评分中的失败分析一起看。

```bash
python benchmarks/benchmark.py sample-evidence \
  --predictions benchmarks/runs/pilot_gpt.json --size 30 --seed 42 \
  --output benchmarks/runs/evidence_review.json
```

人工查看 `text`、端点、`relation` 与 `evidence`，将每项 `verdict` 填为 `supported`、`not_supported` 或 `uncertain`，并填写 `reviewer` 和 `notes`。保留 `null` 表示未复核。完成后执行：

```bash
python benchmarks/benchmark.py summarize-evidence \
  --input benchmarks/runs/evidence_review.json --output benchmarks/runs/evidence_summary.json
```

`support_rate_among_decided = supported / (supported + not_supported)`；不确定和未复核的数量分别保留，完全没有明确判断时结果为 `null`。这是抽样人工支持率，不是召回率、F1 或自动语义验证；抽样方案和评审者一致性需要另行设计。

## 数据约定

完整例子见 [`synthetic_reference.json`](../examples/synthetic_reference.json) 和 [`synthetic_predictions.json`](../examples/synthetic_predictions.json)。顶层为 `format`、`dataset_id`、`kind`、声明完整覆盖的 `tasks` 和 `records`。每篇有唯一字符串 `id`、完整模型输入 `text`、`graph.entities` 与 `graph.relations`；预测 `status` 可为 `complete` 或 `failed`。节点 ID 仅用于关联同篇图中的关系，并不参与跨图匹配。

每个实体有 `id`、`label`、`name`；四层任务还需：

- `mentions` 列表，每个 mention 有 `id`、`section`、`start`、`end`、`text`。默认 `section: "text"` 使用整篇 `text`；若按标题/摘要分别标注，可在记录中增加 `sections: {"title": "...", "abstract": "..."}`。下标是相应部分的 **Python Unicode 字符位置，左闭右开**，必须与原文切片完全一致，不是 UTF-8 字节数或 JavaScript UTF-16 偏移。
- `concept_id` 是预先约定词表中的稳定概念标识；不能用每篇生成的实体 ID 代替。只在 NEL/C-RE 需要。
- 关系的 `source`、`target` 是节点 ID，`relation` 是标签。M-RE 的端点若各自恰有一个 mention 可以省略 `source_mention` / `target_mention`；某端有多个 mention 时，必须明确写出该端选中的 mention ID。C-RE 不要求关系绑定具体 mention。

多轮运行或人工支持率不会自动处理盲测设计、审稿仲裁、同义词表版本或人工证据真伪。需要人的裁决、稳定概念库或模型专用 oracle 接口尚未准备好时，[`pending.py`](pending.py) 中的函数会明确报 `NotImplementedError`，不会悄悄返回空结果。

## 检查

```bash
python -m unittest discover -s benchmarks/tests -v
```
