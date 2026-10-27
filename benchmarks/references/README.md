**本次仓库梳理与 benchmark 调研，2026-10-26**

- [仓库当前训练路线、数据、实验结果及瓶颈](../docs/repo_training_review.md)
- [八篇论文的评测方法，以及适合本项目的 benchmark 方案](../docs/benchmark_review.md)

2026-10-26 调研时仅在原 `temp/benchmark_20261026/` 新增阅读资料、提取文本、公开语料与说明。2026-10-27 将论文及提取文本迁入本目录，将方案迁入 `../docs/`、公开语料迁入 `../datasets/public/mdiec/`。性能数字来自仓库截至 2026-10-19 的报告，未重跑训练/推理；benchmark 方案尚未执行。

八篇 PDF 均已用 dev 环境中的 PyMuPDF 打开并提取为同名 `.txt`。`txt` 中的 `--- PAGE n ---` 为 PDF 文件的页序，便于定位。

| 文件 | 论文 | PDF 页数 | 下载来源 |
|---|---|---:|---|
| [mdkg_2025.pdf](mdkg_2025.pdf) | MDKG / mental health exploration，Nature Communications 2025 | 16 | [Nature PDF](https://www.nature.com/articles/s41467-025-62781-z.pdf) |
| [gutbrainie_2026.pdf](gutbrainie_2026.pdf) | GutBrainIE，Findings of EACL 2026 | 19 | [ACL PDF](https://aclanthology.org/2026.findings-eacl.301.pdf) |
| [zero_shot_biomedical_re_2025.pdf](zero_shot_biomedical_re_2025.pdf) | End-to-end zero-shot biomedical RE，WASP 2025 | 12 | [ACL PDF](https://aclanthology.org/2025.wasp-main.6.pdf) |
| [biored_2022.pdf](biored_2022.pdf) | BioRED，2022 | 23 | [arXiv PDF](https://arxiv.org/pdf/2204.04263) |
| [text2kgbench_2023.pdf](text2kgbench_2023.pdf) | Text2KGBench，2023 | 15 | [arXiv PDF](https://arxiv.org/pdf/2308.02357) |
| [schema_constrained_2026.pdf](schema_constrained_2026.pdf) | Schema-Constrained Evaluation Framework，KG-LLM @ LREC 2026 | 8 | [会议 PDF](https://www.lrec-conf.org/proceedings/lrec2026/workshops/kgllm/pdf/2026.kgllm-1.21.pdf) |
| [redocred_2022.pdf](redocred_2022.pdf) | Re-DocRED，EMNLP 2022 | 16 | [ACL PDF](https://aclanthology.org/2022.emnlp-main.580.pdf) |
| [clinical_kg_2024.pdf](clinical_kg_2024.pdf) | Clinical KG from EMR notes，BioNLP 2024 | 23 | [ACL PDF](https://aclanthology.org/2024.bionlp-1.23.pdf) |

公开语料是 [MDIEC.zip](../datasets/public/mdiec/MDIEC.zip)，来自 [作者 Zenodo 记录](https://zenodo.org/records/10960357)，已直接解压到 [MDIEC/](../datasets/public/mdiec/MDIEC/)。当前包有 946 对 `.txt/.ann` 文件，9 类实体、9 个关系标签；论文“500 篇”与下载包规模有差异，且未附官方数据划分，不能未经确认就说是论文原评测版本。“7 类关系”与 9 个标签的区别已在[官方定义说明](../datasets/public/mdiec/MDIEC_schema/README.md)中解释。实际计数见 [MDIEC_inventory.json](../datasets/public/mdiec/MDIEC_inventory.json)。

`lrec2026.html` 保留官方会议页面，供核对论文元数据与下载地址。
