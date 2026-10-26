# 当前文章筛选结果简要抽样审计

审计日期：2026-08-25

checkpoint 快照：2026-08-24 22:25（Asia/Singapore）

本报告沿用 [`gpt56_luna_article_screening_audit_50000.md`](gpt56_luna_article_screening_audit_50000.md) 的基本逻辑：只从严格验证通过的结果中按模型决策分层抽样，重新阅读标题、完整摘要和候选事实，再给出人工 KEEP / REVIEW / DROP。为保持简短，本次只审计 55 条。

**主要结论：当前 Gemini/v3 批次的 KEEP 和 REVIEW 样本整体可靠，但 DROP 出现明显漏召回。25 条 Embase DROP 中，12 条应 KEEP、4 条应 REVIEW，只有 9 条可维持 DROP。最突出的错误是把“研究疗效”整体视为不可抽取，从而遗漏当前 schema 明确允许的 `Symptom relieved_by Treatment/Medication`。因此，当前 DROP 不宜直接删除。**

## 当前运行状态

当前 checkpoint 为 `data/treatment_related_articles/filtering/gpt56_luna_article_screening_checkpoint.jsonl`。按每个索引的最新一次 attempt 去重：

| 项目 | 数量 |
| --- | ---: |
| 全 checkpoint 已尝试 | 125,967 |
| 全 checkpoint 严格有效 | 107,018 |
| 当前 Gemini attempts | 67,034 |
| 当前 Gemini 严格有效 | 51,713 |
| Gemini 完成但验证失败 | 15,217 |
| Gemini JSON 解析失败 | 4 |
| Gemini API 请求失败 | 100 |

Gemini 的 51,713 条严格有效结果包括 27,725 KEEP、23,154 DROP 和 834 REVIEW。

15,217 条“完成但验证失败”主要是输出包装问题：15,176 条在 JSON 外带了 Markdown JSON 代码围栏，其中 15,150 条除此之外没有内容校验错误；真正带字段、schema 或证据片段错误的只有 67 条，且与代码围栏记录有 26 条重叠。因此大部分可本地去除围栏后恢复，无需重新请求 API。审计时没有筛选进程在运行。

另一个操作层问题是 checkpoint 已经混合模型：文件名和首行 metadata 仍写 `gpt-5.6-luna`，但当前 runner 及新增 attempt 使用 `gemini-3.7-flash`；其中还混合了 v2、v3.0.0-draft.1 和 v3.0.0-draft.2。后续统计应以每条 attempt 的 `model` 和 `output.schema_version` 为准。

## 抽样方法

使用固定随机种子 `20260825`，从严格有效结果中按来源和模型决策分层抽取：

| 来源 | 模型 / schema | DROP | KEEP | REVIEW | 合计 |
| --- | --- | ---: | ---: | ---: | ---: |
| Embase | Gemini 3.7 Flash / v3.0.0-draft.2 | 25 | 16 | 4 | 45 |
| Cochrane | GPT-5.6 Luna / v2.0.0-draft.2 | 5 | 4 | 1 | 10 |
| 合计 | — | 30 | 20 | 5 | 55 |

当前处理到的最大索引为 `126269`，尚未进入从 `128701` 开始的 PubMed 区段，因此本次没有可审计的 PubMed 筛选结果。Cochrane 与 Embase 使用不同模型和 schema，下面分别报告，不能合并成单一模型准确率。抽样也有意提高了 DROP 和 Cochrane 的比例，不代表全量来源或决策分布。

本次只读取现有文章和 checkpoint，没有发送 API 请求。人工标签属于单人质量审计，不是正式 gold standard。

## 语义复核结果

### 当前 Gemini/v3 Embase 样本

单元格为“人工 KEEP / REVIEW / DROP”。

| 模型决策 | 人工复核 | 结论 |
| --- | ---: | --- |
| DROP（25） | **12 / 4 / 9** | 16/25（64.0%）不宜直接过滤 |
| KEEP（16） | **16 / 0 / 0** | 16/16 决策可维持 |
| REVIEW（4） | **0 / 4 / 0** | 4/4 保留到复核合理 |

25 条 DROP 中“不应过滤”的点估计为 64.0%，Wilson 95% 区间为 44.5%-79.8%。样本较小，不能直接投影成全量错误篇数，但足以说明当前 DROP 存在系统性风险。

### 旧 Luna/v2 Cochrane 样本

| 模型决策 | 人工 KEEP | 人工 REVIEW | 人工 DROP |
| --- | ---: | ---: | ---: |
| DROP（5） | 0 | 0 | 5 |
| KEEP（4） | 3 | 1 | 0 |
| REVIEW（1） | 0 | 1 | 0 |

该小样本中 9/10 精确决策一致，10/10 的“保留/过滤”方向一致。唯一分歧是索引 `122`：两项很小且证据质量很低的试验中报告了药物组更常见的不良反应，直接泛化为 `common_side_effects` 偏强，更适合 REVIEW。

## 发现的主要问题

### 1. DROP 系统性忽略 `relieved_by`

当前 prompt 只禁止把一般疗效自动转成“推荐”或“适应证”，并没有禁止直接抽取症状缓解关系。以下模型 DROP 都有较清楚的 `relieved_by`：

