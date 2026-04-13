# Report Templates

`report_templates/` 集中存放“报告类型定义”，不存放某一次诊断的具体产物。

这里的每个模板目录都描述一种长期稳定的报告类型，通常包含：

- `template.tex`
  - 主模板或主排版骨架
- `spec.yaml`
  - 模板级规格定义
- `chapter_guidelines.md`
  - 章节写作与资产读取说明
- `style/`
  - 模板共用的样式宏、排版片段
- `fragments/`
  - 按章节或页面拆开的轻量模板片段
- `notes.md`
  - 当前模板的继承来源、稳定度和后续泛化说明

配套的最小执行入口放在：

- `renderers/`
  - 读取实例级 `report_config.yaml`，直接从同批次 `diagnostics/` 生成 `generated/` 骨架

## 当前模板

- `legal_diagnostic_report/`
  - 基于“法务系统排查报告_模拟版.tex”建立的首个正式模板定义

## 模板定义与报告实例的关系

- 模板定义：长期集中维护在 `report_templates/`
- 报告实例：落在具体诊断批次目录下的 `artifacts/monitored_systems/<system_key>/<batch_key>/reports/<report_type_id>/`

第三阶段默认直接读取同批次下的 `diagnostics/` 资产，不要求先构造一层新的重型 `report_input_bundle/`。

当前可执行入口：

```bash
python3 report_templates/renderers/render_report_instance.py \
  --config artifacts/monitored_systems/<system_key>/<batch_key>/reports/legal_diagnostic_report/report_config.yaml
```
