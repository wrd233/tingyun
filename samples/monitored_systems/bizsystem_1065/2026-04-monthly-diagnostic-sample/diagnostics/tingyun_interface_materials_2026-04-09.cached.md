# Tingyun 接口逐条素材包（缓存版）

- 生成时间：2026-04-09T11:57:57.365272+08:00
- 模式：cached_only
- 接口数：32
- 已对齐 trace 数：26
- 已补 dependency breakdown 数：28

## 1. URI/grcv5/dwr/call/plaincall/dwrLawCheckService.lawyerEorkTimeTop10Data.dwr

- 用户关注点：单次耗时极端，优先核对对应 SQL、连接池等待和数据库独占耗时。
- 聚合指标：请求 5, 平均 1528404.4 ms, 错误 0, 错误率 0.0, 慢次数 5
- 主 action：{'application_id': 1645, 'action_id': 31342, 'action_name': 'URI/grcv5/dwr/call/plaincall/dwrLawCheckService.lawyerEorkTimeTop10Data.dwr'}
- action 映射：
  - 1644/31762: 请求 2, 平均 1541760.0 ms, 错误 0, 慢次数 2
  - 1645/31342: 请求 3, 平均 1519501.0 ms, 错误 0, 慢次数 3
- 代表 trace：{'trace_id_numeric': '1488639791', 'duration_ms': 1532067.823}, status 200, uri /grcv5/dwr/call/plaincall/dwrLawCheckService.lawyerEorkTimeTop10Data.dwr, duration 1532067.823 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 1532061.893 ms, count 0
  - POOL/None: exclusive 0.258 ms, count 6
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 1519499.0 ms, 次数 84, 错误 0
  - NoSQL-Redis: 响应 707691.0 ms, 次数 15, 错误 0
  - Pool-Redis: 响应 607800.0 ms, 次数 15, 错误 0
  - Database-MySQL: 响应 1519501.0 ms, 次数 3, 错误 0
  - Pool-Database: 响应 1519501.0 ms, 次数 3, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 2. SpringController/ProductIndexController.afterPropertiesSet

- 用户关注点：接口名与真实业务入口可能不一致，需保留别名与真实 URI 一起看。
- 聚合指标：请求 47, 平均 363957.468 ms, 错误 0, 错误率 0.0, 慢次数 47
- 主 action：{'application_id': 1645, 'action_id': 13161, 'action_name': 'SpringController/ProductIndexController.afterPropertiesSet'}
- action 映射：
  - 1644/13155: 请求 22, 平均 9051.0 ms, 错误 0, 慢次数 22
  - 1645/13161: 请求 25, 平均 676276.0 ms, 错误 0, 慢次数 25
- 代表 trace：{'trace_id_numeric': '1699647009', 'duration_ms': 13691.55}, status 200, uri /grcv5/api/flow-mobile/v1/task-form-process/todo-pages/2248480, duration 13691.55 ms
- trace 可疑点：
  - CODE/javax.servlet.ServletRequestListener.requestInitialized: exclusive 7711.285 ms, count 0
  - POOL/None: exclusive 10.579999999999934 ms, count 672
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - NoSQL-Redis: 响应 226821.0 ms, 次数 515, 错误 0
  - Code-Java: 响应 552695.0 ms, 次数 189, 错误 0
  - Pool-Redis: 响应 162015.0 ms, 次数 515, 错误 0
  - Pool-Database: 响应 538307.0 ms, 次数 62, 错误 0
  - Database-MySQL: 响应 19404.0 ms, 次数 1720, 错误 0
- 当前根因判断：当前更像外部依赖或预览服务链路放大。

## 3. SpringController/TemplateUploadController.setTemplateService

- 用户关注点：低频但极慢，优先确认文件解析、模板校验、存储读写或外部预览放大。
- 聚合指标：请求 45, 平均 84458.933 ms, 错误 2, 错误率 0.044444, 慢次数 24
- 主 action：{'application_id': 1645, 'action_id': 13336, 'action_name': 'SpringController/TemplateUploadController.setTemplateService'}
- action 映射：
  - 1644/13239: 请求 20, 平均 2883.0 ms, 错误 2, 慢次数 9
  - 1645/13336: 请求 25, 平均 149720.0 ms, 错误 0, 慢次数 15
- 代表 trace：{'trace_id_numeric': '1701589579', 'duration_ms': 11525.581}, status 200, uri /grcv5/bpm/create.htm, duration 11525.581 ms
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 7852.568 ms, count 0
  - POOL/None: exclusive 14.760999999999907 ms, count 1360
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 295304.0 ms, 次数 128, 错误 0
  - Code-Java: 响应 98514.0 ms, 次数 255, 错误 0
  - NoSQL-Redis: 响应 32233.0 ms, 次数 492, 错误 0
  - NoSQL-Redis: 响应 7878.0 ms, 次数 1935, 错误 0
  - Pool-Redis: 响应 5254.0 ms, 次数 1935, 错误 0
- 当前根因判断：当前更像附件/预览/模板处理链路放大，需要把上传、预览、存储读取拆开看。

## 4. SpringController/serverapi/restapi/other/v1

- 用户关注点：低频但均值高，适合结合 trace 先看具体调用栈。
- 聚合指标：请求 49, 平均 22302.02 ms, 错误 1, 错误率 0.020408, 慢次数 2
- 主 action：{'application_id': 1645, 'action_id': 13158, 'action_name': 'SpringController/serverapi/restapi/other/v1'}
- action 映射：
  - 1644/13163: 请求 23, 平均 751.0 ms, 错误 0, 慢次数 1
  - 1645/13158: 请求 26, 平均 41366.0 ms, 错误 1, 慢次数 1
