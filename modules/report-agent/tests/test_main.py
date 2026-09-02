import unittest

from main import EvidenceEvent, RuleAnalyzer, child_story_for_event, normalize_report


def event(event_id: str, candidate: str, strength: str = "strong") -> EvidenceEvent:
    return EvidenceEvent(id=event_id, module="story", event_type="story_revision", occurred_at="2026-08-25T08:00:00Z", behavior_summary="孩子尝试调整故事顺序", intelligence_candidates=[candidate], evidence_level=strength, context={})


class ReportAnalyzerTests(unittest.TestCase):
    def test_child_story_uses_concrete_session_content(self):
        chat_event = EvidenceEvent(
            id="ev-chat", module="chat", event_type="chat.observation-shared.v1",
            occurred_at="2026-09-01T08:00:00Z", behavior_summary="分享了一次观察或想法。",
            intelligence_candidates=["naturalistic"], raw_evidence={"turnCount": 4, "topicKey": "运动"},
            context={"sessionSummary": {"childWords": "我想学会更快地跑步。"}, "artifacts": []},
        )
        story = child_story_for_event(chat_event)
        self.assertIn("运动", story)
        self.assertIn("我想学会更快地跑步", story)
        self.assertNotIn("自然观察", story)

    def test_rule_output_uses_canonical_key_and_teacher(self):
        result = RuleAnalyzer().analyze([event("ev-1", "logical_mathematical")])
        keys = {item["key"] for item in result["dimensions"]}
        self.assertIn("logical", keys)
        self.assertNotIn("logical_mathematical", keys)
        self.assertIn("teacher", result["recommendations"])
        self.assertTrue(result["recommendations"]["family"])

    def test_normalizer_removes_fabricated_references(self):
        candidate = {"dimensions": [{"key": "logical", "analysis": "留意解题过程", "evidence_refs": ["fake", "ev-1"]}], "cross_insights": [{"text": "会反复尝试", "evidence_refs": ["fake", "ev-1"]}], "recommendations": {"family": "一起复盘", "teacher": "提供多种材料"}}
        result = normalize_report(candidate, [event("ev-1", "logical")])
        logical = next(item for item in result["dimensions"] if item["key"] == "logical")
        self.assertEqual(logical["evidence_refs"], ["ev-1"])
        self.assertEqual(result["cross_insights"][0]["evidence_refs"], ["ev-1"])
        self.assertNotIn("fake", str(result))
        self.assertNotIn("ev-1", result["recommendations"]["family"])


if __name__ == "__main__":
    unittest.main()
