# Adapter 阶段 3 交付说明

这份文档说明 Tingyun adapter 在阶段 3 已经完成的用例层能力。

## 已完成范围

阶段 3 已经具备 4 个基础 pack builder：

- `build_system_snapshot`
- `build_action_hotspot_pack`
- `build_trace_case_pack`
- `build_report_fact_pack`

这些 builder 支持三种来源模式：

- `sample`
  - 优先使用 `captured_api/` 中已经抓到的样本
- `live`
  - 直接调用真实听云 HTTP 接口
- `auto`
  - 如果已经挂载 `captured_api/`，优先走样本；否则走 live

## 新增模块

核心 usecase 层：

- `src/tingyun_adapter/usecases/builders.py`

阶段 3 补充的 client：

- `src/tingyun_adapter/clients/application_client.py`
- `src/tingyun_adapter/clients/health_client.py`

SDK 集成：

- `Adapter.build_system_snapshot(...)`
- `Adapter.build_action_hotspot_pack(...)`
- `Adapter.build_trace_case_pack(...)`
- `Adapter.build_report_fact_pack(...)`

CLI 集成：

- `--build-pack system_snapshot`
- `--build-pack action_hotspot_pack`
- `--build-pack trace_case_pack`
- `--build-pack report_fact_pack`

## 每个 builder 当前做什么

### 1. `system_snapshot`

采集：

- 业务系统总览
- 健康统计
- 响应时间 / 吞吐率 / 错误趋势

输出：

- 业务系统快照
- 趋势摘要
- 可直接作为报告基础证据的 evidence

### 2. `action_hotspot_pack`

采集：

- action 列表
- 匹配到的 action overview

输出：

- 热点 action 排名
- 入选理由
- 简单严重度分数
- evidence

### 3. `trace_case_pack`

采集：

- trace detail
- call tree 摘要
- exception 摘要

输出：

- 典型 trace 个案
- selector
- 下钻路径
- evidence

### 4. `report_fact_pack`

组合：

- `system_snapshot`
- `action_hotspot_pack`
- `trace_case_pack`

输出：

- 报告范围
- 概要事实
- 初版问题清单
- 下钻路径
- 合并 evidence

## 测试覆盖

阶段 3 的样本模式测试位于：

- `tests/unit/test_usecases.py`

## 典型命令

运行全部单元测试：

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

构建 `system_snapshot`：

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --captured-api-dir ./captured_api \
  --build-pack system_snapshot \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

构建 `trace_case_pack`：

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --captured-api-dir ./captured_api \
  --build-pack trace_case_pack \
  --biz-system-id 1062 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

## 当前限制

阶段 3 仍然是“第一版用例层”，有几个已知边界：

- `sample` 模式完全依赖 `captured_api/` 中现有样本
- 某些样本的 `bizSystemId` 与当前构建上下文不完全对齐
- `trace_current_overview` 在样本模式下还没有完整重建，因此个别场景会回退到 `action/trace/detail` 样本
- 问题提取逻辑目前仍是启发式规则，不是完整归因逻辑

## 下一步目标

下一阶段是阶段 4：

- `database_component_pack`
- `nosql_component_pack`
- `connection_pool_pack`
- 更完整的组件诊断闭环
