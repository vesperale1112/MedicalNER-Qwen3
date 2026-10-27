# MDIEC schema 与官方来源

整理日期：2026-10-26。

**官方定义已下载，位于 [补充材料 PDF](official_supplementary_information.pdf) 第 4–5 页（§2.1–2.2）。** 没有找到独立发布的完整 schema JSON / BRAT annotation.conf；这里的 JSON 是从本地标注整理的，不能冒充官方约束文件。

## 文件

| 文件 | 来源与用途 |
|---|---|
| [official_supplementary_information.pdf](official_supplementary_information.pdf) | 出版社原始补充材料；实体与关系定义见第 4–5 页，7 类关系与 2 类条件陈述见第 7 页 |
| [official_supplementary_information.txt](official_supplementary_information.txt) | 用 dev 环境 PyMuPDF 从上述 PDF 提取，附页码 |
| [observed_schema.json](observed_schema.json) | 本次从 946 个 `.ann` 统计的实际标签、数量、真实例子和观察到的端点类型组合；不是官方允许组合全集 |
| [official_ann2json_updated.py](official_ann2json_updated.py) | 作者仓库原始标注转换代码，仅供阅读，未执行 |
| [official_Triplets_refine_prompt.py](official_Triplets_refine_prompt.py) | 作者仓库原始三元组复核提示，仅供阅读，未执行；不是完整 schema |

## 本地数据到底是什么

`../MDIEC/` 有 946 对 `.txt/.ann`：`.txt` 是语料原文（论文摘要等文本，不是整篇论文 PDF 全文），`.ann` 是 BRAT 实体与关系标注，**不是模型预测结果**。共 28,660 个实体提及、10,560 条关系。

压缩包没有官方 train/dev/test 清单。因此这是下载包中的完整标注语料，不能称为“论文的全部测试集和测试结果”。论文描述复核 500 篇，与下载包的 946 对文件仍存在规模差异。

## 官方实体定义（中文概述）

| 官方名称 | 含义 |
|---|---|
| Health Factors | 影响健康问题发生可能性的行为、临床照护、社会经济及环境因素 |
| Anatomy | 器官、组织、细胞等身体结构 |
| Phenotype | 解剖、生理或体征上可观察、可测量的变化 |
| Sign | 检查或实验室检测得到的身体/器官功能与状态指标 |
| Method/Procedure | 研究、诊断、治疗、预防的方法与程序，也含相关学科和职业 |
| Physiology | 生物、分子和细胞功能，以及心理过程、器官和组织功能 |
| Gene/Protein | 基因及蛋白、酶、受体等相关实体 |
| Disease/Symptom | 疾病、损伤、病理、精神行为及其他异常或功能障碍 |
| Drug/Chemical | 药物、有机/无机化合物、激素、有害物质等 |

本地实际标签为：`Health_factors`, `region`, `symptom`, `signs`, `method`, `physiology`, `gene`, `disease`, `drug`。

**官方展示名称和文件标签并不完全相同，未找到逐项官方映射表。尤其不能只因名称就认定 `symptom` 等于补充材料中的 Phenotype，或将 `disease` 与 `symptom` 任意合并。** 原样保留标签，具体范围结合指南和真实标注核对。

## 关系定义与文件标签

下表对应关系是依据补充材料含义和本地标签名称整理的说明，不是作者另行发布的机器映射。

| 官方名称 / 本地标签 | 定义摘要 | 本地条数 |
|---|---|---:|
| Risk / `risk_factor_of` | 增加疾病发生概率或加重疾病进展的因素 | 1,205 |
| Diagnostic / `help_diagnose` | 有助于诊断的方法、特征或生物标志物 | 592 |
| Characteristic / `characteristic_of` | 疾病的症状、临床表现或特征，可涉及生理、生化、行为及遗传层面 | 719 |
| Association / `associated_with` | 存在关联，但不必然意味着因果 | 2,704 |
| Therapeutic / `treatment_for` | 治疗或干预与疾病/状态之间的联系，涵盖药物、心理、生活方式、手术等 | 1,260 |
| Hierarchical / `hyponym_of` | 同类实体的分类与层级关系 | 1,183 |
| Abbreviation / `abbreviation_for` | 缩写与完整术语之间的关系 | 1,114 |
| Occurs in / `occurs_in` | 补充材料第 7 页归为条件陈述；§2.2 未提供同等详细定义 | 1,260 |
| Located in / `located_in` | 补充材料第 7 页归为条件陈述；§2.2 未提供同等详细定义 | 523 |

这解释了为什么官方简介写 **7 类关系**，本地却有 **9 个关系标签**：另外两类在补充材料中单列为条件陈述。

BRAT 的 `Arg1`、`Arg2` 被作者转换代码分别读为 head、tail。`observed_schema.json` 保留这个顺序及真实例子；没有根据词义猜测对称性、全部合法端点类型或其他约束。

另需注意：下载的作者转换代码含跳过 `hyponym_of` 等标签的逻辑，不能将其默认处理后的任务直接当作原始包全部 9 标签评测。本次没有运行或修改作者代码。

## 原始来源

- [Zenodo 数据页](https://zenodo.org/records/10960357)
- [论文](https://doi.org/10.1038/s41467-025-62781-z)
- [出版社补充材料原始下载](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-025-62781-z/MediaObjects/41467_2025_62781_MOESM1_ESM.pdf)
- [作者仓库](https://github.com/MonsterTea/MDKG)，本次读取版本：`b6b745aa3789cca430240489151826e9a2b21e41`。
- [标注转换代码来源](https://github.com/MonsterTea/MDKG/blob/b6b745aa3789cca430240489151826e9a2b21e41/NER%26RE_model/SynSpERT/ann2json_updated.py)
- [三元组复核提示来源](https://github.com/MonsterTea/MDKG/blob/b6b745aa3789cca430240489151826e9a2b21e41/Triplets_refine_prompt.py)
