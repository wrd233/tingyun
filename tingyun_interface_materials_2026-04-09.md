# Tingyun 接口逐条素材包

- 生成时间：2026-04-09T11:58:25.137245+08:00
- 数据来源：机器 B 通过 `tingyun_adapter_client` 调机器 A adapter，`source_mode=live`
- 统计窗口：bizSystemId=1065，endTime=2026-04-01 00:00，periodMinutes=146880
- 接口数：32

## 1. URI/grcv5/dwr/call/plaincall/dwrLawCheckService.lawyerEorkTimeTop10Data.dwr

- 用户关注点：单次耗时极端，优先核对对应 SQL、连接池等待和数据库独占耗时。
- 聚合指标：请求 5, 平均 1528404.4 ms, 错误 0, 错误率 0.0, 慢次数 5
- 主 action：app 1645/action 31342 (URI/grcv5/dwr/call/plaincall/dwrLawCheckService.lawyerEorkTimeTop10Data.dwr)
- action 映射：
  - 1644/31762: 请求 2, 平均 1541760.0 ms, 错误 0, 慢次数 2
  - 1645/31342: 请求 3, 平均 1519501.0 ms, 错误 0, 慢次数 3
- 代表 trace：1488639791，duration 1532067.823 ms，status 200，uri /grcv5/dwr/call/plaincall/dwrLawCheckService.lawyerEorkTimeTop10Data.dwr
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 1532061.893 ms, count 0
  - POOL/None: exclusive 0.258 ms, count 6
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 1519499.0 ms, 总耗时 127637886.0, 次数 84, 错误 None
  - NoSQL-Redis: 响应 707691.0 ms, 总耗时 10615364.0, 次数 15, 错误 None
  - Pool-Redis: 响应 607800.0 ms, 总耗时 9117004.0, 次数 15, 错误 None
  - Database-MySQL: 响应 1519501.0 ms, 总耗时 4558502.0, 次数 3, 错误 None
  - Pool-Database: 响应 1519501.0 ms, 总耗时 4558502.0, 次数 3, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。 同时存在数据库连接池/获取连接开销，建议把 SQL 执行时间和连接等待一起核对。
- 证据缺口：
  - 未单独拉取 connection_pool_pack，无法定量确认等待连接占比。
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 2. SpringController/ProductIndexController.afterPropertiesSet

- 用户关注点：接口名与真实业务入口可能不一致，需保留别名与真实 URI 一起看。
- 聚合指标：请求 47, 平均 363957.468 ms, 错误 0, 错误率 0.0, 慢次数 47
- 主 action：app 1645/action 13161 (SpringController/ProductIndexController.afterPropertiesSet)
- action 映射：
  - 1644/13155: 请求 22, 平均 9051.0 ms, 错误 0, 慢次数 22
  - 1645/13161: 请求 25, 平均 676276.0 ms, 错误 0, 慢次数 25
- 代表 trace：1699647009，duration 13691.55 ms，status 200，uri /grcv5/api/flow-mobile/v1/task-form-process/todo-pages/2248480
- trace 可疑点：
  - CODE/javax.servlet.ServletRequestListener.requestInitialized: exclusive 7711.285 ms, count 0
  - POOL/None: exclusive 10.579999999999934 ms, count 672
- 依赖拆解 TOP 组件：
  - NoSQL-Redis: 响应 226821.0 ms, 总耗时 116812661.0, 次数 515, 错误 None
  - Code-Java: 响应 552695.0 ms, 总耗时 104459444.0, 次数 189, 错误 None
  - Pool-Redis: 响应 162015.0 ms, 总耗时 83437615.0, 次数 515, 错误 None
  - Pool-Database: 响应 538307.0 ms, 总耗时 33375046.0, 次数 62, 错误 None
  - Database-MySQL: 响应 19404.0 ms, 总耗时 33375046.0, 次数 1720, 错误 None
- 当前根因判断：当前更像应用代码路径本身放大：代表 trace 的首个热点落在代码段而非单一外部组件，需要结合真实入口 URI 和初始化/装配逻辑继续下钻。
- 证据缺口：
  - 未补方法级代码栈和对应业务代码位置，暂无法直接定位到具体类/方法。

## 3. SpringController/TemplateUploadController.setTemplateService

- 用户关注点：低频但极慢，优先确认文件解析、模板校验、存储读写或外部预览放大。
- 聚合指标：请求 45, 平均 84458.933 ms, 错误 2, 错误率 0.044444, 慢次数 24
- 主 action：app 1645/action 13336 (SpringController/TemplateUploadController.setTemplateService)
- action 映射：
  - 1644/13239: 请求 20, 平均 2883.0 ms, 错误 2, 慢次数 9
  - 1645/13336: 请求 25, 平均 149720.0 ms, 错误 0, 慢次数 15
- 代表 trace：1701589579，duration 11525.581 ms，status 200，uri /grcv5/bpm/create.htm
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 7852.568 ms, count 0
  - POOL/None: exclusive 14.760999999999907 ms, count 1360
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 295304.0 ms, 总耗时 37798874.0, 次数 128, 错误 None
  - Code-Java: 响应 98514.0 ms, 总耗时 25121093.0, 次数 255, 错误 None
  - NoSQL-Redis: 响应 32233.0 ms, 总耗时 15858781.0, 次数 492, 错误 None
  - NoSQL-Redis: 响应 7878.0 ms, 总耗时 15243893.0, 次数 1935, 错误 None
  - Pool-Redis: 响应 5254.0 ms, 总耗时 10165863.0, 次数 1935, 错误 None
- 当前根因判断：当前更像附件公共能力链路偏慢/偏错：素材显示问题不只在单点 controller，而是在上传、模板处理、附件读取或存储访问之间放大。
- 证据缺口：
  - 未补文件服务/对象存储/外部预览依赖 pack，暂无法拆出各子链路占比。

## 4. SpringController/serverapi/restapi/other/v1

- 用户关注点：低频但均值高，适合结合 trace 先看具体调用栈。
- 聚合指标：请求 49, 平均 22302.02 ms, 错误 1, 错误率 0.020408, 慢次数 2
- 主 action：app 1645/action 13158 (SpringController/serverapi/restapi/other/v1)
- action 映射：
  - 1644/13163: 请求 23, 平均 751.0 ms, 错误 0, 慢次数 1
  - 1645/13158: 请求 26, 平均 41366.0 ms, 错误 1, 慢次数 1
- 代表 trace：1709041248，duration 970.645 ms，status 500，uri /grcv5/rest/mobile/thirdpartylogin.json
- trace 可疑点：
  - None/org.springframework.web.util.NestedServletException: exclusive 0.0 ms, count 0
  - CODE/com.hd.rcugrc.platform.rest.mobile.filter.MyMobilePreLoginFilter.doFilter: exclusive 335.167 ms, count 0
  - POOL/None: exclusive 0.673 ms, count 9
