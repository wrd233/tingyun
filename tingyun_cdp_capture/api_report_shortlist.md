# 听云系统当前情况报告接口短名单

生成时间：2026-04-03  
分析基于目录：`/Users/wangrundong/work/mywork/tingyun_cdp_capture/captured_api`  
索引规模：`129` 个接口路径  
背景参考：`/Users/wangrundong/work/mywork/基调听云应用与微服务用户使用手册.pdf`

## 结论

这次更新后，报告导向的接口短名单应该分成三层，而不再只是“系统总览 + trace 附录”：

1. 系统总体运行情况  
2. 热点 action / 热点事务  
3. 关键下游组件，尤其是 Database 和 NoSQL

结合手册中的页面结构：

- `3.4 业务系统`
- `3.5 应用与实例`
- `3.6 事务`
- `3.9 DATABASE 服务组件`
- `3.10 NOSQL 服务组件`
- `3.14 请求追踪`

当前最适合直接支撑报告正文的接口，优先顺序建议如下：

1. `application/business/overview/1059`
2. `health/healthLevelStatistics`
3. `application/charts/response`
4. `application/charts/throught`
5. `application/charts/error`
6. `webaction/list/actionList`
7. `webaction/overview`
8. `Database/list`
9. `Database/info`
10. `Database/analysis`
11. `NoSQL/list`
12. `NoSQL/analysis`
13. `connection/list`
14. `component/database/actionList`
15. `component/database/actionTraceList`
16. `action/trace/detail`
17. `action/trace/detail/exceptions`
18. `action/trace/callTree`

## 一、最适合写报告首页结论的接口

### `application/business/overview/1059`

**推荐程度：最高**

它仍然是目前最适合放在报告开头的总览接口。当前样本已经给出完整的业务系统概况值：

- `bizSystemName: 铃与堆场`
- `apdex: 0.979`
- `applicationCount: 1`
- `hostCount: 2`
- `instanceCount: 3`
- `response: 122`
- `throught: 8.39`
- `successCount: 15104`
- `error: 0.0`
- `slowCount: 0`
- `respTimeHis: [34.59, 184.60, 419.95, 1317.92]`

这类值非常适合作为“业务系统整体情况”摘要。

### `health/healthLevelStatistics`

**推荐程度：最高**

这个接口最适合写健康度总览。当前样本能直接支持这种表述：

- 业务系统层：`normal=1`
- 应用层：`normal=1`
- 实例层：`normal=3`
- 动作层：`normal=156`、`warn=1`、`criteria=3`

结合手册中对动态基线和健康度的说明，它特别适合当“风险概览”部分。

## 二、最适合写趋势与运行态的接口

### `application/charts/response`

**推荐程度：最高**

当前样本给出的信息非常适合写性能趋势：

- `overviews.avg: 122`
- `overviews.max: 41530`
- 分钟级 `series.data`
- tooltip 含：
  - `响应时间`
  - `50分位值`
  - `80分位值`
  - `95分位值`
  - `99分位值`

结合手册里“响应时间中位数、平均响应时间和吞吐率趋势”的描述，可以把它明确视为应用概览中的核心趋势接口。

### `application/charts/throught`

**推荐程度：最高**

当前样本里可以直接用于写负载与吞吐：

- `overviews.avg: 8.39`
- `overviews.count: 15104`
- tooltip 含：
  - `吞吐率`
  - `请求数`

### `application/charts/error`

**推荐程度：高**

当前窗口下错误趋势较平稳：

- `overviews.avg/count/max` 都接近 `0`
- `series` 为 `错误率` 与 `错误数`

这适合作为“当前窗口下未见明显错误抬升”的证据。

## 三、最适合写热点事务和重点动作的接口

### `webaction/list/actionList`

**推荐程度：最高**

这个接口仍然是“找到最慢 action”的主入口。当前样本第一条就能说明它的价值：

- `actionId: 31376`
- `actionName: DubboProvider/com.eporttech.stos.service.WebViewService/getDate`
- `response: 5779`
- `slowCount: 30`
- `totalResponse: 173376`

而你后续的真实 replay 验证也已经证明：