- 代表 trace：{'trace_id_numeric': '1709041248', 'duration_ms': 970.645}, status 500, uri /grcv5/rest/mobile/thirdpartylogin.json, duration 970.645 ms
- trace 可疑点：
  - None/org.springframework.web.util.NestedServletException: exclusive 0.0 ms, count 0
  - CODE/com.hd.rcugrc.platform.rest.mobile.filter.MyMobilePreLoginFilter.doFilter: exclusive 335.167 ms, count 0
  - POOL/None: exclusive 0.673 ms, count 9
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - NoSQL-Redis: 响应 141642.0 ms, 次数 30, 错误 0
  - Code-Java: 响应 34155.0 ms, 次数 124, 错误 0
  - Pool-Redis: 响应 106183.0 ms, 次数 30, 错误 0
  - Database-MySQL: 响应 354159.0 ms, 次数 3, 错误 0
  - Pool-Database: 响应 265619.0 ms, 次数 4, 错误 0
- 当前根因判断：当前已确认这是显著慢调用，但还缺少更细的 SQL/错误样本拆解。

## 5. URI/grcv5/dwr/call/plaincall/dwrAssessEvaService.copyAssessEva.dwr

- 用户关注点：调用量不高但耗时已进入重点排查范围，先补 trace 和依赖分解。
- 聚合指标：请求 4, 平均 55913.75 ms, 错误 0, 错误率 0.0, 慢次数 4
- 主 action：{'application_id': 1644, 'action_id': 18590, 'action_name': 'URI/grcv5/dwr/call/plaincall/dwrAssessEvaService.copyAssessEva.dwr'}
- action 映射：
  - 1644/18590: 请求 4, 平均 55914.0 ms, 错误 0, 慢次数 4
- 代表 trace：当前缓存未对齐到该接口样本
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 70870.0 ms, 次数 56, 错误 0
  - Code-Java: 响应 47190.0 ms, 次数 28, 错误 0
  - Code-Java: 响应 34717.0 ms, 次数 28, 错误 0
  - NoSQL-Redis: 响应 53154.0 ms, 次数 8, 错误 0
  - Pool-Redis: 响应 35436.0 ms, 次数 8, 错误 0
- 当前根因判断：当前已确认这是显著慢调用，但还缺少更细的 SQL/错误样本拆解。
- 证据缺口：
  - 当前缓存里还没有这条接口的对齐 trace_fact_sheet。

## 6. URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getInitData.dwr

- 用户关注点：LegalDemand 域初始化读取慢，优先看初始化查询、缓存命中和列表装配。
- 聚合指标：请求 23, 平均 24237.087 ms, 错误 0, 错误率 0.0, 慢次数 14
- 主 action：{'application_id': 1645, 'action_id': 14562, 'action_name': 'URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getInitData.dwr'}
- action 映射：
  - 1644/14118: 请求 9, 平均 33504.0 ms, 错误 0, 慢次数 7
  - 1645/14562: 请求 14, 平均 18280.0 ms, 错误 0, 慢次数 7
- 代表 trace：{'trace_id_numeric': '1488359386', 'duration_ms': 33654.052}, status 200, uri /grcv5/dwr/call/plaincall/dwrLegalDemandService.getInitData.dwr, duration 33654.052 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 22251.629 ms, count 0
  - POOL/None: exclusive 0.081 ms, count 8
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 17481.0 ms, 次数 112, 错误 0
  - Code-Java: 响应 13497.0 ms, 次数 140, 错误 0
  - Code-Java: 响应 14364.0 ms, 次数 84, 错误 0
  - Code-Java: 响应 38831.0 ms, 次数 28, 错误 0
  - Code-Java: 响应 36551.0 ms, 次数 28, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 7. URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getCountByPast5.dwr

- 用户关注点：LegalDemand 域初始化读取慢，优先看初始化查询、缓存命中和列表装配。
- 聚合指标：请求 21, 平均 25688.524 ms, 错误 0, 错误率 0.0, 慢次数 21
- 主 action：{'application_id': 1645, 'action_id': 14565, 'action_name': 'URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getCountByPast5.dwr'}
- action 映射：
  - 1644/14120: 请求 9, 平均 34459.0 ms, 错误 0, 慢次数 9
  - 1645/14565: 请求 12, 平均 19111.0 ms, 错误 0, 慢次数 12
- 代表 trace：{'trace_id_numeric': '1488360227', 'duration_ms': 36598.935}, status 200, uri /grcv5/dwr/call/plaincall/dwrLegalDemandService.getCountByPast5.dwr, duration 36598.935 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 22250.912 ms, count 0
  - POOL/None: exclusive 0.19000000000000003 ms, count 20
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 17406.0 ms, 次数 84, 错误 0
  - Code-Java: 响应 12481.0 ms, 次数 112, 错误 0
  - Code-Java: 响应 15271.0 ms, 次数 84, 错误 0
  - Code-Java: 响应 41726.0 ms, 次数 28, 错误 0
  - Code-Java: 响应 39628.0 ms, 次数 28, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 8. URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getServerType.dwr

- 用户关注点：LegalDemand 域初始化读取慢，优先看初始化查询、缓存命中和列表装配。
- 聚合指标：请求 22, 平均 24038.364 ms, 错误 0, 错误率 0.0, 慢次数 13
- 主 action：{'application_id': 1645, 'action_id': 14563, 'action_name': 'URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getServerType.dwr'}
- action 映射：
  - 1644/14119: 请求 9, 平均 33339.0 ms, 错误 0, 慢次数 7
  - 1645/14563: 请求 13, 平均 17600.0 ms, 错误 0, 慢次数 6
- 代表 trace：{'trace_id_numeric': '1488359455', 'duration_ms': 33836.291}, status 200, uri /grcv5/dwr/call/plaincall/dwrLegalDemandService.getServerType.dwr, duration 33836.291 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 20768.479 ms, count 0
  - POOL/None: exclusive 0.3660000000000001 ms, count 12
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 17694.0 ms, 次数 112, 错误 0
  - Code-Java: 响应 14634.0 ms, 次数 84, 错误 0
  - Code-Java: 响应 39078.0 ms, 次数 28, 错误 0
  - Code-Java: 响应 9572.0 ms, 次数 112, 错误 0
  - Code-Java: 响应 36724.0 ms, 次数 28, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 9. URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getPlace.dwr

