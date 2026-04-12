# APM 导出列表作为主表基础的适配性分析与主表生成流程设计（修订版）

> 本文档是当前 APM 导出列表到主表流水线的主设计说明。

## 1. 文档定位

这份文档聚焦于这样一件事情：
我现在已经可以从 APM 平台导出几份相对稳定的列表型文件，那么这些文件是否适合作为各类主表的基础？如果适合，应该怎样重新设计这些表格？以及从“获取表格 → 放到对应文件夹 → 用代码做首轮筛选 → 转化为各个主表”这一整条流程，应该如何落地。

这份修订版重点吸收了三个新要求：

1. 一次诊断中，同一类导出可能不止一张，例如数据库 SQL 导出往往会按数据库实例分别导出，因此必须考虑多张表的整合方式；
2. 原先建议的 `第二阶段操作`、`第二阶段理由` 两列过于生硬，而且与“第二阶段”强耦合，需要调整成更通用、能贯穿整个主表生命周期的字段；
3. 归一基础表与首轮筛选结果表不必拆成两个阶段，这一部分应由代码完成，而不是交给大模型处理。

因此，本版文档不再把流程理解为“原始导出 → 归一基础表 → 首轮筛选表 → 主表”，而是调整为：

> **原始导出 → 代码生成准备表（归一 + 首轮筛选注记）→ 主表 → 证据索引 / 写作派生产物**

也就是说，主表前的那一层，仍然保留全量记录，但已经同时完成：

- 字段归一；
- 多文件整合；
- 首轮筛选标记；
- 候选对象初步收束；
- 主表物化准备。

## 2. 当前可直接拿到的几份列表，以及我对它们的基本判断

结合当前样例目录里的几份 CSV / Excel，我仍然认为它们可以作为主表基础，但它们更准确的定位应该是：

- 平台导出表；
- 主表生成前的基础底稿；
- 对象候选池的原始输入；
- 准备表生成脚本的输入来源。

### 2.1 应用级概览表：`graph_overview_export_application__application_overview-*.csv`

这份表更适合作为 **应用主表 / 系统整体状态表** 的基础。

它天然回答的是：

- 哪些应用当前状态较差；
- 哪个应用慢请求多；
- 哪个应用错误率更突出；
- 哪个应用在全局上值得先看。

因此我仍然建议把它定位成：

- `application_prepared.csv` 的基础输入；
- 系统整体状态主表的主要来源；
- 报告中“检测范围与整体状态”部分的核心素材。

它不适合承担细粒度对象深挖任务。

### 2.2 请求概览表：`graph_overview_export_request__request_overview-*.csv`

这份表提供：

- Apdex；
- P50 / P75 / P95 / P99；
- 平均请求时间；
- 请求数；
- 吞吐率；
- 错误率；
- 错误次数；
- 慢次数；
- 异常次数；
- 请求类型。

它非常适合做 **事务 / 请求主表的增强输入**，尤其适合补充分位数、异常次数和请求类型。

但我仍然不建议把它单独作为事务主表的唯一基础，因为它不如 `action_list_export` 那样适合直接做影响面排序。

### 2.3 事务列表表：`action_list_export__actionList-*.csv`

这份表仍然是当前最适合做 **事务 / 请求主表首轮筛选基础表** 的文件。它提供：

- 事务别名；
- 名称；
- 平均响应时间；
- 总耗时；
- 耗时百分比；
- 请求数；
- 吞吐率；
- 错误率 / 错误数；
- 慢次数；
- 应用。

因此我仍然建议：

- `action_list` 负责“先把谁筛出来”；
- `request_overview` 负责“补齐运行画像”；
- 二者合并后形成 `request_prepared.csv`，再进一步物化为 `request_master.csv`。

### 2.4 服务接口列表：`interface_list_export__interfaceList-*.csv`

这份表更适合做 **接口簇主表 / 服务接口摘要表** 的基础，而不是细粒度事务主表的替代品。

它的价值主要在于：

- 接口簇摘要；
- 高一层的服务接口聚合视图；
- 帮助把多个事务归并到同一个接口簇或问题簇；
- 在报告里承接“重点接口簇概览”。

