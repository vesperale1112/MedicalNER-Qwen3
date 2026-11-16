# KG 40 篇抽取示例

`kg40_codex_v3.2.json` 是 Codex 根据 40 篇文章的标题和摘要重新抽取的图草稿，使用 `schemas/v3.2.0/schema1115.xlsx` 的节点和关系。它是用于试跑的助手标注，不是模型推理输出或人工金标；抽取并非穷尽，需人工复核。

文件采用 `medicalner-benchmark-v1`，包含 40 篇、333 个实体和 249 条关系。每篇 `text` 与所选参考一致，节点 ID 只在本篇内有效。每条关系的 `evidence` 是源文章的连续上下文片段；部分片段包含条件、对照或不确定表述，不能因为有原文片段就视为关系已经人工核实。`status: complete` 表示该篇已有可评分的图，不代表标注完整或经审核。

参考标注没有字符位置和稳定概念 ID，示例也仅声明 `graph`，不能据此计算 NER、NEL、M-RE 或 C-RE。完整评分命令和结果见 [`result/README.md`](../result/README.md)。