- 用户关注点：LegalDemand 域初始化读取慢，优先看初始化查询、缓存命中和列表装配。
- 聚合指标：请求 22, 平均 23166.045 ms, 错误 0, 错误率 0.0, 慢次数 13
- 主 action：{'application_id': 1645, 'action_id': 14559, 'action_name': 'URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getPlace.dwr'}
- action 映射：
  - 1644/14117: 请求 8, 平均 31743.0 ms, 错误 0, 慢次数 6
  - 1645/14559: 请求 14, 平均 18265.0 ms, 错误 0, 慢次数 7
- 代表 trace：{'trace_id_numeric': '1488359381', 'duration_ms': 33491.837}, status 200, uri /grcv5/dwr/call/plaincall/dwrLegalDemandService.getPlace.dwr, duration 33491.837 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 27492.634 ms, count 0
  - POOL/None: exclusive 0.068 ms, count 9
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 17475.0 ms, 次数 112, 错误 0
  - Code-Java: 响应 13514.0 ms, 次数 140, 错误 0
  - Code-Java: 响应 14373.0 ms, 次数 84, 错误 0
  - Code-Java: 响应 38684.0 ms, 次数 28, 错误 0
  - Code-Java: 响应 36406.0 ms, 次数 28, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 10. SpringController/${url.bpm.user.senopInfo}

- 用户关注点：先按 trace/依赖分解补证，再区分代码、数据库、外部依赖还是路由参数问题。
- 聚合指标：请求 65, 平均 38147.769 ms, 错误 0, 错误率 0.0, 慢次数 65
- 主 action：{'application_id': 1645, 'action_id': 16223, 'action_name': 'SpringController/${url.bpm.user.senopInfo}'}
- action 映射：
  - 1644/16011: 请求 31, 平均 37628.0 ms, 错误 0, 慢次数 31
  - 1645/16223: 请求 34, 平均 38621.0 ms, 错误 0, 慢次数 34
- 代表 trace：{'trace_id_numeric': '1700014268', 'duration_ms': 53969.498}, status 200, uri /grcv5/user/senopInfo.htm, duration 53969.498 ms
- trace 可疑点：
  - CODE/com.hd.rcugrc.web.servlet.mvc.UserController.getSenstiveOperationInfos: exclusive 53834.871 ms, count 0
  - NOSQL/None: exclusive 4.552999999999999 ms, count 11
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 52075.0 ms, 次数 66, 错误 0
  - Code-Java: 响应 33851.0 ms, 次数 99, 错误 0
  - Code-Java: 响应 31293.0 ms, 次数 99, 错误 0
  - Code-Java: 响应 26803.0 ms, 次数 96, 错误 0
  - Code-Java: 响应 56432.0 ms, 次数 33, 错误 0
- 当前根因判断：当前已确认这是显著慢调用，但还缺少更细的 SQL/错误样本拆解。

## 11. URI/grcv5/user/component/AttachmentController/upload

- 用户关注点：上传错误样本接口，可作为上传异常簇的 trace 入口重点追查。
- 聚合指标：请求 11, 平均 81268.545 ms, 错误 11, 错误率 1.0, 慢次数 9
- 主 action：{'application_id': 1644, 'action_id': 18885, 'action_name': 'URI/grcv5/user/component/AttachmentController/upload'}
- action 映射：
  - 1644/18885: 请求 6, 平均 63626.0 ms, 错误 6, 慢次数 5
  - 1645/19684: 请求 5, 平均 102440.0 ms, 错误 5, 慢次数 4
- 代表 trace：当前缓存未对齐到该接口样本
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 58370.0 ms, 次数 56, 错误 0
  - Code-Java: 响应 29355.0 ms, 次数 56, 错误 0
  - NoSQL-Redis: 响应 47146.0 ms, 次数 16, 错误 0
  - Pool-Redis: 响应 31431.0 ms, 次数 16, 错误 0
  - NoSQL-Redis: 响应 23711.0 ms, 次数 16, 错误 0
- 当前根因判断：当前更像附件/预览/模板处理链路放大，需要把上传、预览、存储读取拆开看。
- 证据缺口：
  - 当前缓存里还没有这条接口的对齐 trace_fact_sheet。

## 12. URI/grcv5/user/component/AttachmentController/frmIndiDocs

- 用户关注点：先按 trace/依赖分解补证，再区分代码、数据库、外部依赖还是路由参数问题。
- 聚合指标：请求 2, 平均 122517.0 ms, 错误 2, 错误率 1.0, 慢次数 2
- 主 action：{'application_id': 1644, 'action_id': 19286, 'action_name': 'URI/grcv5/user/component/AttachmentController/frmIndiDocs'}
- action 映射：
  - 1644/19286: 请求 2, 平均 122517.0 ms, 错误 2, 慢次数 2
- 代表 trace：当前缓存未对齐到该接口样本
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 56881.0 ms, 次数 56, 错误 0
  - NoSQL-Redis: 响应 45944.0 ms, 次数 16, 错误 0
  - Pool-Redis: 响应 30629.0 ms, 次数 16, 错误 0
- 当前根因判断：当前更像附件/预览/模板处理链路放大，需要把上传、预览、存储读取拆开看。
- 证据缺口：
  - 当前缓存里还没有这条接口的对齐 trace_fact_sheet。

## 13. SpringController/onlinePreview

- 用户关注点：高访问高慢次数，优先排查预览服务、文件转换、缓存和存储读取。
- 聚合指标：请求 36311, 平均 3712.716 ms, 错误 0, 错误率 0.0, 慢次数 7731
- 主 action：{'application_id': 1646, 'action_id': 13229, 'action_name': 'SpringController/onlinePreview'}
- action 映射：
  - 1646/13229: 请求 36311, 平均 3713.0 ms, 错误 0, 慢次数 7731
