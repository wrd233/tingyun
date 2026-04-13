---
name: request-diagnosis-skill
description: Use when analyzing request or interface problems in this Tingyun project, especially when working from request_master.csv, request_evidence_index.csv, interface_cluster outputs, and deep-dive bundles to produce stable request diagnosis blocks for diagnostics or report chapter 2.2.
---

# Request Diagnosis Skill

## Goal

围绕接口 / 事务主表建立稳定的 request 诊断流程，形成可进入 `2.2 系统接口检查` 的对象分析素材，并在有 deep-dive 时补充证据和现状说明。

## Scope

适用：

- 分析 `request_master.csv`
- 需要从 `request_evidence_index.csv` 判断证据是否足够
- 需要结合 `04_deep_dive/request/` 或 `04_deep_dive/interface_cluster/` 输出重点对象说明
- 需要生成报告 `2.2.*` 章节素材

不适用：

- 主机资源与部署盘点
- 纯 SQL 主导的问题分析
- 跳过主表、直接从 raw export 重建对象池

## Inputs

优先输入：

- `diagnostics/02_master_tables/request_master.csv`
- `diagnostics/03_evidence_indexes/request_evidence_index.csv`

补充输入：

- `diagnostics/02_master_tables/interface_cluster_master.csv`
- `diagnostics/03_evidence_indexes/interface_cluster_evidence_index.csv`
- `diagnostics/04_deep_dive/deep_dive_registry.csv`
- `diagnostics/04_deep_dive/request/<object_id>/<deep_dive_id>/`
- `diagnostics/04_deep_dive/interface_cluster/<object_id>/<deep_dive_id>/`

## Outputs

- 重点慢接口表格
- 重点异常接口表格
- “关键数据 + 判断 + 现状”对象分析块
- 缺失项说明或占位文案

## Core Process

1. 从 `request_master.csv` 读取对象，优先看 `selected_for_master`、`followup_status`、`selected_for_deep_dive`、`deep_dive_status`。
2. 按场景排序：
   - 慢接口：优先看 `avg_rt_ms`、`slow_count`、`total_time_ms`
   - 重点高影响接口：优先看 `request_count` 与 `total_time_ms`
   - 异常接口：优先看 `error_rate_pct`、`error_count`
3. 用 `request_evidence_index.csv` 检查证据状态：
   - `evidence_status`
   - `page_link_count`
   - `trace_link_count`
   - `screenshot_hint_status`
4. 如果对象已进入 deep-dive，去 `04_deep_dive/request/` 或 registry 取最新 bundle 摘要。
5. 输出时保持固定结构：
   - 对象标题
   - 关键数据
   - 判断
   - 现状 / 证据说明
6. 如果多个 request 共享明显 cluster hint，再参考 `interface_cluster` 视角决定是否归并叙述。
7. 证据不足时稳定占位，不补造根因。

## Judgment Rules

- 高请求量 + 高慢次数 + 高总耗时：优先级最高，优先进入重点接口段。
- 错误率高但平均响应低：优先怀疑快速失败，不要直接归因到慢 SQL。
- 附件、预览、下载、在线查看这类对象：优先怀疑共享问题簇，不要孤立看单个入口。
- 已存在 deep-dive 且 `page_link_count` / `trace_link_count` 不为 0：可提高结论表达的确定性，但仍应和主表一致。
- `followup_status` 为 `排除` 或 `降级观察`：默认不要放进重点对象段，除非有明确报告需求。

## Common Misjudgments

- 看到平均响应高就直接写“数据库问题”。
- 跳过主表，直接从 raw export 或临时 pack 重新选对象。
- 只因为请求量低就忽略极慢但有明显证据的对象。
- 把 diagnostics 的覆盖边界误认为生成器或 skill 执行失败。

## Missing Policy

- 缺 `request_master.csv`：停止并明确说明主线输入缺失。
- 缺 evidence index：可以继续做主表级分析，但证据段只能写 `【待补充】`。
- 缺 deep-dive：不阻塞 request 章节生成，按主表 + evidence index 输出。
- 没有足够证据时，固定使用：
  - `【暂无充分证据支撑该判断】`
  - `【待补充】`

## Definition Of Done

- 已成功读取 request 主表和 request evidence index。
- 至少输出一组 request 排序结果或对象分析块。
- 没有绕开主表重新定义对象池。
- deep-dive 存在时已正确挂接；不存在时已稳定占位。
- 没有在证据不足时补造确定性根因。
