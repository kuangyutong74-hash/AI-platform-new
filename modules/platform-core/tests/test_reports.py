import json
import re
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


def chat_event(event_id: str, words: str, topic: str = "我的新发现") -> dict:
    return {
        "id": event_id, "module": "chat", "event_type": "chat.observation-shared.v1",
        "evidence_level": "reference", "behavior_summary": "分享了一次观察或想法",
        "intelligence_candidates": ["interpersonal", "intrapersonal"],
        "raw_evidence": {"turnCount": 2, "topicKey": topic},
        "context": {"sessionSummary": {"childWords": words}},
    }


class CoreFallbackReportCopyTests(unittest.TestCase):
    """Core 兜底报告是家长端的最后一道防线，不能退回重复的泛化文案。"""

    def test_analysis_does_not_repeat_the_same_generic_sentence(self):
        events = [
            chat_event("chat-1", "我今天中午吃到了非常好吃的东西"),
            chat_event("chat-2", "我最近在折纸飞机，可好玩啦"),
            chat_event("chat-3", "我今天什么事都不用干"),
        ]
        analysis = {item["key"]: item for item in generate_internal_report("小雨", events)["dimensions"]}["intrapersonal"]["analysis"]
        sentences = [part.strip() for part in analysis.split("。") if len(part.strip()) > 12]
        self.assertEqual(len(sentences), len(set(sentences)))
        self.assertNotIn("没有保存", analysis)
        self.assertIn("我今天什么事都不用干", analysis)

    def test_prompt_echo_is_not_used_as_evidence(self):
        analysis = {item["key"]: item for item in generate_internal_report("小雨", [chat_event("chat-echo", "今天最想记住的事")])["dimensions"]}["intrapersonal"]["analysis"]
        self.assertNotIn("今天最想记住的事", analysis)
        self.assertIn("没有可复述的原话或操作细节", analysis)

    def test_cross_insights_carry_real_numbers(self):
        events = [
            {
                "id": "rotate", "module": "deep_sea", "event_type": "deep-sea.spatial-task-completed.v1",
                "evidence_level": "reference", "behavior_summary": "完成深海基地建造任务",
                "intelligence_candidates": ["logical"], "raw_evidence": {"level": 2, "adjustmentCount": 17},
                "context": {"sessionSummary": {"levelTwoReview": {"rotateCount": 17, "connected": True}}},
            },
            {
                "id": "pair", "module": "deep_sea", "event_type": "deep-sea.spatial-task-completed.v1",
                "evidence_level": "reference", "behavior_summary": "完成深海基地建造任务",
                "intelligence_candidates": ["naturalistic"], "raw_evidence": {"level": 1, "successfulPairs": 4, "totalPairs": 4},
                "context": {"sessionSummary": {"levelOneReview": {"matchedRelationships": ["双锯鱼 → 海葵"]}}},
            },
        ]
        insights = generate_internal_report("小雨", events)["cross_insights"]
        text = "".join(item["text"] for item in insights)
        self.assertIn("17 次", text)
        self.assertIn("4 组生态配对", text)
        self.assertTrue(all(item["evidence_refs"] for item in insights))

    def test_story_summaries_are_not_identical_across_sessions(self):
        def story_event(event_id: str, title: str) -> dict:
            return {
                "id": event_id, "module": "story", "event_type": "story.contribution-completed.v1",
                "evidence_level": "reference", "behavior_summary": "完成故事共创表达",
                "intelligence_candidates": ["linguistic"], "raw_evidence": {"contributionCount": 2, "storyTitle": title},
                "context": {"sessionSummary": {"storyTitle": title}},
            }
        report = generate_internal_report("小雨", [story_event("s1", "童话王国"), story_event("s2", "深海探险")])
        summaries = [item["summary"] for item in report["evidence_explanations"]]
        self.assertEqual(len(summaries), len(set(summaries)))
        self.assertTrue(all("《" in summary for summary in summaries))

    def test_report_never_contains_nested_quotes(self):
        """兜底报告同样不允许出现嵌套引号：孩子原话自带引号时外层改用「」。"""
        quoted = "我想从“一个从没去过的地方”开始"
        events = [
            {
                "id": "chat-quoted", "module": "chat", "event_type": "chat.observation-shared.v1",
                "evidence_level": "reference", "behavior_summary": "分享了一次观察或想法",
                "intelligence_candidates": ["intrapersonal"], "raw_evidence": {"turnCount": 3},
                "context": {"sessionSummary": {"childWords": quoted}},
            },
            {
                "id": "chat-activity", "module": "chat", "event_type": "chat.observation-shared.v1",
                "evidence_level": "reference", "behavior_summary": "完成了一次互动小任务",
                "intelligence_candidates": ["interpersonal"],
                "raw_evidence": {"turnCount": 1, "interactionActivities": [{"activityType": "picture_choice", "response": quoted, "revisionCount": 1}]},
                "context": {"sessionSummary": {"childWords": quoted}},
            },
            {
                "id": "story-highlight", "module": "story", "event_type": "story.contribution-completed.v1",
                "evidence_level": "reference", "behavior_summary": "完成故事共创表达",
                "intelligence_candidates": ["linguistic"],
                "raw_evidence": {"contributionCount": 2, "storyTitle": "月亮迷路了"},
                "context": {"sessionSummary": {"storyTitle": "月亮迷路了", "storySynopsis": "月亮在云里绕了三圈。", "childHighlight": quoted}},
            },
        ]

        report = generate_internal_report("小星", events)
        blob = json.dumps(report, ensure_ascii=False)

        nested = re.findall(r"“[^”]{0,80}“", blob)
        self.assertEqual(nested, [], f"报告里出现嵌套引号：{nested}")
        self.assertIn(f"「{quoted}」", blob)
    def test_session_id_alone_marks_a_completed_level(self):
        """只带 session_id、没有 session_completed 时，兜底报告同样认得出整场走完。"""
        session = "session-abc"
        events = [
            {
                "id": "level-2", "module": "deep_sea", "event_type": "deep-sea.spatial-task-completed.v1",
                "session_id": session, "evidence_level": "reference", "behavior_summary": "完成深海基地建造任务",
                "intelligence_candidates": ["spatial"], "raw_evidence": {"level": 2, "adjustmentCount": 14},
                "context": {"sessionSummary": {"levelTwoReview": {"connected": True, "rotateCount": 14}}},
            },
            {
                "id": "session-done", "module": "deep_sea", "event_type": "deep-sea.session-completed.v1",
                "session_id": session, "evidence_level": "reference", "behavior_summary": "完成深海基地三关完整重建",
                "intelligence_candidates": ["spatial"], "raw_evidence": {"completedLevels": 3, "totalLevels": 3},
                "context": {},
            },
        ]

        report = generate_internal_report("小星", events)
        spatial = next(item for item in report["dimensions"] if item["key"] == "spatial")

        self.assertEqual(len(spatial["evidence_refs"]), 1)
        self.assertIn("其中 1 条较完整", spatial["analysis"])


if __name__ == "__main__":
    unittest.main()