- 依赖拆解 TOP 组件：
  - NoSQL-Redis: 响应 141642.0 ms, 总耗时 4249254.0, 次数 30, 错误 None
  - Code-Java: 响应 34155.0 ms, 总耗时 4235182.0, 次数 124, 错误 None
  - Pool-Redis: 响应 106183.0 ms, 总耗时 3185488.0, 次数 30, 错误 None
  - Database-MySQL: 响应 354159.0 ms, 总耗时 1062476.0, 次数 3, 错误 None
  - Pool-Database: 响应 265619.0 ms, 总耗时 1062476.0, 次数 4, 错误 None
- 当前根因判断：当前素材已能确认该接口属于显著慢调用，但代表 trace 没有把单一外部依赖完全坐实，优先继续补失败样本、SQL 和方法级调用树。
- 证据缺口：
  - 当前只补到 action/trace/依赖拆解三层，缺少更细的 SQL、连接池或错误样本明细。

## 5. URI/grcv5/dwr/call/plaincall/dwrAssessEvaService.copyAssessEva.dwr

- 用户关注点：调用量不高但耗时已进入重点排查范围，先补 trace 和依赖分解。
- 聚合指标：请求 4, 平均 55913.75 ms, 错误 0, 错误率 0.0, 慢次数 4
- 主 action：app 1644/action 18590 (URI/grcv5/dwr/call/plaincall/dwrAssessEvaService.copyAssessEva.dwr)
- action 映射：
  - 1644/18590: 请求 4, 平均 55914.0 ms, 错误 0, 慢次数 4
- 代表 trace：未拿到对齐样本 (no_matching_trace_candidate)
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 70870.0 ms, 总耗时 3968717.0, 次数 56, 错误 None
  - Code-Java: 响应 47190.0 ms, 总耗时 1321315.0, 次数 28, 错误 None
  - Code-Java: 响应 34717.0 ms, 总耗时 972065.0, 次数 28, 错误 None
  - NoSQL-Redis: 响应 53154.0 ms, 总耗时 425232.0, 次数 8, 错误 None
  - Pool-Redis: 响应 35436.0 ms, 总耗时 283488.0, 次数 8, 错误 None
- 当前根因判断：当前更像应用代码路径本身放大：代表 trace 的首个热点落在代码段而非单一外部组件，需要结合真实入口 URI 和初始化/装配逻辑继续下钻。
- 证据缺口：
  - 当前未拿到和该接口 action 对齐的代表性 trace。
  - 未补方法级代码栈和对应业务代码位置，暂无法直接定位到具体类/方法。

## 6. URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getInitData.dwr

- 用户关注点：LegalDemand 域初始化读取慢，优先看初始化查询、缓存命中和列表装配。
- 聚合指标：请求 23, 平均 24237.087 ms, 错误 0, 错误率 0.0, 慢次数 14
- 主 action：app 1645/action 14562 (URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getInitData.dwr)
- action 映射：
  - 1644/14118: 请求 9, 平均 33504.0 ms, 错误 0, 慢次数 7
  - 1645/14562: 请求 14, 平均 18280.0 ms, 错误 0, 慢次数 7
- 代表 trace：1488359386，duration 33654.052 ms，status 200，uri /grcv5/dwr/call/plaincall/dwrLegalDemandService.getInitData.dwr
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 22251.629 ms, count 0
  - POOL/None: exclusive 0.081 ms, count 8
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 17481.0 ms, 总耗时 1957907.0, 次数 112, 错误 None
  - Code-Java: 响应 13497.0 ms, 总耗时 1889586.0, 次数 140, 错误 None
  - Code-Java: 响应 14364.0 ms, 总耗时 1206547.0, 次数 84, 错误 None
  - Code-Java: 响应 38831.0 ms, 总耗时 1087273.0, 次数 28, 错误 None
  - Code-Java: 响应 36551.0 ms, 总耗时 1023423.0, 次数 28, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。 同时存在数据库连接池/获取连接开销，建议把 SQL 执行时间和连接等待一起核对。
- 证据缺口：
  - 未单独拉取 connection_pool_pack，无法定量确认等待连接占比。
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 7. URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getCountByPast5.dwr

- 用户关注点：LegalDemand 域初始化读取慢，优先看初始化查询、缓存命中和列表装配。
- 聚合指标：请求 21, 平均 25688.524 ms, 错误 0, 错误率 0.0, 慢次数 21
- 主 action：app 1645/action 14565 (URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getCountByPast5.dwr)
- action 映射：
  - 1644/14120: 请求 9, 平均 34459.0 ms, 错误 0, 慢次数 9
  - 1645/14565: 请求 12, 平均 19111.0 ms, 错误 0, 慢次数 12
- 代表 trace：1488360227，duration 36598.935 ms，status 200，uri /grcv5/dwr/call/plaincall/dwrLegalDemandService.getCountByPast5.dwr
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 22250.912 ms, count 0
  - POOL/None: exclusive 0.19000000000000003 ms, count 20
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 17406.0 ms, 总耗时 1462091.0, 次数 84, 错误 None
  - Code-Java: 响应 12481.0 ms, 总耗时 1397820.0, 次数 112, 错误 None
  - Code-Java: 响应 15271.0 ms, 总耗时 1282726.0, 次数 84, 错误 None
  - Code-Java: 响应 41726.0 ms, 总耗时 1168321.0, 次数 28, 错误 None
  - Code-Java: 响应 39628.0 ms, 总耗时 1109580.0, 次数 28, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。 同时存在数据库连接池/获取连接开销，建议把 SQL 执行时间和连接等待一起核对。
- 证据缺口：
  - 未单独拉取 connection_pool_pack，无法定量确认等待连接占比。
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 8. URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getServerType.dwr

- 用户关注点：LegalDemand 域初始化读取慢，优先看初始化查询、缓存命中和列表装配。
- 聚合指标：请求 22, 平均 24038.364 ms, 错误 0, 错误率 0.0, 慢次数 13
- 主 action：app 1645/action 14563 (URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getServerType.dwr)
- action 映射：
  - 1644/14119: 请求 9, 平均 33339.0 ms, 错误 0, 慢次数 7
  - 1645/14563: 请求 13, 平均 17600.0 ms, 错误 0, 慢次数 6
- 代表 trace：1488359455，duration 33836.291 ms，status 200，uri /grcv5/dwr/call/plaincall/dwrLegalDemandService.getServerType.dwr
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 20768.479 ms, count 0
  - POOL/None: exclusive 0.3660000000000001 ms, count 12
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 17694.0 ms, 总耗时 1981775.0, 次数 112, 错误 None
  - Code-Java: 响应 14634.0 ms, 总耗时 1229253.0, 次数 84, 错误 None
  - Code-Java: 响应 39078.0 ms, 总耗时 1094174.0, 次数 28, 错误 None
  - Code-Java: 响应 9572.0 ms, 总耗时 1072057.0, 次数 112, 错误 None
  - Code-Java: 响应 36724.0 ms, 总耗时 1028265.0, 次数 28, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。 同时存在数据库连接池/获取连接开销，建议把 SQL 执行时间和连接等待一起核对。
