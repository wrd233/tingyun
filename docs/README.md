# Docs

`docs/` 是仓库内所有长期版本化说明文档的统一入口，不存放本地运行产物。

## 子目录

- `architecture/`
  - 仓库目标状态、目录职责、三大主工程边界、系统 / 批次语义
- `workflows/`
  - 机器 A / 机器 B 协作、capture 运行边界、client 物化边界、批次复用方式
- `reporting/`
  - 报告输出术语、材料结构、证据与截图规则、最终交付物形态
- `decisions/`
  - 历史阶段交付与设计决策快照

## 阅读建议

- 想快速建立全局认知：先读 `architecture/`
- 想接手运行链路：再读 `workflows/`
- 想接手报告材料与样例：再读 `reporting/`
- 想理解演进背景：最后查 `decisions/`

`decisions/` 保留历史阶段上下文，内部可能出现旧路径或阶段性命名；当前仓库应以 `architecture/`、`workflows/`、`reporting/` 中的说明为准。