因此它仍然应定位为：

- `interface_cluster_prepared.csv` 的来源；
- 接口簇级主表的基础；
- 事务主表的上层聚合参考。

### 2.5 数据库 SQL 导出：`component_analysis_export_database__SQL_.xls`

这类 Excel 仍然是最适合做 **SQL 主表基础** 的导出。但这里必须强调一个新要求：

> **一次诊断中，这类导出往往不止一张，而是每个数据库实例各有一张。**

因此 SQL 这块不能再按“单文件 → 单主表”去理解，而要按“同类多文件 → 统一整合 → 主表物化”来设计。

这些 Excel 当前已经提供：

- SQL 文本；
- 平均响应时间；
- 响应总时间；
- 吞吐率；
- 执行次数；
- 错误次数；
- 慢次数。

所以它们仍然很适合作为 `sql_prepared_full.csv` 的基础来源，但主表生成时必须考虑：

- 每张 Excel 来自哪个数据库实例；
- 同一条 SQL 是否跨数据库重复出现；
- 同一数据库是否存在多次导出；
- 全局优先级和库内优先级应如何同时保留。

### 2.6 NoSQL 导出：`component_analysis_export_nosql__SQL_.xls`

这类导出当前仍然更适合作为 **NoSQL / 组件操作附表** 的基础，而不是和 SQL 主表完全同级的主工作台。

如果未来 NoSQL 导出行数增多，再提升为独立重点主表更合适。

## 3. 结论：哪些适合作为各个主表的基础

综合来看，我建议这样定。

### 3.1 应用主表

**基础来源：**

- `graph_overview_export_application__application_overview-*.csv`

**输出准备表：**

- `application_prepared.csv`

**输出主表：**

- `application_master.csv`

### 3.2 事务 / 请求主表

**基础来源：**

- 主基础表：`action_list_export__actionList-*.csv`
- 增强表：`graph_overview_export_request__request_overview-*.csv`

**输出准备表：**

- `request_prepared.csv`

**输出主表：**

- `request_master.csv`

### 3.3 接口簇主表

**基础来源：**

- `interface_list_export__interfaceList-*.csv`

**输出准备表：**

- `interface_cluster_prepared.csv`

**输出主表：**

- `interface_cluster_master.csv`

### 3.4 SQL 主表

**基础来源：**

- 多张 `component_analysis_export_database__SQL_.xls`

**输出准备表：**

- `sql_prepared_full.csv`
- （可选）`sql_prepared__<db_key>.csv`

**输出主表：**

- `sql_master.csv`
- （可选）`sql_database_summary.csv`

这里的关键不是“把多张表简单拼起来”，而是：

- 先保留每张表的数据库来源；
- 再做统一字段归一；
- 再做全局筛选和分库保底筛选；
- 最后物化为一个全局 SQL 主表。

### 3.5 NoSQL / 组件操作附表

**基础来源：**

- `component_analysis_export_nosql__SQL_.xls`

**输出准备表：**

- `nosql_prepared.csv`

**输出主表：**

- `nosql_master.csv`

## 4. 为什么这些原始导出不能直接等于最终主表

这些平台导出很有用，但它们更像“平台导出表”而不是“持续演化的工作底稿”。

它们缺少的关键内容包括：

### 4.1 缺少统一对象标识与来源标识

例如：

- `object_id`
- `object_type`
- `canonical_name`
- `display_name`
- `source_case_key`
- `source_file`
- `source_export_key`
- `source_component_key`
- `source_db_key`

### 4.2 缺少首轮筛选注记

例如：

- `bucket_hits`
- `screening_score`
- `screening_reason`
- `selected_for_master`
- `selected_by_global_rank`
- `selected_by_db_rank`

### 4.3 缺少后续跟进状态与说明

原先我建议过 `第二阶段操作`、`第二阶段理由`，但这两个字段过于生硬，而且与“第二阶段”强绑定。

本版建议统一改成：

- `followup_status`
- `followup_note`

中文显示时可以解释为：

- `跟进状态`
- `跟进说明`

这样更自然，也更适合贯穿整个生命周期，而不是只在所谓“第二阶段”使用。

`followup_status` 可以采用如下取值：