- 证据缺口：
  - 未单独拉取 connection_pool_pack，无法定量确认等待连接占比。
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 9. URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getPlace.dwr

- 用户关注点：LegalDemand 域初始化读取慢，优先看初始化查询、缓存命中和列表装配。
- 聚合指标：请求 22, 平均 23166.045 ms, 错误 0, 错误率 0.0, 慢次数 13
- 主 action：app 1645/action 14559 (URI/grcv5/dwr/call/plaincall/dwrLegalDemandService.getPlace.dwr)
- action 映射：
  - 1644/14117: 请求 8, 平均 31743.0 ms, 错误 0, 慢次数 6
  - 1645/14559: 请求 14, 平均 18265.0 ms, 错误 0, 慢次数 7
- 代表 trace：1488359381，duration 33491.837 ms，status 200，uri /grcv5/dwr/call/plaincall/dwrLegalDemandService.getPlace.dwr
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 27492.634 ms, count 0
  - POOL/None: exclusive 0.068 ms, count 9
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 17475.0 ms, 总耗时 1957155.0, 次数 112, 错误 None
  - Code-Java: 响应 13514.0 ms, 总耗时 1891948.0, 次数 140, 错误 None
  - Code-Java: 响应 14373.0 ms, 总耗时 1207292.0, 次数 84, 错误 None
  - Code-Java: 响应 38684.0 ms, 总耗时 1083141.0, 次数 28, 错误 None
  - Code-Java: 响应 36406.0 ms, 总耗时 1019358.0, 次数 28, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。 同时存在数据库连接池/获取连接开销，建议把 SQL 执行时间和连接等待一起核对。
- 证据缺口：
  - 未单独拉取 connection_pool_pack，无法定量确认等待连接占比。
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 10. SpringController/${url.bpm.user.senopInfo}

- 用户关注点：先按 trace/依赖分解补证，再区分代码、数据库、外部依赖还是路由参数问题。
- 聚合指标：请求 65, 平均 38147.769 ms, 错误 0, 错误率 0.0, 慢次数 65
- 主 action：app 1645/action 16223 (SpringController/${url.bpm.user.senopInfo})
- action 映射：
  - 1644/16011: 请求 31, 平均 37628.0 ms, 错误 0, 慢次数 31
  - 1645/16223: 请求 34, 平均 38621.0 ms, 错误 0, 慢次数 34
- 代表 trace：1700014268，duration 53969.498 ms，status 200，uri /grcv5/user/senopInfo.htm
- trace 可疑点：
  - CODE/com.hd.rcugrc.web.servlet.mvc.UserController.getSenstiveOperationInfos: exclusive 53834.871 ms, count 0
  - NOSQL/None: exclusive 4.552999999999999 ms, count 11
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 52075.0 ms, 总耗时 3436944.0, 次数 66, 错误 None
  - Code-Java: 响应 33851.0 ms, 总耗时 3351257.0, 次数 99, 错误 None
  - Code-Java: 响应 31293.0 ms, 总耗时 3097984.0, 次数 99, 错误 None
  - Code-Java: 响应 26803.0 ms, 总耗时 2573051.0, 次数 96, 错误 None
  - Code-Java: 响应 56432.0 ms, 总耗时 1862269.0, 次数 33, 错误 None
- 当前根因判断：当前更像应用代码路径本身放大：代表 trace 的首个热点落在代码段而非单一外部组件，需要结合真实入口 URI 和初始化/装配逻辑继续下钻。
- 证据缺口：
  - 未补方法级代码栈和对应业务代码位置，暂无法直接定位到具体类/方法。

## 11. URI/grcv5/user/component/AttachmentController/upload

- 用户关注点：上传错误样本接口，可作为上传异常簇的 trace 入口重点追查。
- 聚合指标：请求 11, 平均 81268.545 ms, 错误 11, 错误率 1.0, 慢次数 9
- 主 action：app 1644/action 18885 (URI/grcv5/user/component/AttachmentController/upload)
- action 映射：
  - 1644/18885: 请求 6, 平均 63626.0 ms, 错误 6, 慢次数 5
  - 1645/19684: 请求 5, 平均 102440.0 ms, 错误 5, 慢次数 4
- 代表 trace：未拿到对齐样本 (no_matching_trace_candidate)
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 58370.0 ms, 总耗时 3268710.0, 次数 56, 错误 None
  - Code-Java: 响应 29355.0 ms, 总耗时 1643907.0, 次数 56, 错误 None
  - NoSQL-Redis: 响应 47146.0 ms, 总耗时 754332.0, 次数 16, 错误 None
  - Pool-Redis: 响应 31431.0 ms, 总耗时 502888.0, 次数 16, 错误 None
  - NoSQL-Redis: 响应 23711.0 ms, 总耗时 379383.0, 次数 16, 错误 None
- 当前根因判断：当前更像附件公共能力链路偏慢/偏错：素材显示问题不只在单点 controller，而是在上传、模板处理、附件读取或存储访问之间放大。 错误率已经足够高，应优先抓失败样本确认是文件校验、存储访问还是预览服务报错。
- 证据缺口：
  - 当前未拿到和该接口 action 对齐的代表性 trace。
  - 未补文件服务/对象存储/外部预览依赖 pack，暂无法拆出各子链路占比。

## 12. URI/grcv5/user/component/AttachmentController/frmIndiDocs

- 用户关注点：先按 trace/依赖分解补证，再区分代码、数据库、外部依赖还是路由参数问题。
- 聚合指标：请求 2, 平均 122517.0 ms, 错误 2, 错误率 1.0, 慢次数 2
- 主 action：app 1644/action 19286 (URI/grcv5/user/component/AttachmentController/frmIndiDocs)
- action 映射：
  - 1644/19286: 请求 2, 平均 122517.0 ms, 错误 2, 慢次数 2
- 代表 trace：未拿到对齐样本 (no_matching_trace_candidate)
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 56881.0 ms, 总耗时 3185318.0, 次数 56, 错误 None
  - NoSQL-Redis: 响应 45944.0 ms, 总耗时 735102.0, 次数 16, 错误 None
  - Pool-Redis: 响应 30629.0 ms, 总耗时 490068.0, 次数 16, 错误 None
- 当前根因判断：当前更像附件公共能力链路偏慢/偏错：素材显示问题不只在单点 controller，而是在上传、模板处理、附件读取或存储访问之间放大。 错误率已经足够高，应优先抓失败样本确认是文件校验、存储访问还是预览服务报错。
- 证据缺口：
  - 当前未拿到和该接口 action 对齐的代表性 trace。
  - 未补文件服务/对象存储/外部预览依赖 pack，暂无法拆出各子链路占比。

## 13. SpringController/onlinePreview

- 用户关注点：高访问高慢次数，优先排查预览服务、文件转换、缓存和存储读取。
- 聚合指标：请求 36311, 平均 3712.716 ms, 错误 0, 错误率 0.0, 慢次数 7731
- 主 action：app 1646/action 13229 (SpringController/onlinePreview)
- action 映射：
  - 1646/13229: 请求 36311, 平均 3713.0 ms, 错误 0, 慢次数 7731
