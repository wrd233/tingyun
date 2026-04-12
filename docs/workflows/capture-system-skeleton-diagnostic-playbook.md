# 听云系统骨架、接口关系与经典诊断链路总报告

生成时间：2026-04-03  
抓包目录：`/Users/wangrundong/work/mywork/tingyun_cdp_capture/captured_api`  
抓包索引：`129` 个接口路径  
参考手册：`/Users/wangrundong/work/mywork/reference/manuals/基调听云应用与微服务用户使用手册.pdf`

## 1. 这份文档的目的

这份文档不是单纯的接口清单，也不是单条追踪案例分析，而是站在“系统本身的骨架”上，对当前已抓到的接口重新组织，回答四个问题：

1. 听云平台当前这套应用与微服务系统，整体上是如何组织对象和页面的。
2. 当前抓到的调用分别属于系统中的哪个层次，它们在页面上大致扮演什么角色。
3. 各类调用之间如何串联，哪些字段是上游页面传给下游页面的关键键。
4. 如果不依赖浏览器页面，只靠这些调用本身，如何模拟平台里的经典诊断流程。

这份文档的使用场景主要有三个：

- 把当前抓包重新整理成一套“可理解的系统地图”
- 为后续交给模型做接口总结提供清晰上下文
- 为后续编排脚本、复现诊断流程、自动化调用打基础

## 2. 系统骨架：从手册视角重建整个系统

结合手册《基调听云应用与微服务用户使用手册》，当前抓到的接口可以被放进一个非常清晰的系统骨架。

### 2.1 最上层：业务系统

业务系统是整个系统的顶层组织对象。手册里多次强调：

- 业务系统用于归类应用
- 业务系统用于做可视化拓扑和全局分析
- 业务系统是很多应用、事务、组件分析的上层入口

当前抓包里，几乎所有分析流程都能看到 `bizSystemId`。这说明：

- `bizSystemId` 是最核心的主键之一
- 大多数页面都是在某个业务系统上下文里展开的

对应接口族：

- `application/business/overview/*`
- `graph/queryBizDetailGraph`
- `graph/queryBizSystenGraph`
- `graph/queryGraphHealth`
- `health/healthLevelStatistics`

### 2.2 第二层：应用与实例

手册 `3.5 应用与实例` 中的页面负责展示：

- 吞吐率
- 响应时间中位数
- 错误率
- 实例数量
- 技术栈
- 下游应用和服务组件

当前抓包中的应用层接口主要是：

- `application/charts/*`
- `graph/information`
- `graph/query/diagram`
- `graph/query/overview`
- `application/app/*`
- `application/instance/select`

这一层对应的关键键是：

- `applicationId`
- `instanceId`
- `bizSystemId`

### 2.3 第三层：事务 / 请求 / Top Action

手册 `3.6 事务` 与 `3.5.2.4 请求分析` 明确提到：

- 事务列表
- 概览
- 响应时间趋势
- 错误趋势
- 吞吐率趋势
- Top 请求
- 线程剖析

当前抓包中最匹配这一层的是：

- `webaction/list/actionList`
- `webaction/overview`
- `webaction/charts/*`
- `webaction/performance/breakdown*`
- `webaction/threadAnalysisList`

这一层的关键键是：

- `actionId`
- `actionType`
- `applicationId`
- `bizSystemId`

这一层是“从系统全貌走向具体热点对象”的关键转折层。

### 2.4 第四层：请求追踪

手册 `3.14 请求追踪` 中提到的页签包括：

- 请求追踪列表
- 请求追踪详情
- 追踪概览
- 性能分解图
- 疑似问题
- 拓扑
- Call Table
- Call Tree
- 全栈快照
- 异常
- 参数信息
- Code 统计
- SQL 统计
- NoSQL 统计
- 日志

当前抓包里已经和这些页签较强对应的接口有：

- `action/trace/detail`
- `action/trace/detail/exceptions`
- `action/trace/callTree`
- `action/trace/detail/snapshotTimeInfo`
- `action/trace/detail/queryAgentVersionInfo`
- `data/logTrace/searchLogTrace`

这一层的关键键是：

