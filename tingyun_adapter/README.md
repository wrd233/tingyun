# Tingyun Adapter

这个项目负责把听云平台原始接口整理成更适合分析与报告场景的结构化 pack。

当前已经完成的核心能力：

- 阶段 1-2
  - schema / ref / envelope / entity
  - raw client
  - 字段归一化
  - `opName` 解码
  - `CapturedApiRepository`
- 阶段 3
  - `system_snapshot`
  - `action_hotspot_pack`
  - `trace_case_pack`
  - `report_fact_pack`
- 阶段 4
  - `database_component_pack`
  - `nosql_component_pack`
  - `connection_pool_pack`
- 阶段 5
  - `diagnostic_candidate_pack`
  - `action_fact_sheet`
  - `trace_fact_sheet`
  - `suspect_signals`
  - 默认敏感信息脱敏输出
- 阶段 A
  - 本地 HTTP 服务
  - 面向机器 B 的远程调用入口
  - 基础访问节流
- 阶段 6
  - `instance_analysis_pack`
  - `topology_dependency_pack`
  - `external_dependency_pack`
  - `slow_sql_pack`
  - `sql_fact_sheet`
  - `action_dependency_breakdown_pack`
- 阶段 7
  - `business_labels_pack`
  - `stability_signals_pack`
  - `impact_signals_pack`
  - `comparison_signals_pack`
  - `page_experience_pack`

当前暂缓的方向：
- 更复杂的历史基线仓储与长期趋势预测
- 更完整的页面侧 API 采集与 RUM 明细建模

## 阶段 7 设计边界

这 5 个新增能力仍然遵守 adapter 的统一原则：

- 面向对象，不面向页面截图
- 输出稳定 pack，而不是最终报告
- 以事实、标签、轻量派生信号、对比结果为主
- 不在 adapter 内输出最终根因、最终整改建议、最终优先级结论

其中：

- `business_labels_pack`
  - 给 action / dependency / 派生 page 对象补充业务语义标签
- `stability_signals_pack`
  - 表达复现性、扩散范围、时间分布、波动特征
- `impact_signals_pack`
  - 提供排序辅助层，不替代人工判断
- `comparison_signals_pack`
  - 提供 `previous_window` 基线对比
- `page_experience_pack`
  - 当前先做降级版页面体验事实层
  - 缺少页面侧专用输入时会在 `meta.missing_inputs` 中明确说明

## 本地配置

优先使用本地配置文件：

- `config.local.json`

先复制示例：

```bash
cp /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json.example /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json
```

示例结构：

```json
{
  "base_url": "http://169.169.173.25:8080",
  "token": "paste-your-token-here",
  "lang": "zh_CN",
  "timezone": "Asia/Shanghai",
  "timeout_seconds": 30,
  "captured_api_dir": "../tingyun_cdp_capture/captured_api"
}
```

`tingyun_adapter` 会按下面顺序读取配置：

1. CLI 参数
2. `config.local.json`
3. 环境变量
4. 默认值

其中 token 额外支持：

- `TINGYUN_TOKEN`
- `TOKEN`

CLI / SDK 输出中的 `context.auth.token` 默认会脱敏，同时额外给出：

- `token_present`
- `token_env`

## 安装

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install -e .
```

如果你的 macOS 系统 Python 比较老，`pip install -e .` 可能会被系统权限或旧版 `pip` 限制住。这种情况下可以直接使用下面的 fallback：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install --user fastapi uvicorn
```

## 运行测试

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

## 查看 CLI

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli --help
```

## 本地 HTTP 服务

现在已经支持把 adapter 作为本地 HTTP 服务运行。

启动方式：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
tingyun-adapter-service
```

或：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.service.http_api
```

详细说明见：

- [adapter_service_local_and_public.md](/Users/wangrundong/work/mywork/tingyun_adapter/adapter_service_local_and_public.md)
- [../tingyun_adapter_client/README.md](/Users/wangrundong/work/mywork/tingyun_adapter_client/README.md)

## 典型调用

### `system_snapshot`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack system_snapshot \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `report_fact_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack report_fact_pack \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `diagnostic_candidate_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack diagnostic_candidate_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### `action_fact_sheet`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack action_fact_sheet \
  --biz-system-id 1065 \
  --application-id 1644 \
  --action-id 13220 \
  --action-type TX \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### `trace_fact_sheet`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack trace_fact_sheet \
  --biz-system-id 1062 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `database_component_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack database_component_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --component-name '10.190.22.21:3306' \
  --component-subtype 'MySQL'
```

### `instance_analysis_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack instance_analysis_pack \
  --biz-system-id 1059 \
  --application-id 1648 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `topology_dependency_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack topology_dependency_pack \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `external_dependency_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack external_dependency_pack \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `slow_sql_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack slow_sql_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### `sql_fact_sheet`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack sql_fact_sheet \
  --biz-system-id 1065 \
  --component-name '10.190.22.21:3306' \
  --component-subtype 'MySQL' \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `action_dependency_breakdown_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack action_dependency_breakdown_pack \
  --biz-system-id 1059 \
  --application-id 1648 \
  --action-id 20441 \
  --action-type TX \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

本轮新增能力说明见：

- [adapter_phase6_delivery.md](/Users/wangrundong/work/mywork/tingyun_adapter/adapter_phase6_delivery.md)
