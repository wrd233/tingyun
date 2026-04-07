# Tingyun Adapter

这个项目负责把听云平台原始接口整理成更适合分析与报告场景的结构化 pack。

当前已经完成的核心能力：

- 阶段 1-2
  - schema / ref / envelope / entity
  - raw client
  - 字段归一化
  - `opName` 解码
  - `CapturedApiRepository`
- 阶段 3
  - `system_snapshot`
  - `action_hotspot_pack`
  - `trace_case_pack`
  - `report_fact_pack`
- 阶段 4
  - `database_component_pack`
  - `nosql_component_pack`
  - `connection_pool_pack`
- 阶段 5
  - `diagnostic_candidate_pack`
  - `action_fact_sheet`
  - `trace_fact_sheet`
  - `suspect_signals`
  - 默认敏感信息脱敏输出
- 阶段 A
  - 本地 HTTP 服务
  - 面向机器 B 的远程调用入口
  - 基础访问节流
- 阶段 6
  - `instance_analysis_pack`
  - `topology_dependency_pack`
  - `external_dependency_pack`
  - `slow_sql_pack`
  - `sql_fact_sheet`
  - `action_dependency_breakdown_pack`
- 阶段 7
  - `business_labels_pack`
  - `stability_signals_pack`
  - `impact_signals_pack`
  - `comparison_signals_pack`
  - `page_experience_pack`
- 阶段 8
  - `page_links`
  - `screenshot_hints`
  - `metric_semantics`
  - `coverage_boundary`
  - `evidence_linkage`
  - `screenshot_index_pack`
- 阶段 9
  - `knowledge_context_pack`
  - `knowledge_update_proposal_pack`
  - `knowledge/<biz_system>/` 文件化业务记忆层
  - 5 个增强 pack 接入 confirmed knowledge、pending proposals、judgment log
- 阶段 10
  - `report_fact_pack` 扩展 issue / observation / SQL candidate 池
  - `report_writer_input`
  - `template_mapping`
  - `report_pack_exports`
  - `02_sections/sql.md` / `03_issues/*.csv` / `04_raw/*.json` 的文件化导出视图

当前暂缓的方向：
- 更复杂的历史基线仓储与长期趋势预测
- 更完整的页面侧 API 采集与 RUM 明细建模

## 阶段 10 设计边界

本轮新增的是“更稳的巡检素材构建与排序层”，不是最终报告生成器：

- adapter 会扩 issue candidate 与 SQL candidate 池，再做收敛
- adapter 会输出 `issues / observations / sql_opportunities / writer_input`
- adapter 会在 `report_fact_pack` 中提供 `report_pack_exports`，让下游可以直接落成固定路径文件
- adapter 仍然不直接给出最终根因、最终整改方案和最终定稿措辞

本轮重点新增：

- issue 三层输出
  - `issues`
  - `observations`
  - `issue_candidates`
- SQL 三路并集
  - `global_top`
  - `trace_bound`
  - `optimization`
- writer 单入口
  - `report_writer_input`
  - `template_mapping`
  - `report_pack_exports`

### `report_fact_pack` 新增字段

- `observations`
  - 承接低频、弱证据、仅单窗口命中的对象
- `issue_candidates`
  - 原始候选池，保留去重关系、降级原因和证据角色
- `sql_main_candidates`
  - 进入 SQL 主展开层的对象
- `sql_opportunities`
  - 可优化但暂不一定上升为系统主问题的 SQL
- `sql_candidates`
  - SQL 全量候选池，包含 `candidate_source / rank_by_avg / rank_by_total / rank_by_trace / trace_binding_strength`
- `report_writer_input`
  - 供 Codex / ChatGPT / 后续 writer 直接消费的结构化单入口
- `template_mapping`
  - 模板章节和 pack 素材的显式映射
- `report_pack_exports`
  - 把“固定路径文件”表示成 pack 内的导出视图

### `report_pack_exports` 当前固定路径

- `01_foundation/screenshot_index.csv`
- `02_sections/sql.md`
- `03_issues/issues.csv`
- `03_issues/observations.csv`
- `03_issues/sql_opportunities.csv`
- `04_raw/issue_candidates.json`
- `04_raw/sql_candidates.json`
- `00_internal/report_writer_input.md`
- `00_internal/report_writer_input.json`
- `00_internal/template_outline.md`

说明：

- 这个仓库当前仍然返回 envelope，而不是直接写磁盘目录
- `report_pack_exports` 的目标是让下游 materialize 成真实文件时不需要再重新组织
- CSV 导出使用 `columns + rows`
- Markdown 导出使用 `content`
- JSON 导出使用 `data`

