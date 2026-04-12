# 听云手册上下文与抓包接口映射笔记

生成时间：2026-04-03  
手册来源：`/Users/wangrundong/work/mywork/reference/manuals/基调听云应用与微服务用户使用手册.pdf`  
抓包样例目录：`/Users/wangrundong/work/mywork/tingyun_cdp_capture/captured_api`

## 目的

这份笔记的目标不是替代接口清单，而是把：

- 听云平台手册中的页面概念
- 当前抓到的接口家族
- 典型字段和键链路

放到同一张地图里，减少后续“只看接口名硬猜用途”的偏差。

## 一、手册里的核心对象模型

从手册目录和正文可以提取出几个核心对象：

1. 业务系统  
   用来归类应用，作为可视化和追踪分析的上层对象
2. 应用 / 实例  
   展示吞吐率、响应时间中位数、错误率、实例数、技术栈、下游应用和服务组件
3. 事务 / 请求 / 服务接口  
   展示 Top 请求、概览、响应时间、错误、线程剖析、请求追踪
4. 服务组件  
   包括 Database、NoSQL、MQ、外部服务
5. 请求追踪  
   包括追踪概览、性能分解图、疑似问题、拓扑、Call Table、Call Tree、异常、SQL 统计、NoSQL 统计、日志
6. 连接池  
   独立作为一类分析对象

当前抓包出来的对象键，和这个模型是对齐的：

- `bizSystemId`
- `applicationId`
- `instanceId`
- `actionId`
- `componentType`
- `componentSubtype`
- `componentName`
- `traceId`
- `actionGuid`

## 二、手册章节到接口家族的映射

### 1. `3.4 业务系统`

更贴近以下接口：

- `application/business/overview/*`
- `graph/queryBizDetailGraph`
- `graph/queryBizSystenGraph`
- `graph/queryGraphHealth`

这些接口更偏“业务系统级”总览和拓扑。

### 2. `3.5 应用与实例`

更贴近以下接口：

- `application/charts/*`
- `graph/information`
- `graph/query/diagram`
- `graph/query/overview`
- `webaction/*`

手册里提到的：

- 应用概览
- 请求分析
- 响应时间性能分解
- 响应时间分布
- 调用者分析
- 热点方法

大体都能在这批接口中找到承载层。

### 3. `3.6 事务`

更贴近：

- `webaction/list/actionList`
- `webaction/overview`
- `webaction/charts/*`
- `webaction/performance/breakdown*`
- `webaction/threadAnalysisList`

这批接口已经能支撑“事务列表 -> 概览 -> 趋势 -> 性能分解”。

### 4. `3.9 DATABASE 服务组件`

这是这轮新增最明显的一组：

- 概览
  - `Database/list`
  - `Database/info`
- SQL 分析 / 操作分析
  - `Database/analysis`
- 关联动作
  - `component/database/actionList`
- 关联追踪
  - `component/database/actionTraceList`
- 拓扑
  - `graph/component/queryDataBaseGraph`
- 连接池
  - `connection/list`
  - `connection/chart`
  - `connection/database/chart`

### 5. `3.10 NOSQL 服务组件`

与 Database 家族几乎平行：

- `NoSQL/list`
- `NoSQL/overview`
- `NoSQL/analysis`
- `NoSQL/trace`
- `NoSQL/errorTypeAmount`
- `graph/component/queryNosqlGraph`

### 6. `3.14 请求追踪`

这组已经能对应到多个页签级接口：

- 追踪概览
  - `action/trace/detail`
- 异常
  - `action/trace/detail/exceptions`
- Call Tree
  - `action/trace/callTree`
- 快照/片段
  - `action/trace/detail/snapshotTimeInfo`
- 环境信息
  - `action/trace/detail/queryAgentVersionInfo`
- 日志
  - `data/logTrace/searchLogTrace`

## 三、当前最清晰的三条分析闭环

### 1. 事务性能闭环

`bizSystemId -> actionList -> action overview -> trace_current_overview -> trace detail`

对应接口：

