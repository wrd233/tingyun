# 听云抓包接口优先分析清单

生成时间：2026-04-03  
样本目录：`/Users/wangrundong/work/mywork/tingyun_cdp_capture/captured_api`  
索引规模：`129` 个接口路径  
背景参考：`/Users/wangrundong/work/mywork/reference/manuals/基调听云应用与微服务用户使用手册.pdf`

## 总结

这一轮样本相比上一版有两个实质变化：

1. 接口规模从 `87` 扩展到了 `129`，新增了完整的 `Database/*`、`NoSQL/*`、`component/database/*`、`graph/component/*`、`connection/database/*` 链路。
2. 抓包结构已经可以和手册中的页面结构稳定对上，不再只是“接口名猜用途”。

结合手册目录，当前最值得优先分析的接口主线已经很清晰：

1. 业务系统与应用总览  
   对应手册：`3.4 业务系统`、`3.5 应用与实例`
2. 事务与请求分析  
   对应手册：`3.6 事务`、`3.14 请求追踪`
3. DATABASE / NoSQL 服务组件  
   对应手册：`3.9 DATABASE 服务组件`、`3.10 NOSQL 服务组件`
4. 连接池与组件拓扑  
   对应手册：`3.9.6 连接池分析`、`3.4/3.5/3.10 拓扑与下游组件`

## A1：最值得最先分析的接口

| 接口 | 观测次数 | 对应页面/章节 | 典型请求键 | 典型输出内容 | 当前价值判断 |
|---|---:|---|---|---|---|
| `application/business/overview/1059` | 3 | 业务系统详情 / 业务系统总览 | `endTime`、`timePeriod` | `apdex`、`applicationCount`、`hostCount`、`instanceCount`、`response`、`throught`、`successCount` | 业务系统总览的第一入口 |
| `health/healthLevelStatistics` | 3 | 健康度分析 | 时间窗上下文 | `bizSystem/application/instance/action` 的 `normal/warn/criteria` | 健康分层总结入口 |
| `application/charts/response` | 3 | 应用概览趋势图 | `bizSystemId`、`businessType` | `avg/max`、分钟级趋势、`P50/P80/P95/P99` | 写系统当前响应特征最好用 |
| `application/charts/throught` | 3 | 应用概览趋势图 | `bizSystemId`、`businessType` | `avg/count`、吞吐率与请求数 | 写负载和请求量最好用 |
| `webaction/list/actionList` | 8 | 事务列表 / Top 请求 | `bizSystemId`、`sortField`、`sortDirection` | `actionId`、`response`、`slowCount`、`totalResponse` | 找到最慢 action 的主入口 |
| `webaction/overview` | 4 | 事务概览 | `bizSystemId`、`applicationId`、`actionId`、`actionType` | `responseTime`、`tps`、`components.Database/NoSQL` | 单个 action 摘要入口 |
| `action/trace/detail` | 1 | 请求追踪详情 - 追踪概览 / 疑似问题 / 拓扑 | `bizSystemId`、`traceId`、`queryTimestamp` | `traceGuid`、`actionGuid`、`timeLine`、`topology`、`serviceFlow`、`suspectedProblemList` | 单条 trace 的主详情接口 |
| `action/trace/callTree` | 4 | 请求追踪详情 - Call Tree | `actionGuid`、`traceId`、`bizSystemId` | `nodeMap`、`actions`、`applications`、`instances` | 追踪详情的主证据链 |
| `Database/list` | 2 | DATABASE 服务组件 - 概览 | `bizSystemId`、`componentType=Database`、`dataType=COMP` | `componentName`、`componentSubtype`、`count`、`respTime`、`throught`、`traceCount` | 数据库组件全局清单入口 |
| `Database/info` | 2 | DATABASE 服务组件 - 概览摘要 | `bizSystemId`、`componentName`、`componentSubtype` | `execCount`、`respTime`、`throught`、`traceCount`、`currentPoolUsed`、`maxPool` | 数据库组件摘要指标入口 |
| `Database/analysis` | 2 | DATABASE 服务组件 - 操作分析 / SQL 语句列表 | `bizSystemId`、`componentName`、`dataType=OP` | `opName`、`respTime`、`count`、`totalResptime`、`traceCount` | 找最慢 SQL / 操作最好用 |
| `NoSQL/list` | 2 | NOSQL 服务组件 - 概览 | `bizSystemId`、`componentType=NoSQL`、`dataType=COMP` | Redis 节点清单、`count`、`throught`、`totalResptime` | Redis/NoSQL 全局入口 |
| `NoSQL/analysis` | 1 | NOSQL 服务组件 - 操作分析 | `bizSystemId`、`componentName`、`dataType=OP` | `opName=EVAL`、`respTime`、`count`、`traceCount` | 找 NoSQL 热操作入口 |
| `component/database/actionList` | 2 | DATABASE 服务组件 - 操作分析下钻动作 | `bizSystemId`、`componentName`、`opName` | `actionId`、`applicationId`、`count`、`execTime`、`slowCount` | 把慢 SQL 关联到具体 action |
| `component/database/actionTraceList` | 2 | DATABASE 服务组件 - 动作追踪列表 | `actionId`、`componentName`、`opName` | `actionGuid`、`actionTimestamp`、`respTimeMicro` | 从慢 SQL 下钻到具体 trace |
| `graph/component/queryDataBaseGraph` | 2 | 组件拓扑 / 下游数据库依赖 | `bizSystemId`、`componentName` | `linkeDataArray`、`nodeDataArray` | 看哪些 action 依赖该数据库 |