- 代表 trace：{'trace_id_numeric': '1716307688', 'duration_ms': 1806.121}, status 200, uri /preview/onlinePreview, duration 1806.121 ms
- trace 可疑点：
  - CODE/cn.keking.web.controller.OnlinePreviewController.onlinePreview: exclusive 1714.726 ms, count 0
  - POOL/None: exclusive 0.41800000000000004 ms, count 11
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 7480.0 ms, 次数 22482, 错误 0
  - Code-Java: 响应 13908.0 ms, 次数 9248, 错误 0
  - Code-Java: 响应 10019.0 ms, 次数 10914, 错误 0
  - Code-Java: 响应 6916.0 ms, 次数 15170, 错误 0
  - Code-Java: 响应 7024.0 ms, 次数 10355, 错误 0
- 当前根因判断：当前更像外部依赖或预览服务链路放大。

## 14. SpringController/${url.attachment}/${url.attachment.upload} (POST)

- 用户关注点：上传接口同时具备高访问、偏慢和错误，应作为上传/预览异常簇入口。
- 聚合指标：请求 45743, 平均 6068.401 ms, 错误 100, 错误率 0.002186, 慢次数 13695
- 主 action：{'application_id': 1644, 'action_id': 13513, 'action_name': 'SpringController/${url.attachment}/${url.attachment.upload} (POST)'}
- action 映射：
  - 1644/13513: 请求 23535, 平均 5779.0 ms, 错误 38, 慢次数 6635
  - 1645/13332: 请求 22208, 平均 6375.0 ms, 错误 62, 慢次数 7060
- 代表 trace：{'trace_id_numeric': '1715120752', 'duration_ms': 4366.845}, status 200, uri /grcv5/user/component/AttachmentController/upload, duration 4366.845 ms
- trace 可疑点：
  - CODE/cn.keking.web.controller.OnlinePreviewController.onlinePreview: exclusive 3547.909 ms, count 0
  - POOL/None: exclusive 0.9540000000000001 ms, count 22
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 10024.0 ms, 次数 121247, 错误 0
  - Code-Java: 响应 13612.0 ms, 次数 28953, 错误 0
  - Code-Java: 响应 6618.0 ms, 次数 52402, 错误 0
  - Code-Java: 响应 2763.0 ms, 次数 87190, 错误 0
  - NoSQL-Redis: 响应 3918.0 ms, 次数 32647, 错误 0
- 当前根因判断：当前更像外部依赖或预览服务链路放大。

## 15. URI/grcv5/wp/contractView/viewContract.htm

- 用户关注点：高流量页面入口，优先看页面装配、合同明细查询和关联附件/流程信息聚合。
- 聚合指标：请求 118366, 平均 1354.297 ms, 错误 1019, 错误率 0.008609, 慢次数 5145
- 主 action：{'application_id': 1645, 'action_id': 13314, 'action_name': 'URI/grcv5/wp/contractView/viewContract.htm'}
- action 映射：
  - 1644/13566: 请求 57088, 平均 1319.0 ms, 错误 938, 慢次数 2106
  - 1645/13314: 请求 61278, 平均 1387.0 ms, 错误 81, 慢次数 3039
- 代表 trace：{'trace_id_numeric': '1715789838', 'duration_ms': 1223.522}, status 200, uri /grcv5/wp/contractView/viewContract.htm, duration 1223.522 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 221.472 ms, count 0
  - POOL/None: exclusive 1.0440000000000005 ms, count 205
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 1684.0 ms, 次数 132664, 错误 0
  - Code-Java: 响应 1341.0 ms, 次数 95902, 错误 0
  - Code-Java: 响应 1320.0 ms, 次数 84267, 错误 0
  - Code-Java: 响应 1264.0 ms, 次数 84028, 错误 0
  - Code-Java: 响应 1380.0 ms, 次数 70936, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 16. SpringController/${url.workflow.edit}

- 用户关注点：高访问流程页面入口，虽单次不算超慢，但会持续放大总体性能成本。
- 聚合指标：请求 166261, 平均 597.802 ms, 错误 1138, 错误率 0.006845, 慢次数 1040
- 主 action：{'application_id': 1645, 'action_id': 13335, 'action_name': 'SpringController/${url.workflow.edit}'}
- action 映射：
  - 1644/13356: 请求 80171, 平均 593.0 ms, 错误 898, 慢次数 476
  - 1645/13335: 请求 86090, 平均 602.0 ms, 错误 240, 慢次数 564
- 代表 trace：{'trace_id_numeric': '1715646256', 'duration_ms': 155.141}, status 200, uri /grcv5/bpm/edit.htm, duration 155.141 ms
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 74.925 ms, count 0
  - POOL/None: exclusive 3.720999999999994 ms, count 111
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 467.0 ms, 次数 220464, 错误 0
  - Code-Java: 响应 543.0 ms, 次数 176292, 错误 0
  - Code-Java: 响应 1052.0 ms, 次数 67500, 错误 0
  - Code-Java: 响应 541.0 ms, 次数 116352, 错误 0
  - Code-Java: 响应 459.0 ms, 次数 126360, 错误 0
- 当前根因判断：当前更像流程状态判断、权限校验或页面装配逻辑问题，并夹杂一定下游开销。

## 17. SpringController/${url.workflow.view}

- 用户关注点：高访问流程页面入口，虽单次不算超慢，但会持续放大总体性能成本。
- 聚合指标：请求 58581, 平均 662.537 ms, 错误 460, 错误率 0.007852, 慢次数 299
- 主 action：{'application_id': 1645, 'action_id': 13608, 'action_name': 'SpringController/${url.workflow.view}'}
- action 映射：
  - 1644/13406: 请求 28232, 平均 632.0 ms, 错误 341, 慢次数 133
  - 1645/13608: 请求 30349, 平均 691.0 ms, 错误 119, 慢次数 166