- `webaction/list/actionList`
- `webaction/overview`
- `graph/query/overview` 中 `metric=trace_current_overview`
- `action/trace/detail`
- `action/trace/callTree`

### 2. 数据库组件闭环

`bizSystemId -> Database/list -> Database/info -> Database/analysis -> component/database/actionList -> component/database/actionTraceList -> trace`

这一条是这轮最重要的新能力。

### 3. NoSQL 组件闭环

`bizSystemId -> NoSQL/list -> NoSQL/overview -> NoSQL/analysis -> NoSQL/trace`

当前最后一步样本仍偏空，但链路已经建立。

## 四、字段和术语上的重要对齐

### 1. `response`、`respTime`、`totalResptime`

当前抓包里它们通常分别对应：

- `response / respTime`
  - 单次平均或当前对象平均响应时间
- `totalResptime / totalResponse`
  - 时间窗内累计总耗时

不同接口命名略有差异，但语义接近。

### 2. `throught`

抓包字段名一直是 `throught`，不是标准英文 `throughput`。  
结合手册内容，它应当就是吞吐率。

### 3. `count`

在不同页面中通常表示：

- 请求次数
- 调用次数
- SQL/NoSQL 操作次数

需要结合对象层级理解。

### 4. `traceCount`

在组件接口里很有价值，表示该组件对象相关联的 trace 数量，适合用来判断“是否可以继续追踪下钻”。

## 五、数据库与 NoSQL 的编码规则

当前抓包里 `opName` 有两种形式：

1. 明文
   - 例如 `SELECT ...`
   - 例如 `update HD_TODOLIST ...`
2. `tyBase64_` 前缀
   - 例如 `tyBase64_RVZBTA`
   - 例如 `tyBase64_c2VsZWN0IERJU1RJTkNUIGluZm8uSUQ`

已验证：

- `tyBase64_RVZBTA -> EVAL`
- `tyBase64_c2VsZWN0IERJU1RJTkNUIGluZm8uSUQ -> select DISTINCT info.ID`

所以后续如果要自动总结 SQL / Redis 操作名，最好先做：

1. 去掉 `tyBase64_`
2. 再做 Base64 解码

## 六、当前最值得重点关注的典型样本

### Database 组件

当前 `集团法务` 下已经能明确看到：

- `MySQL / 10.190.22.21:3306`
- `count: 60153`
- `respTime: 8.0`
- `throught: 33.42`
- `traceCount: 36`

这说明数据库调用非常活跃，而且已有可追踪样本。

### 慢数据库操作

当前已经能看到：

- `SELECT ... BPM_TODO_LOGO ...`
- `select DISTINCT info.ID ...`
- `update HD_TODOLIST ...`

并且能看到对应的：

- `respTime`
- `count`
- `totalResptime`
- `traceCount`

### Redis / NoSQL 节点

当前 `集团法务` 下可见多个 Redis 分片节点：

- `10.190.22.20:6379/7`
- `10.190.22.20:6379/1`
- `10.190.22.19:6379/2`
- `10.190.22.18:6379/2`

说明 NoSQL 不是单点依赖，而是多节点分布。

## 七、对后续整理工作的建议

如果后面要把这些 JSON 继续交给模型总结，最推荐按下面三组来分批：

1. 业务系统 / 应用 / 事务组
   - `application/*`
   - `webaction/*`
   - `health/*`
2. Database / NoSQL / 连接池组
   - `Database/*`
   - `NoSQL/*`
   - `connection/*`
   - `component/database/*`
   - `graph/component/*`
3. 请求追踪组
   - `action/trace/*`
   - `data/logTrace/*`

这样模型更容易保持上下文一致，不会把对象层级混在一起。

## 结论

从手册和抓包一起看，当前目录里的接口样本已经不只是“抓到了一些 API”，而是基本还原了听云平台的三套核心视角：

1. 业务系统与应用视角
2. 事务与请求追踪视角
3. 服务组件与连接池视角

这意味着后续不管是写报告、做逆向说明，还是继续模拟调用，都会比之前更有结构可循。
