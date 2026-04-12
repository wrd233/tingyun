# Client Materialization Boundary

`tingyun_adapter_client/` 的定位是“远程调用器 + 本地物化器”。

## 它负责什么

- 调远端 `healthz` / `meta`
- 构建 pack
- 获取 export view
- 物化 report materials

## 它不负责什么

- 不替代平台抓取
- 不在源码目录长期保存真实报告
- 不同时充当样例仓、报告仓、运行产物仓

## 推荐落盘路径

真实批次材料：

`artifacts/monitored_systems/<system_key>/<batch_key>/report_materials/`

最终报告正文：

`artifacts/monitored_systems/<system_key>/<batch_key>/reports/`

如果当前批次需要保留 APM 导出列表到主表的中间流水线，建议放在：

`artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics/`

并使用以下层级：

```text
diagnostics/
├── 00_raw_exports/
├── 01_prepared_tables/
├── 02_master_tables/
└── 03_evidence_indexes/
```

如果某次结果要转为长期示例，应从批次目录挑选稳定子集，再迁到 `samples/`。