- `待确认`
- `继续深挖`
- `保留观察`
- `合并处理`
- `降级观察`
- `排除`
- `已确认`

`followup_note` 则使用自然语言记录原因，例如：

- 为什么继续深挖；
- 为什么被排除；
- 为什么与其他对象合并；
- 为什么暂时只保留观察。

### 4.4 缺少证据与写作挂接字段

例如：

- `evidence_status`
- `page_link_count`
- `trace_link_count`
- `screenshot_hint_status`
- `report_group_hint`
- `related_object_ids`
- `writing_note`

## 5. 我建议的表格重新设计方式（修订版）

这次我不再建议拆成“归一基础表”和“首轮筛选结果表”两个阶段，而是建议收成三层。

### 5.1 第 0 层：原始导出层（Raw Exports）

这一层只保存平台导出的原文件，不做语义重构。

### 作用

- 保留平台原貌；
- 便于回放和核验；
- 提供准备脚本输入；
- 保留来源证明。

### 5.2 第 1 层：准备表（Prepared Tables）

这是本次修订最重要的调整。

这一层由 **代码** 直接生成，统一完成两件事：

1. 字段归一；
2. 首轮筛选注记。

也就是说，这一层仍然保留全量，但已经在每一行上补齐：

- 统一字段；
- 来源信息；
- 对象键；
- bucket 命中情况；
- 初步筛选得分；
- 是否进入主表候选。

### 推荐输出

- `application_prepared.csv`
- `request_prepared.csv`
- `interface_cluster_prepared.csv`
- `sql_prepared_full.csv`
- `nosql_prepared.csv`

对于 SQL，可以再额外输出：

- `sql_prepared__<db_key>.csv`

作为按数据库实例拆开的调试视图，但真正的主线仍应是 `sql_prepared_full.csv`。

### 这一层的特点

- 仍然保留全量；
- 不交由大模型处理；
- 由脚本完成字段归一和首轮筛选注记；
- 既是主表物化前的基础底稿，也是后续调试和追溯的依据。

### 5.3 第 2 层：主表（Master Tables）

这一层才是我真正频繁阅读、更新、写报告时使用的主表。

### 推荐输出

- `application_master.csv`
- `request_master.csv`
- `interface_cluster_master.csv`
- `sql_master.csv`
- `nosql_master.csv`

### 特点

- 数量受控；
- 行数已经经过首轮筛选；
- 可持续更新；
- 可以继续挂接证据和写作线索；
- 真正承担“工作底稿”职责。

### 这层建议重点保留的状态字段

- `followup_status`
- `followup_note`
- `evidence_status`
- `related_object_ids`
- `report_group_hint`
- `writing_note`

### 5.4 第 3 层：证据索引与写作派生产物

这一层不是主表本身，但与主表保持稳定关联。

### 推荐输出

- `request_evidence_index.csv`
- `sql_evidence_index.csv`
- `writer_input.md`
- `issue_inventory.csv`
- 其他 report bundle 派生产物

也就是说：

- 主表是主线；
- 证据索引和写作输入由主表再派生；
- 不应反过来让 report bundle 取代主表成为主线对象。

## 6. SQL 多文件整合的专门设计

这是本次修订新增的重点。

### 6.1 原则

对于数据库 SQL 导出，我建议采用：

> **按数据库保留来源 + 在准备表层统一整合 + 在主表层统一筛选与展示**

也就是说，不要简单地“每个数据库一个 SQL 主表”长期并行，也不要完全丢掉数据库来源。

### 6.2 原始导出层的组织方式

建议在 `00_raw_exports/sql_database/` 下按数据库实例分目录：

```text
00_raw_exports/
└── sql_database/
    ├── db_main/
    │   ├── component_analysis_export_database__SQL_.xls
    │   └── summary.json
    ├── db_archive/
    │   ├── component_analysis_export_database__SQL_.xls
    │   └── summary.json
    └── ...
```

同时在 `export_registry.json` 中记录：

- `source_export_key`
- `source_component_key`
- `source_db_key`
- `source_db_name`
- `source_file`
- `sha1`
- `collected_at`

### 6.3 准备表层的整合方式

