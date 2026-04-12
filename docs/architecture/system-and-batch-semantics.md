# System And Batch Semantics

仓库显式区分系统级长期知识与批次级运行产物。

## System

系统表示一个待监测业务系统或被观测对象集合。

建议命名：

- `bizsystem_1065`
- `nb_mobile_legal_affairs`

路径：

`knowledge/monitored_systems/<system_key>/`

这里存放跨批次长期存在的内容，例如：

- system profile
- mappings
- context
- review queue

## Batch

批次表示某个系统某一次独立监测、巡检、诊断或专项排查。

建议命名：

- `2026-04-monthly-check`
- `2026-04-12-special-slow-api`

路径：

`artifacts/monitored_systems/<system_key>/<batch_key>/`

这里存放本次运行独有的内容，例如：

- capture 结果
- packs
- diagnostics
- evidence
- report materials
- reports

## 复用与隔离

- 复用上次沉淀时，优先复用 `knowledge/` 下的系统级信息。
- 如果需要参考旧批次结果，应把复用动作显式带入新批次目录，而不是和旧批次共用同一套运行文件。
- 新开批次时，只继承最小系统背景，不继承旧批次运行产物。