- 页面 URL 数值型 `traceId`
- `queryTimestamp`
- `traceGuid`
- `actionGuid`
- `requestId`
- `instanceId`

### 2.5 第五层：服务组件

手册里把服务组件单独拆成多个分析域：

- `3.9 DATABASE 服务组件`
- `3.10 NOSQL 服务组件`
- `3.11 MQ 服务组件`
- `3.15 连接池`

当前抓包里这层已经很丰富：

- `Database/*`
- `NoSQL/*`
- `MQ/*`
- `connection/*`
- `component/database/*`
- `component/chart/*`
- `graph/component/*`

这一层的关键键是：

- `componentType`
- `componentSubtype`
- `componentName`
- `metricCategory`
- `opName`

## 3. 当前抓包的接口家族分布

按一级路径统计，当前样本大致是：

- `webaction`: 20
- `graph`: 15
- `component`: 13
- `application`: 12
- `error`: 12
- `action`: 10
- `NoSQL`: 9
- `data`: 9
- `Database`: 8
- `connection`: 3
- 以及少量 `MQ`、`health`、`instance`、`setting` 等

这说明现在的抓包已经不仅仅是某一个页面，而是基本覆盖了平台的几个主视角：

- 业务与应用视角
- 事务与请求视角
- 请求追踪视角
- 数据库 / NoSQL / 连接池视角
- 拓扑与图表视角

## 4. 系统中的关键对象和键

为了理解接口之间的联系，必须先把关键键梳理清楚。

### 4.1 顶层对象键

- `bizSystemId`
  - 业务系统主键
  - 几乎所有主流程都从这里起步
- `applicationId`
  - 应用主键
  - 应用概览、事务、组件、trace 经常会带它
- `instanceId`
  - 实例主键
  - 环境信息、连接池、实例分析、trace 环境信息常用

### 4.2 事务对象键

- `actionId`
  - 事务 / 请求 / action 的主键
- `actionType`
  - 常见值如 `TX`、`IF`
- `actionName`
  - 页面上展示名称
- `actionAlias`
  - 别名，有时与名称相同

### 4.3 追踪对象键

- 页面 URL 数值型 `traceId`
  - 例如 `1746761396`
- `queryTimestamp`
  - 页面状态或时间定位参数
- `traceGuid`
  - Trace GUID
- `actionGuid`
  - 当前动作的 GUID
- `requestId`
  - 在很多样本中和 `traceGuid/actionGuid` 相同

这里最重要的结论是：

- 页面 URL 里的 `traceId` 和 `actionGuid/traceGuid` 不是同一个东西
- 在一些接口中，`traceId` 仍然是数值型
- 在另一些接口中，尤其日志关联中，`traceId` 实际更像 GUID 键

### 4.4 组件对象键

- `componentType`
  - `Database` / `NoSQL` / `MQ` / `External` / `Pool`
- `componentSubtype`
  - 例如 `MySQL`、`Redis`
- `componentName`
  - 例如 `10.190.22.21:3306`
  - 或 `10.190.22.20:6379/5`
- `metricCategory`
  - 连接池趋势接口常用
- `opName`
  - SQL 或 NoSQL 操作名

### 4.5 编码规则：`tyBase64_`

当前抓包已经明确显示：

- `opName` 有时不是明文
- 而是以 `tyBase64_` 为前缀的字符串

已验证示例：

- `tyBase64_RVZBTA -> EVAL`
- `tyBase64_c2VsZWN0IERJU1RJTkNUIGluZm8uSUQ -> select DISTINCT info.ID`

因此后续自动化处理 `opName` 时，应该遵循：

1. 判断是否以 `tyBase64_` 开头
2. 去掉前缀
3. Base64 解码
4. 再作为 SQL 或 NoSQL 操作名展示

## 5. 主要接口家族与它们之间的关系

下面不是简单列举接口，而是按系统骨架讲清楚每一组调用在整条分析链路中的位置。

### 5.1 业务系统与应用总览家族

这一家族负责回答：

- 当前业务系统整体情况如何
- 当前应用和实例规模如何
- 负载、响应和错误有没有明显问题

核心接口：

