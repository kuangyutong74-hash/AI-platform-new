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

    def test_groups_three_deep_sea_levels_into_one_completed_activity(self):
        account = {
            "id": "child-3",
            "display_name": "小海",
            "age": 9,
            "created_at": "2026-08-01T00:00:00Z",
        }
        events = []
        for level, event_type, duration in (
            (1, "ecology_strategy", 60),
            (2, "spatial_solution", 70),
            (3, "mediation_response", 80),
        ):
            events.append({
                "id": f"sea-{level}",
                "module": "deep_sea",
                "event_type": event_type,
                "occurred_at": f"2026-08-20T08:0{level}:00Z",
                "evidence_level": "strong",
                "behavior_summary": f"完成第 {level} 关",
                "raw_evidence": {"completed": True, "duration_seconds": duration},
                "context": {"activity_id": "sea-run-1", "level": level},
            })
        events.append({
            "id": "sea-summary",
            "module": "deep_sea",
            "event_type": "deep_sea_session_completed",
            "occurred_at": "2026-08-20T08:04:00Z",
            "evidence_level": "strong",
            "behavior_summary": "完整完成深海基地重建",
            "raw_evidence": {
                "completed": True,
                "duration_seconds": 210,
                "meaningful_adjustments": 5,
                "title": "深海基地完整重建",
            },
            "context": {"activity_id": "sea-run-1"},
        })
        # 有 activity_id 但只完成两关的运行不计入完整足迹。
        for level in (1, 2):
            events.append({
                "id": f"partial-{level}",
                "module": "deep_sea",
                "event_type": "level_completed",
                "occurred_at": f"2026-08-21T08:0{level}:00Z",
                "evidence_level": "reference",
                "behavior_summary": "部分完成",
                "raw_evidence": {"completed": True, "duration_seconds": 30},
                "context": {"activity_id": "sea-run-partial", "level": level},
            })

        result = build_explorer_collection(account, events)
        highlight = next(item for item in result["works"] if item["module"] == "deep_sea")
        summary = next(item for item in result["milestones"] if item["module"] == "deep_sea")

        self.assertIn("完成 3 个任务", highlight["metric_value"])
        self.assertIn("调整 5 次", highlight["metric_value"])
        self.assertEqual(summary["usage_count"], 1)
        self.assertEqual(summary["duration_seconds"], 210)
        self.assertEqual(summary["duration_coverage"], 1.0)

    def test_selects_career_highlight_by_completion_then_active_participation(self):
        account = {
            "id": "child-4", "display_name": "小职", "age": 10,
            "created_at": "2026-08-01T00:00:00Z",
        }
        events = [
            {
                "id": "career-a", "module": "career", "event_type": "workday_process_summary",
                "occurred_at": "2026-08-20T08:00:00Z", "evidence_level": "strong",
                "behavior_summary": "完成医生体验",
                "raw_evidence": {"completed": True, "completed_stages": 3, "stage_count": 3, "interaction_count": 8},
                "context": {"activity_id": "career-run-a", "career_id": "doctor"},
            },
            {
                "id": "career-b", "module": "career", "event_type": "workday_process_summary",
                "occurred_at": "2026-08-21T08:00:00Z", "evidence_level": "strong",
                "behavior_summary": "完成教师体验",
                "raw_evidence": {"completed": True, "completed_stages": 3, "stage_count": 3, "interaction_count": 18},
                "context": {"activity_id": "career-run-b", "career_id": "teacher"},
            },
        ]

        result = build_explorer_collection(account, events)
        highlight = next(item for item in result["works"] if item["module"] == "career")
        summary = next(item for item in result["milestones"] if item["module"] == "career")

        self.assertEqual(highlight["title"], "小学教师的一天")
        self.assertIn("主动尝试 18 次", highlight["metric_value"])
        self.assertEqual(summary["usage_count"], 2)

    def test_sorts_real_instants_and_marks_partial_duration_coverage(self):
        account = {
            "id": "child-5", "display_name": "小时", "age": 8,
            "created_at": "2026-08-01T00:00:00Z",
        }
        events = [
            {
                "id": "chat-later", "module": "chat", "event_type": "narrative_evidence",
                "occurred_at": "2026-08-20T09:00:00+08:00", "evidence_level": "reference",
                "behavior_summary": "较晚完成", "raw_evidence": {"turn_count": 2},
                "context": {"activity_id": "chat-later"},
            },
            {
                "id": "chat-earlier", "module": "chat", "event_type": "narrative_evidence",
                "occurred_at": "2026-08-20T00:30:00Z", "evidence_level": "strong",
                "behavior_summary": "较早完成",
                "raw_evidence": {"turn_count": 4, "duration_seconds": 120},
                "context": {"activity_id": "chat-earlier"},
            },
        ]

        result = build_explorer_collection(account, events)
        summary = next(item for item in result["milestones"] if item["module"] == "chat")

        self.assertEqual(summary["first_used_at"], "2026-08-20T00:30:00Z")
        self.assertEqual(summary["last_used_at"], "2026-08-20T09:00:00+08:00")
        self.assertEqual(summary["duration_coverage"], 0.5)
        self.assertIn("已记录时长", summary["metric_value"])


if __name__ == "__main__":
    unittest.main()
