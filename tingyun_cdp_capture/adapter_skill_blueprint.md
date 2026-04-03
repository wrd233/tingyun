# 听云 Adapter + Skill 建设蓝图与 Adapter 设计文档

生成时间：2026-04-03  
工作目录：`/Users/wangrundong/work/mywork/tingyun_cdp_capture`  
参考资料：

- `captured_api/` 当前抓包接口样本
- `api_analysis_priority.md`
- `api_report_shortlist.md`
- `tingyun_manual_context_and_component_mapping.md`
- `tingyun_system_skeleton_diagnostic_playbook.md`
- `基调听云应用与微服务用户使用手册.pdf`

## 1. 文档目标

这份文档回答三个问题：

1. `adapter/adapt` 层应该是什么，不应该是什么。
2. 基于 `adapter` 之上的 `skill` 应该怎么建设，分层和边界如何设计。
3. 基于当前已经掌握的听云接口，如何设计一份覆盖核心功能的 `adapter`。

本文档的定位不是产品 PRD，也不是代码实现说明，而是：

- 后续建设方向的统一设计底稿
- adapter 设计文档
- skill 设计思路文档

## 2. 设计前提

你现在对系统的理解已经不是“零散抓包结果”，而是一套围绕以下骨架组织的诊断系统：

`业务系统 -> 应用 / 实例 -> 事务 / action -> trace -> 下游组件（Database / NoSQL / MQ / 连接池）`

这是非常正确的出发点，因为当前抓到的大多数接口也确实围绕这套对象层次组织。

因此，后续的 `adapter` 和 `skill` 设计，都不应该从“某个页面发了哪些请求”出发，而应该从“系统中有哪些对象、对象之间有什么关系、什么证据能支撑诊断”出发。

## 3. 总体建设思路

建议整体建设分成两层：

### 3.1 第一层：Adapter / Adapt

职责：

- 向下连接听云原始接口
- 向上输出面向分析的结构化事实包
- 统一对象、字段、关系、证据和下钻链路

不负责：

- 最终结论生成
- 自动归因闭环
- 最终成文报告

一句话概括：

`adapter` 是“面向分析与报告的数据整理层”。

### 3.2 第二层：Skill

职责：

- 消费 adapter 输出
- 组织分析逻辑
- 生成报告、问题清单、诊断结论、优化建议

不负责：

- 直接理解零散原始接口
- 直接处理复杂主键和页面上下文
- 直接兼容各种字段不一致问题

一句话概括：

`skill` 是“面向诊断解释与报告生成的认知层”。

## 4. 先明确边界

### 4.1 Adapter 不是这些东西

当前阶段，adapter 不应该被设计成：

- 原始 API 透传代理
- 听云前端页面复刻器
- 自动根因分析引擎
- 最终报告写作器
- 完整监控平台抽象层

### 4.2 Adapter 当前阶段最应该做的事

当前阶段，adapter 最应该稳定完成的是：

- 统一对象模型
- 统一关键键
- 统一字段表达
- 统一证据表达
- 统一下钻路径表达
- 把零散 API 聚合成“分析包”

也就是先把：

- 事实
- 对象
- 关系
- 证据
- 下钻链路

整理好。

## 5. Adapter 的核心设计原则

### 5.1 面向诊断，不面向页面

adapter 输出的基本单位不应该是：

- 页面卡片
- 页面 tab
- 页面图表 JSON

而应该是：

- 业务系统快照
- 热点 action 集合
- trace 证据包
- 数据库组件风险包
- NoSQL 组件风险包
- 连接池风险包

### 5.2 面向对象，不面向接口

原始接口是：

- `webaction/list/actionList`
- `Database/analysis`
- `graph/query/overview`

adapter 输出应该转成对象语义，例如：

- `ActionHotspot`
- `TraceCase`
- `DatabaseComponent`
- `DatabaseOperation`
- `ConnectionPoolState`

### 5.3 保留证据链

adapter 输出不能只留“汇总结论”，必须保留证据。

建议每个重要结论或事实，都保留：

- 来源接口
- 请求参数
- 原始响应中的关键字段
- 提取规则

这样 skill 才能在生成报告时：