## A2：第二批重点分析接口

| 接口 | 观测次数 | 对应页面/章节 | 当前观察 |
|---|---:|---|---|
| `NoSQL/overview` | 3 | NOSQL 组件概览 | 已能按应用聚合 Redis 组件的 `count/throught/respTime/totalResptime` |
| `NoSQL/trace` | 1 | NOSQL 追踪列表 | 当前 `content=[]`，但位置重要，说明 NoSQL 也支持 trace 下钻 |
| `NoSQL/errorTypeAmount` | 1 | NOSQL 错误 | 当前 `series=[]`，更像错误页占位接口 |
| `connection/list` | 8 | 连接池分析 | 当前样本主要覆盖 Oracle、Druid 池，字段很全 |
| `connection/chart` | 33 | 连接池趋势图 | 可直接看到 `Used connections`、`使用率(%)`、`Connection time`、`Waiter connections` |
| `connection/database/chart` | 1 | 数据库连接耗时趋势 | 当前样本是纯 `Connection time` 图 |
| `graph/component/queryNosqlGraph` | 3 | NoSQL 拓扑 | 能直接看应用到 Redis 的依赖边 |
| `action/trace/detail/exceptions` | 2 | 请求追踪详情 - 异常 | 已抓到 `HTTP ERROR CODE: 404` 这样的异常详情 |
| `action/trace/detail/snapshotTimeInfo` | 2 | 请求追踪详情 - 全栈快照 / span 片段 | 包含 `spanId/rid/tid/tranceId` 等键 |
| `action/trace/detail/queryAgentVersionInfo` | 4 | 环境信息 / 探针信息 | `agentVersion`、`oneAgentVersion`、`os`、`hostIp` |
| `data/logTrace/searchLogTrace` | 7 | 请求追踪详情 - 日志 | 目前结果为空，但键链已比较清晰 |

## 结合手册后的结构判断

### 1. 业务系统、应用、事务、组件是四层对象

手册明确强调：

- 业务系统用于归类应用并做可视化和追踪
- 应用/实例页面负责展示吞吐率、响应时间、错误率、实例数、技术栈
- 事务和请求分析负责展示 Top 请求、趋势图、线程剖析和追踪
- 组件页面负责数据库、NoSQL、MQ、外部服务、连接池等下游对象分析

这和当前抓包对象层级是吻合的：

