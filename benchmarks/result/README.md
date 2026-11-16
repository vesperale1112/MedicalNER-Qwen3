# KG 40 篇图评测试跑

`kg40_codex_vs_youya_v3.2.json` 是 40 篇 Codex 抽取草稿与尤雅单人试标的比较。尤雅参考未经过多人仲裁；按用户指示，参考副本将两条旧方向的 `combined_with` 关系反转，原始标注未修改，详见 [`kg_40/README.md`](../datasets/kg_40/README.md)。参考未按 v3.2.0 对全文重新标注，因此新版新增的实体或关系可能不在参考中。

重新运行（输出路径须不存在）：

```bash
python benchmarks/benchmark.py evaluate \
  --reference benchmarks/datasets/kg_40/youya_v3.2_pilot.json \
  --predictions benchmarks/examples/kg40_codex_v3.2.json \
  --tasks graph --include-errors \
  --output benchmarks/result/kg40_codex_vs_youya_v3.2_new.json
```

全部 40 篇预测均为 complete，输入文本均已核对一致。总体 micro 结果：

| 指标 | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| 图实体 | 98 | 235 | 237 | 0.2943 | 0.2925 | 0.2934 |
| 图关系 | 21 | 228 | 278 | 0.0843 | 0.0702 | 0.0766 |

图实体按名称和类型匹配；名称仅做 Unicode NFKC、大小写和空白规范化，不自动合并同义词或缩写。关系要求两端名称、类型、方向和关系标签一致。例如第一篇草稿的 `esketamine` 与参考的 `Esketamine nasal spray` 不视为同一名称，这也影响涉及该节点的关系。逐篇 FP/FN 可在结果 JSON 的 `per_document` 中查看。

这些分数只表示与该单人试标在现有精确名称匹配规则下的一致性，不是临床正确率或模型性能；评分程序不判断证据是否支持关系。未仲裁参考、schema 版本差异和草稿遗漏都会影响结果。
