---
name: master-table-materialization-skill
description: Use when materializing the diagnostics pipeline in this Tingyun project from raw exports to prepared tables, master tables, evidence indexes, and deep-dive scaffolding, especially in tingyun_adapter_client workflows.
---

# Master Table Materialization Skill

## Goal

把当前 diagnostics 主线稳定地从原始导出推进到 prepared/master/evidence/deep-dive 骨架，为 request 诊断、SQL 诊断和第三阶段报告提供可靠底座。

## Scope

适用：

- `00_raw_exports -> 01_prepared_tables -> 02_master_tables -> 03_evidence_indexes -> 04_deep_dive`
- `tingyun_adapter_client` 下的 materialization 命令和脚本
- 准备表 / 主表 / 证据索引 / deep-dive registry 的初始落盘

不适用：

- 直接写报告正文
- 绕过 adapter/client 自己手工拼 diagnostics

## Inputs

- `diagnostics/00_raw_exports/`
- `diagnostics/01_prepared_tables/` 上游生成所需原始导出
- 可选规则文件，如 `screening_rules.json`
- adapter/client 当前已有导出与 deep-dive source

## Outputs

- `01_prepared_tables/*.csv`
- `02_master_tables/*.csv`
- `03_evidence_indexes/*.csv`
- `04_deep_dive/deep_dive_registry.csv`
- materialization / preparation summary

## Core Process

1. 确认 diagnostics 目录结构已经存在。
2. 运行 prepared 阶段，把原始导出归一、整合并加上首轮筛选注记。
3. 运行 materialize 阶段，生成 request/sql/interface_cluster 等主表。
4. 同步生成证据索引和 deep-dive 骨架目录。
5. 如已存在 deep-dive source，再把 deep-dive 真正挂回主表和 evidence index。
6. 记录 summary、warning 和缺失项。

## Judgment Rules

- `01_prepared_tables/` 保留全量；`02_master_tables/` 是数量受控的工作底稿。
- SQL 场景必须按多数据库实例整合，不要退回单文件视角。
- `followup_status / followup_note` 是主表生命周期字段，不再回到旧的“第二阶段操作/理由”。
- deep-dive 结果必须挂回主表和 evidence index，不能只停留在 JSON 或 bundle 目录。

## Common Misjudgments

- 把 prepared 当成最终主线对象。
- 把 evidence index 当成 report-only 附件，而不是主表派生对象。
- 忽略 SQL 多库来源字段，丢失 `source_db_key / source_db_name`。

## Missing Policy

- 缺某类 raw export：prepared 可以留空骨架，但要写 warning。
- 缺 interface list 时，允许最小合成 `interface_cluster_prepared/master`，并标明来源。
- 缺 deep-dive source：不阻塞主表和 evidence index 落盘。

## Definition Of Done

- diagnostics 五层目录语义明确且落盘。
- request/sql 至少已有 prepared、master、evidence 结果。
- deep-dive registry 至少已初始化。
- 缺失和 warning 已写入 summary，而不是静默吞掉。
