import unittest

from main import EvidenceEvent, RuleAnalyzer, apply_dimension_expansion, child_story_for_event, child_story_for_events, normalize_report


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
        self.assertIn("我想学会更快地跑步", story)
        self.assertNotIn("进入时选择", story)
        self.assertNotIn("自然观察", story)

    def test_rule_output_uses_canonical_key_and_teacher(self):
        result = RuleAnalyzer().analyze([event("ev-1", "logical_mathematical")])
        keys = {item["key"] for item in result["dimensions"]}
        self.assertIn("logical", keys)
        self.assertNotIn("logical_mathematical", keys)
        self.assertIn("teacher", result["recommendations"])
        self.assertTrue(result["recommendations"]["family"])

    def test_star_story_aggregates_all_story_sessions(self):
        events = [
            EvidenceEvent(
                id=f"story-{index}", module="story", event_type="story.contribution-completed.v1",
                occurred_at=f"2026-09-0{index}T08:00:00Z", behavior_summary="完成故事共创表达",
                intelligence_candidates=["linguistic"], raw_evidence={"contributionCount": count},
                context={"artifacts": [{"title": title, "summary": "完成故事"}]},
            )
            for index, count, title in [(1, 3, "星星邮差"), (2, 5, "海底朋友")]
        ]
        story = child_story_for_events(events)
        self.assertIn("2 次故事共创", story)
        self.assertIn("8 个故事片段", story)
        self.assertIn("《星星邮差》", story)
        self.assertIn("《海底朋友》", story)

    def test_star_story_aggregates_all_chat_sessions(self):
        events = [
            EvidenceEvent(
                id=f"chat-{index}", module="chat", event_type="chat.observation-shared.v1",
                occurred_at=f"2026-09-0{index}T08:00:00Z", behavior_summary="分享了一次观察或想法",
                intelligence_candidates=["interpersonal"],
                raw_evidence={"turnCount": turns, "topicKey": topic, "childTurns": [{"turn": 1, "text": words}]},
                context={"sessionSummary": {}, "artifacts": []},
            )
            for index, turns, topic, words in [(1, 4, "学校", "我和同学一起画画"), (2, 6, "朋友", "我们轮流讲故事")]
        ]
        story = child_story_for_events(events)
        self.assertIn("2 次聊天", story)
        self.assertIn("学校", story)
        self.assertIn("朋友", story)
        self.assertIn("一起画画", story)
        self.assertIn("轮流讲故事", story)

    def test_career_story_uses_chinese_name_and_reviews_tasks(self):
        career_event = EvidenceEvent(
            id="career-1", module="career", event_type="career.task-completed.v1",
            occurred_at="2026-09-07T08:00:00Z", behavior_summary="完成职业任务并留下过程记录",
            intelligence_candidates=["intrapersonal"],
            raw_evidence={"taskKey": "animal_caretaker", "attemptCount": 13, "adjustmentCount": 0},
            context={"sessionSummary": {}, "artifacts": [{"title": "动物保护员的一天", "summary": ""}]},
        )
        story = child_story_for_event(career_event)
        self.assertIn("动物保护员", story)
        self.assertIn("晨间巡护打卡", story)
        self.assertIn("动物救助优先级", story)
        self.assertIn("动物健康检查", story)
        self.assertNotIn("animal_caretaker", story)
        self.assertNotIn("调整", story)

    def test_naturalistic_story_reviews_level_one_relationships(self):
        event = EvidenceEvent(
            id="deep-1", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
            occurred_at="2026-09-07T08:00:00Z", behavior_summary="完成生物配对",
            intelligence_candidates=["naturalistic"],
            raw_evidence={"level": 1, "successfulPairs": 4, "totalPairs": 4, "checkAttempts": 2},
            context={"sessionSummary": {"levelOneReview": {"matchedRelationships": ["双锯鱼 → 海葵", "枪虾 ⇋ 鰕虎鱼"]}}},
        )
        story = child_story_for_event(event)
        self.assertIn("第一关", story)
        self.assertIn("双锯鱼 → 海葵", story)
        self.assertIn("枪虾 ⇋ 鰕虎鱼", story)
        self.assertIn("栖息地和共生关系", story)

    def test_partner_story_includes_level_three_negotiation(self):
        chat = EvidenceEvent(
            id="chat-partner", module="chat", event_type="chat.observation-shared.v1",
            occurred_at="2026-09-07T08:00:00Z", behavior_summary="聊天",
            intelligence_candidates=["interpersonal"], raw_evidence={"turnCount": 3},
            context={"sessionSummary": {"childWords": "我很期待见到同学"}},
        )
        negotiation = EvidenceEvent(
            id="deep-partner", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
            occurred_at="2026-09-07T09:00:00Z", behavior_summary="协调分歧",
            intelligence_candidates=["interpersonal", "linguistic"], raw_evidence={"level": 3},
            context={"sessionSummary": {"levelThreeReview": {"solutionSummary": "先安静阅读，再留出练舞时间", "childUtterances": ["我听出来你们都有自己的需要，我们轮流使用阳台吧"]}}},
        )
        story = child_story_for_events([chat, negotiation])
        self.assertIn("聊天交流", story)
        self.assertIn("议事厅协商", story)
        self.assertIn("先安静阅读", story)
        self.assertIn("我们轮流使用阳台吧", story)

    def test_level_three_adult_dimensions_have_different_focus(self):
        event = EvidenceEvent(
            id="deep-dimensions", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
            occurred_at="2026-09-07T09:00:00Z", behavior_summary="协调分歧",
            intelligence_candidates=["interpersonal", "linguistic"], raw_evidence={"level": 3},
            context={"sessionSummary": {"levelThreeReview": {"solutionSummary": "上午安静阅读，下午练舞", "childUtterances": ["我听出来你们都想使用阳台，我们分时段试试吧"]}}},
        )
        dimensions = {item["key"]: item for item in RuleAnalyzer().analyze([event])["dimensions"]}
        linguistic = dimensions["linguistic"]["analysis"]
        interpersonal = dimensions["interpersonal"]["analysis"]
        self.assertIn("我听出来你们", linguistic)
        self.assertNotIn("上午安静阅读", linguistic)
        self.assertIn("上午安静阅读", interpersonal)
        self.assertNotIn("我听出来你们", interpersonal)
        self.assertNotEqual(linguistic, interpersonal)

    def test_chat_evidence_has_distinct_interpersonal_and_intrapersonal_readings(self):
        event = EvidenceEvent(
            id="chat-dimensions", module="chat", event_type="chat.observation-shared.v1",
            occurred_at="2026-09-07T09:00:00Z", behavior_summary="分享了一次观察或想法",
            intelligence_candidates=["interpersonal", "intrapersonal"], raw_evidence={"turnCount": 3},
            context={"sessionSummary": {"childWords": "开学能见到同学我很开心，也有一点担心跟不上大家。"}},
        )
        dimensions = {item["key"]: item for item in RuleAnalyzer().analyze([event])["dimensions"]}
        interpersonal = dimensions["interpersonal"]["analysis"]
        intrapersonal = dimensions["intrapersonal"]["analysis"]
        self.assertIn("同学", interpersonal)
        self.assertIn("对他人和关系", interpersonal)
        self.assertIn("自己的感受", intrapersonal)
        self.assertNotEqual(interpersonal, intrapersonal)

    def test_level_three_generic_model_copy_cannot_override_specific_report(self):
        event = EvidenceEvent(
            id="deep-locked", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
            occurred_at="2026-09-07T09:00:00Z", behavior_summary="完成深海基地建造任务",
            intelligence_candidates=["interpersonal", "linguistic"],
            raw_evidence={"level": 3, "completionSeconds": 52, "adjustmentCount": 0},
            context={"sessionSummary": {"levelThreeReview": {"solutionSummary": "分时使用阳台", "childUtterances": ["我们可以轮流使用"]}}},
        )
        candidate = {
            "dimensions": [
                {"key": "linguistic", "analysis": "相同的通用描述", "evidence_refs": ["deep-locked"]},
                {"key": "interpersonal", "analysis": "相同的通用描述", "evidence_refs": ["deep-locked"]},
            ],
            "evidence_explanations": [{"evidence_ref": "deep-locked", "title": "旧标题", "summary": "用时52秒，无调整", "details": ["调整0次"]}],
        }
        report = normalize_report(candidate, [event])
        dimensions = {item["key"]: item for item in report["dimensions"]}
        self.assertIn("我们可以轮流使用", dimensions["linguistic"]["analysis"])
        self.assertIn("分时使用阳台", dimensions["interpersonal"]["analysis"])
        self.assertNotEqual(dimensions["linguistic"]["analysis"], dimensions["interpersonal"]["analysis"])
        explanation = report["evidence_explanations"][0]
        self.assertEqual(explanation["title"], "深海基地第三关：海洋议事厅")
        self.assertNotIn("调整0次", str(explanation))
        expanded = apply_dimension_expansion(report, {"dimensions": [{"key": "linguistic", "facts": ["覆盖"], "interpretations": ["覆盖"], "limits": ["覆盖"]}]}, [event])
        self.assertIn("我们可以轮流使用", next(item for item in expanded["dimensions"] if item["key"] == "linguistic")["analysis"])

    def test_story_feedback_contains_plot_outline(self):
        event = EvidenceEvent(
            id="story-plot", module="story", event_type="story.contribution-completed.v1",
            occurred_at="2026-09-07T08:00:00Z", behavior_summary="完成故事共创",
            intelligence_candidates=["linguistic"], raw_evidence={"contributionCount": 3, "storyTitle": "月亮邮差"},
            context={"sessionSummary": {"storyTitle": "月亮邮差", "storySynopsis": "小狐狸乘纸飞机寻找丢失的月光，最后和猫头鹰一起把月光送回村庄。", "childHighlight": "月光像一条银色的小河，从纸飞机的翅膀上流下来。", "childIdeas": ["让猫头鹰来帮忙"]}},
        )
        story = child_story_for_event(event)
        self.assertIn("月亮邮差", story)
        self.assertIn("小狐狸乘纸飞机", story)
        self.assertIn("月光像一条银色的小河", story)
        self.assertIn("精彩的一句", story)

    def test_normalizer_removes_fabricated_references(self):
        candidate = {"dimensions": [{"key": "logical", "analysis": "留意解题过程", "adult_observation": "六个维度都一样的通用观察", "evidence_refs": ["fake", "ev-1"]}], "cross_insights": [{"text": "会反复尝试", "evidence_refs": ["fake", "ev-1"]}], "recommendations": {"family": "一起复盘", "teacher": "提供多种材料"}}
        result = normalize_report(candidate, [event("ev-1", "logical")])
        logical = next(item for item in result["dimensions"] if item["key"] == "logical")
        self.assertEqual(logical["evidence_refs"], ["ev-1"])
        self.assertEqual(result["cross_insights"][0]["evidence_refs"], ["ev-1"])
        self.assertNotIn("fake", str(result))
        self.assertNotIn("ev-1", result["recommendations"]["family"])
        self.assertNotIn("六个维度都一样", logical["adult_observation"])
        self.assertIn("预测", logical["adult_observation"])

    def test_each_dimension_has_distinct_adult_observations(self):
        dimensions = ["linguistic", "logical", "spatial", "interpersonal", "intrapersonal", "naturalistic"]
        events = [event(f"ev-{key}", key) for key in dimensions]

        report = RuleAnalyzer().analyze(events)
        observations = {item["key"]: item["adult_observation"] for item in report["dimensions"]}

        self.assertEqual(len(set(observations.values())), 6)
        self.assertIn("人物、起因和结果", observations["linguistic"])
        self.assertIn("位置、方向和连接", observations["spatial"])
        self.assertIn("每个人想要什么", observations["interpersonal"])

    def test_missing_deep_sea_level_never_renders_none(self):
        incomplete = EvidenceEvent(
            id="deep-missing-level", module="deep_sea", event_type="deep-sea.session-completed.v1",
            occurred_at="2026-09-14T08:00:00Z", behavior_summary="完成深海基地任务",
            intelligence_candidates=["logical"], raw_evidence={}, context={"sessionSummary": {}},
        )

        logical = next(item for item in RuleAnalyzer().analyze([incomplete])["dimensions"] if item["key"] == "logical")

        self.assertNotIn("None", logical["adult_observation"])
        self.assertIn("这次深海任务", logical["adult_observation"])


if __name__ == "__main__":
    unittest.main()
