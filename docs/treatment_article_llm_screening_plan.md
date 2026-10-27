# 治疗相关文章的精神疾病领域复筛

## 目标

本步骤只修正首轮结果中的领域误保留：候选事实虽然有原文证据并符合通用医疗 schema，但实际属于躯体疾病或非精神科神经系统内容，不应进入精神疾病知识图谱。

它不是第二次完整筛选，也不负责重新抽取知识图谱、判断全部 relation/property、评价研究质量或裁决疗效证据。通过领域复筛的文章随后再进入完整抽取和证据校验。

40 篇人工复查见[三位人工评审与原模型结果对照](../data/treatment_related_articles/screening_review_40/treatment_review_analysis.md)。人工标签只读取三份文件各自的 `reviewer_decision`；随文件重复保存的 `model_decision` 不是人工意见。人工一致性和多数意见用于定位错误模式，不作为金标准。

## 输入范围

从 `gpt56_luna_article_screening_checkpoint.jsonl` 按 `index` 保留最后一次 attempt，只选择：

- `valid_output == true`；
- 首轮决策为 `KEEP` 或 `REVIEW`。

首轮 `DROP` 暂不进入本轮。运行脚本时如果提供 `--review-file`，只使用其中的 `article_index` 限定测试样本，不读取或发送人工决策与备注。

当前 checkpoint 共 252,502 个最终索引，其中有效 `KEEP` 136,841 篇、有效 `REVIEW` 8,575 篇，因此本轮全量候选池为 145,416 篇。40 篇人工复查样本中有 21 篇进入该候选池。

## 两阶段流程

### 第一阶段：候选事实的领域门控

模型只接收标题、原 schema 版本、已有候选及其 `evidence_quote`，不接收完整摘要、首轮判断理由或人工标签。

- `KEEP`：至少一个已有候选明确属于精神疾病或直接服务于精神心理临床诊疗；模型用类型和数组下标选择该候选，不改写内容。
- `READ_ABSTRACT`：候选为空、全都属于范围外、只有关键词相关，或仅凭候选无法确定。

第一阶段不能输出 `DROP`。现有候选不合格不能证明完整摘要没有其他合格内容。

### 第二阶段：完整摘要的领域门控

只对 `READ_ABSTRACT` 的文章读取 `articles.json` 中的完整标题和摘要，输出：

- `KEEP`：摘要包含实质性的精神疾病或精神心理临床诊疗内容；
- `REVIEW`：完整摘要仍留下具体的领域边界歧义；
- `DROP`：全文只涉及范围外内容，或精神心理词语仅是偶然共现/附带测量。

第二阶段只返回 `decision` 和简短 `reason`，不生成候选关系或属性。协议、阴性试验和缺少疗效结果本身都不是领域排除理由；这些问题留给后续抽取与证据审核。

## 领域口径

保留两类内容：

1. DSM-5 精神障碍、与之直接对应的精神科疾病，以及有明确临床定义的精神心理综合征。
2. 针对上述疾病或综合征的精神科/心理临床诊断、评估、治疗、预防、预后或治疗安全性。是否映射到 DSM-5 不能单独决定去留。

判断对象是事实的实际疾病和临床目的，不是关键词。以下内容默认不纳入：

- 单纯躯体疾病或非精神科神经系统疾病；
- 疼痛、疲劳、运动功能、性功能；
- 普通情绪、一般困扰、应对方式或宽泛心理概念，但没有与精神障碍及其临床诊疗建立直接联系；
- 药物的非精神科适应证；
- 只作为躯体研究附带变量的心理量表、筛查或症状词；
- 仅有宽泛癌症心理关注，但没有连接到认可的精神障碍、临床定义明确的精神心理综合征或其诊疗。

躯体疾病文章并非一律排除。如果其中有直接且实质性的精神疾病临床事实，仍可保留；精神科治疗安全性也可以涉及躯体不良结局。

## 输出与恢复

第一阶段 `KEEP` 的输出保留所选原候选、数组位置和 `source_schema_version`，仅用于说明领域判断依据；它不是迁移后的新图谱。第二阶段只保存领域决策。

每个响应立即写入 checkpoint。正常流程每篇最多两次请求；失败不自动重试，`--retry-failed` 只重试失败的阶段。未完成或失败记录不会被当作 `DROP`。修改 prompt 或阶段语义后应使用新的 checkpoint；脚本的 stage 标识会拒绝旧策略的 checkpoint。

`api_requests`、`usage_by_phase` 和 `usage` 统计实际请求及服务返回的 token 使用量。默认模型为 `gpt-6-luna`，密钥优先读取 `XI_AI_API_KEY`。

## 运行

在仓库根目录预览人工复查样本中属于首轮有效 `KEEP/REVIEW` 的文章：

```bash
python data/treatment_related_articles/filtering/run_treatment_article_rescreening.py \
  --workers 3 \
  --review-file data/treatment_related_articles/screening_review_40/treatment_article_review_DHY.json \
  --checkpoint data/treatment_related_articles/filtering/treatment_article_domain_rescreen_gpt6_luna_pilot21_checkpoint.jsonl \
  --output data/treatment_related_articles/filtering/treatment_article_domain_rescreen_gpt6_luna_pilot21.json \
  --preview
```

去掉 `--preview` 后才会调用 API。`--review-file` 只是用一份导出取得这组 40 篇的共同 `article_index`；人工对照分析仍必须同时读取三份 JSON。去掉 `--review-file` 可处理全部首轮有效 `KEEP/REVIEW`；`--max-samples N` 可限制预运行规模。

## 验证与后续

工程测试覆盖最后 attempt 选择、候选/摘要分流、第一阶段禁止 `DROP`、第二阶段才允许 `DROP`、空候选直达摘要、候选原样保留、断点续跑、显式失败重试、输入文件保护和 token/request 汇总：

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover \
  -s tests -p test_treatment_article_rescreening.py -q
```

复筛通过后再执行完整图谱抽取、schema 校验、原文证据核对和争议裁决。不要在领域复筛中重复这些工作。