- 引用事实
- 回溯证据
- 明确区分事实与推断

### 5.4 容忍原始字段不一致

当前抓包已经明显出现：

- `response` / `respTime` / `responseTime`
- `totalResponse` / `totalResptime`
- `traceId` 数值型与 GUID 型混用
- `throught` 这种不标准拼写
- `opName` 有时是明文，有时是 `tyBase64_...`

adapter 必须承担这些不一致的吸收和归一化。

### 5.5 输出要稳定、短、清晰、关系显式

适合大模型的输入，不应该是巨大的原始响应堆积，而应该是：

- 结构清晰
- 字段含义稳定
- 关键关系显式
- 明确区分 observed / derived / inferred

## 6. Adapter 的目标输出形态

建议 adapter 不直接输出“单接口标准响应”，而是输出三类产物。

### 6.1 领域对象

例如：

- `BizSystem`
- `Application`
- `Instance`
- `Action`
- `Trace`
- `DatabaseComponent`
- `DatabaseOperation`
- `NoSQLComponent`
- `ConnectionPool`

### 6.2 诊断包

例如：

- `system_snapshot`
- `action_hotspot_pack`
- `trace_case_pack`
- `database_component_pack`
- `nosql_component_pack`
- `connection_pool_pack`
- `report_fact_pack`

### 6.3 关系和下钻路径

例如：

- `belongs_to`
- `runs_on`
- `depends_on`
- `cares_about`
- `traced_by`
- `derived_from`
- `drilldown_path`

## 7. Adapter 的统一对象模型

下面这套对象模型建议作为 adapter 的统一语义层。

### 7.1 顶层对象

#### `BizSystem`

核心字段建议：

- `id`
- `name`
- `time_window`
- `overview`
- `health`
- `applications`
- `instances`
- `actions`
- `components`
- `evidence`

#### `Application`

- `id`
- `name`
- `display_name`
- `technology`
- `language`
- `biz_system_id`
- `instance_ids`
- `overview`
- `trends`
- `evidence`

#### `Instance`

- `id`
- `name`
- `application_id`
- `host_ip`
- `host_name`
- `agent_version`
- `one_agent_version`
- `os`
- `evidence`

### 7.2 事务对象

#### `Action`

- `id`
- `type`
- `name`
- `alias`
- `application_id`
- `biz_system_id`
- `metrics`
  - `count`
  - `response_time`
  - `slow_count`
  - `error_count`
  - `total_response_time`
  - `throughput`
- `component_summary`
- `trace_summary`
- `evidence`

#### `ActionHotspot`

这是给 skill 用的二级对象，不一定是永久实体。

- `action_ref`
- `ranking_basis`
- `severity_score`
- `why_selected`
- `evidence`

### 7.3 追踪对象

#### `Trace`

- `trace_id_numeric`
- `trace_guid`
- `action_guid`
- `request_id`
- `timestamp`
- `biz_system_id`
- `application_id`
- `instance_id`
- `action_id`
- `status`
- `duration_ms`
- `error_count`
- `is_slow_trace`
- `suspected_problems`
- `topology_summary`
- `service_flow_summary`
- `timeline_summary`
- `exceptions`
- `logs`
- `evidence`

### 7.4 组件对象

#### `DatabaseComponent`

- `component_type=Database`
- `component_subtype`
- `component_name`
- `biz_system_id`
- `metrics`
  - `count`
  - `resp_time`
  - `throughput`
  - `total_resp_time`
  - `trace_count`
  - `current_pool_used`
  - `max_pool`
- `top_actions`
- `top_operations`
- `top_traces`
- `topology`
- `connection_pool`
- `evidence`

#### `DatabaseOperation`

- `component_ref`
- `op_name_raw`
- `op_name_decoded`
- `decoded`
- `metrics`
  - `resp_time`
  - `count`
  - `total_resp_time`
  - `trace_count`
- `top_actions`
- `top_traces`
- `evidence`

#### `NoSQLComponent`

- `component_type=NoSQL`
- `component_subtype`
- `component_name`
- `biz_system_id`
- `metrics`
- `top_operations`
- `top_traces`
- `topology`
- `evidence`

