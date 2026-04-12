# Artifacts

`artifacts/` 是本地运行产物工作区，默认不入库。

## 组织方式

路径：

`artifacts/monitored_systems/<system_key>/<batch_key>/`

典型子目录：

- `capture/`
- `packs/`
- `diagnostics/`
- `evidence/`
- `report_materials/`
- `reports/`

## 规则

- 每个批次单独隔离
- 可以复用系统级知识，但不能与历史批次共用同一套运行文件
- 新增真实运行结果默认写到这里，而不是主工程源码目录