- `application/business/overview/*`
- `health/healthLevelStatistics`
- `application/charts/response`
- `application/charts/throught`
- `application/charts/error`
- `application/charts/apdex`

典型输出：

- 业务系统级：
  - `apdex`
  - `applicationCount`
  - `hostCount`
  - `instanceCount`
  - `response`
  - `throught`
  - `successCount`
- 健康度级：
  - `bizSystem/application/instance/action` 的 `normal/warn/criteria`
- 趋势级：
  - `avg`
  - `max`
  - `count`
  - 分钟级 `series.data`
  - tooltip 中的 `P50/P80/P95/P99`

这组接口与下游接口的关系是：

- 它们先给出“全局情况”
- 然后引导用户下钻到事务列表、应用详情、组件详情

### 5.2 事务 / Top 请求家族

这一家族负责回答：

- 当前最慢的事务是谁
- 哪些事务总耗时最高
- 哪些事务慢请求最多
- 某个事务的总体画像如何

核心接口：

- `webaction/list/actionList`
- `webaction/overview`
- `webaction/charts/apdex`
- `webaction/charts/error`
- `webaction/charts/response-quantlie`
- `webaction/charts/throught`
- `webaction/performance/breakdown`
- `webaction/performance/breakdown/chart`
- `webaction/performance/breakdown/table`

典型输出：

- `webaction/list/actionList`
  - `actionId`
  - `actionName`
  - `applicationId`
  - `count`
  - `response`
  - `slowCount`
  - `totalResponse`
  - `errorCount`
- `webaction/overview`
  - `actionCalls`
  - `responseTime`
  - `totalResponseTime`
  - `tps`
  - `errorRate`
  - `instanceCount`
  - `technology`
  - `language`
  - `components.Database`
  - `components.NoSQL`

这组接口与上下游的关系是：

- 上游承接业务系统 / 应用总览
- 下游继续进入 trace、组件分解、线程分析

### 5.3 通用图查询家族

这一家族更像平台内部的“通用图表和查询承载层”，而不是单一业务页面。

核心接口：

- `graph/query/overview`
- `graph/query/diagram`
- `graph/information`
- `graph/event`
- `graph/suggestions`

这组接口的特点是：

- 同一路径承载多种 `metric`
- 页面上的很多“图”和“列表”其实复用这些接口
- 真正的业务语义往往来自 `metric` 和 `labels`

典型 `metric`：

- `request_overview`
- `trace_current_overview`
- `request_trace_type`
- `request_response_ms_diagram`
- `throughput_diagram`
- `application_info`
- `request_info`
- `problem_detail_metric`

其中最关键的一层关系是：

- `graph/query/overview` 中的 `metric=trace_current_overview`
  - 负责把 action 下钻成 trace 列表
- `graph/information`
  - 负责把 `actionId`、`applicationId`、`bizSystemId` 的名称和显示信息补齐

### 5.4 请求追踪家族

这一家族负责回答：

- 某一条慢请求到底发生了什么
- 代码、组件、下游调用、异常、日志如何串起来

核心接口：

- `action/trace/detail`
- `action/trace/detail/exceptions`
- `action/trace/callTree`
- `action/trace/detail/snapshotTimeInfo`
- `action/trace/detail/queryAgentVersionInfo`
- `data/logTrace/searchLogTrace`

典型输出和作用：

- `action/trace/detail`
  - 追踪概览主接口
  - 给出 `traceGuid/actionGuid/requestId`
  - 给出 `timeLine/topology/serviceFlow/requestServiceFlow/suspectedProblemList`
- `action/trace/detail/exceptions`
  - 异常页签
  - 给出异常类型、异常消息、HTTP 错误等
- `action/trace/callTree`
  - 调用树主接口
  - 给出 `nodeMap`、`actions`、`applications`、`instances`
- `snapshotTimeInfo`
  - span 或时间片级的附加信息
  - 含 `spanId/rid/tid/tranceId`
- `queryAgentVersionInfo`
  - 环境与探针信息
- `searchLogTrace`
  - 日志关联入口

这组接口之间的依赖关系很明确：