- 代表 trace：{'trace_id_numeric': '1715928102', 'duration_ms': 116.515}, status 200, uri /grcv5/bpm/view.htm, duration 116.515 ms
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 63.711 ms, count 0
  - DATABASE/None: exclusive 36.528999999999996 ms, count 76
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 3174.0 ms, 次数 22932, 错误 0
  - Code-Java: 响应 474.0 ms, 次数 80712, 错误 0
  - Code-Java: 响应 1186.0 ms, 次数 22968, 错误 0
  - Code-Java: 响应 613.0 ms, 次数 41364, 错误 0
  - Code-Java: 响应 513.0 ms, 次数 48240, 错误 0
- 当前根因判断：当前更像流程状态判断、权限校验或页面装配逻辑问题，并夹杂一定下游开销。

## 18. SpringController/${url.attachment}/${url.attachment.updateAttachValid} (POST)

- 用户关注点：附件公共链路偏慢，需放回上传/预览/校验/下载/存储访问整链路里看。
- 聚合指标：请求 96105, 平均 1388.535 ms, 错误 3, 错误率 3.1e-05, 慢次数 18720
- 主 action：{'application_id': 1645, 'action_id': 13331, 'action_name': 'SpringController/${url.attachment}/${url.attachment.updateAttachValid} (POST)'}
- action 映射：
  - 1644/13233: 请求 44965, 平均 1382.0 ms, 错误 1, 慢次数 8756
  - 1645/13331: 请求 51140, 平均 1394.0 ms, 错误 2, 慢次数 9964
- 代表 trace：{'trace_id_numeric': '1715535163', 'duration_ms': 3019.988}, status 200, uri /grcv5/user/component/AttachmentController/updateAttachValid, duration 3019.988 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 506.21 ms, count 0
  - POOL/None: exclusive 0.08 ms, count 10
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 1418.0 ms, 次数 111302, 错误 0
  - Code-Java: 响应 1549.0 ms, 次数 87841, 错误 0
  - Code-Java: 响应 1311.0 ms, 次数 59247, 错误 0
  - Code-Java: 响应 1411.0 ms, 次数 54723, 错误 0
  - Code-Java: 响应 1211.0 ms, 次数 63278, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 19. SpringController/${url.attachment}/${url.attachment.frmIndiDocs}

- 用户关注点：附件公共链路偏慢，需放回上传/预览/校验/下载/存储访问整链路里看。
- 聚合指标：请求 56094, 平均 4160.563 ms, 错误 12, 错误率 0.000214, 慢次数 22305
- 主 action：{'application_id': 1645, 'action_id': 13436, 'action_name': 'SpringController/${url.attachment}/${url.attachment.frmIndiDocs}'}
- action 映射：
  - 1644/13220: 请求 27616, 平均 4062.0 ms, 错误 8, 慢次数 10922
  - 1645/13436: 请求 28478, 平均 4257.0 ms, 错误 4, 慢次数 11383
- 代表 trace：{'trace_id_numeric': '1716328263', 'duration_ms': 2873.183}, status 200, uri /grcv5/user/component/AttachmentController/frmIndiDocs, duration 2873.183 ms
- trace 可疑点：
  - CODE/cn.keking.web.controller.OnlinePreviewController.onlinePreview: exclusive 2643.182 ms, count 0
  - POOL/None: exclusive 7.836 ms, count 30
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 7636.0 ms, 次数 40397, 错误 0
  - Code-Java: 响应 3598.0 ms, 次数 67301, 错误 0
  - Code-Java: 响应 3555.0 ms, 次数 65121, 错误 0
  - Code-Java: 响应 2999.0 ms, 次数 68464, 错误 0
  - Code-Java: 响应 2987.0 ms, 次数 64981, 错误 0
- 当前根因判断：当前更像外部依赖或预览服务链路放大。

## 20. SpringController/${url.attachment}/${url.attachment.download}

- 用户关注点：附件公共链路偏慢，需放回上传/预览/校验/下载/存储访问整链路里看。
- 聚合指标：请求 91088, 平均 1511.187 ms, 错误 0, 错误率 0.0, 慢次数 3331
- 主 action：{'application_id': 1645, 'action_id': 13348, 'action_name': 'SpringController/${url.attachment}/${url.attachment.download}'}
- action 映射：
  - 1644/13266: 请求 43819, 平均 1611.0 ms, 错误 0, 慢次数 1614
  - 1645/13348: 请求 47269, 平均 1418.0 ms, 错误 0, 慢次数 1717
- 代表 trace：{'trace_id_numeric': '1715862453', 'duration_ms': 133.488}, status 200, uri /grcv5/user/component/AttachmentController/download.html, duration 133.488 ms
- trace 可疑点：
  - CODE/com.hd.rcugrc.platform.page.widget.form.attachment.mvc.AttachmentController.download: exclusive 93.57 ms, count 0
  - POOL/None: exclusive 0.459 ms, count 14
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 24176.0 ms, 次数 33524, 错误 0
  - Code-Java: 响应 5609.0 ms, 次数 78068, 错误 0
  - Code-Java: 响应 6222.0 ms, 次数 43355, 错误 0
  - Code-Java: 响应 2271.0 ms, 次数 57652, 错误 0
  - NoSQL-Redis: 响应 7999.0 ms, 次数 10472, 错误 0
- 当前根因判断：当前更像附件/预览/模板处理链路放大，需要把上传、预览、存储读取拆开看。

## 21. URI/grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr

- 用户关注点：高频 DWR 写入/状态更新链路，优先结合 SQL、缓存和事务提交路径排查。
- 聚合指标：请求 184723, 平均 990.63 ms, 错误 0, 错误率 0.0, 慢次数 25073
- 主 action：{'application_id': 1645, 'action_id': 13302, 'action_name': 'URI/grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr'}
- action 映射：
  - 1644/13238: 请求 87303, 平均 957.0 ms, 错误 0, 慢次数 11236
  - 1645/13302: 请求 97420, 平均 1021.0 ms, 错误 0, 慢次数 13837