- 代表 trace：1716307688，duration 1806.121 ms，status 200，uri /preview/onlinePreview
- trace 可疑点：
  - CODE/cn.keking.web.controller.OnlinePreviewController.onlinePreview: exclusive 1714.726 ms, count 0
  - POOL/None: exclusive 0.41800000000000004 ms, count 11
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 7480.0 ms, 总耗时 168175483.0, 次数 22482, 错误 None
  - Code-Java: 响应 13908.0 ms, 总耗时 128620215.0, 次数 9248, 错误 None
  - Code-Java: 响应 10019.0 ms, 总耗时 109345701.0, 次数 10914, 错误 None
  - Code-Java: 响应 6916.0 ms, 总耗时 104918184.0, 次数 15170, 错误 None
  - Code-Java: 响应 7024.0 ms, 总耗时 72729397.0, 次数 10355, 错误 None
- 当前根因判断：当前更像附件/预览链路被外部预览服务或文件处理步骤放大：依赖拓扑中已出现预览服务应用或外部调用，需把上传、转换、预览、存储读取拆开看。
- 证据缺口：
  - 未补文件服务/对象存储/外部预览依赖 pack，暂无法拆出各子链路占比。

## 14. SpringController/${url.attachment}/${url.attachment.upload} (POST)

- 用户关注点：上传接口同时具备高访问、偏慢和错误，应作为上传/预览异常簇入口。
- 聚合指标：请求 45743, 平均 6068.401 ms, 错误 100, 错误率 0.002186, 慢次数 13695
- 主 action：app 1644/action 13513 (SpringController/${url.attachment}/${url.attachment.upload} (POST))
- action 映射：
  - 1644/13513: 请求 23535, 平均 5779.0 ms, 错误 38, 慢次数 6635
  - 1645/13332: 请求 22208, 平均 6375.0 ms, 错误 62, 慢次数 7060
- 代表 trace：1715120752，duration 4366.845 ms，status 200，uri /grcv5/user/component/AttachmentController/upload
- trace 可疑点：
  - CODE/cn.keking.web.controller.OnlinePreviewController.onlinePreview: exclusive 3547.909 ms, count 0
  - POOL/None: exclusive 0.9540000000000001 ms, count 22
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 10024.0 ms, 总耗时 1215420275.0, 次数 121247, 错误 None
  - Code-Java: 响应 13612.0 ms, 总耗时 394108744.0, 次数 28953, 错误 None
  - Code-Java: 响应 6618.0 ms, 总耗时 346793459.0, 次数 52402, 错误 None
  - Code-Java: 响应 2763.0 ms, 总耗时 240931850.0, 次数 87190, 错误 None
  - NoSQL-Redis: 响应 3918.0 ms, 总耗时 127902586.0, 次数 32647, 错误 None
- 当前根因判断：当前更像附件/预览链路被外部预览服务或文件处理步骤放大：依赖拓扑中已出现预览服务应用或外部调用，需把上传、转换、预览、存储读取拆开看。
- 证据缺口：
  - 未补文件服务/对象存储/外部预览依赖 pack，暂无法拆出各子链路占比。

## 15. URI/grcv5/wp/contractView/viewContract.htm

- 用户关注点：高流量页面入口，优先看页面装配、合同明细查询和关联附件/流程信息聚合。
- 聚合指标：请求 118366, 平均 1354.297 ms, 错误 1019, 错误率 0.008609, 慢次数 5145
- 主 action：app 1645/action 13314 (URI/grcv5/wp/contractView/viewContract.htm)
- action 映射：
  - 1644/13566: 请求 57088, 平均 1319.0 ms, 错误 938, 慢次数 2106
  - 1645/13314: 请求 61278, 平均 1387.0 ms, 错误 81, 慢次数 3039
- 代表 trace：1715789838，duration 1223.522 ms，status 200，uri /grcv5/wp/contractView/viewContract.htm
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 221.472 ms, count 0
  - POOL/None: exclusive 1.0440000000000005 ms, count 205
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 1684.0 ms, 总耗时 223451471.0, 次数 132664, 错误 None
  - Code-Java: 响应 1341.0 ms, 总耗时 128636298.0, 次数 95902, 错误 None
  - Code-Java: 响应 1320.0 ms, 总耗时 111194860.0, 次数 84267, 错误 None
  - Code-Java: 响应 1264.0 ms, 总耗时 106230785.0, 次数 84028, 错误 None
  - Code-Java: 响应 1380.0 ms, 总耗时 97863652.0, 次数 70936, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。 同时存在数据库连接池/获取连接开销，建议把 SQL 执行时间和连接等待一起核对。
- 证据缺口：
  - 未单独拉取 connection_pool_pack，无法定量确认等待连接占比。
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 16. SpringController/${url.workflow.edit}

- 用户关注点：高访问流程页面入口，虽单次不算超慢，但会持续放大总体性能成本。
- 聚合指标：请求 166261, 平均 597.802 ms, 错误 1138, 错误率 0.006845, 慢次数 1040
- 主 action：app 1645/action 13335 (SpringController/${url.workflow.edit})
- action 映射：
  - 1644/13356: 请求 80171, 平均 593.0 ms, 错误 898, 慢次数 476
  - 1645/13335: 请求 86090, 平均 602.0 ms, 错误 240, 慢次数 564
- 代表 trace：1715646256，duration 155.141 ms，status 200，uri /grcv5/bpm/edit.htm
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 74.925 ms, count 0
  - POOL/None: exclusive 3.720999999999994 ms, count 111
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 467.0 ms, 总耗时 102954810.0, 次数 220464, 错误 None
  - Code-Java: 响应 543.0 ms, 总耗时 95646058.0, 次数 176292, 错误 None
  - Code-Java: 响应 1052.0 ms, 总耗时 71010549.0, 次数 67500, 错误 None
  - Code-Java: 响应 541.0 ms, 总耗时 62923963.0, 次数 116352, 错误 None
  - Code-Java: 响应 459.0 ms, 总耗时 57957800.0, 次数 126360, 错误 None
- 当前根因判断：当前更像流程域高频读写/页面装配路径偏慢，数据库、缓存和事务提交开销会在高访问下被持续放大。 代表 trace 首个可疑点为 `CODE/javax.servlet.http.HttpServlet.service`。
- 证据缺口：
  - 未补错误明细与业务返回码，仍需区分权限不足、状态不合法、参数缺失和真实服务异常。

## 17. SpringController/${url.workflow.view}

- 用户关注点：高访问流程页面入口，虽单次不算超慢，但会持续放大总体性能成本。
- 聚合指标：请求 58581, 平均 662.537 ms, 错误 460, 错误率 0.007852, 慢次数 299
- 主 action：app 1645/action 13608 (SpringController/${url.workflow.view})
- action 映射：
  - 1644/13406: 请求 28232, 平均 632.0 ms, 错误 341, 慢次数 133
  - 1645/13608: 请求 30349, 平均 691.0 ms, 错误 119, 慢次数 166