- `68766`：MORE 显著降低 pain severity，可支持 `pain severity relieved_by MORE`。原文："Participants in MORE reported significantly greater reductions in pain severity by posttreatment (p = .03) and opioid misuse risk by 3-month follow-up (p = .03) and significantly greater increases in positive psychological health (p <.001) than SG participants."
- `76074`：系统综述结论明确称 ginseng herbal formulas 改善 fatigue severity。原文："Ginseng herbal formulas improved fatigue severity compared to controls, especially among patients with CF, but with a small effect size."
- `91094`：在线疼痛管理项目改善 pain intensity 和 depression。原文："There were significant improvements in pain intensity (11 studies, 1397 participants, SMD −0.30, 95% CI −0.50 to −0.10, p = 0.004), health-related quality of life (eight studies, 1054 participants, SMD 0.41, 95% CI 0.08 to 0.75, p = 0.02), and depression (nine studies, 1283 participants, SMD −0.32, 95% CI −0.55 to −0.08, p = 0.008)."
- `122107`：ACT/TEAM 对 anxiety 和 depression 有显著改善。原文："The results showed significant interaction effects for both ACT and TEAM compared with Control in anxiety (ACT [p < 0.05]; TEAM [p < 0.001]), depression (ACT [p < 0.001]; TEAM [p < 0.001]) and general well-being (ACT [p < 0.05]; TEAM [p < 0.001])."

这些记录的模型理由高度相似，均把“试验或 Meta 分析的疗效结果”整体判为无 schema 事实，说明这是规则理解偏差，不只是零散错误。

### 2. 仍会漏掉明确工具或治疗用途

- `68197`：CDRS-R 和 CGI-BP-S 在 bipolar depression 患者中的评估目标足够明确，至少存在 Assessment Scale 候选。原文："Efficacy analyses included change from baseline to week 6 in Children Depression Rating Scale, Revised (CDRS-R) score (the primary outcome), and Clinical Global Impressions, Bipolar Severity of Depression Score (CGI-BP-S), using mixed model for repeated measures (MMRM) analysis."
- `53288`：BPT 被直接称为儿童 ADHD 的 evidence-based treatment。原文："Behavioral parental training (BPT) and stimulant medication are evidenced-based treatments for children with ADHD."
- `88528`：perampanel 被明确描述为在临床实践中用于 focal/generalised seizures，并汇总了多项临床实践研究中的常见不良反应。原文："Adolescent patients (aged ≥12 - <18 years) treated with PER for focal or generalised seizures were identified from an interim pooled analysis of data from 18 clinical practice studies/work groups."；"AEs were reported for 53.8% of patients; most common AEs were behavioural (aggression/anger/irritability; 25.3%), dizziness/vertigo (17.6%) and somnolence (12.1%)."

### 3. KEEP 决策较稳，但候选事实仍需语义校验

本次 16 条 Gemini KEEP 都应保留，不过个别候选并非最佳表达。例如 `80384` 把 hepatic inflammation 标成 Symptom 仍有类型争议，但同一句的 `Disease.definition` 足以支持 KEEP；`60624` 的 `commonly_affects` 表达略生硬，但 depression 的流行病学属性有直接证据。严格格式验证无法发现这类候选语义问题。

## 简要建议

1. 暂时不要不可逆删除当前 Gemini DROP；优先对包含 `improved`、`reduced`、`relieved`、`decreased` 等症状改善断言的 DROP 做二次复核。
2. 在 prompt 中明确补一句：研究结局不能自动建立推荐或适应证，但当原文直接报告某 Medication/Treatment 缓解某 Symptom 时，可以支持 `relieved_by`。
3. 对 15,150 条仅有 JSON 代码围栏的问题先做本地恢复，不要付费重跑。
4. 后续按模型和 schema 使用独立 checkpoint/output 名称；等处理进入 PubMed 后，再做一次 Cochrane、Embase、PubMed 三来源分层复核。

<details>
<summary>本次 55 条样本索引</summary>

- Cochrane DROP：88, 225, 420, 553, 683
- Cochrane KEEP：7, 122, 294, 416
- Cochrane REVIEW：454
- Embase DROP：53288, 63481, 65520, 66141, 67811, 68197, 68766, 75086, 76074, 76994, 80535, 85120, 85647, 88528, 89217, 91094, 91873, 99197, 100669, 102610, 106119, 118233, 119838, 120606, 122107
- Embase KEEP：60624, 61989, 69907, 80384, 81825, 87570, 93202, 94576, 96881, 102826, 104075, 109273, 112789, 119840, 121257, 123059
- Embase REVIEW：85178, 90254, 91908, 119506
- Embase 的 25 条模型 DROP 复核为 KEEP：53288, 68197, 68766, 76074, 76994, 80535, 85647, 88528, 89217, 91094, 100669, 122107
- Embase 的 25 条模型 DROP 复核为 REVIEW：65520, 85120, 99197, 118233
- Embase 的 25 条模型 DROP 维持 DROP：63481, 66141, 67811, 75086, 91873, 102610, 106119, 119838, 120606

</details>
