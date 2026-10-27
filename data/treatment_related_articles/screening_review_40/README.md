# 文献筛选人工复查：40 篇

本目录保存当时为文献筛选开展的 40 篇人工复查。2026-10-27 从 `temp/` 和 `filtering/` 移入，与 KG benchmark 的 20 篇人工试标分开管理。

| 文件 | 内容 |
|---|---|
| [review_articles_original.json](review_articles_original.json) | 40 篇原文、来源信息和原模型答案 |
| [treatment_article_review_DHY.json](treatment_article_review_DHY.json) | DHY 原始复查导出 |
| [treatment_article_review__ (1).json](<treatment_article_review__ (1).json>) | 尤雅原始复查导出 |
| [treatment_article_review__.json](treatment_article_review__.json) | 评审3原始复查导出 |
| [treatment_review_analysis.md](treatment_review_analysis.md) | 三位评审与原模型结果的分析 |
| [treatment_review_comparison.csv](treatment_review_comparison.csv) | 逐篇对照表 |
| [treatment_article_blind_review_40.html](treatment_article_blind_review_40.html) | 自包含离线盲评页 |

人工判断读取 `reviews[*].reviewer_decision`，备注读取 `reviewer_note`；每份导出附带的 `model_decision` 是同一组模型结果，不是新增人工评审。原文 `index` 与复查导出的 `article_index` 对应，`sample_number` 是本批 40 篇内的编号。

原始 JSON、CSV 和盲评页内容在迁移时保持不变。分析和多数意见用于复查筛选策略，不作为 KG 抽取金标。