#### `ConnectionPool`

- `metric_category`
- `database_type`
- `framework`
- `current_used`
- `current_idle`
- `max_active`
- `min_idle`
- `waiter_connections`
- `connection_time_series`
- `pools`
- `evidence`

## 8. Adapter 的证据模型

建议把证据建模成独立对象，而不是散在各个字段里。

### 8.1 `Evidence`

建议字段：

- `id`
- `source_api`
- `source_path`
- `source_method`
- `request_signature`
- `request_params`
- `response_excerpt`
- `extracted_fields`
- `captured_at`
- `confidence`

### 8.2 `ObservedFact`

- `subject_type`
- `subject_id`
- `fact_type`
- `value`
- `unit`
- `evidence_ids`

例如：

- `Action(13220).response_time = 2967 ms`
- `DatabaseComponent(10.190.22.21:3306).count = 60153`
- `Trace(1751280907).duration = 3832.187 ms`

### 8.3 `DerivedFact`

用于 skill 之前的一些轻量衍生，不涉及重推理。

例如：

- `this action is top_1_by_response`
- `this database operation is top_3_by_total_resp_time`
- `this trace is representative_case`

## 9. Adapter 的统一字段归一化规则

这是 adapter 成功的关键，不然后续 skill 会一直和字段不一致打架。

### 9.1 时间字段统一

统一输出：

- `time_window.end_time`
- `time_window.period_minutes`
- `timestamp_ms`

### 9.2 响应时间字段统一

把这些字段尽量映射到统一语义：

- `response`
- `respTime`
- `responseTime`
- `responseTimeMillisecondAvg`

统一成：

- `response_time_ms`

### 9.3 总耗时字段统一

把这些映射到：

- `totalResponse`
- `totalResptime`
- `totalResponseTime`

统一成：

- `total_response_time_ms`

### 9.4 吞吐字段统一

把：

- `throught`

统一映射成：

- `throughput`

同时保留原字段名到 evidence 中。

### 9.5 Trace 键统一

建议明确拆开：

- `trace_id_numeric`
- `trace_guid`
- `action_guid`
- `request_id`

绝不要只保留一个模糊的 `traceId` 字段。

### 9.6 `opName` 解码规则

规则：

1. 如果以 `tyBase64_` 开头
2. 去掉前缀
3. Base64 解码
4. 生成：
   - `op_name_raw`
   - `op_name_decoded`
   - `decoded=true`

否则：

- `op_name_raw = opName`
- `op_name_decoded = opName`
- `decoded=false`

### 9.7 事实和推断区分

adapter 层只做：

- `observed`
- `normalized`
- `lightly_derived`

不要在 adapter 层做：

- `root_cause = X`
- `problem definitely caused by Y`

## 10. Adapter 的能力域设计

下面是 adapter 需要覆盖的核心能力域设计。这里不是抽象概念，而是直接结合当前已掌握接口设计。

## 10.1 能力域 A：业务系统概览适配

目标：

- 输出业务系统整体运行情况的统一快照

主要来源接口：

- `application/business/overview/*`
- `health/healthLevelStatistics`
- `application/charts/response`
- `application/charts/throught`
- `application/charts/error`
- `application/charts/apdex`

adapter 输出建议：

```json
{
  "pack_type": "system_snapshot",
  "biz_system": {
    "id": 1065,
    "name": "集团法务"
  },
  "overview": {
    "apdex": 0.979,
    "application_count": 1,
    "host_count": 2,
    "instance_count": 3,
    "response_time_ms": 122,
    "throughput": 8.39,
    "success_count": 15104,
    "error_rate": 0.0
  },
  "health": {
    "biz_system": {"normal": 1, "warn": 0, "critical": 0},
    "application": {"normal": 1, "warn": 0, "critical": 0},
    "instance": {"normal": 3, "warn": 0, "critical": 0},
    "action": {"normal": 156, "warn": 1, "critical": 3}
  },
  "trends": {
    "response": {...},
    "throughput": {...},
    "error": {...}
  },
  "evidence": [...]
}
```

## 10.2 能力域 B：热点事务适配

目标：

- 找到需要重点分析的 action

