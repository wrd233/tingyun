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

## 相关文档

- [machine-a-machine-b-collaboration.md](/Users/wangrundong/work/mywork/docs/workflows/machine-a-machine-b-collaboration.md)
- [client-materialization-boundary.md](/Users/wangrundong/work/mywork/docs/workflows/client-materialization-boundary.md)
- [machine-b-agent-adapter-usage.md](/Users/wangrundong/work/mywork/docs/workflows/machine-b-agent-adapter-usage.md)