- 代表 trace：1715928102，duration 116.515 ms，status 200，uri /grcv5/bpm/view.htm
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 63.711 ms, count 0
  - DATABASE/None: exclusive 36.528999999999996 ms, count 76
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 3174.0 ms, 总耗时 72790684.0, 次数 22932, 错误 None
  - Code-Java: 响应 474.0 ms, 总耗时 38241558.0, 次数 80712, 错误 None
  - Code-Java: 响应 1186.0 ms, 总耗时 27239951.0, 次数 22968, 错误 None
  - Code-Java: 响应 613.0 ms, 总耗时 25353776.0, 次数 41364, 错误 None
  - Code-Java: 响应 513.0 ms, 总耗时 24758347.0, 次数 48240, 错误 None
- 当前根因判断：当前更像流程域高频读写/页面装配路径偏慢，数据库、缓存和事务提交开销会在高访问下被持续放大。 代表 trace 首个可疑点为 `CODE/javax.servlet.http.HttpServlet.service`。
- 证据缺口：
  - 未补错误明细与业务返回码，仍需区分权限不足、状态不合法、参数缺失和真实服务异常。

## 18. SpringController/${url.attachment}/${url.attachment.updateAttachValid} (POST)

- 用户关注点：附件公共链路偏慢，需放回上传/预览/校验/下载/存储访问整链路里看。
- 聚合指标：请求 96105, 平均 1388.535 ms, 错误 3, 错误率 3.1e-05, 慢次数 18720
- 主 action：app 1645/action 13331 (SpringController/${url.attachment}/${url.attachment.updateAttachValid} (POST))
- action 映射：
  - 1644/13233: 请求 44965, 平均 1382.0 ms, 错误 1, 慢次数 8756
  - 1645/13331: 请求 51140, 平均 1394.0 ms, 错误 2, 慢次数 9964
- 代表 trace：1715535163，duration 3019.988 ms，status 200，uri /grcv5/user/component/AttachmentController/updateAttachValid
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 506.21 ms, count 0
  - POOL/None: exclusive 0.08 ms, count 10
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 1418.0 ms, 总耗时 157837816.0, 次数 111302, 错误 None
  - Code-Java: 响应 1549.0 ms, 总耗时 136062090.0, 次数 87841, 错误 None
  - Code-Java: 响应 1311.0 ms, 总耗时 77695718.0, 次数 59247, 错误 None
  - Code-Java: 响应 1411.0 ms, 总耗时 77216017.0, 次数 54723, 错误 None
  - Code-Java: 响应 1211.0 ms, 总耗时 76598157.0, 次数 63278, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。 同时存在数据库连接池/获取连接开销，建议把 SQL 执行时间和连接等待一起核对。
- 证据缺口：
  - 未单独拉取 connection_pool_pack，无法定量确认等待连接占比。
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 19. SpringController/${url.attachment}/${url.attachment.frmIndiDocs}

- 用户关注点：附件公共链路偏慢，需放回上传/预览/校验/下载/存储访问整链路里看。
- 聚合指标：请求 56094, 平均 4160.563 ms, 错误 12, 错误率 0.000214, 慢次数 22305
- 主 action：app 1645/action 13436 (SpringController/${url.attachment}/${url.attachment.frmIndiDocs})
- action 映射：
  - 1644/13220: 请求 27616, 平均 4062.0 ms, 错误 8, 慢次数 10922
  - 1645/13436: 请求 28478, 平均 4257.0 ms, 错误 4, 慢次数 11383
- 代表 trace：1716328263，duration 2873.183 ms，status 200，uri /grcv5/user/component/AttachmentController/frmIndiDocs
- trace 可疑点：
  - CODE/cn.keking.web.controller.OnlinePreviewController.onlinePreview: exclusive 2643.182 ms, count 0
  - POOL/None: exclusive 7.836 ms, count 30
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 7636.0 ms, 总耗时 308462781.0, 次数 40397, 错误 None
  - Code-Java: 响应 3598.0 ms, 总耗时 242152478.0, 次数 67301, 错误 None
  - Code-Java: 响应 3555.0 ms, 总耗时 231488391.0, 次数 65121, 错误 None
  - Code-Java: 响应 2999.0 ms, 总耗时 205322056.0, 次数 68464, 错误 None
  - Code-Java: 响应 2987.0 ms, 总耗时 194101143.0, 次数 64981, 错误 None
- 当前根因判断：当前更像附件/预览链路被外部预览服务或文件处理步骤放大：依赖拓扑中已出现预览服务应用或外部调用，需把上传、转换、预览、存储读取拆开看。
- 证据缺口：
  - 未补文件服务/对象存储/外部预览依赖 pack，暂无法拆出各子链路占比。

## 20. SpringController/${url.attachment}/${url.attachment.download}

- 用户关注点：附件公共链路偏慢，需放回上传/预览/校验/下载/存储访问整链路里看。
- 聚合指标：请求 91088, 平均 1511.187 ms, 错误 0, 错误率 0.0, 慢次数 3331
- 主 action：app 1645/action 13348 (SpringController/${url.attachment}/${url.attachment.download})
- action 映射：
  - 1644/13266: 请求 43819, 平均 1611.0 ms, 错误 0, 慢次数 1614
  - 1645/13348: 请求 47269, 平均 1418.0 ms, 错误 0, 慢次数 1717
- 代表 trace：1715862453，duration 133.488 ms，status 200，uri /grcv5/user/component/AttachmentController/download.html
- trace 可疑点：
  - CODE/com.hd.rcugrc.platform.page.widget.form.attachment.mvc.AttachmentController.download: exclusive 93.57 ms, count 0
  - POOL/None: exclusive 0.459 ms, count 14
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 24176.0 ms, 总耗时 810461252.0, 次数 33524, 错误 None
  - Code-Java: 响应 5609.0 ms, 总耗时 437882493.0, 次数 78068, 错误 None
  - Code-Java: 响应 6222.0 ms, 总耗时 269754779.0, 次数 43355, 错误 None
  - Code-Java: 响应 2271.0 ms, 总耗时 130932171.0, 次数 57652, 错误 None
  - NoSQL-Redis: 响应 7999.0 ms, 总耗时 83765805.0, 次数 10472, 错误 None
- 当前根因判断：当前更像附件公共能力链路偏慢/偏错：素材显示问题不只在单点 controller，而是在上传、模板处理、附件读取或存储访问之间放大。
- 证据缺口：
  - 未补文件服务/对象存储/外部预览依赖 pack，暂无法拆出各子链路占比。

## 21. URI/grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr

- 用户关注点：高频 DWR 写入/状态更新链路，优先结合 SQL、缓存和事务提交路径排查。
- 聚合指标：请求 184723, 平均 990.63 ms, 错误 0, 错误率 0.0, 慢次数 25073
- 主 action：app 1645/action 13302 (URI/grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr)
- action 映射：
  - 1644/13238: 请求 87303, 平均 957.0 ms, 错误 0, 慢次数 11236
  - 1645/13302: 请求 97420, 平均 1021.0 ms, 错误 0, 慢次数 13837