脚本读取所有数据库 SQL 导出后，统一输出：

- `sql_prepared_full.csv`

每一行必须保留：

- `source_db_key`
- `source_db_name`
- `source_file`
- `source_row_rank_in_db`
- `source_total_rows_in_db`

同时做 SQL 归一，补出：

- `sql_group_key`
- `representative_sql`
- `query_object_hint`

这里我建议把主键理解成：

- **对象主键 = `source_db_key + sql_group_key`**

而不是单纯按 `sql_group_key` 合并。因为同一类 SQL 在不同数据库实例上的表现可能完全不同，不能过早合并成一行。

### 6.4 首轮筛选时的整合策略

SQL 的首轮筛选不要只做全局排序，否则一个流量很大的数据库可能把候选池全部占满。

我建议同时保留两种选择机制：

1. **全局筛选**
   - 在所有数据库 SQL 上统一按 `avg_rt_ms`、`total_time_ms`、`exec_count`、`slow_count` 等做排序；

2. **分库保底筛选**
   - 每个数据库实例至少保留若干条本库内最值得关注的 SQL；
   - 保证小库不会完全被大库淹没。

这样生成的准备表中，可以增加：

- `selected_by_global_rank`
- `selected_by_db_rank`
- `selected_for_master`

### 6.5 主表层的表达方式

最终 `sql_master.csv` 仍然建议是一张全局主表，但必须保留来源库信息，例如：

- `source_db_key`
- `source_db_name`
- `sql_group_key`
- `representative_sql`
- `avg_rt_ms`
- `total_time_ms`
- `exec_count`
- `slow_count`
- `bucket_hits`
- `screening_score`
- `screening_reason`
- `followup_status`
- `followup_note`

这样既保持统一阅读，又不丢失数据库来源。

如果后续报告确实需要按数据库分章，还可以再从这张全局主表派生出“按数据库过滤视图”，而不是在最早阶段就把主线拆散。

## 7. 我建议的主表字段设计（修订版）

### 7.1 应用主表：`application_master.csv`

建议字段：

- `object_id`
- `system_key`
- `batch_key`
- `application_name`
- `health_status`
- `apdex`
- `score`
- `response_p50_ms`
- `tps`
- `request_count`
- `error_rate_pct`
- `error_count`
- `slow_count`
- `bucket_hits`
- `screening_score`
- `screening_reason`
- `selected_for_master`
- `followup_status`
- `followup_note`
- `writing_note`

### 7.2 事务 / 请求主表：`request_master.csv`

建议字段：

- `object_id`
- `system_key`
- `batch_key`
- `canonical_name`
- `display_name`
- `alias_name`
- `application_name`
- `request_type`
- `interface_cluster_key`
- `avg_rt_ms`
- `p50_ms`
- `p75_ms`
- `p95_ms`
- `p99_ms`
- `apdex`
- `total_time_ms`
- `time_share_pct`
- `request_count`
- `tps`
- `error_rate_pct`
- `error_count`
- `slow_count`
- `exception_count`
- `bucket_hits`
- `screening_score`
- `screening_reason`
- `selected_for_master`
- `followup_status`
- `followup_note`
- `evidence_status`
- `related_sql_count`
- `related_object_ids`
- `report_group_hint`
- `writing_note`

### 7.3 接口簇主表：`interface_cluster_master.csv`

建议字段：

- `object_id`
- `system_key`
- `batch_key`
- `cluster_name`
- `application_name`
- `total_time_ms`
- `avg_rt_ms`
- `request_count`
- `tps`
- `error_rate_pct`
- `error_count`
- `related_request_count`
- `related_request_ids`
- `bucket_hits`
- `screening_score`
- `screening_reason`
- `selected_for_master`
- `followup_status`
- `followup_note`
- `report_group_hint`
- `writing_note`

### 7.4 SQL 主表：`sql_master.csv`

建议字段：

