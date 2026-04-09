# 巡检范围
- 业务系统：集团法务（bizSystemId=1065）
- 巡检窗口：2025-12-20 至 2026-03-31
- 取数方式：机器 B 使用 `tingyun_adapter_client` 通过远端 adapter 服务拉取 live pack
- 主入口：`report_fact_pack`
- 本轮新增深挖 pack：`trace_case_pack`、`action_fact_sheet`、`action_dependency_breakdown_pack`、`trace_fact_sheet`、`instance_analysis_pack`、`connection_pool_pack`

# 能力边界
- 页面章节仍然只能使用“页面代理证据”，不能写成真实 RUM 页面体验数据。
- 代表性页面链接大多是 `direct`，但多个对象仍复用相同 direct_url，截图前必须人工确认页面语义。
- knowledge repository 已配置，但本业务系统的 confirmed knowledge / pending proposals / judgment log 当前均为空，不能把 comparison 结果直接等同于“历史从未出现”。
- 应用/实例层目前只能保守观察 CPU 与实例分布，JVM 图为空，不能替代完整实例资源分析。

# 总体判断
- 业务系统长窗整体指标仍然不差：平均响应时间约 107ms，吞吐约 5.2，Apdex=0.915。
- 真正的风险集中在少数 action/trace/SQL/上传链路，而不是系统总体或主机 CPU 打满。
- 本轮较上一轮更明确地区分了两类数据库问题：
  - 单条极端慢 trace 的瓶颈 SQL/数据库独占耗时
  - 长窗累计最重的全局慢 SQL 与连接池争抢
- 同时也确认：上传异常更像“共享上传/预览链路问题”，不是单个 action 的偶发慢请求。

# 主问题摘要
## MI-01 “afterPropertiesSet” 对象在长窗内呈现新风险，但代表慢样本更像真实业务 URI 的代码级放大
- 对象范围：action / app=1645 / actionId=13161 / alias=SpringController/ProductIndexController.afterPropertiesSet / representative_uri=/grcv5/api/mobile/v1/common-mobile/getCommonOpinion/nbg36512
- 异常时间窗：2025-12-20 至 2026-03-31；comparison baseline 为最近 30 天对比前 30 天
- 影响：action_fact_sheet 显示平均响应 676275.5ms、总耗时 16906887ms、共 25 次调用；comparison_signals_pack 标记为 new_risk，代表 trace 1710818946 单次耗时 8976ms 并伴随错误痕迹。
- 证据 1：comparison_signals_pack：对象在当前窗口出现而基线窗口未出现，delta_metrics 中最大响应时间达到 2,788,495ms。
- 证据 2：action_fact_sheet + action_dependency_breakdown_pack：该对象长窗内有 8 条 trace candidates，依赖分解由 Code-Java、Redis、Database 共同构成，代表 trace 指向代码段 `javax.servlet.ServletRequestListener.requestInitialized`。
- 初判根因：当前更像应用代码路径和 Redis/数据库编排放大，而不是纯数据库单点；同时 action alias 与真实 URI 不一致，增加了对象判读成本。
- 置信度：medium
- 建议动作：正式报告中需同时保留 alias 与代表 URI；下轮建议补 route 映射或业务标签，确认该对象是否真实用户入口。

## MI-02 dwrLawCheckService.lawyerEorkTimeTop10Data.dwr 出现极端慢 trace，瓶颈明确落在 MySQL
- 对象范围：action+trace / app=1644 / actionId=31762 / traceId=1651592641 / URI=URI/grcv5/dwr/call/plaincall/dwrLawCheckService.lawyerEorkTimeTop10Data.dwr
- 异常时间窗：2025-12-20 至 2026-03-31；代表事件时间=2026-03-26 08:20:12
- 影响：action_fact_sheet 显示该 action 平均响应 1541760.0ms，仅 2 次调用就累计 3083520ms；代表 trace 单次耗时 1565149.563ms。
- 证据 1：trace_fact_sheet / trace_case_pack：trace 1651592641 的 suspectedProblemList 将 1,565,144ms 独占耗时指向 `MySQL/10.190.22.21:3306/bpmapp_hg`。
- 证据 2：action_dependency_breakdown_pack：同一 action 的 Database-MySQL 与 Pool-Database 响应时间均达 1,541,760ms，说明数据库与数据库连接层共同拖慢整条链路。
- 初判根因：该问题是数据库主导的极端慢调用，应用层只是承接放大结果；优先排查具体 SQL 与数据库连接占用。
- 置信度：high
- 建议动作：将该 trace 作为正文典型深挖样本，结合 SQL 主问题单列分析，不与 afterPropertiesSet 混写。

