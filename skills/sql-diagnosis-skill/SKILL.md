---
name: sql-diagnosis-skill
description: Use when analyzing slow SQL, abnormal SQL, database-level findings, or SQL evidence in this Tingyun project, especially from sql_master.csv, sql_evidence_index.csv, SQL deep-dive bundles, and report chapter 2.3 workflows.
---

# SQL Diagnosis Skill

## Goal

围绕 SQL 主表建立稳定的 SQL 诊断流程，输出可进入 `2.3 系统SQL检查` 的重点 SQL、数据库整体检查说明和异常 SQL 占位逻辑。

## Scope

适用：

- 慢 SQL 排序和重点 SQL 说明
- 异常 SQL 检查
- 数据库整体检查段的对象摘要
- 需要结合 `sql_evidence_index.csv` 和 SQL deep-dive 补强说明

不适用：

- 纯接口层对象筛选
- 主机、连接池底层资源采集本身
- 绕开 `sql_master.csv` 从原始 `.xls` 重新定义重点对象

## Inputs

优先输入：

- `diagnostics/02_master_tables/sql_master.csv`
- `diagnostics/03_evidence_indexes/sql_evidence_index.csv`

补充输入：

- `diagnostics/04_deep_dive/deep_dive_registry.csv`
- `diagnostics/04_deep_dive/sql/<object_id>/<deep_dive_id>/`
- `diagnostics/01_prepared_tables/sql_prepared_full.csv`
- `diagnostics/00_raw_exports/sql_database/`

## Outputs

- 慢 SQL 表格
- 异常 SQL 表格或稳定占位
- 重点 SQL 分析块
- 数据库实例级摘要
- 缺失项说明

## Core Process

1. 从 `sql_master.csv` 读取对象，优先看：
   - `total_time_ms`
   - `avg_rt_ms`
   - `exec_count`
   - `error_count`
   - `slow_count`
2. 用 `sql_evidence_index.csv` 检查当前证据状态和是否已挂接 deep-dive。
3. 数据库整体检查优先从 `source_db_name`、主表行数、deep-dive 覆盖情况做摘要。
4. 慢 SQL 章节优先按 `total_time_ms` 和 `avg_rt_ms` 组织，不只盯单一最慢值。
5. 异常 SQL 章节必须明确检查 `error_count > 0`：
   - 有数据：输出异常 SQL 表格
   - 没数据：稳定占位，不补造异常对象
6. 如果对象已 deep-dive，补充 bundle 摘要、页面链接和证据数量。

## Judgment Rules

- `total_time_ms` 高 + `exec_count` 高：优先怀疑高影响面 SQL，不要只看单次最慢。
- `avg_rt_ms` 高但 `exec_count` 低：先判断是不是离群值，再决定是否进入重点段。
- 多个 request / interface 与同一类 SQL 关联：优先判断为共享问题簇线索。
- 没有 `error_count > 0`：异常 SQL 章节必须保守，占位即可。
- 数据库整体检查应与 request 侧现象互相印证，不要把慢 SQL 章节写成脱离业务对象的孤岛。

## Common Misjudgments

- 看到一条慢 SQL 就把所有慢接口都归因到数据库。
- 把连接池细项缺失误判成“数据库没问题”。
- 因为当前没有异常 SQL，就硬写异常判断。
- 直接把 prepared 全量表当成最终主线对象，绕开 `sql_master.csv`。

## Missing Policy

- 缺 `sql_master.csv`：停止并明确说明主线输入缺失。
- 缺 `sql_evidence_index.csv`：可继续输出主表排序，但证据说明必须降级。
- 缺 SQL deep-dive：不阻塞章节生成，只说明 `待补 deep-dive`。
- 当前没有异常 SQL：固定输出 `【当前批次未获取到异常SQL主表数据】`。
- 连接池指标未直接沉淀：固定记为当前 diagnostics 覆盖边界。

## Definition Of Done

- 已成功读取 SQL 主表和 SQL evidence index。
- 已输出慢 SQL 表格或重点 SQL 说明。
- 异常 SQL 缺失时已稳定占位，没有臆造内容。
- deep-dive 存在时已挂接摘要，不存在时已说明缺口。
- 结果仍然围绕 `sql_master.csv` 主线，而不是重新发明对象池。