- `detail` 先建立当前 trace 的主上下文
- `callTree` 深入到节点级
- `exceptions` 看异常页签
- `snapshotTimeInfo` 看片段和线程相关细节
- `queryAgentVersionInfo` 补实例环境
- `searchLogTrace` 尝试查日志关联

### 5.5 Database 组件家族

这是当前新增里最重要的一族，已经能形成完整闭环。

核心接口：

- `Database/list`
- `Database/info`
- `Database/analysis`
- `Database/actionName/list`
- `Database/applicationName/list`
- `Database/componentName/list`
- `Database/list/health`
- `Database/operate/analysisList`

辅助下钻接口：

- `component/database/actionList`
- `component/database/actionTraceList`
- `component/database/action_item_list`
- `component/database/errorList`
- `graph/component/queryDataBaseGraph`
- `connection/database/chart`

这组接口的角色分工如下：

- `Database/list`
  - 列出数据库组件对象
  - 回答“这个业务系统用了哪些数据库”
- `Database/info`
  - 给出单个数据库组件摘要
  - 回答“这个数据库总体负载如何”
- `Database/analysis`
  - 给出操作级 / SQL 级清单
  - 回答“最慢 SQL 或最慢操作是什么”
- `component/database/actionList`
  - 把数据库操作关联到业务动作
  - 回答“哪个 action 受这个数据库操作影响最大”
- `component/database/actionTraceList`
  - 把动作进一步关联到 trace
  - 回答“哪个具体 trace 体现了这个数据库问题”
- `graph/component/queryDataBaseGraph`
  - 从拓扑视角描述“哪些动作连向这个数据库”
- `connection/database/chart`
  - 从连接时间维度补充数据库连接行为

这一组是整个平台里最像“数据库诊断工作台”的接口集合。

### 5.6 NoSQL 组件家族

NoSQL 家族与 Database 结构非常相似。

核心接口：

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

这组接口的角色分工如下：

- `NoSQL/list`
  - 列出 Redis / NoSQL 节点
- `NoSQL/overview`
  - 给出应用维度或组件维度的摘要
- `NoSQL/analysis`
  - 给出操作级分析，例如 `EVAL`
- `NoSQL/trace`
  - NoSQL 操作对应的追踪列表
- `NoSQL/errorTypeAmount`
  - 错误类型统计
- `queryNosqlGraph`
  - 看应用到 Redis 的拓扑依赖

当前的局限是：

- `NoSQL/trace`
  - 当前样本还没有抓到非空结果
- `NoSQL/errorTypeAmount`
  - 当前样本 `series=[]`

但结构已经建立，说明这条链路在平台里是真实存在的。

### 5.7 连接池家族

这一家族负责回答：

- 当前连接池是否接近上限
- 当前使用连接数、等待连接数、连接时间是否异常

核心接口：

- `connection/list`
- `connection/chart`
- `connection/database/chart`

典型输出：

- `connection/list`
  - `databaseType`
  - `framework`
  - `currentIdle`
  - `currentUsed`
  - `maxActive`
  - `pools[]`
- `connection/chart`
  - tooltip 中可见：
    - `Used connections`
    - `使用率(%)`
    - `Connection time`
    - `Waiter connections`
- `connection/database/chart`
  - 更聚焦在 `Connection time`

它和 Database 家族的关系是：

- Database 家族偏“数据库对象与操作”
- Connection 家族偏“连接池资源状态”

两者结合，才能完整回答“数据库慢是 SQL 慢，还是连接池紧张”。

## 6. 经典诊断链路

下面这些链路，不是随意拼装的，而是从手册页面结构和当前真实抓包共同抽象出来的“平台经典诊断思路”。

### 6.1 链路一：业务系统总览诊断

目标：

- 快速判断当前业务系统是否整体健康
- 找出是性能、错误、健康度还是请求量方面的问题

典型调用顺序：

1. `application/business/overview/{bizSystemId}`
2. `health/healthLevelStatistics`
3. `application/charts/response`
4. `application/charts/throught`
5. `application/charts/error`

输出结果能回答：

- 业务系统整体规模
- 当前负载水平
- 平均响应和峰值
- 是否存在整体错误抬升
- 健康对象数量