- `object_id`
- `system_key`
- `batch_key`
- `source_db_key`
- `source_db_name`
- `sql_group_key`
- `representative_sql`
- `query_object_hint`
- `avg_rt_ms`
- `total_time_ms`
- `qps`
- `exec_count`
- `error_count`
- `slow_count`
- `bucket_hits`
- `screening_score`
- `screening_reason`
- `selected_by_global_rank`
- `selected_by_db_rank`
- `selected_for_master`
- `followup_status`
- `followup_note`
- `evidence_status`
- `related_request_ids`
- `report_group_hint`
- `writing_note`

### 7.5 NoSQL / 组件操作主表：`nosql_master.csv`

建议字段：

- `object_id`
- `system_key`
- `batch_key`
- `command_name`
- `representative_command`
- `avg_rt_ms`
- `total_time_ms`
- `qps`
- `exec_count`
- `error_count`
- `slow_count`
- `bucket_hits`
- `screening_score`
- `screening_reason`
- `selected_for_master`
- `followup_status`
- `followup_note`
- `writing_note`

## 8. 这些文件应该上传到哪个文件夹（修订版）

结合你当前仓库已经明确的“样例 / 知识 / 运行产物”边界，我建议这样放。

### 8.1 如果是当前真实批次的 APM 导出

应放到：

`artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics/00_raw_exports/`

并按对象类型分目录：

```text
artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics/
├── 00_raw_exports/
│   ├── application/
│   ├── request/
│   ├── action/
│   ├── interface/
│   ├── sql_database/
│   │   ├── <db_key_1>/
│   │   ├── <db_key_2>/
│   │   └── ...
│   ├── sql_nosql/
│   └── summaries/
├── 01_prepared_tables/
├── 02_master_tables/
└── 03_evidence_indexes/
```

和上一版相比，本版做了两个关键调整：

1. 明确 SQL 数据库导出应按数据库实例分目录；
2. 不再拆出 `01_normalized/` 和 `02_screened/` 两层，而是合并为 `01_prepared_tables/`。

### 8.2 如果是希望入库保留的稳定样例

应放到：

`samples/monitored_systems/<system_key>/<sample_batch_key>/diagnostics/`

目录层次建议与真实批次保持一致，这样样例和真实运行路径之间更容易对照。

## 9. 从“获取表格”到“主表生成”的完整流程设计（修订版）

下面给出一个更适合代码落地的版本。

### 9.1 第一步：获取表格并保留来源证明

#### 输入

来自 adapter / client 当前已有导出能力的原始文件：

- CSV / XLS；
- 对应的 `*_summary.json`。

#### 动作

1. 原始文件按类型落到 `00_raw_exports/`；
2. SQL 数据库导出按数据库实例分目录；
3. 同时保留 `summary.json`；
4. 用一个索引文件登记本批次已拿到哪些表。

#### 建议新增索引文件

`00_raw_exports/export_registry.json`

记录：

- `system_key`
- `batch_key`
- `source_case_key`
- `source_export_key`
- `source_component_key`
- `source_db_key`
- `source_db_name`
- `source_file`
- `sha1`
- `byte_size`
- `collected_at`

### 这一步的重点

这一步不是分析，而是先把来源固定住。后面所有准备表和主表都应该能追溯回这些原始导出。

### 9.2 第二步：用代码直接生成准备表（归一 + 首轮筛选注记）

#### 脚本建议

- `prepare_master_table_inputs.py`

如果你更希望按对象类型拆脚本，也可以拆成：

- `prepare_application_table.py`
- `prepare_request_table.py`
- `prepare_interface_cluster_table.py`
- `prepare_sql_table.py`
- `prepare_nosql_table.py`

但我更倾向于先有一个总入口脚本，再按内部模块拆实现。

#### 输入

- `00_raw_exports/` 下的原始 CSV / XLS / summary.json；
- 可选的筛选配置文件，例如 `screening_rules.json`。

#### 输出

- `01_prepared_tables/application_prepared.csv`
- `01_prepared_tables/request_prepared.csv`
- `01_prepared_tables/interface_cluster_prepared.csv`
- `01_prepared_tables/sql_prepared_full.csv`
- `01_prepared_tables/nosql_prepared.csv`
- （可选）`01_prepared_tables/sql_prepared__<db_key>.csv`

#### 这一步做什么

