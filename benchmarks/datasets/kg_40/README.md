# KG 40 篇试标数据

`annotations/` 保留三份标注页原始导出。以下文件由 `benchmarks/benchmark.py import-project` 转换为 `medicalner-benchmark-v1` 格式，原文和文章 ID 均来自各自的原始文件：

| 文件 | 原始标注状态 | 定位 |
|---|---|---|
| `dhy_pilot.json` | 40 篇 completed | DHY 单人试标参考 |
| `youya_pilot.json` | 40 篇 completed | 尤雅单人试标参考 |
| `annotator_in_progress_pilot.json` | 导出为 40 篇 in_progress；据用户说明已完成 | 单人试标；导出状态尚未更新 |

三份文件的文章 ID 和输入文本一致；尚无仲裁金标。`kind: pilot` 不代表金标，也不能证明标注正确。导入器只声明 `graph` 任务，不推测原文位置或概念 ID；框架用实体名称、类型以及有向关系和标签进行精确图匹配。详见 [框架说明](../../framework/README.md)。

原导出元数据记录的是 v3.1.0；当前目标 schema 是 [`schema1115.xlsx`](../../../schemas/v3.2.0/schema1115.xlsx)。上述文件是原样转换，并非完成了 v3.2.0 迁移。尤雅参考中有 2 条 `Treatment → combined_with → Medication` 不符合 v3.2.0 的关系端点；按用户指示，另存的 `youya_v3.2_pilot.json` 将其方向反转，具体变更见 `youya_v3.2_changes.json`。该副本仍是未仲裁试标，并非对全文按 v3.2.0 重新标注。

例如，重新生成 DHY 文件（输出路径必须不存在）：

```bash
python benchmarks/benchmark.py import-project \
  --input benchmarks/datasets/kg_40/annotations/MedicalNER_DHY_40articles_v3.1.0_2026-11-05.json \
  --dataset-id kg40-dhy-pilot --kind pilot \
  --output benchmarks/datasets/kg_40/dhy_pilot_new.json
```
