# Live 接口深度诊断

数据来源：机器 B 通过本地 `tingyun_adapter_client` 调远端 adapter，`source_mode=live`。  
时间窗：`bizSystemId=1065`，`endTime=2026-04-01 00:00`，`periodMinutes=146880`。

## SpringController/onlinePreview

**[现状]** 这个入口当前仍是高访问高慢次数，live 请求约 `35672`，平均耗时约 `3710ms`，慢次数 `7570`。代表性慢样本里，主要时间几乎都落在 `cn.keking.web.controller.OnlinePreviewController.onlinePreview`，其独占时间约 `1715ms`；其次才是 `AttachmentPreConversionController.downLoadAttachementKfv`。数据库只有 2 类 SQL，总 SQL 时间约 `3ms`，不是主要瓶颈。当前证据很集中，核心慢点在预览控制器自身及其前置转换/读取链路，不在数据库。

**[建议]** 优先检查预览服务内部的文件转换、缓存命中、文件读取和预转换链路，不要先从数据库入手。建议先把 `onlinePreview` 方法内部再细分成“文件获取、格式转换、缓存命中/落盘、返回渲染”几个阶段看耗时占比。

## SpringController/${url.attachment}/${url.attachment.upload} (POST)

**[现状]** 这个入口 live 请求约 `44998`，平均耗时约 `6113ms`，错误 `100`，慢次数 `13453`。代表性慢样本里，最主要的耗时仍然落在 `OnlinePreviewController.onlinePreview`，独占时间约 `3548ms`；`AttachmentController.upload` 本身只有约 `118ms`。数据库侧只有少量附件元数据和主键生成相关 SQL，总 SQL 时间约 `11ms`，明显不是主因。当前更像上传请求同步触发了预览/预转换链路，导致上传被整体拖慢。

**[建议]** 优先确认上传后是否同步触发了预览或预转换逻辑，以及这段逻辑是否可以异步化或延后执行。数据库不是当前主方向，先从上传与预览链路耦合、文件落盘后立即预处理、以及预览服务回调方式入手排查。

## URI/grcv5/wp/contractView/viewContract.htm

**[现状]** 这个入口 live 请求约 `113812`，平均耗时约 `1337ms`，错误 `1018`，慢次数 `3778`。代表性样本里，`executeQuery` 调用 `148` 次，数据库独占时间约 `1038ms`，已经占了绝大部分耗时。最重的 SQL 集中在 `HD_FORM_GROUP_MEMBER` 和多张合同扩展信息表，单条查询可到 `221ms`、`163ms`、`112ms`、`88ms`。这里的核心问题已经比较明确，是合同查看页装配时数据库聚合过重。

**[建议]** 先从合同查看页的数据装配 SQL 入手，重点看 `HD_FORM_GROUP_MEMBER` 和合同扩展信息相关查询是否存在重复读取、按块拆得过细或一次请求内多次回表。这个入口应优先做查询合并和装配去重，再看单条 SQL 的索引与执行计划。

## SpringController/${url.workflow.edit}

**[现状]** 这个入口 live 请求约 `161806`，平均耗时约 `595ms`，错误 `1137`，慢次数 `932`。当前拿到的代表样本本身不算慢，耗时约 `155ms`，说明最近样本没有完整复现平均耗时水平。但从 trace 结构看，页面处理链路里已经存在稳定的中等强度数据库 fan-out：`executeQuery` `109` 次，数据库独占约 `47ms`，同时伴随 `Redis` 调用和一组重复的流程历史/人员/前驱步骤查询。当前更像高频页面装配成本持续累积，而不是某一条单点 SQL 爆炸。

**[建议]** 先按“页面装配过细、请求内重复查数”来排，而不是先找单条超慢 SQL。建议重点看编辑页装配过程中对流程历史、已读状态、人员、前驱步骤、合规信息这类数据是否存在循环查询；同时补抓更慢的代表 trace，确认高于均值的样本里是否还有更重的下游链路。

## SpringController/${url.workflow.view}

**[现状]** 这个入口 live 请求约 `57379`，平均耗时约 `662ms`，错误 `453`，慢次数 `273`。当前代表样本耗时约 `117ms`，同样没有完整复现平均耗时，但结构和 `workflow.edit` 很接近：`executeQuery` `76` 次，数据库独占约 `36ms`，也存在重复的流程历史、附件、已读状态和合规信息查询。当前证据指向的仍然是页面查看链路上的中度数据库 fan-out，而不是单一 SQL 或连接池问题。

**[建议]** 建议把它和 `workflow.edit` 放在同一类页面装配问题里处理，重点排查查看页组装过程中重复的流程历史、附件、已读状态相关查询。当前 live 代表样本偏轻，建议补抓更慢样本再确认是否存在更明显的重查询路径。