- 代表 trace：{'trace_id_numeric': '1715109626', 'duration_ms': 387.281}, status 200, uri /grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr, duration 387.281 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 369.185 ms, count 0
  - DATABASE/None: exclusive 375.27700000000004 ms, count 15
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 1472.0 ms, 次数 172815, 错误 0
  - Code-Java: 响应 1272.0 ms, 次数 125727, 错误 0
  - Code-Java: 响应 740.0 ms, 次数 186260, 错误 0
  - Code-Java: 响应 2127.0 ms, 次数 56264, 错误 0
  - Code-Java: 响应 1078.0 ms, 次数 109046, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 22. URI/grcv5/dwr/call/plaincall/dwrHdWorkflowService.save.dwr

- 用户关注点：高频 DWR 写入/状态更新链路，优先结合 SQL、缓存和事务提交路径排查。
- 聚合指标：请求 130033, 平均 794.494 ms, 错误 0, 错误率 0.0, 慢次数 8213
- 主 action：{'application_id': 1645, 'action_id': 13347, 'action_name': 'URI/grcv5/dwr/call/plaincall/dwrHdWorkflowService.save.dwr'}
- action 映射：
  - 1644/13232: 请求 62407, 平均 885.0 ms, 错误 0, 慢次数 3785
  - 1645/13347: 请求 67626, 平均 711.0 ms, 错误 0, 慢次数 4428
- 代表 trace：{'trace_id_numeric': '1715670134', 'duration_ms': 3182.945}, status 200, uri /grcv5/dwr/call/plaincall/dwrHdWorkflowService.save.dwr, duration 3182.945 ms
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 3177.499 ms, count 0
  - POOL/None: exclusive 0.47800000000000004 ms, count 15
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 2657.0 ms, 次数 58522, 错误 0
  - Code-Java: 响应 1303.0 ms, 次数 68813, 错误 0
  - Code-Java: 响应 1319.0 ms, 次数 57792, 错误 0
  - Code-Java: 响应 698.0 ms, 次数 101472, 错误 0
  - Code-Java: 响应 484.0 ms, 次数 139834, 错误 0
- 当前根因判断：当前更像流程状态判断、权限校验或页面装配逻辑问题，并夹杂一定下游开销。

## 23. SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/todo-pages/{id}

- 用户关注点：流程待办链路高错且有一定慢调用，更像状态判断、权限校验、待办装配逻辑共性问题。
- 聚合指标：请求 73260, 平均 721.03 ms, 错误 13811, 错误率 0.18852, 慢次数 894
- 主 action：{'application_id': 1645, 'action_id': 13185, 'action_name': 'SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/todo-pages/{id}'}
- action 映射：
  - 1644/13166: 请求 35967, 平均 690.0 ms, 错误 6880, 慢次数 431
  - 1645/13185: 请求 37293, 平均 751.0 ms, 错误 6931, 慢次数 463
- 代表 trace：{'trace_id_numeric': '1716363147', 'duration_ms': 8.423}, status 404, uri /grcv5/api/flow-mobile/v1/task-form-process/todo-pages/2253109, duration 8.423 ms
- trace 可疑点：
  - None/HTTP ERROR CODE: 404: exclusive 0.0 ms, count 0
  - CODE/com.hd.rcugrc.product.common.filter.CasRedirectFilter.doFilter: exclusive 2.816 ms, count 0
  - POOL/None: exclusive 0.403 ms, count 8
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 584.0 ms, 次数 35055, 错误 0
  - Code-Java: 响应 960.0 ms, 次数 21055, 错误 0
  - Code-Java: 响应 1180.0 ms, 次数 12985, 错误 0
  - Code-Java: 响应 435.0 ms, 次数 34763, 错误 0
  - Code-Java: 响应 574.0 ms, 次数 19918, 错误 0
- 当前根因判断：当前更像流程状态判断、权限校验或页面装配逻辑问题，并夹杂一定下游开销。

## 24. SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/done-pages/{instId}

- 用户关注点：流程已办链路高错且偏慢，建议与 todo-pages 一起看但这里保留单条素材。
- 聚合指标：请求 14121, 平均 1629.348 ms, 错误 1604, 错误率 0.11359, 慢次数 2837
- 主 action：{'application_id': 1645, 'action_id': 13225, 'action_name': 'SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/done-pages/{instId}'}
- action 映射：
  - 1644/13237: 请求 6891, 平均 1604.0 ms, 错误 791, 慢次数 1306
  - 1645/13225: 请求 7230, 平均 1654.0 ms, 错误 813, 慢次数 1531
- 代表 trace：{'trace_id_numeric': '1716193091', 'duration_ms': 8586.789}, status 200, uri /grcv5/api/flow-mobile/v1/task-form-process/done-pages/409889, duration 8586.789 ms
- trace 可疑点：
  - None/org.apache.catalina.connector.ClientAbortException: exclusive 0.0 ms, count 0
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 6425.469 ms, count 0
  - DATABASE/None: exclusive 7607.771 ms, count 2629
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 719.0 ms, 次数 11283, 错误 0
  - Code-Java: 响应 705.0 ms, 次数 9863, 错误 0
  - Code-Java: 响应 685.0 ms, 次数 7774, 错误 0
  - Code-Java: 响应 770.0 ms, 次数 6757, 错误 0
  - Code-Java: 响应 685.0 ms, 次数 7347, 错误 0
- 当前根因判断：当前更像流程状态判断、权限校验或页面装配逻辑问题，并夹杂一定下游开销。

## 25. SpringController/${url.rest.prefix.flowmobileapi.v1}/process-drive/task/dispatch (POST)