### 6.2 链路二：业务系统到最慢事务

目标：

- 找出当前业务系统中最值得关注的 action

典型调用顺序：

1. `webaction/list/actionList`
2. 按 `response`、`slowCount`、`totalResponse` 排序
3. 选出目标 `actionId`
4. `webaction/overview`

输出结果能回答：

- 最慢事务是谁
- 调用多少次
- 平均多慢
- 总耗时有多少
- 涉及哪些组件类型

### 6.3 链路三：事务到请求追踪

目标：

- 从某个慢 action 继续下钻到具体 trace

典型调用顺序：

1. 已知 `bizSystemId`、`applicationId`、`actionId`、`actionType`
2. 调 `graph/query/overview?trace_current_overview&lang=zh_CN`
3. `metric=trace_current_overview`
4. 从结果中拿到：
   - `traceId`
   - `timestamp`
   - `actionGuid`
   - `traceGuid`
   - `requestId`

输出结果能回答：

- 这个 action 最近有哪些 trace
- 哪条 trace 最慢
- 哪条 trace 错误最多

### 6.4 链路四：请求追踪详情诊断

目标：

- 理解一条具体 trace 内部发生了什么

典型调用顺序：

1. `action/trace/detail`
2. `action/trace/detail/exceptions`
3. `action/trace/callTree`
4. `action/trace/detail/snapshotTimeInfo`
5. `action/trace/detail/queryAgentVersionInfo`
6. `data/logTrace/searchLogTrace`

输出结果能回答：

- trace 基本信息是什么
- 疑似问题落在哪个代码点
- 拓扑和服务流如何
- 有哪些异常
- 环境和探针版本是什么
- 是否能关联到日志

### 6.5 链路五：数据库组件诊断

目标：

- 从业务系统角度找到最重的数据库组件和最慢 SQL

典型调用顺序：

1. `Database/list`
2. `Database/info`
3. `Database/analysis`
4. 如需看动作影响，继续：
   - `component/database/actionList`
5. 如需看具体追踪，继续：
   - `component/database/actionTraceList`
6. 如需看结构关系，继续：
   - `graph/component/queryDataBaseGraph`
7. 如需看连接情况，继续：
   - `connection/list`
   - `connection/database/chart`

输出结果能回答：

- 当前最重的数据库节点是谁
- 数据库总体调用量和总耗时如何
- 最慢 SQL / 最慢数据库操作是什么
- 受影响最大的 action 是哪些
- 对应的具体 trace 是哪些
- 连接池是否紧张

### 6.6 链路六：NoSQL / Redis 诊断

目标：

- 从业务系统角度定位 Redis / NoSQL 热点节点与热操作

典型调用顺序：

1. `NoSQL/list`
2. `NoSQL/overview`
3. `NoSQL/analysis`
4. 如需看追踪：
   - `NoSQL/trace`
5. 如需看错误：
   - `NoSQL/errorTypeAmount`
6. 如需看拓扑：
   - `graph/component/queryNosqlGraph`

输出结果能回答：

- Redis 节点有哪些
- 哪个 Redis 节点最热
- 热操作是什么
- 哪些应用依赖这个节点

### 6.7 链路七：连接池诊断

目标：

- 判断慢问题是否与连接池资源耗尽有关

典型调用顺序：

1. `connection/list`
2. `connection/chart`
3. `connection/database/chart`

输出结果能回答：

- 当前池容量与使用量
- 是否出现等待连接
- 连接时间是否显著升高

## 7. 如何用这些调用模拟平台诊断

这一节的重点不是“接口定义是什么”，而是如何把它们编排成真正能跑的模拟诊断流程。

### 7.1 模拟诊断的基本原则

原则一：先拿上层对象，再拿下层对象  
不要一开始就直接打 trace 或 SQL 详情，而应先拿：

- `bizSystemId`
- `applicationId`
- `actionId`
- `componentName`

原则二：每一层都要把“主键”保存下来  
比如：

- 从 actionList 保存 `actionId/applicationId/actionType`
- 从 trace 列表保存 `traceId/timestamp/actionGuid`
- 从 Database/list 保存 `componentName/componentSubtype`