## SpringController/${url.attachment}/${url.attachment.updateAttachValid} (POST)

**[现状]** 这个入口 live 请求约 `93946`，平均耗时约 `1382ms`，错误 `3`，慢次数 `18199`。代表性慢样本耗时约 `3020ms`，而 `executeQuery` 调用虽然只有 `6` 次，但数据库独占时间约 `3011ms`，几乎等于整条请求耗时。核心 SQL 是对 `HD_COMP_ATAH_GROUP_REL` 的读取，平均单次约 `502ms`，重复执行了 `6` 次。这里不是泛化的“附件链路都慢”，而是这个校验接口本身就已经被单一关系查询拖住了。

**[建议]** 先直接检查 `HD_COMP_ATAH_GROUP_REL` 这条查询的执行计划和索引情况，同时排查为什么同一请求里会重复触发 6 次相同类型查询。如果查询模式不变，即使单条 SQL 优化一些，这个入口仍然会被重复读取放大。

## SpringController/${url.attachment}/${url.attachment.frmIndiDocs}

**[现状]** 这个入口 live 请求约 `54939`，平均耗时约 `4184ms`，错误 `12`，慢次数 `21852`。代表性样本里，主要时间仍然集中在 `OnlinePreviewController.onlinePreview`，累计独占约 `3018ms`；其次是 `AttachmentController.saveEdited` 和 `AttachmentPreConversionController.downLoadAttachementKfv`。数据库总 SQL 时间只有约 `19ms`，并不重。这个接口的核心问题和上传链路一致，本质还是附件预览/预转换路径放大，不是数据库瓶颈。

**[建议]** 优先检查 `frmIndiDocs` 是否在进入页面或保存编辑后立即触发了预览转换，以及预览结果是否存在缓存失效或重复转换。数据库可以放后面，这里的优先级仍然是预览服务链路。

## SpringController/${url.attachment}/${url.attachment.download}

**[现状]** 这个入口 live 请求约 `89261`，平均耗时约 `1539ms`，错误 `0`，慢次数 `3312`。但当前拿到的代表样本只有 `133ms`，没有复现平均耗时水平。这个样本里 `AttachmentController.download` 自身约 `94ms`，数据库只表现为一次下载日志写入约 `29ms` 和少量附件元数据查询，明显解释不了 `1.5s` 级别的平均耗时。也就是说，当前 live 样本不足以直接证明慢点已经落在数据库或日志写入上。

**[建议]** 这个入口当前不要过早下数据库结论，先明确标记为证据不足。建议补抓真正的慢下载样本，重点确认慢是在文件流读取、对象存储/共享存储访问、网络传输，还是在下载前的附件定位与权限校验阶段；当前这条代表样本只能说明“正常路径下控制器和日志写入不重”。

## URI/grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr

**[现状]** 这个入口 live 请求约 `179047`，平均耗时约 `975ms`，错误 `0`，慢次数 `24011`。代表性样本里，主要时间直接落在数据库：`executeQuery` `11` 次，数据库独占约 `373ms`。最重的 SQL 是 `SELECT ID from hd_todo_seen_log where TODO_ID=...`，单条约 `369ms`，另外还有对 `hd_todo_seen_log` 的插入以及 `BPM_TODO_LOGO` 的更新。这里的核心问题不是广义的“写接口慢”，而是已读标记链路被读前校验和状态更新这组数据库操作卡住了，尤其是 `hd_todo_seen_log` 查询最突出。

**[建议]** 优先检查 `hd_todo_seen_log` 相关查询和索引，确认 `TODO_ID` 维度是否命中有效索引，以及当前实现是否存在“先查后写”导致的额外往返。其次再看 `BPM_TODO_LOGO` 更新是否存在事务串行化或不必要的同步写入。

## URI/grcv5/dwr/call/plaincall/dwrHdWorkflowService.save.dwr

**[现状]** 这个入口 live 请求约 `126848`，平均耗时约 `794ms`，错误 `0`，慢次数 `7878`。代表性慢样本耗时约 `3183ms`，但数据库总 SQL 时间只有约 `1.5ms`，数据库不是主要瓶颈。调用树里最突出的热点是 `javax.servlet.http.HttpServlet.service`，独占约 `3177ms`，下游只看到很轻的 Redis 和少量查询，没有识别出明显的重 SQL。这说明当前慢点主要在应用代码或事务处理本身，而不是数据库。

**[建议]** 这个入口应优先往应用层查，不要先从 SQL 入手。建议重点看保存链路中的业务组装、状态推进、事务提交、同步回写和可能的序列化/锁等待；当前 trace 已经足够说明数据库不是主因，但还不足以把应用层瓶颈精确到具体 service 方法，建议继续补更细的慢样本或在保存链路加阶段性耗时埋点。
