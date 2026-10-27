# KG benchmark

这里集中保存本项目知识图谱抽取 benchmark 的方案、阅读资料、20 篇人工试标和模型对照结果。2026-10-27 从 `temp/` 整理迁入；此次仅调整目录、构建路径和文档，没有重新训练或推理。

## 入口

- [Benchmark 方案](docs/benchmark_review.md)
- [当前训练路线及实验梳理](docs/repo_training_review.md)：2026-10-26 调研快照，代码及结果来源见文内引用。
- [论文与阅读资料索引](references/README.md)
- [20 篇人工试标选文](datasets/kg_pilot_20/kg_article_selection_20.json)
- [离线 KG 标注页](datasets/kg_pilot_20/pages/kg_annotation_20.html)
- [三人 KG 对照页](datasets/kg_pilot_20/pages/MedicalNER_三人知识图谱对照.html)
- [20 篇 GPT 抽取结果](predictions/kg_pilot_20_gpt61sol.json)
- [MDIEC 公开语料说明](datasets/public/mdiec/README.md)

训练路线文档引用的 `agent/` 和 `docs/audits/` 在本地保存的 `origin/main`（`ea6449c`）中可读，当前检出的 `main`（`0e6817d`）尚无这些文件。此次未切换或同步分支；这些代码引用在当前工作树中暂不能直接打开。

## 文件组织

| 目录 | 内容 |
|---|---|
| `docs/` | Benchmark 设计和训练路线梳理 |
| `references/` | 论文 PDF、PyMuPDF 提取文本和会议页面 |
| `datasets/kg_pilot_20/` | 选文清单、三份人工原始导出、离线页面 |
| `datasets/public/mdiec/` | 下载包、原生 BRAT 语料、schema 资料和盘点 |
| `tools/` | 标注页、对照页的构建源码 |
| `predictions/` | 与试标集对应的模型预测 |

20 篇试标来自 `data/treatment_related_articles/` 的筛选结果，选文文件保留来源路径和文章 `index`。三份人工导出的 `records[*].index`、选文的 `records[*].index` 与模型预测的 `[*].article_index` 对应同一批文章；实体 ID 仅在各文章、各标注版本内部有效，不能跨文件直接合并。

人工原始导出保存在 [annotations/](datasets/kg_pilot_20/annotations/)，此次未修改内容。截至本次整理，DHY 和尤雅各有 20 篇标记为 completed，第三份导出的 20 篇仍标记为 in_progress。这里是试标材料，尚未生成仲裁金标；后续仲裁应另存文件。

人工工具使用 `schemas/v3.0.0/final_schema.xlsx`，新 semantic 模型使用 `agent/kg_agent/ontology.json`；正式计分前须明确标签对应和评测范围。公开 MDIEC 保留原生标签，不直接并入本项目人工金标。

文献筛选的 40 篇人工复查归于 [screening_review_40/](../data/treatment_related_articles/screening_review_40/README.md)。`filtering_tests/` 与历史 22 篇模型实验保留原位，不属于此次整理范围。

## 重新生成离线页面

在仓库根目录运行，无需调用 API：

```bash
python benchmarks/tools/kg_annotation/build_page.py
python benchmarks/tools/kg_comparison/build_page.py
```

两条命令分别读取选文和三份人工原始导出，将页面写入 `datasets/kg_pilot_20/pages/`。生成页面内嵌数据、样式和脚本，可单文件离线打开。

页面的 dataset_id 和 localStorage key 沿用原值。文件路径改变后，浏览器未必继承旧路径的本地进度；导出的 JSON 可通过标注页导入。对照页展示三份原始导出，不代表已完成仲裁。
