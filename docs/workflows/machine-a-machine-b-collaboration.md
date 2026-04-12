# Machine A / Machine B Collaboration

顶层架构与协作主说明以 [project-overall-architecture-and-collaboration.md](/Users/wangrundong/work/mywork/docs/architecture/project-overall-architecture-and-collaboration.md) 为准；本文件只补充机器 A / 机器 B 的协作边界与落盘方式。

## 机器 A

主要职责：

- 访问听云平台
- 运行 `tingyun_adapter/`
- 管理 token、样本能力、service API key

## 机器 B

主要职责：

- 运行 `tingyun_adapter_client/`
- 调用机器 A 暴露的 adapter 服务
- 物化本地材料目录
- 供 agent、Codex、写作者继续消费

## 协作边界

- capture 用来确认平台行为和关键链路，不替代机器 B 的材料物化
- adapter 负责中间层结构，不负责批次目录归档
- client 负责把 pack 与 export view 落到本地目录，不负责平台抓取

## 推荐结果落盘方式

机器 B 侧产物应优先落在：

`artifacts/monitored_systems/<system_key>/<batch_key>/`

典型子目录：

- `packs/`
- `diagnostics/`
- `evidence/`
- `report_materials/`
- `reports/`

其中 `diagnostics/` 如果承载 APM 导出到主表的流水线，内部建议继续固定为：

- `00_raw_exports/`
- `01_prepared_tables/`
- `02_master_tables/`
- `03_evidence_indexes/`