- 代表 trace：1715109626，duration 387.281 ms，status 200，uri /grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 369.185 ms, count 0
  - DATABASE/None: exclusive 375.27700000000004 ms, count 15
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 1472.0 ms, 总耗时 254442364.0, 次数 172815, 错误 None
  - Code-Java: 响应 1272.0 ms, 总耗时 159933446.0, 次数 125727, 错误 None
  - Code-Java: 响应 740.0 ms, 总耗时 137839150.0, 次数 186260, 错误 None
  - Code-Java: 响应 2127.0 ms, 总耗时 119677703.0, 次数 56264, 错误 None
  - Code-Java: 响应 1078.0 ms, 总耗时 117588569.0, 次数 109046, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。
- 证据缺口：
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 22. URI/grcv5/dwr/call/plaincall/dwrHdWorkflowService.save.dwr

- 用户关注点：高频 DWR 写入/状态更新链路，优先结合 SQL、缓存和事务提交路径排查。
- 聚合指标：请求 130033, 平均 794.494 ms, 错误 0, 错误率 0.0, 慢次数 8213
- 主 action：app 1645/action 13347 (URI/grcv5/dwr/call/plaincall/dwrHdWorkflowService.save.dwr)
- action 映射：
  - 1644/13232: 请求 62407, 平均 885.0 ms, 错误 0, 慢次数 3785
  - 1645/13347: 请求 67626, 平均 711.0 ms, 错误 0, 慢次数 4428
- 代表 trace：1715670134，duration 3182.945 ms，status 200，uri /grcv5/dwr/call/plaincall/dwrHdWorkflowService.save.dwr
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 3177.499 ms, count 0
  - POOL/None: exclusive 0.47800000000000004 ms, count 15
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 2657.0 ms, 总耗时 155508178.0, 次数 58522, 错误 None
  - Code-Java: 响应 1303.0 ms, 总耗时 89636816.0, 次数 68813, 错误 None
  - Code-Java: 响应 1319.0 ms, 总耗时 76212107.0, 次数 57792, 错误 None
  - Code-Java: 响应 698.0 ms, 总耗时 70858971.0, 次数 101472, 错误 None
  - Code-Java: 响应 484.0 ms, 总耗时 67687429.0, 次数 139834, 错误 None
- 当前根因判断：当前更像流程域高频读写/页面装配路径偏慢，数据库、缓存和事务提交开销会在高访问下被持续放大。 代表 trace 首个可疑点为 `CODE/javax.servlet.http.HttpServlet.service`。
- 证据缺口：
  - 未补错误明细与业务返回码，仍需区分权限不足、状态不合法、参数缺失和真实服务异常。

## 23. SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/todo-pages/{id}

- 用户关注点：流程待办链路高错且有一定慢调用，更像状态判断、权限校验、待办装配逻辑共性问题。
- 聚合指标：请求 73260, 平均 721.03 ms, 错误 13811, 错误率 0.18852, 慢次数 894
- 主 action：app 1645/action 13185 (SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/todo-pages/{id})
- action 映射：
  - 1644/13166: 请求 35967, 平均 690.0 ms, 错误 6880, 慢次数 431
  - 1645/13185: 请求 37293, 平均 751.0 ms, 错误 6931, 慢次数 463
- 代表 trace：1716363147，duration 8.423 ms，status 404，uri /grcv5/api/flow-mobile/v1/task-form-process/todo-pages/2253109
- trace 可疑点：
  - None/HTTP ERROR CODE: 404: exclusive 0.0 ms, count 0
  - CODE/com.hd.rcugrc.product.common.filter.CasRedirectFilter.doFilter: exclusive 2.816 ms, count 0
  - POOL/None: exclusive 0.403 ms, count 8
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 584.0 ms, 总耗时 20486019.0, 次数 35055, 错误 None
  - Code-Java: 响应 960.0 ms, 总耗时 20215084.0, 次数 21055, 错误 None
  - Code-Java: 响应 1180.0 ms, 总耗时 15317627.0, 次数 12985, 错误 None
  - Code-Java: 响应 435.0 ms, 总耗时 15118266.0, 次数 34763, 错误 None
  - Code-Java: 响应 574.0 ms, 总耗时 11427090.0, 次数 19918, 错误 None
- 当前根因判断：当前更像流程域的状态判断、权限校验、页面装配或参数边界问题，并夹杂一定的数据库/缓存访问成本。 代表 trace 首个可疑点为 `未知类型/HTTP ERROR CODE: 404`。
- 证据缺口：
  - 未补错误明细与业务返回码，仍需区分权限不足、状态不合法、参数缺失和真实服务异常。

## 24. SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/done-pages/{instId}

- 用户关注点：流程已办链路高错且偏慢，建议与 todo-pages 一起看但这里保留单条素材。
- 聚合指标：请求 14121, 平均 1629.348 ms, 错误 1604, 错误率 0.11359, 慢次数 2837
- 主 action：app 1645/action 13225 (SpringController/${url.rest.prefix.flowmobileapi.v1}/task-form-process/done-pages/{instId})
- action 映射：
  - 1644/13237: 请求 6891, 平均 1604.0 ms, 错误 791, 慢次数 1306
  - 1645/13225: 请求 7230, 平均 1654.0 ms, 错误 813, 慢次数 1531
- 代表 trace：1716193091，duration 8586.789 ms，status 200，uri /grcv5/api/flow-mobile/v1/task-form-process/done-pages/409889
- trace 可疑点：
  - None/org.apache.catalina.connector.ClientAbortException: exclusive 0.0 ms, count 0
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 6425.469 ms, count 0
  - DATABASE/None: exclusive 7607.771 ms, count 2629
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 719.0 ms, 总耗时 8118020.0, 次数 11283, 错误 None
  - Code-Java: 响应 705.0 ms, 总耗时 6958245.0, 次数 9863, 错误 None
  - Code-Java: 响应 685.0 ms, 总耗时 5321460.0, 次数 7774, 错误 None
  - Code-Java: 响应 770.0 ms, 总耗时 5200352.0, 次数 6757, 错误 None
  - Code-Java: 响应 685.0 ms, 总耗时 5031692.0, 次数 7347, 错误 None
- 当前根因判断：当前更像流程域的状态判断、权限校验、页面装配或参数边界问题，并夹杂一定的数据库/缓存访问成本。 代表 trace 首个可疑点为 `未知类型/org.apache.catalina.connector.ClientAbortException`。
- 证据缺口：
  - 未补错误明细与业务返回码，仍需区分权限不足、状态不合法、参数缺失和真实服务异常。

## 25. SpringController/${url.rest.prefix.flowmobileapi.v1}/process-drive/task/dispatch (POST)

- 用户关注点：流程流转链路出现错误与慢调用并存，优先核对状态判断、权限和路由参数。
- 聚合指标：请求 38940, 平均 733.367 ms, 错误 340, 错误率 0.008731, 慢次数 554
- 主 action：app 1645/action 13353 (SpringController/${url.rest.prefix.flowmobileapi.v1}/process-drive/task/dispatch (POST))
- action 映射：
  - 1644/13203: 请求 19130, 平均 724.0 ms, 错误 140, 慢次数 282
  - 1645/13353: 请求 19810, 平均 743.0 ms, 错误 200, 慢次数 272
