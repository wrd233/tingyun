# legal_diagnostic_report 实例

这是 `legal_diagnostic_report` 模板在当前诊断批次下的报告实例目录。

## 实例关系

- 报告类型：`legal_diagnostic_report`
- 系统：`bizsystem_1065`
- 批次：`2026-04-12-live-export-test-2210`
- 读取来源：同级 [diagnostics](/Users/wangrundong/work/mywork/artifacts/monitored_systems/bizsystem_1065/2026-04-12-live-export-test-2210/diagnostics)
- 模板定义： [report_templates/legal_diagnostic_report](/Users/wangrundong/work/mywork/report_templates/legal_diagnostic_report)

## 目录说明

- `report_config.yaml`
  - 当前实例的轻量配置
- `generated/`
  - 后续 agent 生成的中间 tex/json/md 文件
- `output/`
  - 最终 tex/pdf/docx 等产物
- `assets/`
  - 截图、插图、表格附件等实例级补充素材

## 重要约束

- 这个实例目录直接读取同级 `diagnostics/` 资产
- 不要求也不建议先把 diagnostics 再复制成新的 `report_input_bundle/`
- 如果后续要生成正式报告，应优先在这里写中间产物和最终产物，而不是改动 `diagnostics/` 目录本身
