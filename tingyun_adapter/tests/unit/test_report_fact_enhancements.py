from __future__ import annotations

import unittest

from tingyun_adapter.usecases.report_fact_enhancements import (
    build_candidate_registry,
    build_codex_review_input,
    build_writer_input,
    dedupe_issue_candidates,
    rank_issue_candidate,
    render_codex_review_input_markdown,
    render_writer_input_markdown,
    select_candidate_outcomes,
    sql_fingerprint,
    union_sql_candidates,
)


class ReportFactEnhancementTests(unittest.TestCase):
    def test_low_frequency_issue_is_downgraded(self) -> None:
        candidate = rank_issue_candidate(
            {
                "issue_type": "action_latency",
                "title": "低频慢接口",
                "occurrence_count": 1,
                "active_windows": 1,
                "affected_objects": 1,
                "affected_traces": 1,
                "business_criticality": "low",
                "evidence_strength": "weak",
            }
        )
        self.assertNotIn(candidate["report_priority"], {"P0", "P1"})
        self.assertIn(candidate["report_priority"], {"P2", "P3", "observation"})

    def test_low_frequency_but_fatal_core_issue_is_upgraded(self) -> None:
        candidate = rank_issue_candidate(
            {
                "issue_type": "action_error",
                "title": "核心上传链路 100% 失败",
                "occurrence_count": 1,
                "active_windows": 1,
                "affected_objects": 1,
                "business_criticality": "high",
                "evidence_strength": "strong",
                "critical_path": True,
                "fatal": True,
                "failure_rate": 1.0,
                "severity_level": "critical",
            }
        )
        self.assertIn(candidate["report_priority"], {"P0", "P1"})

    def test_duplicate_issues_share_canonical_key(self) -> None:
        deduped = dedupe_issue_candidates(
            [
                {
                    "canonical_issue_key": "action:latency:13238",
                    "issue_type": "action_latency",
                    "title": "接口慢",
                    "occurrence_count": 6,
                    "affected_objects": 2,
                    "business_criticality": "high",
                    "evidence_strength": "strong",
                },
                {
                    "canonical_issue_key": "action:latency:13238",
                    "issue_type": "action_latency",
                    "title": "Trace 中也看到接口慢",
                    "occurrence_count": 2,
                    "affected_objects": 1,
                    "business_criticality": "medium",
                    "evidence_strength": "medium",
                    "primary_section": "3.5 请求追踪与根因分析专题",
                },
            ]
        )
        primary = [item for item in deduped if item["duplicate_of"] is None]
        duplicates = [item for item in deduped if item["duplicate_of"]]
        self.assertEqual(len(primary), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(primary[0]["canonical_issue_key"], "action:latency:13238")
        self.assertEqual(duplicates[0]["duplicate_of"], "action:latency:13238")

    def test_sql_union_keeps_multiple_sources(self) -> None:
        sql_text = "SELECT DISTINCT id FROM contract_info WHERE LOWER(name) LIKE '%abc%' ORDER BY id"
        fingerprint = sql_fingerprint(sql_text)
        inventory = union_sql_candidates(
            [
                {
                    "opName": sql_text,
                    "op_name_decoded": sql_text,
                    "componentName": "db-a",
                    "componentSubtype": "MySQL",
                    "response_time_ms": 1800,
                    "total_response_time_ms": 6400,
                    "count": 22,
                    "traceCount": 8,
                    "sql_features": {"tags": ["DISTINCT", "ORDER_BY", "LIKE_PREFIXLESS", "FUNCTION_ON_COLUMN"]},
                },
                {
                    "opName": sql_text,
                    "op_name_decoded": sql_text,
                    "componentName": "db-a",
                    "componentSubtype": "MySQL",
                    "response_time_ms": 900,
                    "total_response_time_ms": 5000,
                    "count": 10,
                    "traceCount": 2,
                    "sql_features": {"tags": ["DISTINCT", "ORDER_BY"]},
                },
            ],
            trace_case={"trace": {"trace_id_numeric": "trace-1", "action_id": 20441}},
            sql_fact_payloads={
                fingerprint: {
                    "related_actions": [{"actionId": 20441, "applicationId": 1648, "actionName": "核心提交接口"}],
                    "related_traces": [{"actionId": 20441, "resp_time_ms": 1800}],
                }
            },
        )
        self.assertEqual(len(inventory["sql_candidates"]), 1)
        candidate = inventory["sql_candidates"][0]
        self.assertIn("global_top", candidate["candidate_source"])
        self.assertIn("trace_bound", candidate["candidate_source"])
        self.assertIn("optimization", candidate["candidate_source"])
        self.assertIn(candidate["report_recommendation"], {"main_issue", "section_highlight"})

    def test_writer_input_handles_missing_materials_with_boundary(self) -> None:
        writer_input = build_writer_input(
            report_scope={"bizSystemId": 1059, "endTime": "2026-04-03 12:20", "periodMinutes": 30, "sourceMode": "sample"},
            summary={"biz_system_name": "示例系统"},
            coverage_boundary={"page_experience": {"status": "partial", "reason": "缺少 RUM 明细。"}},
            issues=[],
            observations=[],
            sql_main_candidates=[],
            sql_opportunities=[],
            trace_case={},
            page_payload={},
            screenshot_index_summary={"card_count": 0},
            page_links=[],
            screenshot_index_rows=[],
            main_issue_selections=[],
            deep_dive_targets=[],
            template_mapping={"sections": []},
        )
        markdown = render_writer_input_markdown(writer_input)
        self.assertIn("能力边界", markdown)
        self.assertIn("缺少 RUM 明细", markdown)
        self.assertGreater(len(writer_input["manual_review_items"]), 0)
        self.assertIn("section_order", writer_input)
        self.assertIn("page_capability_boundary", writer_input)

    def test_candidate_registry_merges_action_and_comparison_sources(self) -> None:
        registry = build_candidate_registry(
            report_scope={"bizSystemId": 1059},
            snapshot_payload={"health": {}},
            diagnostic_payload={"system_signals": []},
            hotspot_payload={
                "hotspots": [
                    {
                        "action": {
                            "id": 20441,
                            "biz_system_id": 1059,
                            "application_id": 1648,
                            "type": "TX",
                            "name": "核心提交接口",
                            "metrics": {"slow_count": 8, "error_count": 0},
                        },
                        "overview": {"components": {"db": 1}},
                        "suspect_signals": [{"type": "high_response_time_ms"}],
                    }
                ]
            },
            trace_candidates=[],
            trace_case={},
            sql_candidates=[],
            external_payload={"external_dependencies": []},
            comparison_payload={
                "objects": [
                    {
                        "target_ref": {"kind": "action", "biz_system_id": 1059, "application_id": 1648, "action_id": 20441, "action_type": "TX"},
                        "display_name": "核心提交接口",
                        "change_class": "regressed",
                        "trend_confidence": "medium",
                        "evidence_refs": ["comparison"],
                        "source_basis": [{"value": "previous_window"}],
                    }
                ]
            },
            labels_payload={
                "objects": [
                    {
                        "target_ref": {"kind": "action", "biz_system_id": 1059, "application_id": 1648, "action_id": 20441, "action_type": "TX"},
                        "candidate_labels": ["core_business_path"],
                        "confirmed_labels": [],
                    }
                ]
            },
            stability_payload={"objects": []},
            impact_payload={"objects": []},
            knowledge_payload={"core_context": {}},
        )
        self.assertEqual(len(registry), 1)
        candidate = registry[0]
        self.assertIn("action_hotspot_pack", candidate["source_packs"])
        self.assertIn("comparison_signals_pack", candidate["source_packs"])
        self.assertIn("regressed", candidate["review_hints"])

    def test_candidate_registry_accepts_diagnostic_trace_and_marks_weak_candidates(self) -> None:
        registry = build_candidate_registry(
            report_scope={"bizSystemId": 1065},
            snapshot_payload={"health": {}, "suspect_signals": [{"type": "high_response_time_ms", "level": "high", "source_api": "overview"}]},
            diagnostic_payload={
                "system_signals": [],
                "action_candidates": [],
                "trace_candidates": [
                    {
                        "trace_id_numeric": "trace-1065-1",
                        "trace_guid": "guid-1",
                        "query_timestamp": "1700000000000",
                        "suspect_signals": [],
                        "_registry_source_packs": ["diagnostic_candidate_pack"],
                        "_registry_source_basis": ["diagnostic_trace_candidate"],
                    }
                ],
            },
            hotspot_payload={"hotspots": []},
            trace_candidates=[],
            trace_case={},
            sql_candidates=[],
            external_payload={"external_dependencies": []},
            comparison_payload={"objects": []},
            labels_payload={"objects": []},
            stability_payload={"objects": []},
            impact_payload={"objects": []},
            knowledge_payload={"core_context": {}},
        )
        trace_candidate = next(item for item in registry if item["candidate_type"] == "trace")
        signal_candidate = next(item for item in registry if item["candidate_type"] == "regression_signal")
        self.assertIn("diagnostic_candidate_pack", trace_candidate["source_packs"])
        self.assertIn("diagnostic_trace_candidate", trace_candidate["source_basis"])
        self.assertIn("low_frequency", trace_candidate["review_hints"])
        self.assertIn("suspect_signal", signal_candidate["source_basis"])

    def test_codex_review_input_groups_candidates(self) -> None:
        candidate_registry = [
            {
                "candidate_key": "action:1",
                "candidate_type": "action",
                "display_name": "核心接口",
                "evidence_strength": "strong",
                "impact_scope": "core_path",
                "review_hints": ["high_latency"],
                "recommended_next_packs": ["action_fact_sheet"],
            },
            {
                "candidate_key": "sql:1",
                "candidate_type": "sql",
                "display_name": "sql:1",
                "evidence_strength": "medium",
                "impact_scope": "local",
                "review_hints": ["optimization"],
                "recommended_next_packs": ["sql_fact_sheet"],
                "report_recommendation": "appendix_candidate",
            },
        ]
        outcomes = select_candidate_outcomes(candidate_registry)
        review_input = build_codex_review_input(
            report_scope={"bizSystemId": 1059, "endTime": "2026-04-03 12:20"},
            summary={"biz_system_name": "示例系统"},
            candidate_registry=candidate_registry,
            main_issue_selections=outcomes["main_issue_selections"],
            observation_candidates=outcomes["observation_candidates"],
            sql_opportunity_candidates=outcomes["sql_opportunity_candidates"],
            deep_dive_targets=outcomes["deep_dive_targets"],
            knowledge_payload={"confirmed_knowledge_summary": {"entry_count": 0}, "pending_proposals_summary": {"pending_count": 0}, "missing_items": []},
        )
        markdown = render_codex_review_input_markdown(review_input)
        self.assertIn("主问题高可信候选", markdown)
        self.assertIn("优化机会级 SQL 候选", markdown)
        self.assertEqual(len(review_input["main_issue_candidates"]), 1)
        self.assertEqual(len(review_input["sql_candidates"]["optimization_level"]), 1)

    def test_select_candidate_outcomes_prioritizes_multi_type_deep_dive_targets(self) -> None:
        candidate_registry = [
            {
                "candidate_key": "trace:1",
                "candidate_type": "trace",
                "display_name": "trace-1",
                "evidence_strength": "medium",
                "impact_scope": "local",
                "review_hints": ["needs_confirmation"],
                "recommended_next_packs": ["trace_fact_sheet"],
            },
            {
                "candidate_key": "sql:1",
                "candidate_type": "sql",
                "display_name": "sql-1",
                "evidence_strength": "weak",
                "impact_scope": "local",
                "review_hints": [],
                "recommended_next_packs": ["sql_fact_sheet", "database_component_pack"],
                "report_recommendation": "section_highlight",
            },
            {
                "candidate_key": "dependency:1",
                "candidate_type": "dependency",
                "display_name": "dep-1",
                "evidence_strength": "medium",
                "impact_scope": "local",
                "review_hints": ["needs_confirmation"],
                "recommended_next_packs": ["external_dependency_pack", "topology_dependency_pack"],
            },
            {
                "candidate_key": "action:1",
                "candidate_type": "action",
                "display_name": "action-1",
                "evidence_strength": "medium",
                "impact_scope": "core_path",
                "review_hints": [],
                "recommended_next_packs": ["action_fact_sheet", "action_dependency_breakdown_pack"],
            },
        ]
        outcomes = select_candidate_outcomes(candidate_registry)
        deep_dive_types = [item["candidate_type"] for item in outcomes["deep_dive_targets"]]
        self.assertIn("trace", deep_dive_types)
        self.assertIn("sql", deep_dive_types)
        self.assertIn("dependency", deep_dive_types)
        sql_target = next(item for item in outcomes["deep_dive_targets"] if item["candidate_type"] == "sql")
        self.assertEqual(sql_target["source_master_table"], "sql_master.csv")
        self.assertEqual(sql_target["object_type"], "sql")
        self.assertTrue(sql_target["selected_for_deep_dive"])


if __name__ == "__main__":
    unittest.main()