原则三：区分对象视角和图表壳子  
例如：

- `webaction/overview` 是对象摘要
- `graph/query/overview` / `graph/query/diagram` 很多时候是通用壳子

原则四：对 `opName` 做解码  
否则 SQL / NoSQL 操作名会丢失可读性。

### 7.2 模拟“系统总体情况”诊断

步骤：

1. 输入 `bizSystemId`
2. 调 `application/business/overview/{bizSystemId}`
3. 调 `health/healthLevelStatistics`
4. 调 `application/charts/response`
5. 调 `application/charts/throught`
6. 调 `application/charts/error`
7. 汇总：
   - Apdex
   - 应用数 / 实例数 / 主机数
   - 平均响应 / 峰值
   - 吞吐
   - 错误率
   - 健康分层统计

这就可以模拟平台里“业务系统详情 + 应用概览”的主视图。

### 7.3 模拟“找最慢事务”

步骤：

1. 输入 `bizSystemId`
2. 调 `webaction/list/actionList`
3. 排序策略：
   - 主排序：`response`
   - 次排序：`slowCount`
   - 再次排序：`totalResponse`
4. 选出目标 action
5. 调 `webaction/overview`

汇总结果：

- 事务名称
- 平均响应
- 调用次数
- 慢请求数
- 总耗时
- 涉及组件类型

### 7.4 模拟“从事务到 trace”

步骤：

1. 已有：
   - `bizSystemId`
   - `applicationId`
   - `actionId`
   - `actionType`
2. 调 `graph/query/overview`
3. query 带：
   - `trace_current_overview`
   - `lang=zh_CN`
4. body 带：
   - `metric=trace_current_overview`
   - `labels.actionIds`
   - `labels.applicationIds`
   - `labels.systemIds`
   - `labels.actionTypes`
   - `order.fields=['timestamp']`
   - `page`
5. 从结果选出一条 trace

常见选择策略：

- 选最新
- 选最慢
- 选错误数最高

### 7.5 模拟“trace 详情诊断”

步骤：

1. 已有：
   - 数值型 `traceId`
   - `bizSystemId`
   - `queryTimestamp`
   - 时间窗
2. 调 `action/trace/detail`
3. 从返回中保存：
   - `traceGuid`
   - `actionGuid`
   - `requestId`
   - `instanceId`
4. 并行或顺序继续调：
   - `action/trace/detail/exceptions`
   - `action/trace/callTree`
   - `action/trace/detail/snapshotTimeInfo`
   - `action/trace/detail/queryAgentVersionInfo`
   - `data/logTrace/searchLogTrace`

最终可输出：

- trace 摘要
- 可疑代码点
- 异常列表
- 调用树结构
- 环境信息
- 日志联动结果

### 7.6 模拟“数据库问题诊断”

步骤：

1. 输入 `bizSystemId`
2. 调 `Database/list`
3. 选择目标数据库组件：
   - 按 `count`
   - 按 `throught`
   - 按 `totalResptime`
   - 按 `traceCount`
4. 调 `Database/info`
5. 调 `Database/analysis`
6. 从 `Database/analysis` 选出目标 `opName`
7. 调 `component/database/actionList`
8. 选出最受影响 action
9. 调 `component/database/actionTraceList`
10. 选出目标 `actionGuid`
11. 如需深入到请求追踪，再走 `action/trace/*`

这样就能模拟平台中的：

- 数据库概览
- SQL 分析
- 操作分析
- 关联动作
- 关联 trace

### 7.7 模拟“NoSQL / Redis 问题诊断”

步骤：

1. 输入 `bizSystemId`
2. 调 `NoSQL/list`
3. 选目标 Redis 节点
4. 调 `NoSQL/overview`
5. 调 `NoSQL/analysis`
6. 选目标 `opName`
7. 继续调 `NoSQL/trace`
8. 如需结构图，调 `graph/component/queryNosqlGraph`

如果当前 `NoSQL/trace` 为空，也仍然能完成：

- 节点级诊断
- 热操作诊断
- 拓扑依赖分析

