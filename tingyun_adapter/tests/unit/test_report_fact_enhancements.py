from __future__ import annotations

import unittest

from tingyun_adapter.usecases.report_fact_enhancements import (
    build_writer_input,
    dedupe_issue_candidates,
    rank_issue_candidate,
    render_writer_input_markdown,
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
            template_mapping={"sections": []},
        )
        markdown = render_writer_input_markdown(writer_input)
        self.assertIn("能力边界", markdown)
        self.assertIn("缺少 RUM 明细", markdown)
        self.assertGreater(len(writer_input["manual_review_items"]), 0)


if __name__ == "__main__":
    unittest.main()