主要来源接口：

- `webaction/list/actionList`
- `webaction/overview`
- `webaction/charts/*`
- `webaction/performance/breakdown*`

adapter 输出建议：

```json
{
  "pack_type": "action_hotspot_pack",
  "biz_system_id": 1065,
  "selection_policy": {
    "primary_sort": "response_time_ms",
    "secondary_sort": "slow_count"
  },
  "hotspots": [
    {
      "action": {...},
      "overview": {...},
      "ranking_reason": [
        "top_1_by_response_time",
        "slow_count_high"
      ],
      "component_summary": {...},
      "evidence": [...]
    }
  ]
}
```

## 10.3 能力域 C：trace 列表与 trace 详情适配

目标：

- 从 action 下钻到 trace，再从 trace 形成可供报告引用的证据包

主要来源接口：

- `graph/query/overview` 中 `metric=trace_current_overview`
- `action/trace/detail`
- `action/trace/detail/exceptions`
- `action/trace/callTree`
- `action/trace/detail/snapshotTimeInfo`
- `action/trace/detail/queryAgentVersionInfo`
- `data/logTrace/searchLogTrace`

adapter 输出建议：

```json
{
  "pack_type": "trace_case_pack",
  "trace_selector": {
    "policy": "slowest"
  },
  "trace_case": {
    "trace": {...},
    "suspected_problems": [...],
    "exceptions": [...],
    "call_tree_summary": {...},
    "timeline_summary": {...},
    "service_flow_summary": {...},
    "environment_summary": {...},
    "logs_summary": {...}
  },
  "drilldown_path": [
    "bizSystem -> action -> trace_list -> trace_detail -> call_tree -> exceptions"
  ],
  "evidence": [...]
}
```

## 10.4 能力域 D：Database 组件适配

目标：

- 输出数据库组件级诊断输入

主要来源接口：

- `Database/list`
- `Database/info`
- `Database/analysis`
- `Database/actionName/list`
- `Database/applicationName/list`
- `Database/componentName/list`
- `Database/list/health`
- `Database/operate/analysisList`
- `component/database/actionList`
- `component/database/actionTraceList`
- `component/database/action_item_list`
- `component/database/errorList`
- `graph/component/queryDataBaseGraph`
- `connection/database/chart`

adapter 输出建议：

```json
{
  "pack_type": "database_component_pack",
  "component": {
    "type": "Database",
    "subtype": "MySQL",
    "name": "10.190.22.21:3306"
  },
  "summary": {...},
  "top_operations": [...],
  "top_impacted_actions": [...],
  "top_related_traces": [...],
  "topology": {...},
  "connection_pool": {...},
  "evidence": [...]
}
```

## 10.5 能力域 E：NoSQL 组件适配

目标：

- 输出 Redis/NoSQL 组件诊断输入

主要来源接口：

- `NoSQL/list`
- `NoSQL/overview`
- `NoSQL/analysis`
- `NoSQL/trace`
- `NoSQL/errorTypeAmount`
- `NoSQL/actionName/list`
- `NoSQL/applicationName/list`
- `NoSQL/componentName/list`
- `NoSQL/list/health`
- `graph/component/queryNosqlGraph`

adapter 输出建议：

```json
{
  "pack_type": "nosql_component_pack",
  "component": {
    "type": "NoSQL",
    "subtype": "Redis",
    "name": "10.190.22.20:6379/5"
  },
  "summary": {...},
  "top_operations": [...],
  "top_related_traces": [...],
  "error_summary": {...},
  "topology": {...},
  "evidence": [...]
}
```

## 10.6 能力域 F：连接池适配

目标：

- 输出连接池资源状态适配包

主要来源接口：

- `connection/list`
- `connection/chart`
- `connection/database/chart`

adapter 输出建议：

```json
{
  "pack_type": "connection_pool_pack",
  "pool": {...},
  "summary": {
    "current_used": 5,
    "current_idle": 55,
    "max_active": 60
  },
  "time_series": {...},
  "waiter_risk": {...},
  "evidence": [...]
}
```

## 10.7 能力域 G：组件拓扑适配

目标：

- 输出组件与 action / application 之间的关系图

