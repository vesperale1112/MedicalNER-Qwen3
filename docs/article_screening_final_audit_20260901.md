# 治疗相关文章筛选最终结果综合审计

审计日期：2026-09-01

审计对象：

- `data/treatment_related_articles/filtering/gpt56_luna_article_screening_checkpoint.jsonl`
- `data/treatment_related_articles/filtering/gpt56_luna_article_screening.json`
- `data/treatment_related_articles/articles.json`

本报告整合此前前 50,000 条 Luna/v2 审计、50 条 Luna/v3 试跑审计、2026-08-25 混合 checkpoint 审计，并增加最终全量结果统计和一轮新的 Gemini/v3 Embase/PubMed 分层抽样。报告可独立阅读；人工复核均为单人质量审计，不是双人标注并仲裁后的正式 gold standard。

## 结论摘要

1. **技术流程已经完整结束。** 252,502 个索引连续覆盖 `0..252501`，最新 checkpoint 全部为 `completed`，final JSON 与每个索引的最新 `output` 逐条比较后差异为 0。
2. **格式有效不等于语义正确。** validator 能检查 JSON、schema、允许的类型组合和原文 span，但不能发现漏掉的关系、错误实体语义、过度泛化或不恰当的 DROP。
3. **最稳定的语义风险仍是 DROP 漏召回。** 旧 Luna/v2 审计中 34/150 DROP 应 KEEP 或 REVIEW；2026-08-25 Gemini/Embase 审计中为 16/25；本次新抽样中为 10/20。各次样本、模型和 prompt 不同，比例不能直接合并或外推，但方向一致：DROP 不适合不可逆删除。
4. **KEEP/REVIEW 的“是否保留”方向较稳。** 本次 16 条 KEEP 全部维持 KEEP，4 条 REVIEW 全部维持 REVIEW；但部分候选事实仍存在类型或论元表达不够准确的问题，进入 KG 前仍需语义校验。
5. **final output 混合了三个 schema 世代。** v2.0.0-draft.2、v3.0.0-draft.1 和 v3.0.0-draft.2 分别有 47,597、7,708 和 197,197 条。下游不能假定所有记录遵循同一套关系和属性定义。

## 最终文件状态

| 项目 | 数量 |
| --- | ---: |
| 原始文章 | 252,502 |
| 最新 completed | 252,502 |
| 最新 validation/request/parse error | 0 |
| KEEP | 136,841 |
| REVIEW | 8,575 |
| DROP | 107,086 |
| KEEP + REVIEW | 145,416（57.59%） |
| checkpoint attempt 记录 | 256,595 |
| 被后续 attempt 覆盖的旧记录 | 4,093 |

checkpoint 为 446,627,683 bytes，包含运行 metadata、全部历史 attempts、模型、时间、raw response、usage 和 validation 信息。final JSON 为 139,013,706 bytes，只保留按 index 排序的最新 `{index, output}`。final 共 252,502 条，逐条与 checkpoint 最新 output 比较，未发现不一致。

final JSON 包含 KEEP、REVIEW 和 DROP，并不是仅保留文章的列表；模型来源也没有写入 final。需要追踪模型、重试历史或人工修复来源时，仍应保留 checkpoint。

## 数据来源与模型/schema 构成

| 来源 | DROP | KEEP | REVIEW | 合计 |
| --- | ---: | ---: | ---: | ---: |
| Cochrane | 138 | 648 | 10 | 796 |
| Embase | 53,651 | 70,732 | 3,522 | 127,905 |
| PubMed | 53,297 | 65,461 | 5,043 | 123,801 |
| 合计 | **107,086** | **136,841** | **8,575** | **252,502** |

| 最新模型 / schema | 数量 | 主要来源 |
| --- | ---: | --- |
| GPT-5.6 Luna / v2.0.0-draft.2 | 47,597 | Cochrane、Embase |
| GPT-5.6 Luna / v3.0.0-draft.1 | 7,708 | Embase |
| Gemini 3.7 Flash / v3.0.0-draft.2 | 197,197 | Cochrane、Embase、PubMed |

checkpoint 文件名和首行 metadata 仍记录最初的 `gpt-5.6-luna` 与 v2 schema，不能代表全部最新结果。准确 provenance 必须以每个 index 的最新 attempt 中的 `model` 和 `output.schema_version` 为准。

## 技术问题与最终处理

全量首次完成时有 205,557 条 valid、46,945 条 `completed_with_validation_errors`。其中 43,374 条只是 Gemini 在合法 JSON 外添加了标准 Markdown JSON 围栏，本地去除围栏后无需重新请求。后续处理过程如下：

