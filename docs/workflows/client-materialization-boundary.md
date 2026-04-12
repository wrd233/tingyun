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
├── 03_evidence_indexes/
└── 04_deep_dive/
```

如果需要把数据库 SQL / NoSQL 操作导出真正落盘到 `00_raw_exports/`，当前 client 已补了一个专门入口：

- `export-component-analysis-raw`

它会把 SQL 导出写到：

- `00_raw_exports/sql_database/<db_key>/component_analysis_export_database__SQL_.xls`

把 NoSQL 导出写到：

- `00_raw_exports/nosql/<component_key>/component_analysis_export_nosql__SQL_.xls`

如果某次结果要转为长期示例，应从批次目录挑选稳定子集，再迁到 `samples/`。

当前 `materialize-master-tables` 在生成 `02_master_tables/` 与 `03_evidence_indexes/` 的同时，也会初始化 `04_deep_dive/`：

- 创建 `deep_dive_registry.csv`
- 初始化 `request/`、`sql/`、`interface_cluster/`、`application/`、`dependency/`、`shared/`
- 给主表补齐 `selected_for_deep_dive / deep_dive_count / deep_dive_status / latest_deep_dive_id / latest_deep_dive_at` 等摘要字段

如果本地已经有 `report_fact_pack.json` 或 review bundle JSON，当前 client 还支持继续执行：

- `materialize-deep-dive`

它会读取：

- `deep_dive_targets`
- `selected_target_expansions`

并把它们真正落为：

- `04_deep_dive/deep_dive_registry.csv`
- `04_deep_dive/request/<object_id>/<deep_dive_id>/`
- `04_deep_dive/sql/<object_id>/<deep_dive_id>/`
- `04_deep_dive/interface_cluster/<object_id>/<deep_dive_id>/`

同时把 `latest_deep_dive_id / deep_dive_status / page_link_count / trace_link_count / screenshot_hint_status` 回写到主表和证据索引。
