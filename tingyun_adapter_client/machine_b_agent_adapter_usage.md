# 机器 B 模型 / Agent 调用指南

生成时间：2026-04-05  
项目目录：`/Users/wangrundong/work/mywork/tingyun_adapter_client`

## 1. 这是什么

这是给机器 B 上的大模型、agent、Codex 使用的一份说明。

机器 B 不直接连接听云原始接口，而是通过本地 CLI 调用机器 A 上的 `tingyun_adapter` HTTP 服务。

推荐入口：

- [cli.py](/Users/wangrundong/work/mywork/tingyun_adapter_client/src/tingyun_adapter_client/cli.py)

## 2. 背后的系统结构

当前分层如下：

1. 机器 A
   - 持有听云 token
   - 持有 `captured_api`
   - 运行 `tingyun_adapter` HTTP 服务
2. 机器 B
   - 持有 `service_base_url`
   - 持有 `service_api_key`
   - 运行 `tingyun_adapter_client`
3. 模型 / agent / Codex
   - 通过 `tingyun_adapter_client` 获取 pack
   - 使用 pack 做诊断、分析和报告生成

## 3. 能调用什么

当前机器 A 服务支持这些 pack：

- `system_snapshot`
- `action_hotspot_pack`
- `diagnostic_candidate_pack`
- `action_fact_sheet`
- `trace_case_pack`
- `trace_fact_sheet`
- `report_fact_pack`
- `database_component_pack`
- `nosql_component_pack`
- `connection_pool_pack`
- `instance_analysis_pack`
- `topology_dependency_pack`
- `external_dependency_pack`
- `slow_sql_pack`
- `sql_fact_sheet`
- `action_dependency_breakdown_pack`
- `business_labels_pack`
- `stability_signals_pack`
- `impact_signals_pack`
- `comparison_signals_pack`
- `page_experience_pack`
- `screenshot_index_pack`
- `knowledge_context_pack`
- `knowledge_update_proposal_pack`

## 4. 每类 pack 的用途

### `system_snapshot`

适合：

- 写系统总体情况
- 写健康度、趋势、应用数、实例数

### `action_hotspot_pack`

适合：

- 找最慢 action
- 找 errorCount / slowCount 较高的事务

### `diagnostic_candidate_pack`

适合：

- 先拿一份“值得继续看”的候选集合
- 让模型快速聚焦，而不是先看全量明细

### `action_fact_sheet`

适合：

- 对某个 action 做深入分析
- 看它的 overview、关联 trace、可疑信号、证据

### `trace_fact_sheet`

适合：

- 对某个 trace 做深入分析
- 看 detail、问题线索、下游调用、证据

### `database_component_pack`

适合：

- 分析数据库组件
- 看热点操作、受影响 action、可继续下钻的线索

### `nosql_component_pack`

适合：

- 分析 Redis / NoSQL 组件
- 看热点操作、影响 action、trace 是否为空

### `connection_pool_pack`

适合：

- 看连接池是否紧张
- 看使用率、等待连接、连接时间

## 5. adapter 的边界

机器 A 上的 adapter 会做：

- 字段归一化
- 对象关系整理
- 证据保留
- 候选对象筛选
- `suspect_signals` 标注
- 历史知识读取
- 待确认知识提议结构化写入

机器 A 上的 adapter 不会做：

- 最终根因判断
- 最终结论生成
- 最终建议成文

因此，机器 B 上的模型 / agent 应该把 pack 视为：

- 分析输入
- 事实基础
- 候选对象与下钻线索

而不是“已经分析完的结论”。

## 6. 推荐的调用顺序

### 场景一：先做总体诊断

1. 调 `system_snapshot`
2. 调 `diagnostic_candidate_pack`
3. 从 candidates 中选重点 action / component
4. 对重点对象继续调对应 fact sheet / component pack

### 场景二：先分析最慢事务

1. 调 `action_hotspot_pack`
2. 选第一名或前几名热点 action
3. 调 `action_fact_sheet`
4. 如果返回了 trace 候选，再调 `trace_fact_sheet`

注意：

- `trace_fact_sheet` 的 `queryTimestamp` 在 HTTP 接口里按字符串接收
- 当前 client CLI 已经自动做了这个兼容转换

### 场景三：先分析某个组件

1. 确认组件类型
2. 调：
   - `database_component_pack`
   - `nosql_component_pack`
   - `connection_pool_pack`
3. 从返回结果中找：
   - top operations
   - impacted actions
   - related traces
   - suspect signals

## 7. `sample` 和 `live`

### `sample`

含义：

- 使用机器 A 本地 `captured_api` 样本

适合：

- 验证调用链
- 开发与测试
- 结果稳定复现

### `live`

含义：

- 让机器 A 用听云 token 真实调用接口

适合：

- 当前真实诊断
- 当前时段问题排查

### 建议

先用 `sample` 验证请求、参数和链路，再切到 `live`。

## 8. 常用 CLI 示例

### 看服务健康

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli healthz
```

### 看能力元信息

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli meta
```

### 拿系统快照

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type system_snapshot \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### 拿诊断候选

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type diagnostic_candidate_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### 深挖某个 action

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type action_fact_sheet \
  --biz-system-id 1065 \
  --application-id 1644 \
  --action-id 13220 \
  --action-type TX \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### 读取业务记忆

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type knowledge_context_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### 写入待确认提议

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type knowledge_update_proposal_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --proposal-file ./proposal.example.json \
  --persist-proposals
```

## 9. 速率与节流

机器 A 的服务现在会做基础节流，默认：

- 最小请求间隔：`800ms`
- 每分钟最大请求数：`30`

如果机器 B 的 agent 要连续调多个 pack，建议：

1. 先拿 `diagnostic_candidate_pack`
2. 只对最关键的少量对象继续下钻
3. 不要无差别轮询所有 pack

## 10. 对模型的使用建议

当拿到 pack 后，推荐按下面方式理解：

- `summary` / `overview`
  - 适合快速建立总体判断
- `suspect_signals`
  - 适合判断哪些对象值得优先分析
- `evidence`
  - 适合回溯事实来源
- `warnings`
  - 适合识别当前数据缺口或源接口限制

推荐模型输出：

- 当前系统总体情况
- 重点问题对象
- 证据链
- 下钻链路
- 问题清单
- 优化建议
