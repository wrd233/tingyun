# Adapter 阶段 5 交付说明

生成时间：2026-04-04  
项目目录：`/Users/wangrundong/work/mywork/tingyun_adapter`

## 1. 本阶段目标

本阶段围绕最近两轮对话中的几个关键问题展开：

- adapter 能否做“候选筛选”而不越界承担最终分析
- adapter 能否为特定 `action / trace / component` 提供更适合大模型深入分析的输入
- 当前 pack 输出中暴露的几个问题如何修正

因此本阶段聚焦三类工作：

1. 修正当前已暴露的问题
2. 补充 adapter 的边界与下一阶段设计
3. 落地一批新的 next-step pack

## 2. 已修正的问题

### 2.1 token 不再明文输出

修正前：

- `context.auth.token` 会在 pack 中完整输出

修正后：

- `context.auth.token` 默认脱敏或为空
- 新增：
  - `token_present`
  - `token_env`

### 2.2 `connection_pool_pack` 的最新已用连接数抽取错误

修正前：

- `latest_used_connections` 错误地取了 `latest_point.y`

修正后：

- 优先从 tooltip 中解析 `Used connections`
- 同时补充：
  - `latest_connection_time_ms`

### 2.3 pack 中开始显式输出 `suspect_signals`

新增后：

- `system_snapshot`
- `action_hotspot_pack`
- `trace_case_pack`
- `database_component_pack`
- `nosql_component_pack`
- `connection_pool_pack`

都开始输出一组轻量可疑信号，供 skill 聚焦而不是直接下结论。

## 3. 新增的 pack

### 3.1 `diagnostic_candidate_pack`

定位：

- 用于“先看什么”
- 面向 skill 的诊断入口

典型输出：

- `system_signals`
- `action_candidates`
- `trace_candidates`
- `component_candidates`
- `recommended_next_packs`

### 3.2 `action_fact_sheet`

定位：

- 面向单个 action 的深入事实包

典型输出：

- `action_ref`
- `action`
- `overview`
- `suspect_signals`
- `trace_candidates`
- `downstream_components`
- `drilldown_keys`

### 3.3 `trace_fact_sheet`

定位：

- 面向单条 trace 的深入事实包

典型输出：

- `selector`
- `trace`
- `detail_summary`
- `call_tree_summary`
- `exception_summary`
- `suspect_signals`
- `drilldown_keys`

## 4. 为什么这一步没有越界成“分析器”

这一步虽然加入了：

- 候选筛选
- 可疑信号
- fact sheet

但 adapter 仍然没有承担：

- 最终根因判断
- 最终优先级结论
- 最终建议生成
- 最终报告成文

所以它仍然是：

- 面向分析的整理层

而不是：

- 最终诊断层

## 5. 当前 CLI 新增的能力

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

## 6. 验证情况

本阶段已验证：

- `python3 -m py_compile` 通过
- `20` 个单元测试全部通过
- CLI 新增 pack 可正常输出
- `connection_pool_pack` 中 `latest_used_connections` 已修正
- pack 输出默认不再暴露明文 token