- `bizSystemId`
- `applicationId`
- `actionId`
- `componentName/componentSubtype/componentType`
- `traceId/actionGuid`

### 2. DATABASE 服务组件已经能被分成四层接口

根据手册 `3.9 DATABASE 服务组件`，当前抓包接口大致能映射成：

- 概览层：
  - `Database/list`
  - `Database/info`
- SQL/操作层：
  - `Database/analysis`
- 关联动作层：
  - `component/database/actionList`
- 关联追踪层：
  - `component/database/actionTraceList`
- 组件拓扑层：
  - `graph/component/queryDataBaseGraph`
- 连接池层：
  - `connection/list`
  - `connection/chart`
  - `connection/database/chart`

这意味着数据库链路已经不是零散接口，而是一整套可以独立分析的页面族。

### 3. NoSQL 结构与 Database 基本平行

根据手册 `3.10 NOSQL 服务组件`，当前抓包也能对出一条平行链：

- 概览层：
  - `NoSQL/list`
  - `NoSQL/overview`
- 操作层：
  - `NoSQL/analysis`
- 追踪层：
  - `NoSQL/trace`
- 错误层：
  - `NoSQL/errorTypeAmount`
- 组件拓扑层：
  - `graph/component/queryNosqlGraph`

这说明后续整理说明文档时，Database 和 NoSQL 可以采用同一套分析框架。

## 典型输出最值得看的接口

### `Database/list`

当前样本直接给出一个典型数据库组件：

- `bizSystemName: 集团法务`
- `componentName: 10.190.22.21:3306`
- `componentSubtype: MySQL`
- `count: 60153`
- `respTime: 8.0`
- `throught: 33.42`
- `totalResptime: 863355`
- `traceCount: 36`
- `connUsed: 1`

这类接口适合回答：

- 当前业务系统主要依赖了哪些数据库
- 哪个数据库调用最频繁
- 哪个数据库总耗时最高

### `Database/info`

当前样本更像数据库组件的摘要卡片：

- `execCount: 60153`
- `respTime: 8.0`
- `throught: 33.42`
- `traceCount: 36`
- `currentPoolUsed: 1`
- `maxPool: 180`
- `callerActionCount: 219`
- `maxConnTime: 30`

这类接口适合写数据库组件的“总体负载 + 池使用状态”。

### `Database/analysis`

这是本轮最值得重点注意的新接口之一，已经能直接给出操作级慢 SQL：

- `componentName: 10.190.22.21:3306`
- `componentSubtype: MySQL`
- `opName: SELECT ? FROM BPM_TODO_LOGO ...`
- `respTime: 2485.0`
- `count: 21`
- `totalResptime: 52183`
- `traceCount: 21`

另外当前样本中还出现了更长 SQL 和 `update HD_TODOLIST ...` 这类写操作，说明它确实承载了“SQL 语句列表 / 操作分析”。

### `component/database/actionList`

这一层已经把数据库操作和业务 action 连起来了：

- `actionId: 13238`
- `actionName: URI/grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr`
- `applicationId: 1644`
- `count: 524`
- `execTime: 181.0`
- `slowCount: 28`
- `totalResptime: 94706`

这一步非常关键，因为它把“慢 SQL”变成了“影响哪个业务动作”。

### `component/database/actionTraceList`

当前样本已经能拿到具体追踪对象：

- `actionGuid: 7101fff31a80619e`
- `actionTimestamp: 1775189172000`
- `respTimeMicro: 2522.765`
- `actionId: 13238`

这一步是数据库分析到 trace 分析之间的桥。

### `graph/component/queryDataBaseGraph`

当前样本的 `linkeDataArray` 已经能直接描述：

- 哪个 action 指向数据库节点
- 每条边的 `response`
- 每条边的 `throught`
- 每条边的 `maxEexcTime`

例如当前样本里已出现：

- `SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/done-pages/{instId}`
- `URI/grcv5/dwr/call/plaincall/dwrContractArchiveService.findArchiveByContractId.dwr`
- `URI/grcv5/dwr/call/plaincall/dwrWorkflowService.getCandidates.dwr`