- 代表 trace：1716362216，duration 445.047 ms，status 200，uri /grcv5/api/flow-mobile/v1/process-drive/task/dispatch
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 109.334 ms, count 0
  - DATABASE/None: exclusive 337.2129999999998 ms, count 145
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 3621.0 ms, 总耗时 36371823.0, 次数 10045, 错误 None
  - NoSQL-Redis: 响应 1080.0 ms, 总耗时 26229861.0, 次数 24290, 错误 None
  - Pool-Redis: 响应 887.0 ms, 总耗时 21554305.0, 次数 24290, 错误 None
  - Code-Java: 响应 2798.0 ms, 总耗时 15530992.0, 次数 5551, 错误 None
  - NoSQL-Redis: 响应 875.0 ms, 总耗时 11252699.0, 次数 12861, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。
- 证据缺口：
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 26. SpringController/${url.workflow.create}

- 用户关注点：流程创建入口有一定错误和慢调用，优先核对页面装配、权限与初始化查询。
- 聚合指标：请求 16427, 平均 333.083 ms, 错误 145, 错误率 0.008827, 慢次数 493
- 主 action：app 1645/action 13476 (SpringController/${url.workflow.create})
- action 映射：
  - 1644/13503: 请求 7995, 平均 383.0 ms, 错误 118, 慢次数 234
  - 1645/13476: 请求 8432, 平均 286.0 ms, 错误 27, 慢次数 259
- 代表 trace：1715177992，duration 4076.839 ms，status 200，uri /grcv5/bpm/create.htm
- trace 可疑点：
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 3868.149 ms, count 0
  - POOL/None: exclusive 6.049999999999903 ms, count 1223
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 186.0 ms, 总耗时 4422119.0, 次数 23730, 错误 None
  - Code-Java: 响应 379.0 ms, 总耗时 4134559.0, 次数 10921, 错误 None
  - Code-Java: 响应 231.0 ms, 总耗时 3631654.0, 次数 15716, 错误 None
  - Code-Java: 响应 345.0 ms, 总耗时 3364048.0, 次数 9765, 错误 None
  - Code-Java: 响应 226.0 ms, 总耗时 3301298.0, 次数 14618, 错误 None
- 当前根因判断：当前更像流程域高频读写/页面装配路径偏慢，数据库、缓存和事务提交开销会在高访问下被持续放大。 代表 trace 首个可疑点为 `CODE/javax.servlet.http.HttpServlet.service`。
- 证据缺口：
  - 未补错误明细与业务返回码，仍需区分权限不足、状态不合法、参数缺失和真实服务异常。

## 27. SpringController/serverapi/v1/flow-mobile/task-form-process/download-attachments-kfv/{code}

- 用户关注点：附件下载错误多，优先核对文件服务、鉴权、对象存储访问和路径拼装。
- 聚合指标：请求 16060, 平均 126.772 ms, 错误 1282, 错误率 0.079826, 慢次数 54
- 主 action：app 1645/action 13228 (SpringController/serverapi/v1/flow-mobile/task-form-process/download-attachments-kfv/{code})
- action 映射：
  - 1644/13167: 请求 7551, 平均 128.0 ms, 错误 583, 慢次数 20
  - 1645/13228: 请求 8509, 平均 125.0 ms, 错误 699, 慢次数 34
- 代表 trace：1713489300，duration 471.858 ms，status 200，uri /grcv5/serverapi/v1/flow-mobile/task-form-process/download-attachments-kfv/1669687
- trace 可疑点：
  - CODE/com.hd.rcugrc.bpm.facade.mobile.mvc.AttachmentPreConversionController.downLoadAttachementKfv: exclusive 466.37 ms, count 0
  - POOL/None: exclusive 0.297 ms, count 10
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 1206.0 ms, 总耗时 3792860.0, 次数 3146, 错误 None
  - Code-Java: 响应 483.0 ms, 总耗时 2529089.0, 次数 5236, 错误 None
  - Code-Java: 响应 305.0 ms, 总耗时 1476795.0, 次数 4840, 错误 None
  - Code-Java: 响应 264.0 ms, 总耗时 1061116.0, 次数 4026, 错误 None
  - Pool-Redis: 响应 172.0 ms, 总耗时 345097.0, 次数 2002, 错误 None
- 当前根因判断：当前更像附件公共能力链路偏慢/偏错：素材显示问题不只在单点 controller，而是在上传、模板处理、附件读取或存储访问之间放大。
- 证据缺口：
  - 未补文件服务/对象存储/外部预览依赖 pack，暂无法拆出各子链路占比。

## 28. URI/grcv5/rest/mobile/thirdpartylogin.json

- 用户关注点：登录/对接链路错误偏多，优先看第三方返回码、超时、重试和签名鉴权校验。
- 聚合指标：请求 50705, 平均 121.186 ms, 错误 2716, 错误率 0.053565, 慢次数 197
- 主 action：app 1645/action 13209 (URI/grcv5/rest/mobile/thirdpartylogin.json)
- action 映射：
  - 1644/13184: 请求 23936, 平均 120.0 ms, 错误 1300, 慢次数 93
  - 1645/13209: 请求 26769, 平均 122.0 ms, 错误 1416, 慢次数 104
- 代表 trace：1716281728，duration 369.456 ms，status 200，uri /grcv5/rest/mobile/thirdpartylogin.json
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 321.098 ms, count 0
  - POOL/None: exclusive 0.44 ms, count 8
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 660.0 ms, 总耗时 6371779.0, 次数 9652, 错误 None
  - NoSQL-Redis: 响应 391.0 ms, 总耗时 1635530.0, 次数 4185, 错误 None
  - Pool-Redis: 响应 391.0 ms, 总耗时 1635432.0, 次数 4185, 错误 None
  - Pool-Database: 响应 2640.0 ms, 总耗时 1589528.0, 次数 602, 错误 None
  - External-Https: 响应 1347.0 ms, 总耗时 1589424.0, 次数 1180, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。 同时存在数据库连接池/获取连接开销，建议把 SQL 执行时间和连接等待一起核对。
- 证据缺口：
  - 未单独拉取 connection_pool_pack，无法定量确认等待连接占比。
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。

## 29. SpringController/serverapi/v1/thirdParty/getOppDocking

- 用户关注点：第三方对接链路高访问且有错误，优先核对外部依赖返回、鉴权、参数和状态判断。
- 聚合指标：请求 88184, 平均 200.836 ms, 错误 443, 错误率 0.005024, 慢次数 5
- 主 action：app 1644/action 13846 (SpringController/serverapi/v1/thirdParty/getOppDocking)
- action 映射：
  - 1644/13846: 请求 66130, 平均 195.0 ms, 错误 102, 慢次数 4
  - 1645/16217: 请求 22054, 平均 219.0 ms, 错误 341, 慢次数 1
