# Tingyun Adapter Client

`tingyun_adapter_client/` 运行在机器 B，定位是“远程调用器 + 本地物化器”。

## 在整体链路中的位置

- 调用机器 A 上发布的 `tingyun_adapter` 服务
- 获取 pack / export view
- 把结果落到本地材料目录，供 agent、写作者和脚本继续消费

## 负责什么

- `healthz` / `meta` 远程探活
- 远程构建 pack
- 构建本地 materialized report pack

## 不负责什么

- 不直接访问听云原始接口
- 不替代 `tingyun_cdp_capture/`
- 不在源码工程里长期堆放真实报告结果

## 目录说明

- `src/tingyun_adapter_client/cli.py`
  - CLI 入口
- `src/tingyun_adapter_client/http_client.py`
  - 远程 HTTP 客户端
- `src/tingyun_adapter_client/report_pack_builder.py`
  - report materialization 逻辑
- `tests/`
  - client 自身测试

## 与多系统 / 多批次的关系

推荐把 client 物化结果写入：

- `artifacts/monitored_systems/<system_key>/<batch_key>/report_materials/`
- `artifacts/monitored_systems/<system_key>/<batch_key>/reports/`

如果某次结果要保留为长期示例，再从批次目录挑选稳定子集迁入 `samples/`。

## 本地配置

先复制：

```bash
cp /Users/wangrundong/work/mywork/tingyun_adapter_client/config.local.json.example /Users/wangrundong/work/mywork/tingyun_adapter_client/config.local.json
```

建议配置：

```json
{
  "service_base_url": "https://your-adapter-service.example.com",
  "service_api_key": "machine-a-service-api-key",
  "timeout_seconds": 30,
  "default_source_mode": "sample"
}
```

## 最小运行入口

安装：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
python3 -m pip install -e .
```

探活：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli healthz
```

查看能力：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli meta
```

构建 pack：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type report_fact_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

构建本地报告材料时，建议显式写到某个批次目录：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-report-pack \
  --biz-system-id 1065 \
  --start-time '2025-12-20' \
  --end-time '2026-03-31' \
  --source-mode live \
  --limit 6 \
  --output-dir /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/report_materials/report_pack
```

## APM 导出到主表流水线

围绕 diagnostics 目录，当前新增了一条和现有导出能力兼容的主表流水线：

```text
diagnostics/
├── 00_raw_exports/
├── 01_prepared_tables/
├── 02_master_tables/
├── 03_evidence_indexes/
└── 04_deep_dive/
```

如果要先把 SQL / NoSQL 原始导出按组件落到 `00_raw_exports/`，可以先运行：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli export-component-analysis-raw \
  --diagnostics-dir /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics \
  --biz-system-id 1065 \
  --end-time '2026-04-12 22:15' \
  --period-minutes 2880 \
  --source-mode live
```

默认会优先通过 `database_component_pack` / `nosql_component_pack` 自动发现一个主组件，再调用现有 `data_export_pack` 落出：

- `00_raw_exports/sql_database/<db_key>/component_analysis_export_database__SQL_.xls`
- `00_raw_exports/nosql/<component_key>/component_analysis_export_nosql__SQL_.xls`

如果你已经拿到了明确组件清单，也可以改用：

- `--database-components-file <database_components.json>`
- `--nosql-components-file <nosql_components.json>`

推荐使用现有总 CLI：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli prepare-master-table-inputs \
  --diagnostics-dir /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics \
  --system-key <system_key> \
  --batch-key <batch_key> \
  --rules-file /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics/screening_rules.json
```

然后再物化主表和证据索引：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli materialize-master-tables \
  --diagnostics-dir /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics \
  --system-key <system_key> \
  --batch-key <batch_key>
```

这一步现在还会同时做两件事情：

- 初始化 `04_deep_dive/deep_dive_registry.csv` 和对象类型目录
- 给 `request_master.csv`、`sql_master.csv`、`interface_cluster_master.csv` 等主表补齐 deep-dive 摘要字段

如果本批次没有拿到 `interface_list_export` 原始导出，当前 client 会先基于 `request_prepared.csv` 合成最小 `interface_cluster_prepared.csv / interface_cluster_master.csv`，这样 request 与 interface_cluster 的 deep-dive 都还能继续挂回主表主线。

如果当前已经拿到 `report_fact_pack.json`、review bundle JSON，或者任何包含：

- `deep_dive_targets`
- `selected_target_expansions`

的 JSON 文件，还可以继续把 deep-dive 真正落到 diagnostics 主线里：

正式入口与 `prepare / materialize master` 保持一致，推荐直接使用模块脚本或安装后的 console script：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.materialize_deep_dive \
  --diagnostics-dir /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics \
  --system-key <system_key> \
  --batch-key <batch_key> \
  --source-json /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/report_materials/report_pack/04_raw/report_fact_pack.json
```

等价的总 CLI 子命令也保留：

- `python3 -m tingyun_adapter_client.cli materialize-deep-dive ...`
- `tingyun-materialize-deep-dive ...`

这一步会做四件事：

- 读取 `deep_dive_targets + selected_target_expansions`
- 匹配 `request_master.csv / sql_master.csv / interface_cluster_master.csv`
- 落 `04_deep_dive/deep_dive_registry.csv` 和真实 bundle 目录
- 回写主表与 `request_evidence_index.csv / interface_cluster_evidence_index.csv / sql_evidence_index.csv`

也可以直接运行模块脚本：

- `python3 -m tingyun_adapter_client.prepare_master_table_inputs --rules-file <screening_rules.json>`
- `python3 -m tingyun_adapter_client.materialize_master_tables`
- `python3 -m tingyun_adapter_client.materialize_deep_dive --source-json <deep_dive_source.json>`

## 相关文档

- [machine-a-machine-b-collaboration.md](/Users/wangrundong/work/mywork/docs/workflows/machine-a-machine-b-collaboration.md)
- [client-materialization-boundary.md](/Users/wangrundong/work/mywork/docs/workflows/client-materialization-boundary.md)
- [machine-b-agent-adapter-usage.md](/Users/wangrundong/work/mywork/docs/workflows/machine-b-agent-adapter-usage.md)
- [deep-dive-stage-and-adapter-bridge.md](/Users/wangrundong/work/mywork/docs/architecture/deep-dive-stage-and-adapter-bridge.md)