- 用户关注点：流程流转链路出现错误与慢调用并存，优先核对状态判断、权限和路由参数。
- 聚合指标：请求 38940, 平均 733.367 ms, 错误 340, 错误率 0.008731, 慢次数 554
- 主 action：{'application_id': 1645, 'action_id': 13353, 'action_name': 'SpringController/${url.rest.prefix.flowmobileapi.v1}/process-drive/task/dispatch (POST)'}
- action 映射：
  - 1644/13203: 请求 19130, 平均 724.0 ms, 错误 140, 慢次数 282
  - 1645/13353: 请求 19810, 平均 743.0 ms, 错误 200, 慢次数 272
- 代表 trace：{'trace_id_numeric': '1716362216', 'duration_ms': 445.047}, status 200, uri /grcv5/api/flow-mobile/v1/process-drive/task/dispatch, duration 445.047 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 109.334 ms, count 0
  - DATABASE/None: exclusive 337.2129999999998 ms, count 145
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 3621.0 ms, 次数 10045, 错误 0
  - NoSQL-Redis: 响应 1080.0 ms, 次数 24290, 错误 0
  - Pool-Redis: 响应 887.0 ms, 次数 24290, 错误 0
  - Code-Java: 响应 2798.0 ms, 次数 5551, 错误 0
  - NoSQL-Redis: 响应 875.0 ms, 次数 12861, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 26. SpringController/${url.workflow.create}

- 用户关注点：流程创建入口有一定错误和慢调用，优先核对页面装配、权限与初始化查询。
- 聚合指标：请求 16427, 平均 333.083 ms, 错误 145, 错误率 0.008827, 慢次数 493
- 主 action：{'application_id': 1645, 'action_id': 13476, 'action_name': 'SpringController/${url.workflow.create}'}
- action 映射：
  - 1644/13503: 请求 7995, 平均 383.0 ms, 错误 118, 慢次数 234
  - 1645/13476: 请求 8432, 平均 286.0 ms, 错误 27, 慢次数 259
- 代表 trace：{'trace_id_numeric': '1715177992', 'duration_ms': 4076.839}, status 200, uri /grcv5/bpm/create.htm, duration 4076.839 ms
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 3868.149 ms, count 0
  - POOL/None: exclusive 6.049999999999903 ms, count 1223
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 186.0 ms, 次数 23730, 错误 0
  - Code-Java: 响应 379.0 ms, 次数 10921, 错误 0
  - Code-Java: 响应 231.0 ms, 次数 15716, 错误 0
  - Code-Java: 响应 345.0 ms, 次数 9765, 错误 0
  - Code-Java: 响应 226.0 ms, 次数 14618, 错误 0
- 当前根因判断：当前更像流程状态判断、权限校验或页面装配逻辑问题，并夹杂一定下游开销。

## 27. SpringController/serverapi/v1/flow-mobile/task-form-process/download-attachments-kfv/{code}

- 用户关注点：附件下载错误多，优先核对文件服务、鉴权、对象存储访问和路径拼装。
- 聚合指标：请求 16060, 平均 126.772 ms, 错误 1282, 错误率 0.079826, 慢次数 54
- 主 action：{'application_id': 1645, 'action_id': 13228, 'action_name': 'SpringController/serverapi/v1/flow-mobile/task-form-process/download-attachments-kfv/{code}'}
- action 映射：
  - 1644/13167: 请求 7551, 平均 128.0 ms, 错误 583, 慢次数 20
  - 1645/13228: 请求 8509, 平均 125.0 ms, 错误 699, 慢次数 34
- 代表 trace：{'trace_id_numeric': '1713489300', 'duration_ms': 471.858}, status 200, uri /grcv5/serverapi/v1/flow-mobile/task-form-process/download-attachments-kfv/1669687, duration 471.858 ms
- trace 可疑点：
  - CODE/com.hd.rcugrc.bpm.facade.mobile.mvc.AttachmentPreConversionController.downLoadAttachementKfv: exclusive 466.37 ms, count 0
  - POOL/None: exclusive 0.297 ms, count 10
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 1206.0 ms, 次数 3146, 错误 0
  - Code-Java: 响应 483.0 ms, 次数 5236, 错误 0
  - Code-Java: 响应 305.0 ms, 次数 4840, 错误 0
  - Code-Java: 响应 264.0 ms, 次数 4026, 错误 0
  - Pool-Redis: 响应 172.0 ms, 次数 2002, 错误 0
- 当前根因判断：当前更像附件/预览/模板处理链路放大，需要把上传、预览、存储读取拆开看。

## 28. URI/grcv5/rest/mobile/thirdpartylogin.json

- 用户关注点：登录/对接链路错误偏多，优先看第三方返回码、超时、重试和签名鉴权校验。
- 聚合指标：请求 50705, 平均 121.186 ms, 错误 2716, 错误率 0.053565, 慢次数 197
- 主 action：{'application_id': 1645, 'action_id': 13209, 'action_name': 'URI/grcv5/rest/mobile/thirdpartylogin.json'}
- action 映射：
  - 1644/13184: 请求 23936, 平均 120.0 ms, 错误 1300, 慢次数 93
  - 1645/13209: 请求 26769, 平均 122.0 ms, 错误 1416, 慢次数 104
- 代表 trace：{'trace_id_numeric': '1716281728', 'duration_ms': 369.456}, status 200, uri /grcv5/rest/mobile/thirdpartylogin.json, duration 369.456 ms
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 321.098 ms, count 0
  - POOL/None: exclusive 0.44 ms, count 8
- 依赖拆解来源：dependency_breakdown_pack
- TOP 组件：
  - Code-Java: 响应 660.0 ms, 次数 9652, 错误 0
  - NoSQL-Redis: 响应 391.0 ms, 次数 4185, 错误 0
  - Pool-Redis: 响应 391.0 ms, 次数 4185, 错误 0
  - Pool-Database: 响应 2640.0 ms, 次数 602, 错误 0
  - External-Https: 响应 1347.0 ms, 次数 1180, 错误 0