| 阶段 | 剩余 invalid | 主要情况 |
| --- | ---: | --- |
| 全量首次结束 | 46,945 | 43,374 条标准围栏；其余为真实或非标准错误 |
| 首次本地恢复后 | 3,571 | 对剩余记录发起定向 retry |
| retry 3,571 后 | 1,346 | 1,273 条再次仅有围栏，73 条真实 span 错误 |
| 本地恢复 1,273 后 | 73 | 定向 retry |
| retry 73 后 | 56 | 17 条仅围栏，39 条真实错误 |
| 本地恢复 17 后 | 39 | 定向 retry |
| retry 39 后 | 36 | 5 条仅围栏，31 条字段验证错误 |
| 最终本地裁决 | 0 | 5 围栏、20 反斜杠、3 大小写、8 人工修正 |

持续失败并不都代表模型语义错误。20 条来自原始数据中的字面转义字符，例如模型自然输出 `[PHQ-9]`、`BP>140/90`，而输入保存为 `\[PHQ-9\]`、`BP\>140/90`；另有 3 条仅为大小写差异。最后 8 条非机械问题逐条对照原文修正，其中 OCR 栏位交错的 `26215` 改为 `REVIEW_INCOMPLETE_OR_CORRUPTED_TEXT`，其余修正为连续原文 span 或更准确的论元。

这说明：

- 标准 JSON 围栏应作为兼容性包装处理，不能当作语义错误；
- exact-span validator 会受到上游反斜杠、控制字符、OCR 拼接和大小写影响；
- 本地恢复只能处理可证明等价的包装或字符差异，不能把真实 schema/span 错误直接标为 valid；
- 最终 100% structural valid 不能解释为 100% semantic accuracy。

## 历史语义审计汇总

### Luna/v2 前 50,000 条：275 条分层样本

固定种子 `20260804`，将 `0..49999` 分为五个 10,000 段，每段抽取 30 DROP、20 KEEP、5 REVIEW。复核矩阵为“人工 KEEP / REVIEW / DROP”。

| 模型决策 | 人工复核 | 主要结论 |
| --- | ---: | --- |
| DROP（150） | 18 / 16 / 116 | 34/150（22.7%）不应不可逆过滤 |
| KEEP（100） | 92 / 4 / 4 | 96/100 仍应保留 |
| REVIEW（25） | 4 / 21 / 0 | 25/25 都值得保留 |

最主要漏检是把临床量表、问卷或评分工具视为“只是研究结局”，遗漏工具与疾病/症状间的评估关系。KEEP 的主要问题是把试验目的当适应证、把小样本不良事件泛化为通用副作用、把队列严重程度当疾病亚型，以及把风险标志误作疾病症状。

### Luna/v3.0.0-draft.1：连续 50 条试跑

索引 `50000..50049` 全部逐条复核：

| 模型决策 | 人工 KEEP | 人工 REVIEW | 人工 DROP |
| --- | ---: | ---: | ---: |
| KEEP（33） | 31 | 0 | 2 |
| REVIEW（8） | 2 | 6 | 0 |
| DROP（9） | 1 | 1 | 7 |

精确决策一致 44/50（88.0%），保留/过滤一致 46/50（92.0%）。主要新问题是 `Etiology` 与 `Risk` 混淆、把 Newcastle-Ottawa Scale 等研究质量工具当作临床量表，以及让通用 `Evidence.study_type` 单独触发 KEEP。5 条格式失败均为非连续或改写后的 evidence quote。

### 2026-08-25 混合 checkpoint：55 条来源分层样本

| 子样本 | 模型决策 | 人工 KEEP / REVIEW / DROP |
| --- | --- | ---: |
| Gemini/v3 Embase | DROP（25） | 12 / 4 / 9 |
| Gemini/v3 Embase | KEEP（16） | 16 / 0 / 0 |
| Gemini/v3 Embase | REVIEW（4） | 0 / 4 / 0 |
| Luna/v2 Cochrane | DROP（5） | 0 / 0 / 5 |
| Luna/v2 Cochrane | KEEP（4） | 3 / 1 / 0 |
| Luna/v2 Cochrane | REVIEW（1） | 0 / 1 / 0 |

Gemini/Embase 的主要错误是把 RCT 或 meta-analysis 中的疗效结论整体视为不可抽取，从而遗漏明确的 `Symptom relieved_by Treatment/Medication`。这轮审计后，prompt 增加了精简的 Tool、Risk-factor、Treatment-effect 和 Use/indication 边界，但最终新抽样表明漏召回仍未完全消失。

### 历史代表案例

为保留旧报告中最重要的证据，以下案例仍应作为回归检查点：

