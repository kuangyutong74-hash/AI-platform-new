import unittest

from reports import generate_internal_report


class ReportInteractionActivityTests(unittest.TestCase):
    def test_chat_activity_source_and_child_response_are_visible(self):
        event = {
            "id": "chat-activity-1",
            "module": "chat",
            "event_type": "chat.observation-shared.v1",
            "evidence_level": "strong",
            "behavior_summary": "孩子分享了自己的想法",
            "intelligence_candidates": ["intrapersonal"],
            "raw_evidence": {
                "turnCount": 3,
                "topicKey": "朋友相处",
                "interactionActivities": [
                    {
                        "activityType": "picture_choice",
                        "prompt": "哪幅画面最像刚才的情景？",
                        "response": "我选了和伙伴一起想办法，因为可以听完大家的话。",
                        "selectedOptions": ["和伙伴一起想办法"],
                        "revisionCount": 1,
                        "sourceTopic": "朋友相处",
                    }
                ],
            },
            "context": {"sessionSummary": {"childWords": "我想先听听朋友怎么说"}},
        }

        report = generate_internal_report("小雨", [event])
        intrapersonal = next(item for item in report["dimensions"] if item["key"] == "intrapersonal")
        details = report["evidence_explanations"][0]["details"]

        self.assertIn("图片选择", intrapersonal["child_story"])
        self.assertTrue(any("活动来源：图片选择" in detail for detail in details))
        self.assertTrue(any("听完大家的话" in detail for detail in details))
        self.assertTrue(any("修改了 1 次" in detail for detail in details))


if __name__ == "__main__":
    unittest.main()
