# Directory Responsibilities

## 根目录

- 只保留长期主干
- 不再承载日期化调试文件、临时 pack 结果、缓存 markdown/json

## `reference/`

- 长期外部参考资料
- 不存放过程性产物

## `docs/`

- 长期版本化说明
- 解释结构、流程、术语和决策

## `samples/`

- 稳定样例
- 可入库
- 供 agent 阅读和回归对照

## `knowledge/`

- 系统级长期知识
- 跨批次复用

## `artifacts/`

- 批次级本地运行产物
- 默认不入库

## 三大主工程

- `tingyun_cdp_capture/`：抓取与回放工程
- `tingyun_adapter/`：诊断中间层
- `tingyun_adapter_client/`：远程调用与本地物化