### issue 体系说明

- `issues`
  - 正文主问题
  - 会带 `report_priority / selection_reason / evidence_strength / business_criticality`
- `observations`
  - 观察项
  - 适合承接低频、低影响、证据不足但值得保留的对象
- `issue_candidates`
  - 原始候选池
  - 会带 `canonical_issue_key / duplicate_of / evidence_role`

### SQL 候选池说明

- `global_top`
  - 来自全局慢 SQL 排序
- `trace_bound`
  - 来自 traceCount、trace 关联 action 或 SQL fact 的绑定关系
- `optimization`
  - 来自复杂结构、高频累计耗时或明显优化特征

SQL candidate 当前会补：

- `sql_fingerprint`
- `candidate_source`
- `rank_by_avg`
- `rank_by_total`
- `rank_by_trace`
- `trace_binding_strength`
- `caller_objects`
- `impact_objects`
- `sql_feature_tags`
- `optimization_hypothesis`
- `report_recommendation`

### 兼容性说明

- 原有 `summary / issues / page_links / screenshot_hints` 继续保留
- `issues` 仍保留旧消费者常用字段，如 `priority / category / title / evidence_ref / details`
- 新字段尽量以增量方式追加，不要求旧消费者立刻迁移
- 若下游希望稳定消费正式报告素材，优先读取：
  - `report_writer_input`
  - `report_pack_exports`

## 阶段 9 设计边界

本轮新增的是“面向大模型的业务记忆层 + 读写协助层”，不是审批系统，也不是最终报告层：

- adapter 负责读取 confirmed knowledge、pending proposals、judgment log
- adapter 负责把模型建议规范化为 pending proposal
- adapter 不直接把模型建议写成 confirmed knowledge
- adapter 不直接输出最终业务标签、最终重要性和最终业务结论

新增 pack：

- `knowledge_context_pack`
  - 统一输出某个业务系统的 confirmed / pending / judgment log 摘要
- `knowledge_update_proposal_pack`
  - 接收提议并写入 `review_queue`
  - 做 dedupe / conflict awareness / merge-not-overwrite

新增配置：

- `knowledge_dir`
  - 默认为 `./knowledge`
  - 用于按 `biz_system` 隔离存放业务知识文件

## 阶段 8 设计边界

本轮新增的是“正式报告取证支撑层”，不是报告写作层：

- adapter 负责输出可点击链接、截图建议、证据链和能力边界
- adapter 不负责术语翻译、对象展示名注册、reader-friendly 清洗
- adapter 不新增 `report-safe` 模式
- adapter 不输出最终根因、最终整改建议或最终报告结论

新增的统一字段：

- `page_links`
  - 面向听云控制台页面的导航提示
  - 当前优先保证可点击根链接、页面类型、建议导航路径和筛选条件
- `screenshot_hints`
  - 说明“建议截图什么、标注什么、适合放在哪个章节”
- `metric_semantics`
  - 说明指标主语、聚合方式、单位、时间窗口和样本范围
- `coverage_boundary`
  - 标准化声明能力覆盖与缺失，尤其是页面体验能力边界
- `evidence_linkage`
  - 显式串起时间窗、接口、trace、SQL、依赖和下一跳建议页面

新增 pack：

- `screenshot_index_pack`
  - 用于聚合截图候选卡片与页面深链
  - 适合让 Codex / ChatGPT 直接生成 Word 中的“截图索引”
  - `screenshot_cards` 现在也会同步带上 `url_status`、`direct_url`、`fallback_url`、`navigation_path`、`url_source`，避免上层导出层只能看到裸 `url`

## 阶段 7 设计边界

这 5 个新增能力仍然遵守 adapter 的统一原则：

- 面向对象，不面向页面截图
- 输出稳定 pack，而不是最终报告
- 以事实、标签、轻量派生信号、对比结果为主
- 不在 adapter 内输出最终根因、最终整改建议、最终优先级结论

其中：

- `business_labels_pack`
  - 给 action / dependency / 派生 page 对象补充业务语义标签
- `stability_signals_pack`
  - 表达复现性、扩散范围、时间分布、波动特征
- `impact_signals_pack`
  - 提供排序辅助层，不替代人工判断
- `comparison_signals_pack`
  - 提供 `previous_window` 基线对比
- `page_experience_pack`
  - 当前先做降级版页面体验事实层
  - 缺少页面侧专用输入时会在 `meta.missing_inputs` 中明确说明

## 本地配置

优先使用本地配置文件：

- `config.local.json`

先复制示例：

```bash
cp /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json.example /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json
```

示例结构：

