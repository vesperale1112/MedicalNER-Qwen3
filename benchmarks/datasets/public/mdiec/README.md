# MDIEC 公开标注语料

2026-10-26 调研时下载，2026-10-27 从 `temp/benchmark_20261026/` 迁入本目录。保留原始文件名、BRAT 标签及目录内部结构。

- [MDIEC.zip](MDIEC.zip)：作者发布的原始下载包。
- [MDIEC/](MDIEC/)：解压后的 946 对 `.txt/.ann`；`.ann` 是语料标注，不是本项目模型预测。
- [MDIEC_inventory.json](MDIEC_inventory.json)：实体、关系与文档数量盘点。
- [MDIEC_schema/README.md](MDIEC_schema/README.md)：官方定义、补充材料、作者代码及本地观察 schema 的来源说明。

本地共 28,660 个实体提及、10,560 条关系，9 类实体、9 个关系标签。官方补充材料将其中两类另列为条件陈述，因此简介的 7 类关系与文件中 9 个标签已有解释；论文 500 篇与下载包 946 篇的规模差异仍需厘清，包内没有官方 train/dev/test 清单。

`observed_schema.json` 是从本地标注统计的观察结果，不是作者发布的完整约束文件。公开数据保持原生任务定义，尚未并入本项目的人工试标或正式测试集。
