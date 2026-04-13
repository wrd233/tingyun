# Skills

`skills/` 是当前仓库的项目级 skill 目录，用来沉淀围绕听云诊断链路形成的可复用工作单元。

这里的 skill 不是新的平台层，也不替代现有代码目录。它们主要承担三件事：

- 把已经稳定下来的诊断流程、判断经验和缺失处理方式沉淀成可复用定义
- 让后续 Codex / agent 进入仓库后，知道应该如何围绕主表、证据索引、deep-dive 和报告模板工作
- 为后续更正式的 Codex skill 形态预留目录和文件边界

## 与现有目录的关系

- `tingyun_adapter/`
  - 提供候选对象、deep-dive、证据增强和报告支撑能力
- `tingyun_adapter_client/`
  - 把 adapter 能力物化成 `diagnostics/`、`04_deep_dive/`、`reports/`
- `report_templates/`
  - 定义第三阶段正式报告类型和渲染骨架
- `skills/`
  - 定义 agent 应如何使用这些能力、如何判断、如何在缺失时稳定占位

可以把它理解为：

- 代码目录回答“能力在哪里”
- `skills/` 回答“围绕这些能力该怎么做”

## 当前第一批核心 skill

- `request-diagnosis-skill/`
  - 围绕 `request_master.csv`、`request_evidence_index.csv`、request/interface_cluster deep-dive 的接口诊断 skill
- `sql-diagnosis-skill/`
  - 围绕 `sql_master.csv`、`sql_evidence_index.csv` 和 SQL deep-dive 的 SQL 诊断 skill
- `report-generation-skill/`
  - 围绕 `report_templates/legal_diagnostic_report` 与实例级 `reports/` 的第三阶段报告生成 skill
- `master-table-materialization-skill/`
  - 围绕 `00_raw_exports -> 01_prepared_tables -> 02_master_tables -> 03_evidence_indexes -> 04_deep_dive` 的主表流水线 skill

## 目录约定

每个 skill 使用独立目录，并采用 `SKILL.md` 作为主定义文件。

这样做的原因是：

- 符合 Codex 常见 skill 目录习惯
- 目录足够轻量，不需要引入额外平台
- 以后如果要继续补 `references/`、`scripts/` 或更正式的 metadata，可以平滑扩展

## 当前成熟度

当前这批 skill 属于“文档型 + 可进一步强化”的第一轮落地：

- 已经能清楚表达目标、输入、输出、流程、判断、缺失处理和验收标准
- 已经和现有 `diagnostics/`、`report_templates/`、adapter/client 结构对齐
- 还没有全部强化成脚本化、规则化或自动调用型 skill

如果后续 agent 需要接手诊断或报告工作，建议先读本目录，再按任务类型进入对应 `SKILL.md`。
