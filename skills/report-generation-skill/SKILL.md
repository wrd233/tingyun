---
name: report-generation-skill
description: Use when generating, updating, or validating third-stage reports in this Tingyun project, especially for report_templates/legal_diagnostic_report, instance-level report_config.yaml, direct-read diagnostics, generated chapter files, and final tex/pdf outputs.
---

# Report Generation Skill

## Goal

围绕第三阶段报告实例目录，直接读取同批次 `diagnostics/` 资产，生成可复核的 `generated/` 中间产物和 `output/` 报告结果。

## Scope

适用：

- `report_templates/legal_diagnostic_report/`
- `artifacts/.../<batch_key>/reports/legal_diagnostic_report/`
- 生成或回归 `report_context.json`、章节 tex、assembled tex、pdf
- 同步缺失项占位和 build status

不适用：

- 重做 stage1/stage2 目录结构
- 新增重型 `report_input_bundle/`
- 绕过主表和证据索引，直接从 raw export 自由发挥

## Inputs

优先输入：

- 实例级 `report_config.yaml`
- 模板级 `report_templates/legal_diagnostic_report/spec.yaml`
- 模板级 `chapter_guidelines.md`
- `diagnostics/02_master_tables/*.csv`
- `diagnostics/03_evidence_indexes/*.csv`

补充输入：

- `diagnostics/04_deep_dive/`
- `diagnostics/01_prepared_tables/preparation_summary.json`
- `diagnostics/00_raw_exports/export_registry.json`

## Outputs

- `generated/report_context.json`
- `generated/chapter_stubs.json`
- `generated/chapters/*.tex`
- `generated/assembled_main.tex`
- `generated/missing_data_report.md`
- `output/legal_diagnostic_report.tex`
- `output/build_status.json`
- `output/legal_diagnostic_report.pdf`（当编译器可用）

## Core Process

1. 读取实例级 `report_config.yaml`，确认 `path_mode=repo_relative` 和 direct-read 语义。
2. 读取模板级 `spec.yaml`，确认 required / optional assets、章节顺序、缺失规则。
3. 直接检查同批次 `diagnostics/` 是否存在所需资产。
4. 章节生成时遵守主线：
   - 对象排序优先主表
   - 证据状态优先 evidence index
   - deep-dive 只作补充，不反向替代主表
5. 把缺失项统一写入 `report_context.json` 与 `missing_data_report.md`。
6. 组装 `assembled_main.tex` 和实例级 `.tex`。
7. 优先尝试本机 `xelatex`；如不可用，再使用容器化 XeLaTeX 回退。
8. 把构建状态、warning 摘要和日志路径写回 `output/build_status.json`。

## Judgment Rules

- 第三阶段必须 direct read from diagnostics，不再复制 diagnostics。
- 模板定义和实例输出必须分离：模板在 `report_templates/`，产物在批次实例目录。
- 缺失项是当前 diagnostics 覆盖边界时，应稳定占位，不要臆测补全。
- `generated/` 是可追踪的中间层，不能只留一个最终 PDF。
- build status 必须和实际编译结果一致，不能出现“PDF 已出但状态仍写失败”。

## Common Misjudgments

- 把 report instance 当成新的输入包目录。
- 让第三阶段反向决定 stage1/stage2 的主表结构。
- 为了“让报告完整”而补造根因、部署信息或异常 SQL。
- 只看最终 PDF，不保留 `report_context.json` 和 `missing_data_report.md`。

## Missing Policy

- 缺 required assets：章节保留并明确说明缺失来源。
- 缺 optional assets：跳过并写 note，不阻塞报告骨架生成。
- 缺截图 / URL / deep-dive：保持占位或弱化表达，不写确定性结论。
- 缺本机 LaTeX：允许回退到 Docker 编译；若两者都不可用，至少保留最终 `.tex` 和失败状态。

## Definition Of Done

- 已成功读取实例配置、模板定义和同批次 diagnostics。
- `generated/` 下已有可追踪的上下文、章节和缺失报告。
- `output/build_status.json` 与真实编译状态一致。
- 报告输出仍然落在当前实例目录，不污染模板目录。
- 没有引入新的 `report_input_bundle/`。