- `3071`、`15090`、`16613`、`26648`：PCL-5、PHQ-8/9、BDI、HAM-D 等量表与目标症状/疾病关系明确，却因“只是试验结局”被 DROP。
- `13323`：试验仅评估 SPN-812 治疗 ADHD 的效果，模型却把研究目的当成既定 Medication.indication。
- `27590`：把与术后谵妄相关的 EEG waveform suppression 误标为谵妄症状。
- `32023`：把 14 名健康志愿者单剂量 PK 研究中的不良事件泛化为通用 common side effects。
- `40079`：把研究入组的 `mild to moderate` 严重程度当成 OSA 疾病 subtype。
- `50039`：空气污染暴露与 ASD 风险的 meta-analysis 结果被 DROP；按 v3 应使用 `Etiology contributes_to Disease`。
- `50046`：Newcastle-Ottawa Scale 是研究质量工具，不是临床 `Assessment Scale`。
- `68766`、`76074`、`91094`、`122107`：明确报告 pain、fatigue、depression 或 anxiety 改善，却因属于 RCT/meta-analysis outcome 被 DROP。
- `88528`：perampanel 的临床用途和常见不良反应均有直接文本支持，但被当作普通研究描述漏掉。

历史指标分别基于当时的 v2、v3 draft.1 或 v3 draft.2 prompt/schema，不能把它们当作同一模型同一任务上的纵向 accuracy 曲线。

## 最终结果新抽样

### 方法

使用固定种子 `20260901`，只从最终结果中最新的 Gemini 3.7 Flash / v3.0.0-draft.2 记录抽样，以补充旧审计缺少的 PubMed，并与 Embase 对照：

| 来源 | DROP | KEEP | REVIEW | 合计 |
| --- | ---: | ---: | ---: | ---: |
| Embase | 10 | 8 | 2 | 20 |
| PubMed | 10 | 8 | 2 | 20 |
| 合计 | 20 | 16 | 4 | 40 |

逐条阅读标题、完整摘要、decision、全部 candidate 和 evidence。该设计有意提高 DROP 与 REVIEW 的比例，因此不代表全量自然分布，也不能将样本比例直接乘到全语料。

### 决策复核结果

| 来源 | 模型决策 | 人工 KEEP | 人工 REVIEW | 人工 DROP |
| --- | --- | ---: | ---: | ---: |
| Embase | DROP（10） | 3 | 3 | 4 |
| Embase | KEEP（8） | 8 | 0 | 0 |
| Embase | REVIEW（2） | 0 | 2 | 0 |
| PubMed | DROP（10） | 3 | 1 | 6 |
| PubMed | KEEP（8） | 8 | 0 | 0 |
| PubMed | REVIEW（2） | 0 | 2 | 0 |
| 合计 | DROP（20） | **6** | **4** | **10** |
| 合计 | KEEP（16） | **16** | **0** | **0** |
| 合计 | REVIEW（4） | **0** | **4** | **0** |

20 条 DROP 中有 10 条应 KEEP 或 REVIEW，点估计为 50.0%，Wilson 95% 区间为 29.9%-70.1%。Embase 为 6/10，PubMed 为 4/10；来源样本都很小，但足以说明漏召回并非只出现在 Embase。

本次精确决策一致为 30/40（75.0%）；保留/过滤方向一致也是 30/40。该数字被刻意过采样的 DROP 显著影响，不应当作全量 accuracy。

### 新发现与代表案例

#### 1. DROP 仍会遗漏明确症状缓解或治疗事实

- `53353`：NYU Summer Program for Kids 被直接描述为 effective、evidence-based，并能减少 negative behaviors；模型仍因“general efficacy”而 DROP。
- `98609`：meta-analysis 给出 MBTs 对 ADHD inattention 和 hyperactivity/impulsivity 的效应量，并总结可能减少 ADHD symptoms；至少应 REVIEW。
- `110208`：背景直接称 dementia psychosocial interventions 能减少 stress、增强 well-being；即使正文是 review protocol，该背景断言仍可能支持 `relieved_by`。

prompt 已明确“RCT/meta-analysis 中直接报告某治疗缓解某症状可以支持 `relieved_by`”，但模型仍偶尔只看文章研究设计而忽略具体句子。

#### 2. 临床量表/工具漏检仍然存在

- `81514`：MDRS、MMSE、Telephone Interview of Cognitive Status 和 Trail Making Tests 被用于认知结局，模型以“RCT outcomes”整体 DROP。
- `187421`：Motor Status Scale 明确用于 upper-limb motor status，仍被视为单纯 feasibility outcome。

这与 Luna/v2 前 50,000 条的 `assesses_for` 漏检属于同一模式：工具作为试验结局并不会自动失去可复用的评估目标。

#### 3. 药物不良结局和风险事实会被当作普通 trial outcome

