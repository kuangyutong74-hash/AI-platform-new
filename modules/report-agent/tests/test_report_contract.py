import unittest

from main import EvidenceEvent, SYSTEM_PROMPT, normalize_report


class ReportContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = EvidenceEvent(
            id="event-1",
            module="career",
            event_type="workday_process_summary",
            occurred_at="2026-08-29T12:00:00+00:00",
            evidence_level="strong",
            intelligence_candidates=["logical"],
            behavior_summary="孩子比较了多个方案并主动调整选择。",
            raw_evidence={"interaction_count": 18, "adjustment_count": 2},
        )

    def test_prompt_declares_the_exact_nested_contract(self) -> None:
        for field in (
            '"dimensions"',
            '"cross_insights"',
            '"evidence_explanations"',
            '"recommendations"',
            '"family"',
            '"teacher"',
        ):
            self.assertIn(field, SYSTEM_PROMPT)
        self.assertIn("family 与 teacher 只能位于 recommendations 内", SYSTEM_PROMPT)

    def test_normalizer_preserves_a_valid_llm_response(self) -> None:
        candidate = {
            "dimensions": [{
                "key": "logical",
                "status": "证据丰富",
                "evidence_refs": ["event-1"],
                "analysis": "模型生成的逻辑维度分析。",
                "adult_observation": "模型生成的成人观察建议。",
                "child_story": "你比较了不同办法，还主动调整了选择。",
            }],
            "cross_insights": [{"text": "模型生成的跨维度观察。", "evidence_refs": ["event-1"]}],
            "evidence_explanations": [{
                "evidence_ref": "event-1",
                "title": "模型生成的过程标题",
                "summary": "模型生成的过程摘要",
                "details": ["主动尝试了 18 次。"],
            }],
            "recommendations": {
                "family": ["模型生成的家庭建议。"],
                "teacher": ["模型生成的教师建议。"],
            },
        }

        report = normalize_report(candidate, [self.event])
        logical = next(item for item in report["dimensions"] if item["key"] == "logical")
        self.assertEqual(logical["analysis"], "模型生成的逻辑维度分析。")
        self.assertEqual(report["cross_insights"][0]["text"], "模型生成的跨维度观察。")
        self.assertEqual(report["evidence_explanations"][0]["title"], "模型生成的过程标题")
        self.assertEqual(report["recommendations"]["family"][0], "模型生成的家庭建议。")
        self.assertEqual(report["recommendations"]["teacher"][0], "模型生成的教师建议。")


if __name__ == "__main__":
    unittest.main()