主要来源接口：

- `graph/component/queryDataBaseGraph`
- `graph/component/queryNosqlGraph`
- `graph/queryActionGraph`
- `graph/queryBizDetailGraph`
- `graph/queryBizSystenGraph`

adapter 输出建议：

```json
{
  "pack_type": "topology_relation_pack",
  "nodes": [...],
  "edges": [...],
  "relation_summary": [
    {
      "from_type": "Action",
      "to_type": "DatabaseComponent",
      "response_time_ms": 204,
      "throughput": 0.05
    }
  ],
  "evidence": [...]
}
```

## 10.8 能力域 H：报告事实包适配

这是面向 skill 的关键能力。

目标：

- 不是输出原始 API 聚合
- 而是输出“可直接支持报告写作”的结构化事实包

建议组合上述各能力域，生成统一格式：

```json
{
  "pack_type": "report_fact_pack",
  "report_scope": {
    "biz_system_id": 1065,
    "time_window": {
      "end_time": "2026-04-03 12:20",
      "period_minutes": 30
    }
  },
  "summary": {...},
  "hotspots": {...},
  "components": {...},
  "trace_case": {...},
  "issues": [...],
  "drilldown_paths": [...],
  "evidence": [...]
}
```

这个 `report_fact_pack` 将是后续 skill 的主输入。

## 11. Adapter 的对外能力接口建议

建议 adapter 对外不要暴露所有原始接口，而是暴露少量、稳定、分析导向的方法。

例如：

### 11.1 概览类

- `build_system_snapshot(biz_system_id, time_window)`
- `build_health_snapshot(biz_system_id, time_window)`
- `build_application_trend_snapshot(biz_system_id, time_window)`

### 11.2 热点类

- `build_action_hotspot_pack(biz_system_id, time_window, sort_policy)`
- `build_database_component_pack(biz_system_id, component_name, time_window)`
- `build_nosql_component_pack(biz_system_id, component_name, time_window)`
- `build_connection_pool_pack(biz_system_id, metric_category, time_window)`

### 11.3 追踪类

- `list_traces_for_action(action_ref, time_window, selector)`
- `build_trace_case_pack(trace_ref, time_window)`

### 11.4 最终分析输入类

- `build_report_fact_pack(biz_system_id, time_window)`
- `build_action_investigation_pack(action_ref, time_window)`
- `build_database_investigation_pack(component_ref, time_window)`

## 12. Skill 的建设思路

在 adapter 层之上，建议 skill 不做“大而全”的一个技能，而是先拆成几个明确职责的 skill 模式。

## 12.1 Skill 总体定位

skill 的定位应该是：

- 消费 adapter 输出
- 组织诊断逻辑
- 生成可读、可解释、有证据的结果

而不是直接：

- 调几十个原始接口
- 自己推断各种字段含义
- 在原始 JSON 上做脆弱拼装

## 12.2 建议的 skill 能力域

### Skill A：系统当前情况分析

输入：

- `system_snapshot`
- `application_trend_snapshot`
- `health_snapshot`
- `action_hotspot_pack`

输出：

- 系统总体运行情况
- 当前健康度判断
- 当前趋势变化
- 重点对象列表

### Skill B：热点事务分析

输入：

- `action_hotspot_pack`
- 可选 `trace_case_pack`

输出：

- 热点 action 清单
- 每个 action 的关注理由
- 哪些 action 值得继续下钻

### Skill C：组件风险分析

输入：

- `database_component_pack`
- `nosql_component_pack`
- `connection_pool_pack`

输出：

- 关键 Database / NoSQL 组件
- 慢 SQL / 热操作
- 影响动作
- 连接池风险说明

### Skill D：trace 案例分析

输入：

- `trace_case_pack`

输出：

- 典型慢 trace 说明
- 关键耗时链路
- 异常和可疑点
- 可能的排查方向

### Skill E：报告生成

输入：

- `report_fact_pack`

输出：

- 巡检报告
- 问题清单
- 优先级
- 建议与事实对应关系

## 12.3 Skill 的分析输出原则

skill 层输出建议明确区分三种内容：

### `Facts`

