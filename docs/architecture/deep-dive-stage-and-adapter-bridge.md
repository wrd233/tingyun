# 深挖阶段设计：与第一阶段主表的关联方式、文件结构、可复用 pack 与 adapter 改进点

> 本文档是当前 deep-dive 阶段与 master table 主线衔接方式的正式补充文档。adapter 的上位设计仍以 [adapter-design-and-intermediate-artifacts.md](/Users/wangrundong/work/mywork/docs/architecture/adapter-design-and-intermediate-artifacts.md) 为准。

## 1. 当前定位

当前仓库已经把第一阶段主线收敛为：

`00_raw_exports -> 01_prepared_tables -> 02_master_tables -> 03_evidence_indexes`

deep-dive 阶段不是另起一套 shortlist，也不是让旧 pack 世界重新取代主表，而是：

- 继续以 `02_master_tables/` 中的对象为主线
- 用 `04_deep_dive/` 承接一对多的 deep-dive bundle
- 让 adapter 的 `candidate_registry / deep_dive_targets / page_links / screenshot_hints / evidence_linkage` 成为 deep-dive bundle 的上游协议来源

主表负责对象身份、状态摘要与回写锚点；deep-dive bundle 负责对象级详情与证据集合。

## 2. 与 master tables 的关系

主表仍是 deep-dive 的锚点，不是一次性筛选结果。当前各类主表至少应保留：

- `object_id`
- `object_type`
- `selected_for_deep_dive`
- `followup_status`
- `followup_note`
- `deep_dive_count`
- `deep_dive_status`
- `latest_deep_dive_id`
- `latest_deep_dive_at`
- `evidence_status`
- `related_object_ids`
- `report_group_hint`

边界是：

- 主表只保留状态摘要，不展开所有 deep-dive 明细
- deep-dive 完成后，主表必须留下回写痕迹
- 详细 trace、page link、截图提示、依赖上下文应放入 deep-dive bundle

## 3. diagnostics 目录中的 deep-dive 层

在现有 diagnostics 主线之后，当前推荐显式补出：

```text
diagnostics/
├── 00_raw_exports/
├── 01_prepared_tables/
├── 02_master_tables/
├── 03_evidence_indexes/
└── 04_deep_dive/
    ├── deep_dive_registry.csv
    ├── request/
    ├── sql/
    ├── interface_cluster/
    ├── application/
    ├── dependency/
    └── shared/
```

这里的语义是：

- `deep_dive_registry.csv`
  - 全局索引，一行代表一份 deep-dive bundle
- `request/<object_id>/<deep_dive_id>/`
  - 某个请求对象的一份深挖 bundle
- `sql/<object_id>/<deep_dive_id>/`
  - 某个 SQL 对象的一份深挖 bundle
- `shared/`
  - 暂时还没有单独 master table 的共享问题簇、跨对象线索或过渡材料

## 4. deep_dive_registry.csv 的字段

当前 registry 至少应记录：

- `deep_dive_id`
- `object_id`
- `object_type`
- `system_key`
- `batch_key`
- `source_master_table`
- `deep_dive_kind`
- `deep_dive_scope`
- `pack_source`
- `status`
- `summary`
- `evidence_count`
- `page_link_count`
- `screenshot_hint_count`
- `generated_at`
- `bundle_path`

当前仓库还额外保留了几列，作为问题簇与对象关系的正式落盘入口：

- `related_object_ids`
- `suspected_cluster_key`
- `report_group_hint`

## 5. 一对象多份深挖信息的处理方式

deep-dive 现在明确采用“一对象对多 bundle”的组织方式，而不是把所有详情硬塞进主表一行。

推荐目录形态：

```text
04_deep_dive/request/<object_id>/<deep_dive_id>/
04_deep_dive/sql/<object_id>/<deep_dive_id>/
04_deep_dive/interface_cluster/<object_id>/<deep_dive_id>/
```

当前 bundle 目录骨架允许包含：

- `summary.json`
- `evidence_index.csv`
- `page_links.json`
- `screenshot_hints.csv`
- `related_objects.json`
- `pack_payloads/`
- `notes.md`

这样一个对象就可以同时挂多份：

- `trace_primary`
- `sql_bottleneck`
- `dependency_chain`
- `database_component_context`
- `manual_review_note`

## 6. adapter 当前应复用的能力

当前 deep-dive 阶段不重做候选池，而是复用 adapter 已有能力：

- `BuildSession.candidate_registry`
- `BuildSession.deep_dive_budget`
- `report_fact_enhancements.deep_dive_targets`
- `page_links / screenshot_hints / evidence_linkage`

当前优先保留为 deep-dive 阶段复用的 pack：

- `trace_case_pack`
- `database_component_pack`
- `nosql_component_pack`
- `connection_pool_pack`
- `topology_dependency_pack`
- `external_dependency_pack`
- `page_experience_pack`
- `business_labels_pack`
- `stability_signals_pack`
- `impact_signals_pack`
- `comparison_signals_pack`

不再把旧 shortlist 或 `action_hotspot_pack` 重新拉回第一阶段主线。

## 7. 当前仓库已经补出的协议骨架

### 7.1 adapter 侧

新增了 `tingyun_adapter/usecases/deep_dive_protocol.py`，用于把 `deep_dive_targets` 规范化成更适合落回 master table 的 deep-dive 种子信息，至少包括：

- `object_type`
- `source_master_table`
- `deep_dive_kind`
- `deep_dive_scope`
- `pack_source`
- `master_match_hints`
- `related_object_ids`
- `report_group_hint`

它解决的是“让 adapter 输出显式带上 deep-dive 桥接协议”，而不是一次性解决所有 `object_id` 精确回写问题。

### 7.2 client 侧

`master_tables_pipeline.py` 现在会：

- 在 `materialize_master_tables()` 后自动初始化 `04_deep_dive/`
- 创建 `deep_dive_registry.csv`
- 给主表补齐 deep-dive 摘要字段默认值
- 提供 deep-dive bundle 初始化与 registry 同步辅助函数

当前 client 侧的正式 deep-dive 物化入口已经补齐为：

- `python3 -m tingyun_adapter_client.materialize_deep_dive`
- `tingyun-materialize-deep-dive`
- `python3 -m tingyun_adapter_client.cli materialize-deep-dive`

它会从 `report_fact_pack.json` 或 review bundle JSON 中读取：

- `deep_dive_targets`
- `selected_target_expansions`

并完成：

- seed 匹配到 master table
- registry 落盘
- bundle 目录物化
- master table 回写
- evidence index 回写

当前优先支持的对象类型是：

- `request`
- `sql`
- `interface_cluster`

## 8. 当前仍然保留的 adapter 缺口

1. adapter 还没有在 pack 构建阶段直接产出“精确等于 master table object_id”的回写键
2. dependency / topology 还没有正式进入独立 master table
3. deep-dive 完成后的主表回写还主要是 client 侧辅助逻辑，adapter 侧还没有统一回写 API
4. 不同 pack 的证据明细还没有完全统一成同一份 bundle manifest 协议

## 9. 下一步最值得继续补齐的点

1. adapter 直接输出 `master_match_hints -> object_id` 的映射协议
2. deep-dive bundle 里统一 evidence manifest / screenshot template / page link template
3. 补一个“deep-dive 完成后回写主表”的稳定入口，而不是只靠人工改 CSV