- 当前根因判断：当前证据更偏向数据库主导，代表 trace 首个可疑点已落到数据库节点。
- 证据缺口：
  - 仍需补 SQL 文本、执行计划或连接池等待明细。

## 29. SpringController/serverapi/v1/thirdParty/getOppDocking

- 用户关注点：第三方对接链路高访问且有错误，优先核对外部依赖返回、鉴权、参数和状态判断。
- 聚合指标：请求 88184, 平均 200.836 ms, 错误 443, 错误率 0.005024, 慢次数 5
- 主 action：{'application_id': 1644, 'action_id': 13846, 'action_name': 'SpringController/serverapi/v1/thirdParty/getOppDocking'}
- action 映射：
  - 1644/13846: 请求 66130, 平均 195.0 ms, 错误 102, 慢次数 4
  - 1645/16217: 请求 22054, 平均 219.0 ms, 错误 341, 慢次数 1
- 代表 trace：{'trace_id_numeric': '1712558999', 'duration_ms': 235.407}, status 200, uri /grcv5/serverapi/v1/thirdParty/getOppDocking, duration 235.407 ms
- trace 可疑点：
  - EXTERNAL/http://open.api.tianyancha.com:80/services/open/ic/baseinfo/normal: exclusive 185.918 ms, count 0
  - POOL/None: exclusive 0.05700000000000001 ms, count 11
- 依赖拆解来源：action_overview_fallback
- TOP 组件：
  - External-default: 响应 132.63965 ms, 次数 73429, 错误 0
  - Database-default: 响应 0.35365692 ms, 次数 271540, 错误 0
  - NoSQL-Redis: 响应 0.2963507 ms, 次数 330939, 错误 0
- 当前根因判断：当前更像外部依赖或预览服务链路放大。
- 证据缺口：
  - 依赖拆解先用 action overview 的组件摘要兜底，尚未补到独立 dependency breakdown pack。

## 30. URI/grcv5/api/flow-mobile/v1/task-form-process/done-pages/undefined

- 用户关注点：路径中直接出现 undefined，优先检查前后端参数传递、路由拼装和空值保护。
- 聚合指标：请求 3050, 平均 4.814 ms, 错误 3050, 错误率 1.0, 慢次数 0
- 主 action：{'application_id': 1645, 'action_id': 13439, 'action_name': 'URI/grcv5/api/flow-mobile/v1/task-form-process/done-pages/undefined'}
- action 映射：
  - 1644/13438: 请求 1460, 平均 5.0 ms, 错误 1460, 慢次数 0
  - 1645/13439: 请求 1590, 平均 5.0 ms, 错误 1590, 慢次数 0
- 代表 trace：当前缓存未对齐到该接口样本
- 依赖拆解来源：action_overview_fallback
- TOP 组件：
  - NoSQL-Redis: 响应 0.26624134 ms, 次数 11129, 错误 0
- 当前根因判断：当前证据更偏向前端/调用方参数拼装问题：接口路径直接带 `undefined`，且请求极快失败。
- 证据缺口：
  - 当前缓存里还没有这条接口的对齐 trace_fact_sheet。
  - 依赖拆解先用 action overview 的组件摘要兜底，尚未补到独立 dependency breakdown pack。

## 31. URI/grcv5/api/flow-mobile/v1/user-tasks/undefined

- 用户关注点：路径中直接出现 undefined，优先检查前后端参数传递、路由拼装和空值保护。
- 聚合指标：请求 104, 平均 6.865 ms, 错误 104, 错误率 1.0, 慢次数 0
- 主 action：{'application_id': 1645, 'action_id': 13837, 'action_name': 'URI/grcv5/api/flow-mobile/v1/user-tasks/undefined'}
- action 映射：
  - 1645/13837: 请求 104, 平均 7.0 ms, 错误 104, 慢次数 0
- 代表 trace：当前缓存未对齐到该接口样本
- 依赖拆解来源：action_overview_fallback
- TOP 组件：
  - NoSQL-Redis: 响应 0.26648352 ms, 次数 728, 错误 0
- 当前根因判断：当前证据更偏向前端/调用方参数拼装问题：接口路径直接带 `undefined`，且请求极快失败。
- 证据缺口：
  - 当前缓存里还没有这条接口的对齐 trace_fact_sheet。
  - 依赖拆解先用 action overview 的组件摘要兜底，尚未补到独立 dependency breakdown pack。

## 32. SpringController/${url.rest.prefix.flowmobileapi.v1}/process-drive/task-candidate-infos (POST)

- 用户关注点：量大且存在错误，优先看候选人装配、权限判断和参数边界。
- 聚合指标：请求 48746, 平均 153.62 ms, 错误 187, 错误率 0.003836, 慢次数 67
- 主 action：{'application_id': 1645, 'action_id': 13202, 'action_name': 'SpringController/${url.rest.prefix.flowmobileapi.v1}/process-drive/task-candidate-infos (POST)'}
- action 映射：
  - 1644/13350: 请求 23821, 平均 152.0 ms, 错误 58, 慢次数 31
  - 1645/13202: 请求 24925, 平均 155.0 ms, 错误 129, 慢次数 36
- 代表 trace：当前缓存未对齐到该接口样本
- 依赖拆解来源：action_overview_fallback
- TOP 组件：
  - Database-default: 响应 6.0923076 ms, 次数 433865, 错误 0
  - NoSQL-Redis: 响应 0.26464653 ms, 次数 570323, 错误 0
- 当前根因判断：当前证据更偏向数据库/数据库池主导，建议把 SQL 和连接等待一起核对。
- 证据缺口：
  - 当前缓存里还没有这条接口的对齐 trace_fact_sheet。
  - 依赖拆解先用 action overview 的组件摘要兜底，尚未补到独立 dependency breakdown pack。
  - 仍需补 SQL 文本、执行计划或连接池等待明细。
