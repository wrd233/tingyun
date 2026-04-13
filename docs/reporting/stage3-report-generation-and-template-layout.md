# 第三阶段报告生成结构说明

本文件描述当前仓库里“第三阶段报告生成”的正式落地方式。

## 目标

第三阶段不再重新采集和重新诊断，而是在某个批次已经存在 `diagnostics/` 资产的前提下，按某一种报告模板生成最终报告。

## 当前结构

模板定义集中放在：

- `report_templates/<report_type_id>/`

某次诊断的报告实例放在：

- `artifacts/monitored_systems/<system_key>/<batch_key>/reports/<report_type_id>/`

也就是说，报告实例与同批次 `diagnostics/` 同级，而不是再引入一个新的中间重型输入目录。

## 当前首个模板

- `report_templates/legal_diagnostic_report/`
  - 基于“法务系统排查报告_模拟版.tex”的 LaTeX 模板样板

## 模板目录职责

模板目录负责长期稳定的“报告类型定义”，通常包括：

- `template.tex`
- `spec.yaml`
- `chapter_guidelines.md`
- `style/`
- `fragments/`
- `notes.md`

这些文件描述的是“这种报告怎么写、怎么排版、需要哪些资产”，而不是“某次报告的实例数据”。

## 实例目录职责

实例目录只负责某一个批次下的报告生成工作区，通常包括：

- `report_config.yaml`
- `generated/`
- `output/`
- `assets/`

这里的 `report_config.yaml` 是薄配置，只负责指定：

- 采用哪个模板
- 读哪个 diagnostics 目录
- 输出到哪里

它不复制 diagnostics 中的主表、证据索引和 deep-dive 资产。

## 当前最小执行入口

当前第三阶段已经有一个最小 renderer：

- `report_templates/renderers/render_report_instance.py`

它会：

- 读取实例级 `report_config.yaml`
- 解析模板目录下的 `spec.yaml`
- 直接检查同批次 `diagnostics/` 下的 required / optional assets
- 在实例目录的 `generated/` 下生成最小骨架：
  - `report_context.json`
  - `chapter_stubs.json`
  - `assembled_main.tex`
  - `asset_index_stub.json`

它当前还不会自动产出完整高质量正文，但已经能证明第三阶段“开始可执行”。

## 当前原则

- 保持 stage1 / stage2 与最终报告模板解耦
- 第三阶段直接读取 diagnostics
- 不引入 `report_input_bundle/`
- 模板定义与报告实例分离
- 报告实例与诊断批次强绑定
