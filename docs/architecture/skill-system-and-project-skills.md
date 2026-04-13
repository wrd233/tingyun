# Skill 体系与项目级 Skills

这份文档用于说明当前仓库内 skill 体系的落地方式，以及 skill 与现有 adapter/client/report_templates 的关系。

## 定位

这里讨论的 skill，不是新的执行平台，也不是为了替代代码目录。

当前仓库中的 skill 更接近：

- 项目级可复用工作单元
- 围绕“对象 - 证据 - 判断 - 表达”的流程定义
- 先以文档型 `SKILL.md` 落地，再逐步向更正式的 Codex skill 形态演进

## 当前目录

项目级 skill 统一放在仓库根：

- `skills/`

当前首批已落地 skill：

- `skills/request-diagnosis-skill/`
- `skills/sql-diagnosis-skill/`
- `skills/report-generation-skill/`
- `skills/master-table-materialization-skill/`

## 与现有目录的关系

- `tingyun_adapter/`
  - 提供候选对象、deep-dive、证据增强和报告支撑能力
- `tingyun_adapter_client/`
  - 把这些能力物化到 `diagnostics/`、`04_deep_dive/` 和 `reports/`
- `report_templates/`
  - 定义第三阶段正式报告类型
- `skills/`
  - 定义 agent 如何围绕上述目录和资产稳定工作

因此，skill 解决的是“怎么做”，而不是“能力代码放在哪”。

## 当前采用 `SKILL.md` 的原因

当前第一轮 skill 采用每个 skill 一个目录、目录下一个 `SKILL.md` 的方式，原因是：

- 目录轻量，和现有仓库结构兼容
- 更接近 Codex 常见 skill 组织方式
- 便于后续继续增加 `references/`、`scripts/` 或更正式 metadata
- 先把流程、判断规则和缺失处理压实，再决定哪些部分进一步脚本化

## 当前 skill 的成熟度

当前这些 skill 属于“文档型 + 可逐步强化”的第一轮落地：

- 已有目标、输入、输出、流程、判断规则、缺失处理和验收标准
- 已和当前 `diagnostics/`、主表流水线、deep-dive、第三阶段报告实例对齐
- 还没有全部进化成强规则化或强自动执行 skill

## 演进方向

下一步更合理的方向是：

1. 把高置信流程继续压成 checklist / 半结构化规则。
2. 把最稳定的部分进一步沉到脚本或渲染逻辑中。
3. 让 skill 与实例级产物、回归测试和第三阶段生成器形成更稳定闭环。