### 7.8 模拟“连接池问题诊断”

步骤：

1. 输入：
   - `bizSystemId`
   - `applicationId`
   - `instanceId`
   - 或 `metricCategory`
2. 调 `connection/list`
3. 选目标池
4. 调 `connection/chart`
5. 调 `connection/database/chart`

最终重点看：

- `Used connections`
- `使用率(%)`
- `Waiter connections`
- `Connection time`

## 8. 每类调用的典型价值总结

### 8.1 最适合写“当前情况报告”的调用

- `application/business/overview/*`
- `health/healthLevelStatistics`
- `application/charts/*`
- `webaction/list/actionList`
- `webaction/overview`
- `Database/list`
- `Database/info`
- `NoSQL/list`

### 8.2 最适合写“问题对象下钻”的调用

- `graph/query/overview` 中 `trace_current_overview`
- `action/trace/detail`
- `action/trace/callTree`
- `Database/analysis`
- `component/database/actionList`
- `component/database/actionTraceList`
- `NoSQL/analysis`

### 8.3 最适合写“结构关系”的调用

- `graph/component/queryDataBaseGraph`
- `graph/component/queryNosqlGraph`
- `action/trace/detail.topology`
- `action/trace/detail.serviceFlow`
- `action/trace/callTree`

## 9. 当前样本已经具备的能力边界

### 9.1 已经比较完整的能力

- 业务系统总览
- 应用趋势
- 事务列表和事务概览
- trace 详情主链
- Database 组件概览、操作分析、动作关联、trace 关联
- NoSQL 节点和操作分析
- 连接池基础分析
- trace 异常页签

### 9.2 还可以继续补样本的能力

- `NoSQL/trace`
  - 当前样本为空
- `NoSQL/errorTypeAmount`
  - 当前样本为空
- `data/logTrace/searchLogTrace`
  - 当前样本为空
- 一些 MQ 相关页签
- 更完整的 `trace_current_overview` 原始响应样本

### 9.3 这意味着什么

这意味着当前已经足够做：

- 结构化系统说明
- 报告骨架编写
- 事务到 trace 的模拟调用
- 数据库到 trace 的模拟调用

但如果要把日志、NoSQL trace、MQ 分析也做成完整闭环，还值得继续补抓。

## 10. 建议的后续工作方式

如果后面要继续整理或自动化，我建议按三个方向推进：

### 10.1 先按对象层拆分

分三组整理：

1. 业务系统 / 应用 / 事务
2. Database / NoSQL / 连接池
3. Trace / 异常 / 日志

### 10.2 给每条经典链路做成脚本

最值得先做成脚本的三条：

1. `bizSystem -> action -> trace -> detail`
2. `bizSystem -> database -> op -> action -> trace`
3. `bizSystem -> nosql -> op -> trace`

### 10.3 把关键键抽成统一模型

建议后续在代码里统一维护一套键模型：

- 业务对象键
  - `bizSystemId`
  - `applicationId`
  - `instanceId`
  - `actionId`
- 追踪键
  - `traceId`
  - `queryTimestamp`
  - `actionGuid`
  - `traceGuid`
  - `requestId`
- 组件键
  - `componentType`
  - `componentSubtype`
  - `componentName`
  - `opName`

有了这套模型，后续很多脚本就不会散在各个接口里重复拼参数。

## 11. 结论

基于当前抓包和手册，整个听云系统已经可以被理解为一套围绕“业务系统”组织起来的多视角诊断平台：

- 上层是业务系统、应用、实例和健康度
- 中层是事务、Top 请求和趋势图
- 下层是请求追踪、调用树、异常、日志
- 横向能力是 Database、NoSQL、连接池和组件拓扑

而当前已经抓到的调用，已经足够支撑三条非常实用的诊断闭环：

1. 从业务系统找到最慢事务，再下钻到 trace
2. 从业务系统找到最重数据库，再下钻到 SQL、动作和 trace
3. 从业务系统找到最热 Redis 节点，再下钻到操作和拓扑

这意味着我们现在拿到的，不只是若干 API 样本，而是一套已经能模拟平台诊断思路的“系统调用骨架”。
