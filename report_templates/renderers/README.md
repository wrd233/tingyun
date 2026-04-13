# Renderers

`report_templates/renderers/` 放第三阶段的轻量执行入口。

这里的脚本不负责重新诊断，也不构造重型 `report_input_bundle/`。它们只做几件事：

- 读取某个报告实例目录下的 `report_config.yaml`
- 解析对应模板目录下的 `spec.yaml`
- 直接读取同批次 `diagnostics/` 资产
- 在实例目录的 `generated/` 下落最小可运行骨架

当前入口：

- `render_report_instance.py`
  - 通用的最小实例渲染脚手架

示例：

```bash
python3 report_templates/renderers/render_report_instance.py \
  --config artifacts/monitored_systems/bizsystem_1065/2026-04-12-live-export-test-2210/reports/legal_diagnostic_report/report_config.yaml
```
