# Docs

`docs/` 是仓库内所有长期版本化说明文档的统一入口，不存放本地运行产物。

## 当前主设计入口

- `architecture/project-overall-architecture-and-collaboration.md`
  - 当前顶层架构与协作主文档
- `architecture/adapter-design-and-intermediate-artifacts.md`
  - 当前 adapter 主设计文档
- `reporting/final-deliverable-and-report-expression.md`
  - 当前交付与报告表达主文档

## 子目录

- `architecture/`
  - 当前主设计、仓库目标状态、目录职责、系统 / 批次语义
- `workflows/`
  - 机器 A / 机器 B 协作、capture 运行边界、client 物化边界、批次复用方式
- `reporting/`
  - 当前报告主设计、术语、证据与截图规则、最终交付物表达
- `decisions/`
  - 历史阶段交付与设计决策快照

## 阅读建议

- 想快速建立全局认知：先读三份主设计文档
- 想接手运行链路：再读 `workflows/`
- 想接手报告材料与样例：再读 `reporting/`
- 想理解演进背景：最后查 `decisions/`

当前与 diagnostics / 主表流水线最相关的补充文档：

- `workflows/apm-export-tables-to-master-tables.md`
- `architecture/deep-dive-stage-and-adapter-bridge.md`
- `reporting/stage3-report-generation-and-template-layout.md`

如果要接手 deep-dive 的落盘与回写，建议再读：

- `workflows/client-materialization-boundary.md`

当前 deep-dive 的正式触发入口以 client 侧三个等价入口为准：

- `python3 -m tingyun_adapter_client.materialize_deep_dive`
- `tingyun-materialize-deep-dive`
- `python3 -m tingyun_adapter_client.cli materialize-deep-dive`

`decisions/` 保留历史阶段上下文、legacy 设计和阶段判断，不作为当前事实来源。当前仓库以三份主设计文档及其补充文档为准。

第三阶段的模板定义目录在仓库根 `report_templates/`，而某次批次的报告实例目录在 `artifacts/monitored_systems/<system_key>/<batch_key>/reports/`。