都指向同一个 `MySQL/10.190.22.21:3306` 节点。

### `NoSQL/list` 与 `NoSQL/analysis`

NoSQL 当前样本已能直接说明：

- Redis 节点分布：
  - `10.190.22.20:6379/7`
  - `10.190.22.20:6379/1`
  - `10.190.22.19:6379/2`
  - `10.190.22.18:6379/2`
- 每个节点的：
  - `count`
  - `throught`
  - `totalResptime`
- 热操作：
  - `opName=EVAL`
  - `respTime=1.0`
  - `count=472`

这说明 Redis 侧也已经具备“节点级 + 操作级”分析能力。

### `action/trace/detail/exceptions`

当前样本已经明确打到“请求追踪详情 - 异常”页签：

- `type: HTTP Error Code`
- `name: HTTP ERROR CODE: 404`
- `msg` 中含具体资源 URL

这说明 trace 页签级别的接口已经不只是概览，而是覆盖了异常 tab。

## 当前最重要的搜索键链路

### 1. 业务系统 -> 动作 -> Trace

这是通用性能分析主线：

`bizSystemId -> actionId -> applicationId -> traceId -> actionGuid`

当前接口链：

- `webaction/list/actionList`
- `webaction/overview`
- `graph/query/overview` 中的 `metric=trace_current_overview`
- `action/trace/detail`
- `action/trace/callTree`

### 2. 业务系统 -> 数据库组件 -> SQL/操作 -> 动作 -> Trace

这是数据库定位主线：

`bizSystemId -> componentName/componentSubtype -> opName -> actionId -> actionGuid`

当前接口链：

- `Database/list`
- `Database/info`
- `Database/analysis`
- `component/database/actionList`
- `component/database/actionTraceList`
- 再进一步进入 `action/trace/*`

### 3. 业务系统 -> NoSQL 组件 -> 操作 -> Trace

这是 NoSQL 定位主线：

`bizSystemId -> componentName/componentSubtype -> opName -> trace`

当前抓包还缺一段真正非空的 NoSQL trace 下钻结果，但链路已经出现：

- `NoSQL/list`
- `NoSQL/overview`
- `NoSQL/analysis`
- `NoSQL/trace`

### 4. 数据库/NoSQL 名称编码与解码

当前抓包中非常重要的一个细节是：

- `opName` 有时直接就是 SQL 或操作名
- 有时会带 `tyBase64_` 前缀

例如：

- `tyBase64_RVZBTA` 解码后是 `EVAL`
- `tyBase64_c2VsZWN0IERJU1RJTkNUIGluZm8uSUQ` 解码后是 `select DISTINCT info.ID`

这意味着后续做接口说明或自动分析时，需要把 `tyBase64_` 作为一个显式规则处理。

## 结合“系统当前情况”报告的优先级

如果目标是面向报告或诊断说明文档，当前最值得优先总结的接口顺序建议调整为：

1. `application/business/overview/1059`
2. `health/healthLevelStatistics`
3. `application/charts/response`
4. `application/charts/throught`
5. `webaction/list/actionList`
6. `webaction/overview`
7. `Database/list`
8. `Database/info`
9. `Database/analysis`
10. `component/database/actionList`
11. `component/database/actionTraceList`
12. `graph/component/queryDataBaseGraph`
13. `NoSQL/list`
14. `NoSQL/analysis`
15. `action/trace/detail`
16. `action/trace/detail/exceptions`
17. `action/trace/callTree`

## 结论

这轮抓包最重要的升级不是“接口数量更多”，而是已经形成了三条完整分析闭环：

1. 业务系统 -> 动作 -> trace
2. 业务系统 -> 数据库组件 -> SQL/操作 -> 动作 -> trace
3. 业务系统 -> NoSQL 组件 -> 操作 -> trace

再加上手册中的章节结构已经能和抓包对上，说明现在这批 JSON 文件已经足够支撑后续做较高质量的接口归纳和使用说明了。