```json
{
  "base_url": "http://169.169.173.25:8080",
  "token": "paste-your-token-here",
  "lang": "zh_CN",
  "timezone": "Asia/Shanghai",
  "timeout_seconds": 30,
  "captured_api_dir": "../tingyun_cdp_capture/captured_api",
  "knowledge_dir": "./knowledge",
  "console_public_base_url": "https://your-tingyun-console.example.com"
}
```

`tingyun_adapter` 会按下面顺序读取配置：

1. CLI 参数
2. `config.local.json`
3. 环境变量
4. 默认值

其中 token 额外支持：

- `TINGYUN_TOKEN`
- `TOKEN`

CLI / SDK 输出中的 `context.auth.token` 默认会脱敏，同时额外给出：

- `token_present`
- `token_env`

如果你希望 pack 中的 `page_links.url` 在 Word 或外部文档里可直接点击，建议配置：

- `console_public_base_url`
  - 一个报告读者可以访问到的听云控制台根地址
  - 当前 adapter 会优先输出“控制台根地址 + 页面类型 + 导航路径 + 筛选条件”
  - 这样即使某些 SPA 路由还没完全反推，也不会输出不可用的假深链

如果你希望增强 pack 和知识 pack 复用历史业务上下文，建议同时配置：

- `knowledge_dir`
  - 可使用默认值 `./knowledge`
  - 目录下将按 `biz_system_<id>/` 组织 `system_profile`、`action_labels`、`known_patterns`、`review_queue`、`judgment_log` 等文件

## 安装

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install -e .
```

如果你的 macOS 系统 Python 比较老，`pip install -e .` 可能会被系统权限或旧版 `pip` 限制住。这种情况下可以直接使用下面的 fallback：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install --user fastapi uvicorn
```

## 运行测试

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

## 查看 CLI

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli --help
```

## 本地 HTTP 服务

现在已经支持把 adapter 作为本地 HTTP 服务运行。

启动方式：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
tingyun-adapter-service
```

或：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.service.http_api
```

详细说明见：

- [adapter_service_local_and_public.md](/Users/wangrundong/work/mywork/tingyun_adapter/adapter_service_local_and_public.md)
- [../tingyun_adapter_client/README.md](/Users/wangrundong/work/mywork/tingyun_adapter_client/README.md)

## 典型调用

### `system_snapshot`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack system_snapshot \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `report_fact_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack report_fact_pack \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

重点看这些字段：

- `payload.issues`
- `payload.observations`
- `payload.sql_main_candidates`
- `payload.sql_opportunities`
- `payload.report_writer_input`
- `payload.report_pack_exports`

### `screenshot_index_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack screenshot_index_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### `knowledge_context_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack knowledge_context_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### `knowledge_update_proposal_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack knowledge_update_proposal_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --proposal-file ./proposal.example.json \
  --persist-proposals
```

## 报告取证字段说明

典型 pack 现在会带上：

- `primary_console_url`
- `related_console_urls`
- `page_links`
- `screenshot_hints`
- `metric_semantics`
- `coverage_boundary`
- `evidence_linkage`

这些字段的目标是让下游更容易完成：

- 在 Word 中插入可点击听云链接
- 在链接下方自动写“建议截图 / 建议标注”
- 明确哪些章节证据充分，哪些章节只能保守表述
- 减少对指标主语、统计口径和时间窗口的误读

### `diagnostic_candidate_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack diagnostic_candidate_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### `action_fact_sheet`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack action_fact_sheet \
  --biz-system-id 1065 \
  --application-id 1644 \
  --action-id 13220 \
  --action-type TX \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### `trace_fact_sheet`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack trace_fact_sheet \
  --biz-system-id 1062 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `database_component_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack database_component_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --component-name '10.190.22.21:3306' \
  --component-subtype 'MySQL'
```

### `instance_analysis_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack instance_analysis_pack \
  --biz-system-id 1059 \
  --application-id 1648 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `topology_dependency_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack topology_dependency_pack \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `external_dependency_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack external_dependency_pack \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `slow_sql_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack slow_sql_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### `sql_fact_sheet`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack sql_fact_sheet \
  --biz-system-id 1065 \
  --component-name '10.190.22.21:3306' \
  --component-subtype 'MySQL' \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `action_dependency_breakdown_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack action_dependency_breakdown_pack \
  --biz-system-id 1059 \
  --application-id 1648 \
  --action-id 20441 \
  --action-type TX \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

本轮新增能力说明见：

- [adapter_phase6_delivery.md](/Users/wangrundong/work/mywork/tingyun_adapter/adapter_phase6_delivery.md)