## MI-03 SQL sql:6307bcf55ade35ac 是长窗内累计影响最大的数据库问题，并伴随连接池争抢信号
- 对象范围：sql / MySQL 10.190.22.21:3306 / fingerprint=sql:6307bcf55ade35ac
- 异常时间窗：2025-12-20 至 2026-03-31
- 影响：平均响应时间 1,695,508ms，总耗时 269,585,795ms，159 次执行、110 条 trace 绑定、79 次错误；同一 MySQL 连接池历史最大 waiter_connections 达 92。
- 证据 1：slow_sql_pack + sql_fact_sheet：该 SQL 带有 DISTINCT/SUBQUERY 特征，errorRate=49.69%，同时命中 global_top、optimization、trace_bound。
- 证据 2：database_component_pack + connection_pool_pack：MySQL 组件总耗时 2,151,883,527ms，top_actions 错误率高；连接池 waiter_risk=high，max_waiter_connections=92。
- 初判根因：复杂 count 子查询导致执行计划与索引覆盖不佳，并在高峰时段放大为数据库连接池争抢。
- 置信度：high
- 建议动作：把这条 SQL 作为 SQL 章节主问题 1；下轮若改代码，应补 impacted_actions / related_traces 的更稳定出参。

## MI-04 附件上传链路是高量高错异常簇，代表错误样本指向在线预览代码路径
- 对象范围：action cluster / actionId=13513(app1644) + 13332(app1645) / alias=SpringController/${url.attachment}/${url.attachment.upload} (POST)
- 异常时间窗：2025-12-20 至 2026-03-31
- 影响：两条上传链路 action_fact_sheet 合计 45962 次调用、errorCount=100，errorRate 分别为 0.161 和 0.277。
- 证据 1：action_fact_sheet：两条 action 都具备大量慢 trace/error trace 候选，代表 trace 1715659568 单次 3,869ms 且 trace candidate 标记 error_count=5。
- 证据 2：trace_fact_sheet + action_dependency_breakdown_pack：代表 trace 的 maxExclusiveTime 指向 `cn.keking.web.controller.OnlinePreviewController.onlinePreview`；上传链路依赖分解长期被 Code-Java、Redis、Database、External-Http 共同占据。
- 初判根因：问题更像共享的附件上传/在线预览链路异常，可能涉及文件预览服务、公共代码路径和下游依赖协同放大。
- 置信度：high
- 建议动作：正文中建议把两条上传 action 合并成一个“上传/预览链路异常簇”，并单独说明 route 演进与文件服务关系。

# observations 摘要
- 外部 http 依赖在 comparison 中呈回归趋势，但暂不足以单独上升为系统主问题：current response_time_ms 从 4506ms 升至 5507ms，长窗平均 4944ms，错误率 13.25%，影响 3 个上游应用。 建议=保留为 observation，正式报告可写成跨系统共享风险，不宜单独定为核心根因。
- 两个 main_issue trace 候选在手工追取后仍拿不到有效 detail，属于深挖素材不足：虽然 main_issue_selections 将其列为强候选，但 trace_fact_sheet 返回 detail_summary 为空，无法用于正式正文举证。 建议=在 01_exec_summary.md 记为下轮改代码建议；本轮只把它们保留为 observation。
- 应用 / 实例层未见明显 CPU 不均衡，问题更集中在请求与下游组件层：三套 application 都是单实例部署，CPU latest/peak 均较低（0.46%~2.95%），没有主机资源打满迹象。 建议=在正式报告中把“应用/实例层未见明显不均衡”写成排除项，同时说明 JVM 图为空是能力边界。
- 上传链路在 comparison 中出现“旧 upload 路由 disappeared、当前 POST 变体仍异常”的路由演进迹象：comparison_signals_pack 同时给出 disappeared 与 insufficient_baseline 信号，说明上传链路对象标识存在演进或切换。 建议=正式报告中按“上传/预览异常簇”聚合对象，避免把 disappeared route 误判成问题消失。