- `bizSystemId=1065` 下可以直接通过它挑出最慢 action
- 再顺着 `webaction/overview -> trace_current_overview -> action/trace/detail` 走通

### `webaction/overview`

**推荐程度：最高**

当前样本能直接支持“动作级摘要”：

- `actionCalls: 180`
- `responseTime: 1209.8556`
- `totalResponseTime: 217774`
- `tps: 0.1`
- `instanceCount: 2`
- `technology: Jetty`
- `language: Java`

并且当前样本中已经有组件摘要：

- `components.Database[0].count: 214`
- `components.Database[0].respTime: 955.42993`

这说明它天然就是“事务概览”页的数据源。

## 四、最适合写数据库组件分析的接口

手册 `3.9 DATABASE 服务组件` 中明确把数据库分析拆成：

- 概览
- 响应时间
- 错误
- SQL 分析
- 操作分析
- 连接池分析

当前抓包已经能对上其中大部分。

### `Database/list`

**推荐程度：最高**

这是数据库组件列表入口。当前样本中 `集团法务` 下的 MySQL 节点已经很典型：

- `componentName: 10.190.22.21:3306`
- `componentSubtype: MySQL`
- `count: 60153`
- `respTime: 8.0`
- `throught: 33.42`
- `totalResptime: 863355`
- `traceCount: 36`

这非常适合写“系统当前主要数据库依赖是谁、调用量有多高、总耗时有多大”。

### `Database/info`

**推荐程度：最高**

这是数据库组件摘要卡片，当前样本可直接写入报告：

- `execCount: 60153`
- `respTime: 8.0`
- `throught: 33.42`
- `traceCount: 36`
- `currentPoolUsed: 1`
- `maxPool: 180`
- `callerActionCount: 219`
- `maxConnTime: 30`

这类字段很适合用来解释“数据库调用频繁，但连接池未见明显耗尽”。

### `Database/analysis`

**推荐程度：最高**

这是本轮新增里最有价值的接口之一，因为它已经拿到了操作级慢 SQL / 慢数据库操作：

- `componentName: 10.190.22.21:3306`
- `componentSubtype: MySQL`
- `respTime: 2485.0`
- `count: 21`
- `totalResptime: 52183`
- `traceCount: 21`
- `opName: SELECT ? FROM BPM_TODO_LOGO ...`

同一接口里还出现了：

- 长 `select DISTINCT info.ID ...`
- `update HD_TODOLIST ...`

这意味着它并不是简单“数据库节点概览”，而是已经进入 SQL/操作明细层。

### `component/database/actionList`

**推荐程度：高**

这是数据库操作到业务动作的桥。当前样本里已能看到：

- `actionId: 13238`
- `actionName: URI/grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr`
- `applicationId: 1644`
- `count: 524`
- `execTime: 181.0`
- `slowCount: 28`

这非常适合回答：

- 某个热点 SQL / 数据库操作，主要影响了哪些业务动作

### `component/database/actionTraceList`

**推荐程度：高**

这是数据库分析继续下钻到 trace 的关键一步。当前样本里已经拿到：

- `actionGuid`
- `actionTimestamp`
- `respTimeMicro`
- `actionId`

这一步把数据库问题和请求追踪真正串起来了。

### `connection/list`

**推荐程度：高**

这个接口当前样本主要落在 Oracle / Druid 场景，但它清楚展示了连接池信息：

- `databaseType`
- `framework`
- `currentIdle`
- `currentUsed`
- `maxActive`
- `minIdle`
- `pools[]`

如果报告需要说明“数据库慢是不是连接池耗尽导致”，它是直接证据源。

## 五、最适合写 NoSQL / Redis 组件分析的接口

手册里把 NoSQL 单独作为服务组件类别，当前抓包也已经对出来了。

### `NoSQL/list`

**推荐程度：高**

当前样本已经抓到多个 Redis 节点：

- `10.190.22.20:6379/7`
- `10.190.22.20:6379/1`
- `10.190.22.19:6379/2`
- `10.190.22.18:6379/2`

并且每个节点都有：

- `count`
- `throught`
- `totalResptime`

这很适合写“Redis 分布及调用热点”。

