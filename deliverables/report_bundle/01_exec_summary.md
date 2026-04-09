# 执行摘要

## 访问方式
- 机器 B 通过 `tingyun_adapter_client` 调用机器 A 的 `tingyun_adapter` 服务。
- client 配置来源：`tingyun_adapter_client/config.local.json`
- service_base_url：`https://pie-cloudy-wyoming-lions.trycloudflare.com`
- API key：已配置
- default_source_mode：`live`
- 本轮巡检窗口：`2025-12-20 00:00` 至 `2026-03-31 23:59`，实际远端调用统一使用 `endTime=2026-04-01 00:00`、`periodMinutes=146880`。

## 已成功调用的能力
- `healthz`
- `meta`
- `report_fact_pack`
- `system_snapshot`
- `screenshot_index_pack`
- `slow_sql_pack`
- `external_dependency_pack`
- `comparison_signals_pack`
- `knowledge_context_pack`
- `trace_case_pack`
- `action_fact_sheet`：`1645/13161`、`1644/31762`、`1644/13513`、`1645/13332`
- `action_dependency_breakdown_pack`：`1645/13161`、`1644/31762`、`1644/13513`、`1645/13332`
- `trace_fact_sheet`：`1651592641`、`1710818946`、`1715659568`，以及两条候选 `1423238353`、`1432031331` 的补取尝试
- `instance_analysis_pack`：`1644`、`1645`、`1646`
- `connection_pool_pack`

## 主入口复用情况
- 主入口仍然使用 `report_fact_pack`，并复用了其 `candidate_registry / codex_review_input / main_issue_selections / deep_dive_targets / selected_target_expansions / report_writer_input / template_mapping / report_pack_exports`。
- `report_fact_pack.meta.build_stats`：`upstream_call_count=124`，`cache_hit_count=6`，`shard_count=8`，`degrade_mode=long_window_short_comparison`。
- 当前统一候选池规模：`candidate_registry_count=98`；selected deep dive：`deep_dive_target_count=6`，`selected_target_expansion_count=11`。

## 候选池覆盖检查
- diagnostic_candidate_pack：26 个候选命中统一候选池
- action_hotspot_pack：40 个候选命中统一候选池
- system_snapshot suspect_signals：2 条总体异常信号
- trace_case_pack：15 个候选命中统一候选池
- slow_sql_pack：15 个候选命中统一候选池
- sql_main_candidates：15 条
- sql_opportunities：0 条
- sql_candidates：15 条
- external_dependency_pack：2 个候选命中统一候选池
- comparison_signals_pack：58 个候选命中统一候选池

## 当前素材不足
- 页面能力仍然只有“页面代理证据”，缺少真实前端 RUM 指标。
- knowledge_context_pack 仍为空，无法用 confirmed knowledge / pending proposals / judgment log 做历史基线校准。
- trace_fact_sheet 对 trace:1423238353 和 trace:1432031331 只返回 requestId，缺少 detail/uri/status，无法做正文深挖。
- sql_fact_sheet 虽然提示 `sql_related_action_count=2`，但 `impacted_actions` 与 `related_traces` 为空，SQL->action/trace 证据链不完整。
- instance_analysis_pack 的 JVM 图为空，只能保守判断“未见明显 CPU 失衡”，不能替代完整实例资源分析。
- 多条 direct_url 仍落在相同 trace-detail 页面，链接语义需要人工复核。

## 候选池缺口
- report_fact_pack 的 `observations` 数组仍为空，但 `codex_review_input.observation_candidates` 有 12 条，弱候选没有进入统一导出视图。
- adapter 返回的 `sql_opportunities` 为空，本轮 SQL 优化储备只能从 `sql_candidates` 中人工派生。
- system_snapshot 只有 2 条 suspect_signals，难以单独体现应用/实例层是否均衡，需要补 instance_analysis_pack 才能覆盖该视角。

## 深挖素材不足
- selected_target_expansions 覆盖了 6 个 deep_dive_targets，但 main_issue_selections 中的多条 trace 强候选没有被自动展开，需要机器 B 侧手工补取。
- 手工补取后，trace:1423238353 / 1432031331 仍然缺 detail，属于“深挖尝试成功但素材未充足返回”。
- 手工补取了 action_fact_sheet / action_dependency_breakdown_pack 后，13161 与上传链路主问题可写性明显提升；这说明默认 selective deep dive 对正文对象仍偏少。

## 下轮改代码建议
- 让 report_fact_pack 在 observations 为空但 observation_candidates 存在时，显式输出 observations 视图和 export。
- 扩大 main_issue_selections 的默认 selective deep dive，让正文主问题对象优先自动拿到 action_fact_sheet / trace_fact_sheet / dependency breakdown。
- 补强 trace_fact_sheet 对历史 trace 的稳定取数，避免只返回 requestId 而没有 detail。
- 补强 sql_fact_sheet 的 impacted_actions / related_traces 填充链路，减少 SQL 主问题与 action/trace 断链。
- 优化 page_links / screenshot_index_pack 的对象级 deep link 选择，避免多个对象复用同一 trace-detail direct_url。
- 为 sql_opportunities 保留独立的低优先级储备池，避免机器 B 侧必须从 sql_candidates 手工派生。