# SQL 主问题
- `sql:6307bcf55ade35ac`：长窗累计最重 SQL，avg=1,695,508ms，total=269,585,795ms，count=159，trace_count=110，error_count=79，伴随 DISTINCT/SUBQUERY 与连接池 waiter 风险。
- `sql:61ab02dec2c8559a`：同表系 count/列表查询的次一级重 SQL，avg=118,007ms，count=50，trace_count=23，建议在 SQL 章节作为“同类复杂 SQL 第二梯队”保留。
- 代表性慢 trace `1651592641` 的 primary_sql_fingerprint 为 `sql:38dc89d7da5b3f12`，它更适合写进 trace 深挖专题，不应与全局最重 SQL 混为同一对象。

# SQL 优化储备
- 当前 adapter `sql_opportunities` 为空，以下为机器 B 基于 `sql_candidates` 手工整理的 SQL 优化储备，不代表 adapter confirmed opportunities。
- sql:b654acf7ba89a028：28 次执行、trace_count=28、总耗时 383,779ms，虽然单次不如主问题 SQL 极端，但频次稳定。 初判=结果集裁剪、索引命中和读取路径仍有优化空间。
- sql:75960d2532477f1c：5 次执行，总耗时 65,528ms，trace_count=2，结构复杂度高于其出现频次。 初判=复杂 join/subquery 结构带来放大风险。
- sql:574e665bb656f41e：3 次执行、总耗时 235,688ms，带 SUBQUERY 标签。 初判=子查询结构可能在特定业务参数下放大。

# trace 典型样本
- 超慢样本：trace `1651592641`，发生于 2026-03-26 08:20:12，duration=1565149.563ms，数据库独占耗时约 1,565,144ms。
- 代码级慢样本：trace `1710818946`，action alias=`SpringController/ProductIndexController.afterPropertiesSet`，真实 URI=`/grcv5/api/mobile/v1/common-mobile/getCommonOpinion/nbg36512`，duration=8976.0ms，maxExclusiveTime 指向代码段 `javax.servlet.ServletRequestListener.requestInitialized`。
- 上传错误样本：trace `1715659568`，URI=`/grcv5/user/component/AttachmentController/upload`，duration=3869.932ms，maxExclusiveTime 指向 `cn.keking.web.controller.OnlinePreviewController.onlinePreview`。
- 候选但未成功深挖：trace `1423238353` 与 `1432031331` 仍只拿到 requestId，没有 detail。

# 页面能力边界
- 页面体验：状态=`partial`，说明=Dedicated page-side APIs are not exposed yet; page objects are inferred from topology and backend request evidence.
- 可用页面证据：user_to_application_topology, representative_request_urls, external_dependency_edges, backend_action_and_trace_correlation
- 缺失页面证据：slow_pages, slow_requests, js_errors, browser_breakdown, geo_breakdown, frontend_resource_timing
- 链接边界：状态=`base_url_fallback`，说明=Links now prefer captured real page URLs when page context exists; otherwise they still fall back to console root URLs plus navigation hints.

# 链接与截图摘要
- screenshot_index_pack 共 9 张截图建议卡；本轮另外补入 action/trace/dependency/connection_pool 对象页链接，统一索引到 `04_evidence_index.csv`。
- 页面章节必须明确标注“页面代理证据”，不能虚构慢页面占比、JS 错误数、浏览器分布、地域分布、首屏时间、完全加载时间。
- 连接池、外部依赖、trace 详情页虽然多数为 direct deep link，但仍需人工确认页面确实落在目标对象，而不是被 captured page context 错配。

# 待人工定稿项
- action 13161 的 alias 是 `afterPropertiesSet`，但代表 trace 对应真实 URI 是 `/grcv5/api/mobile/v1/common-mobile/getCommonOpinion/nbg36512`，需人工确认对象映射和业务含义。
- 代表性慢 trace 的 primary_sql_fingerprint=`sql:38dc89d7da5b3f12`，而长窗最重 SQL 是 `sql:6307bcf55ade35ac`，正式报告不能把“单次最慢 trace SQL”和“全局最重 SQL”混写成同一对象。
- 上传链路 trace 1715659568 在 detail 中 status=200、exception_summary=0，但 trace candidate 又显示 error_count=5，需人工确认 error_count 的统计口径。
- 连接池 overview 的 direct_url 指向接口 overview 页而非专门的连接池页面，取证截图前需人工确认是否落对页面。
- topology_dependency_pack 的 business_graph 包含其他业务系统节点，使用时要明确这是跨业务系统拓扑视角，不要误写成本业务系统内部依赖。