直接来自 adapter 的事实，不做强化解释。

例如：

- 某业务系统平均响应时间为 `122ms`
- 某数据库组件 30 分钟内调用了 `60153` 次

### `Findings`

基于事实的分析性发现，但尽量不夸大。

例如：

- 当前数据库组件 `10.190.22.21:3306` 调用总量和总耗时都较高，值得纳入重点关注对象

### `Suggestions`

建议必须和 findings 对应。

例如：

- 针对 `Database/analysis` 中 `SELECT ... BPM_TODO_LOGO ...` 的慢 SQL，建议进一步检查执行计划和索引

## 13. Adapter 与 Skill 的协作方式

推荐采用下面这种职责分工：

### Adapter 负责

- 获取和归一化数据
- 建模对象与关系
- 组织证据和下钻路径
- 输出稳定的分析包

### Skill 负责

- 挑重点
- 做层次化总结
- 做问题编排
- 生成诊断说明与报告

### 这种分工的好处

- skill 变轻，不再依赖页面上下文
- adapter 变稳，不需要承担过强解释
- 两层都更容易迭代

## 14. 推荐的建设节奏

为了避免一开始做得太重，建议按三期推进。

## 14.1 第一期：做最小可用 adapter

目标：

- 先打通“系统当前情况 + 热点 action + 典型 trace”

优先实现：

- `build_system_snapshot`
- `build_action_hotspot_pack`
- `build_trace_case_pack`
- `build_report_fact_pack`

优先覆盖接口：

- `application/business/overview/*`
- `health/healthLevelStatistics`
- `application/charts/*`
- `webaction/list/actionList`
- `webaction/overview`
- `graph/query/overview` 中 `trace_current_overview`
- `action/trace/detail`
- `action/trace/callTree`
- `action/trace/detail/exceptions`

## 14.2 第二期：补强 Database / NoSQL

目标：

- 把下游组件能力接进来，形成“问题对象 -> 下游组件 -> trace”的闭环

优先实现：

- `build_database_component_pack`
- `build_nosql_component_pack`
- `build_connection_pool_pack`

优先覆盖接口：

- `Database/*`
- `NoSQL/*`
- `component/database/*`
- `graph/component/*`
- `connection/*`

## 14.3 第三期：建设 skill

目标：

- 让 adapter 的分析包真正服务报告生成

优先实现：

- 系统当前情况 skill
- 热点对象分析 skill
- 组件风险分析 skill
- trace 案例分析 skill
- 报告生成 skill

## 15. 当前这份 adapter 设计覆盖了哪些核心功能

按你的要求，这份 adapter 设计已经覆盖当前阶段的核心功能：

- 业务系统总览
- 健康度
- 响应、吞吐、错误趋势
- 热点 action / 热点事务
- action overview
- trace 列表与典型 trace 下钻
- trace 详情、异常、调用树、环境信息
- Database 组件概览
- 慢 SQL / 慢操作
- 受影响 action
- 相关 trace
- NoSQL 节点与热操作
- 连接池分析
- 组件拓扑
- 报告事实包

也就是说，它已经覆盖了你当前阶段想服务的主场景：

`系统当前情况 + 热点对象 + 下游组件 + 典型问题请求`

## 16. 最终结论

你现在的方向是非常对的：

- 不做前端复刻
- 不做原始接口透传
- 不急着做最终自动结论
- 先做 adapter，把对象、关系、证据和下钻路径整理好
- 再在其上建设分析与报告 skill

从当前掌握的接口来看，完全有条件把这件事做成一套稳定的两层体系：

第一层 `adapter`

- 吸收页面驱动和字段不一致
- 输出稳定、适合大模型理解的分析包

第二层 `skill`

- 读取 adapter 的分析包
- 生成有概述、有重点、有证据、有链路、有建议的报告

如果后续继续推进，我建议下一步优先做的是：

1. 把这里的 adapter 对象模型和 pack 模型固化成 JSON Schema 或 Python dataclass
2. 先实现 `system_snapshot`、`action_hotspot_pack`、`trace_case_pack`
3. 再实现 `database_component_pack`
4. 最后再让 report skill 基于 `report_fact_pack` 成形