1. 统一编码、字段名、数值格式；
2. 多文件整合；
3. 为每条记录补元数据列；
4. 生成对象基础键；
5. 对 SQL 做最基础的清洗、截断与分组；
6. 同时完成 bucket 命中、分数计算与候选标记；
7. 输出全量准备表。

### 这一步的重要约束

这一层必须由代码实现，而不是交给大模型。

也就是说，首轮筛选的基础判断应该被显式写成：

- 可配置规则；
- 可复跑脚本；
- 可追溯输出。

而不是由模型临时阅读 CSV 再凭自然语言做首轮筛选。

### 9.3 第三步：首轮筛选原则（由代码执行）

我仍然不建议只给一个总分，而是保留多个筛选桶（bucket），并在准备表中记录命中结果。

#### 9.3.1 事务 / 请求类筛选桶

建议保留：

- 高平均响应时间；
- 高访问慢请求；
- 高错误率请求；
- 高访问高错误请求；
- 高总耗时请求；
- 高慢次数请求；
- 极端低频离群点。

准备表中建议记录：

- `bucket_hits`
- `screening_score`
- `screening_reason`
- `selected_for_master`

#### 9.3.2 SQL 类筛选桶

建议保留：

- 高平均响应时间 SQL；
- 高总耗时 SQL；
- 高频但不够快的 SQL；
- 高慢次数 SQL；
- 高错误 SQL；
- 分库保底 SQL。

其中最后一个是本次修订新增的重点：

- 即便某个数据库在全局上不够突出，也要保留其库内最值得关注的 SQL；
- 这样可以避免候选池完全被单个大库占满。

#### 9.3.3 应用类筛选桶

应用主表更简单，主要看：

- `apdex`
- `score`
- `error_rate_pct`
- `slow_count`

目标不是产生很多对象，而是明确全局优先级。

### 9.4 第四步：从准备表物化为主表

#### 脚本建议

- `materialize_master_tables.py`

#### 输入

- `01_prepared_tables/*`

#### 输出

- `02_master_tables/application_master.csv`
- `02_master_tables/request_master.csv`
- `02_master_tables/interface_cluster_master.csv`
- `02_master_tables/sql_master.csv`
- `02_master_tables/nosql_master.csv`

#### 这一步做什么

1. 只保留进入工作台的对象；
2. 把 bucket 命中与筛选原因固化进主表；
3. 补齐阅读友好的列顺序与显示字段；
4. 预留 `followup_status`、`followup_note`、`evidence_status`、`report_group_hint` 等后续列。

### 一个关键原则

不要让准备表直接充当主表。

准备表仍然偏“程序加工底稿”，而主表应当更偏“人工阅读、持续更新、可直接进报告的工作台”。

### 9.5 第五步：后续深挖时持续回写主表

这一层不再使用 `第二阶段操作` / `第二阶段理由` 这种强耦合命名，而是统一回写：

- `followup_status`
- `followup_note`

这样后续无论是：

- 继续深挖；
- 保留观察；
- 合并处理；
- 降级观察；
- 排除；
- 已确认；

都能用一套稳定字段表达。

同时新增附属索引：

- `03_evidence_indexes/request_evidence_index.csv`
- `03_evidence_indexes/sql_evidence_index.csv`

这两张表负责挂接：

- trace；
- page URL；
- screenshot hint；
- 依赖关系；
- 其他证据说明。

主表中只保留状态和关联键，不把所有证据细节硬塞进去。

## 10. 我建议保留并沿用的当前能力

这一整条流程里，我不建议推倒重来，以下能力都可以继续沿用：

### 10.1 adapter / client 的导出能力

当前既然已经能导出：

- action list；
- request overview；
- application overview；
- interface list；
- database SQL xls；
- nosql xls；
- summary json；

那么这部分能力不需要重做。

### 10.2 diagnostics 作为原始诊断材料容器

当前 `diagnostics` 目录语义本身没有问题。需要优化的是它的内部层次，而不是否定这个目录。

### 10.3 report bundle 的后续思路

主表、证据索引、写作输入、问题矩阵这些东西，最终仍然可以继续流向 report bundle。

也就是说，这次把主表流程重新设计清楚，并不是和最终交付方向冲突，而是给它提供更稳定的基础。