- `184792`：组合 RAAS inhibitor therapy 的 AKI incidence 显著更高，原试验还因 AKI events 提前停止；存在 `Medication causes_side_effect Disease` 候选，模型 DROP 过强。
- `96490`：lithium、sertraline 或联合治疗与 mood switch 的发生率被直接评估，但是否足以泛化为通用副作用仍需 REVIEW，不宜直接 DROP。
- `221136`：radiotherapy 被明确称造成持续 sebaceous gland damage，heparinoid moisturizer 可防止 water loss；至少存在可复核的病因或症状缓解候选。

#### 4. KEEP 决策稳定，但候选表达不一定最优

本次 16 条 KEEP 均应保留，但至少有三类候选层问题：

- `86240` 把机构名称 `National Institute for Health and Care Excellence (NICE)` 直接标成 `Guideline`；推荐事实存在，但 source 实体并不是可识别的指南文档。
- `128866` 的 KEEP 有 `disability relieved_by Cerebrolysin` 支持，但另一条把 NIHSS 表达成“evaluates stroke”，不如“测量神经功能缺损/严重程度”精确。
- `216867` 用泛称 `intervention` 作为 Treatment target；关系方向正确，但应优先使用可识别的 `executive function training (EFT)`。

因此，decision audit 不能替代 candidate-level KG 审计。

#### 5. REVIEW 仍是有用的安全出口

本次 4 条 REVIEW 均维持 REVIEW：`81523` 的“recommend avoiding”是否等同 contraindication、`90213` 的摘要拼接污染、`204217` 的新诊断 T1D 与 suicidal ideation 关联，以及 `252032` 的 antiplatelet therapy 与 dementia risk 均有真实但不宜强行确定的歧义。

## 综合问题清单

| 问题 | 影响 | 是否被格式 validator 发现 |
| --- | --- | --- |
| JSON Markdown 围栏 | 大量假 validation error | 是 |
| 上游 `\>`、`\[` 等字面转义 | exact-span 假失败 | 是 |
| evidence 改写、使用省略号、非连续拼接 | 候选不可追溯 | 是 |
| 量表/问卷作为 outcome 时被忽略 | DROP 漏召回 | 否 |
| RCT/meta-analysis 症状改善被整体忽略 | DROP 漏召回 | 否 |
| 试验目的被当作适应证 | KEEP 过度保留 | 否 |
| 单研究不良事件被泛化为通用副作用 | KEEP 过度保留 | 否 |
| Etiology 与 Risk 混淆 | 实体类型和方向错误 | 通常否 |
| 研究质量工具被当作临床量表 | 实体语义错误 | 否 |
| 泛称或代词作为 source/target | 候选难以复用 | 通常否 |
| checkpoint 混合模型/schema | 下游兼容风险 | 不适用 |

## 使用建议

1. **不要把 DROP 直接作为不可逆删除。** 更适合将其视为低优先级队列；对含明确量表、`improved/reduced/relieved`、治疗相关风险或“evidence-based/first-line/used to treat”等句式的 DROP 做规则救援或二次复核。
2. **KEEP 可用于文章保留，但候选事实进入 KG 前应再做 candidate-level validation。** 至少检查实体语义、关系方向、论元是否可识别、证据是否自包含，以及是否把队列观察过度泛化。
3. **REVIEW 应完整保留。** 历次审计中 REVIEW 很少出现明确应 DROP 的案例，是合理的安全出口。
4. **下游先处理 schema 世代。** v2、v3 draft.1 和 v3 draft.2 不宜直接当作同构候选合并；应按 `schema_version` 分支消费或先做显式迁移。
5. **保留 checkpoint。** final JSON 适合下游读取，但没有模型 provenance、raw response、usage、重试和人工修复信息。
6. **正式质量指标需要独立 gold set。** 建议建立 300-500 条、覆盖 Cochrane/Embase/PubMed、由双人标注并仲裁的数据，重点增加 DROP、量表、治疗效果、适应证、副作用、风险因素和研究质量工具边界。

## 新抽样索引与人工标签

<details>
<summary>展开查看 40 条可复现样本</summary>

- Embase 模型 DROP -> 人工 KEEP：53353, 81514, 110208
- Embase 模型 DROP -> 人工 REVIEW：80060, 96490, 98609
- Embase 模型 DROP -> 人工 DROP：92962, 114063, 119693, 122317
- Embase 模型 KEEP -> 人工 KEEP：65266, 74300, 86240, 91388, 93240, 97928, 100990, 123862
- Embase 模型 REVIEW -> 人工 REVIEW：81523, 90213
- PubMed 模型 DROP -> 人工 KEEP：184792, 187421, 221136
- PubMed 模型 DROP -> 人工 REVIEW：222326
- PubMed 模型 DROP -> 人工 DROP：144801, 158924, 195101, 201160, 216704, 232964
- PubMed 模型 KEEP -> 人工 KEEP：128866, 136924, 179580, 198235, 216867, 222535, 247695, 251152
- PubMed 模型 REVIEW -> 人工 REVIEW：204217, 252032

</details>