### `NoSQL/analysis`

**推荐程度：高**

当前样本已经拿到一个明确的 Redis 操作：

- `opName: EVAL`
- `componentName: 10.190.22.20:6379/5`
- `count: 472`
- `respTime: 1.0`

说明这条接口确实是 NoSQL 操作分析，而不是概览壳子。

### `NoSQL/overview`

**推荐程度：中高**

它当前更像按应用聚合的 NoSQL 组件摘要：

- `applicationId`
- `appName`
- `count`
- `throught`
- `totalResptime`

适合写“哪个应用最依赖 Redis / NoSQL”。

## 六、最适合写追踪案例附录的接口

### `action/trace/detail`

**推荐程度：高**

这个接口当前依然是单条 trace 报告的核心入口，当前样本已包含：

- `requestId`
- `traceGuid`
- `actionGuid`
- `bizSystemId / bizSystemName`
- `applicationId / applicationName`
- `actionId / actionName`
- `instanceId / instanceName`
- `respTime / duration / actionDuration`
- `timeLine`
- `topology`
- `serviceFlow`
- `requestServiceFlow`
- `suspectedProblemList`

### `action/trace/detail/exceptions`

**推荐程度：高**

这是这轮新确认的重要页签级接口。当前样本里已经出现：

- `type: HTTP Error Code`
- `name: HTTP ERROR CODE: 404`
- `msg` 包含具体静态资源 URL

说明 trace 详情页里的“异常”页签已经能独立抓出来。

### `action/trace/callTree`

**推荐程度：高**

这个接口最适合提供“调用链结构证据”：

- `nodeMap`
- `actions`
- `applications`
- `instances`
- `methodTotalParam`

## 七、需要重点记录的搜索键

### 1. 业务系统主键

当前整批分析几乎都从 `bizSystemId` 起步，尤其是：

- `webaction/*`
- `Database/*`
- `NoSQL/*`
- `graph/component/*`

### 2. 数据库组件三元组

数据库和 NoSQL 下钻的核心键已经很清晰：

- `componentType`
- `componentSubtype`
- `componentName`

例如：

- `Database / MySQL / 10.190.22.21:3306`
- `NoSQL / Redis / 10.190.22.20:6379/5`

### 3. 操作名 `opName`

这是数据库/NoSQL 操作分析的关键键。

特别注意：

- 有些 `opName` 是明文
- 有些带 `tyBase64_` 前缀，需要先解码

例如：

- `tyBase64_RVZBTA -> EVAL`
- `tyBase64_c2VsZWN0IERJU1RJTkNUIGluZm8uSUQ -> select DISTINCT info.ID`

### 4. 动作与追踪键

组件问题继续下钻时，关键链路是：

`opName -> actionId -> actionGuid -> traceId/actionGuid -> trace detail`

其中：

- `component/database/actionList` 提供 `actionId`
- `component/database/actionTraceList` 提供 `actionGuid`
- `action/trace/detail` 需要 `traceId + queryTimestamp`

## 八、当前最适合写成报告提纲的结构

如果现在就要写一份“系统当前情况 + 下游组件风险”的报告，我建议结构是：

1. 用 `application/business/overview/*` + `health/healthLevelStatistics` 写总览
2. 用 `application/charts/*` 写响应、吞吐、错误趋势
3. 用 `webaction/list/actionList` + `webaction/overview` 写热点事务
4. 用 `Database/list` + `Database/info` 写数据库组件总览
5. 用 `Database/analysis` 写慢 SQL / 慢操作
6. 用 `component/database/actionList` 写数据库问题影响到哪些动作
7. 用 `NoSQL/list` + `NoSQL/analysis` 写 Redis/NoSQL 组件情况
8. 如需附案例，再用 `action/trace/detail` + `exceptions` + `callTree`

## 结论

这次更新后，最关键的变化是：

- 报告主线不该只盯着 action 和 trace
- 数据库与 NoSQL 已经有足够丰富的接口样本，完全可以单独成章
- 手册章节和抓包页面结构已经能稳定对应，后续无论是人工整理还是交给模型总结，都会比之前可靠很多