- 代表 trace：1712558999，duration 235.407 ms，status 200，uri /grcv5/serverapi/v1/thirdParty/getOppDocking
- trace 可疑点：
  - EXTERNAL/http://open.api.tianyancha.com:80/services/open/ic/baseinfo/normal: exclusive 185.918 ms, count 0
  - POOL/None: exclusive 0.05700000000000001 ms, count 11
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 191.0 ms, 总耗时 69430554.0, 次数 362659, 错误 None
  - Code-Java: 响应 193.0 ms, 总耗时 64002227.0, 次数 331199, 错误 None
  - NoSQL-Redis: 响应 115.0 ms, 总耗时 19021456.0, 次数 164820, 错误 None
  - NoSQL-Redis: 响应 117.0 ms, 总耗时 17545244.0, 次数 150563, 错误 None
  - Pool-Redis: 响应 77.0 ms, 总耗时 12724788.0, 次数 164821, 错误 None
- 当前根因判断：当前更像第三方对接链路问题：接口自身平均耗时不高，但错误量明显，优先关注外部返回码、超时、重试和签名鉴权。
- 证据缺口：
  - 未补外部依赖明细和失败返回码分布，暂不能区分超时、鉴权失败还是业务拒绝。

## 30. URI/grcv5/api/flow-mobile/v1/task-form-process/done-pages/undefined

- 用户关注点：路径中直接出现 undefined，优先检查前后端参数传递、路由拼装和空值保护。
- 聚合指标：请求 3050, 平均 4.814 ms, 错误 3050, 错误率 1.0, 慢次数 0
- 主 action：app 1645/action 13439 (URI/grcv5/api/flow-mobile/v1/task-form-process/done-pages/undefined)
- action 映射：
  - 1644/13438: 请求 1460, 平均 5.0 ms, 错误 1460, 慢次数 0
  - 1645/13439: 请求 1590, 平均 5.0 ms, 错误 1590, 慢次数 0
- 代表 trace：1714546146，duration 5.691 ms，status 400，uri /grcv5/api/flow-mobile/v1/task-form-process/done-pages/undefined
- trace 可疑点：
  - None/HTTP ERROR CODE: 400: exclusive 0.0 ms, count 0
  - CODE/com.hd.rcugrc.product.common.filter.CasRedirectFilter.doFilter: exclusive 2.735 ms, count 0
  - NOSQL/None: exclusive 2.239 ms, count 7
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 4.0 ms, 总耗时 4921.0, 次数 1160, 错误 None
  - Code-Java: 响应 4.0 ms, 总耗时 3840.0, 次数 920, 错误 None
  - Code-Java: 响应 4.0 ms, 总耗时 2827.0, 次数 690, 错误 None
  - Code-Java: 响应 4.0 ms, 总耗时 2636.0, 次数 620, 错误 None
  - Code-Java: 响应 4.0 ms, 总耗时 2497.0, 次数 610, 错误 None
- 当前根因判断：错误主因更像前端或调用方把路径参数直接拼成 `undefined`。当前聚合指标是低时延但 100% 失败，说明请求很快被参数校验/路由层拦截，不像后端性能瓶颈。
- 证据缺口：
  - 未补失败样本的入参来源和前端路由代码，仍需研发核对参数传递链路。

## 31. URI/grcv5/api/flow-mobile/v1/user-tasks/undefined

- 用户关注点：路径中直接出现 undefined，优先检查前后端参数传递、路由拼装和空值保护。
- 聚合指标：请求 104, 平均 6.865 ms, 错误 104, 错误率 1.0, 慢次数 0
- 主 action：app 1645/action 13837 (URI/grcv5/api/flow-mobile/v1/user-tasks/undefined)
- action 映射：
  - 1645/13837: 请求 104, 平均 7.0 ms, 错误 104, 慢次数 0
- 代表 trace：1710096679，duration 8.423 ms，status 404，uri /grcv5/api/flow-mobile/v1/user-tasks/undefined
- trace 可疑点：
  - None/HTTP ERROR CODE: 404: exclusive 0.0 ms, count 0
  - CODE/javax.servlet.http.HttpServlet.service: exclusive 3.975 ms, count 0
  - NOSQL/None: exclusive 2.4789999999999996 ms, count 7
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 6.0 ms, 总耗时 419.0, 次数 70, 错误 None
  - Code-Java: 响应 6.0 ms, 总耗时 405.0, 次数 70, 错误 None
  - Code-Java: 响应 6.0 ms, 总耗时 393.0, 次数 70, 错误 None
  - Code-Java: 响应 7.0 ms, 总耗时 333.0, 次数 50, 错误 None
  - Code-Java: 响应 6.0 ms, 总耗时 280.0, 次数 50, 错误 None
- 当前根因判断：错误主因更像前端或调用方把路径参数直接拼成 `undefined`。当前聚合指标是低时延但 100% 失败，说明请求很快被参数校验/路由层拦截，不像后端性能瓶颈。
- 证据缺口：
  - 未补失败样本的入参来源和前端路由代码，仍需研发核对参数传递链路。

## 32. SpringController/${url.rest.prefix.flowmobileapi.v1}/process-drive/task-candidate-infos (POST)

- 用户关注点：量大且存在错误，优先看候选人装配、权限判断和参数边界。
- 聚合指标：请求 48746, 平均 153.62 ms, 错误 187, 错误率 0.003836, 慢次数 67
- 主 action：app 1645/action 13202 (SpringController/${url.rest.prefix.flowmobileapi.v1}/process-drive/task-candidate-infos (POST))
- action 映射：
  - 1644/13350: 请求 23821, 平均 152.0 ms, 错误 58, 慢次数 31
  - 1645/13202: 请求 24925, 平均 155.0 ms, 错误 129, 慢次数 36
- 代表 trace：1715805177，duration 143.223 ms，status 200，uri /grcv5/api/flow-mobile/v1/process-drive/task-candidate-infos
- trace 可疑点：
  - DATABASE/MySQL/10.190.22.21:3306/bpmapp_hg: exclusive 109.522 ms, count 0
  - DATABASE/None: exclusive 121.47699999999998 ms, count 36
- 依赖拆解 TOP 组件：
  - Code-Java: 响应 170.0 ms, 总耗时 3324596.0, 次数 19572, 错误 None
  - Code-Java: 响应 285.0 ms, 总耗时 2870427.0, 次数 10068, 错误 None
  - Code-Java: 响应 109.0 ms, 总耗时 2286059.0, 次数 20964, 错误 None
  - Code-Java: 响应 164.0 ms, 总耗时 1858949.0, 次数 11316, 错误 None
  - Code-Java: 响应 168.0 ms, 总耗时 1694802.0, 次数 10104, 错误 None
- 当前根因判断：当前证据更偏向数据库主导：代表 trace 的首要可疑点落在数据库节点，依赖拆解也把 MySQL/数据库池放在高位。
- 证据缺口：
  - 未补 SQL fact / slow SQL 明细，仍需下钻 SQL 文本、执行计划和索引命中。
