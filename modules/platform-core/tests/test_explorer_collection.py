import unittest

from explorer_collection import build_explorer_collection


class ExplorerCollectionTests(unittest.TestCase):
    def test_selects_module_highlights_and_starts_timeline_at_registration(self):
        account = {
            "id": "child-1",
            "display_name": "小航",
            "age": 8,
            "created_at": "2026-08-01T08:00:00+00:00",
        }
        events = [
            {
                "id": "event-1",
                "module": "story",
                "event_type": "story_completed",
                "occurred_at": "2026-08-20T08:00:00+00:00",
                "evidence_level": "strong",
                "behavior_summary": "完成了会发光的雨伞故事",
                "raw_evidence": {
                    "title": "会发光的雨伞",
                    "content": "小龙撑着雨伞走过黑夜。",
                    "child_words": "这样它就不怕黑啦。",
                },
                "context": {},
            },
            {
                "id": "event-2",
                "module": "story",
                "event_type": "story_completed",
                "occurred_at": "2026-08-22T08:00:00+00:00",
                "evidence_level": "strong",
                "behavior_summary": "完成了更长的星星城堡故事",
                "raw_evidence": {
                    "title": "星星城堡历险记",
                    "content": "很长的故事内容" * 30,
                    "duration_seconds": 720,
                },
                "context": {},
            },
            {
                "id": "event-3",
                "module": "deep_sea",
                "event_type": "level_completed",
                "occurred_at": "2026-08-23T08:00:00+00:00",
                "evidence_level": "strong",
                "behavior_summary": "快速完成珊瑚花园重建",
                "raw_evidence": {
                    "title": "珊瑚花园重建",
                    "duration_seconds": 252,
                },
                "context": {},
            },
        ]

        result = build_explorer_collection(account, events)

        self.assertEqual(result["account"]["display_name"], "小航")
        story_highlight = next(item for item in result["works"] if item["module"] == "story")
        self.assertEqual(story_highlight["title"], "星星城堡历险记")
        self.assertEqual(story_highlight["kind"], "highlight")
        self.assertIn("字", story_highlight["metric_value"])

        self.assertEqual(result["milestones"][0]["kind"], "registration")
        self.assertEqual(result["milestones"][0]["occurred_at"], account["created_at"])
        story_summary = next(item for item in result["milestones"] if item["module"] == "story")
        self.assertEqual(story_summary["usage_count"], 2)
        self.assertIn("2 次", story_summary["metric_value"])

    def test_uses_safe_fallbacks_for_sparse_evidence(self):
        result = build_explorer_collection(
            {
                "id": "child-2",
                "display_name": "小雨",
                "age": 7,
                "created_at": "2026-08-02T08:00:00+00:00",
            },
            [
                {
                    "id": "event-2",
                    "module": "chat",
                    "event_type": "curiosity_shared",
                    "occurred_at": "2026-08-21T08:00:00+00:00",
                    "evidence_level": "reference",
                    "behavior_summary": "认真说出了自己观察到的云朵变化",
                    "raw_evidence": {},
                    "context": {},
                }
            ],
        )

        self.assertEqual(result["works"][0]["title"], "倾听之洲的新发现")
        self.assertEqual(result["works"][0]["summary"], "认真说出了自己观察到的云朵变化")
        self.assertEqual(result["works"][0]["quote"], "")
        self.assertEqual(len(result["works"]), 1)
        self.assertEqual(len(result["milestones"]), 5)
        self.assertFalse(next(item for item in result["milestones"] if item["module"] == "story")["unlocked"])


if __name__ == "__main__":
    unittest.main()
