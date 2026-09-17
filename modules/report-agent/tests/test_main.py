import json
import re
import unittest

from main import EvidenceEvent, RuleAnalyzer, apply_dimension_expansion, child_story_for_event, child_story_for_events, dimension_event_story, normalize_report


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
        self.assertIn("回应他人", interpersonal)
        self.assertIn("自己的感受", intrapersonal)
        self.assertNotEqual(interpersonal, intrapersonal)

    def test_dimension_analysis_never_repeats_the_same_sentence(self):
        """同维度多条记录过去会被写成同一句泛化文案，这里锁定不再复读。"""
        events = [
            EvidenceEvent(
                id=f"chat-{index}", module="chat", event_type="chat.observation-shared.v1",
                occurred_at=f"2026-09-0{index}T09:00:00Z", behavior_summary="分享了一次观察或想法",
                intelligence_candidates=["intrapersonal"], raw_evidence={"turnCount": 2, "topicKey": "运动"},
                context={"sessionSummary": {"childWords": words}},
            )
            for index, words in [(1, "我今天中午吃到了非常好吃的东西"), (2, "我最近在折纸飞机，可好玩啦"), (3, "我一般暑假一周游两次")]
        ]
        analysis = {item["key"]: item for item in RuleAnalyzer().analyze(events)["dimensions"]}["intrapersonal"]["analysis"]
        sentences = [part.strip() for part in analysis.split("。") if len(part.strip()) > 12]
        self.assertEqual(len(sentences), len(set(sentences)))
        self.assertNotIn("没有保存", analysis)

    def test_prompt_echo_and_short_fragments_are_not_evidence(self):
        """入口提示语和口头碎片只能说明点开过聊天，不能当成孩子的表达。"""
        events = [
            EvidenceEvent(
                id="echo", module="chat", event_type="chat.observation-shared.v1",
                occurred_at="2026-09-16T09:00:00Z", behavior_summary="分享了一次观察或想法",
                intelligence_candidates=["intrapersonal"], raw_evidence={"turnCount": 1, "topicKey": "我的新发现"},
                context={"sessionSummary": {"childWords": "今天最想记住的事"}},
            ),
            EvidenceEvent(
                id="fragment", module="chat", event_type="chat.observation-shared.v1",
                occurred_at="2026-09-15T09:00:00Z", behavior_summary="分享了一次观察或想法",
                intelligence_candidates=["intrapersonal"], raw_evidence={"turnCount": 1, "topicKey": "运动"},
                context={"sessionSummary": {"childWords": "游泳"}},
            ),
        ]
        analysis = {item["key"]: item for item in RuleAnalyzer().analyze(events)["dimensions"]}["intrapersonal"]["analysis"]
        self.assertNotIn("今天最想记住的事", analysis)
        self.assertIn("没有可复述的原话或操作细节", analysis)

    def test_tokenized_child_words_are_restored_before_quoting(self):
        """语音识别的逐词空格和句首悬空虚词要还原成正常句子。"""
        event = EvidenceEvent(
            id="tokenized", module="chat", event_type="chat.observation-shared.v1",
            occurred_at="2026-09-02T09:00:00Z", behavior_summary="分享了一次观察或想法",
            intelligence_candidates=["intrapersonal"], raw_evidence={"turnCount": 3, "topicKey": "我的新发现"},
            context={"sessionSummary": {"childWords": "的 我 今天 什么 事 都 不用 干"}},
        )
        analysis = {item["key"]: item for item in RuleAnalyzer().analyze([event])["dimensions"]}["intrapersonal"]["analysis"]
        self.assertIn("“我今天什么事都不用干”", analysis)

    def test_long_synopsis_is_clipped_on_a_sentence_boundary(self):
        """故事梗概不能截到半句话，也不能留下未闭合的引号。"""
        synopsis = (
            "舷窗外，蓝白相间的地球渐渐缩小成一颗弹珠。小Q坐在“萤火号”飞船的驾驶舱里，金属手指轻轻搭在操控板上。"
            "它刚刚把飞船调成自动驾驶，准备前往木星的第二颗卫星——欧罗巴，去检查那里新发现的冰下信号。"
            "小Q习惯性地整理数据，小声嘀咕：“起飞时间是标准时07:12:33，比计划晚了0.4秒。”"
        )
        event = EvidenceEvent(
            id="long-story", module="story", event_type="story.contribution-completed.v1",
            occurred_at="2026-09-03T09:00:00Z", behavior_summary="完成故事共创表达",
            intelligence_candidates=["linguistic"], raw_evidence={"contributionCount": 5, "storyTitle": "小Q的星空探险"},
            context={"sessionSummary": {"storyTitle": "小Q的星空探险", "storySynopsis": synopsis}},
        )
        analysis = {item["key"]: item for item in RuleAnalyzer().analyze([event])["dimensions"]}["linguistic"]["analysis"]
        # 引号必须成对，且截断点落在句末标点上，不能停在半句话或未闭合的引语里。
        self.assertEqual(analysis.count("“"), analysis.count("”"))
        self.assertNotIn("小声嘀咕：“起飞时间是标准", analysis)
        self.assertIn("情节创作，故事讲到", analysis)
        self.assertRegex(analysis, r"故事讲到[^。]*。")

    def test_cross_insights_are_anchored_in_real_numbers(self):
        """综合观察要有可复核的结论，而不是一句通用说明。"""
        events = [
            EvidenceEvent(
                id="rotate", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
                occurred_at="2026-09-07T09:00:00Z", behavior_summary="完成深海基地建造任务",
                intelligence_candidates=["logical"], raw_evidence={"level": 2, "adjustmentCount": 14, "completionSeconds": 197},
                context={"sessionSummary": {"levelTwoReview": {"rotateCount": 14, "connected": True}}},
            ),
            EvidenceEvent(
                id="pair", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
                occurred_at="2026-09-07T09:05:00Z", behavior_summary="完成深海基地建造任务",
                intelligence_candidates=["naturalistic"], raw_evidence={"level": 1, "successfulPairs": 4, "totalPairs": 4},
                context={"sessionSummary": {"levelOneReview": {"matchedRelationships": ["双锯鱼 → 海葵"]}}},
            ),
        ]
        insights = RuleAnalyzer().analyze(events)["cross_insights"]
        text = "".join(item["text"] for item in insights)
        self.assertIn("14 次", text)
        self.assertIn("4 组生态配对", text)
        self.assertTrue(all(item["evidence_refs"] for item in insights))

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
            id="deep-missing-level", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
            occurred_at="2026-09-14T08:00:00Z", behavior_summary="完成深海基地任务",
            intelligence_candidates=["logical"], raw_evidence={"level": 2}, context={"sessionSummary": {}},
        )

        logical = next(item for item in RuleAnalyzer().analyze([incomplete])["dimensions"] if item["key"] == "logical")

        self.assertNotIn("None", logical["analysis"])
        self.assertNotIn("None", logical["adult_observation"])
        # 观察任务要落在这一次真实发生的关卡上，而不是一句通用说明。
        self.assertIn("洋流电网", logical["adult_observation"])

    def test_deep_sea_without_level_falls_back_to_the_module_name(self):
        unknown = EvidenceEvent(
            id="deep-unknown-level", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
            occurred_at="2026-09-14T08:00:00Z", behavior_summary="完成深海基地任务",
            intelligence_candidates=["logical"], raw_evidence={}, context={"sessionSummary": {}},
        )

        logical = next(item for item in RuleAnalyzer().analyze([unknown])["dimensions"] if item["key"] == "logical")

        self.assertNotIn("None", logical["adult_observation"])
        self.assertIn("这次深海任务", logical["adult_observation"])

    def test_completed_deep_sea_summary_is_not_dimension_evidence(self):
        """完整通关记录是三个关卡的合并摘要，不再单独算进任一维度。"""
        summary = EvidenceEvent(
            id="deep-summary", module="deep_sea", event_type="deep-sea.session-completed.v1",
            occurred_at="2026-09-14T08:10:00Z", behavior_summary="完成深海基地三关完整重建",
            intelligence_candidates=["logical", "spatial"],
            raw_evidence={"completedLevels": 3, "totalLevels": 3, "adjustmentCount": 14},
            context={"sessionSummary": {}},
        )

        report = RuleAnalyzer().analyze([summary])

        for dimension in report["dimensions"]:
            self.assertEqual(dimension["evidence_refs"], [], dimension["key"])
        cited = [ref for insight in report["cross_insights"] for ref in insight["evidence_refs"]]
        self.assertNotIn("deep-summary", cited)

    def test_level_record_strength_follows_the_whole_session(self):
        """单关记录只有整场走完才算留下完整过程，口径与家长端卡片标签一致。"""
        def analysis_for(completed: bool) -> str:
            level = EvidenceEvent(
                id="level-1", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
                occurred_at="2026-09-14T08:00:00Z", behavior_summary="完成深海基地建造任务",
                intelligence_candidates=["spatial"], session_completed=completed,
                raw_evidence={"level": 1, "successfulPairs": 4, "totalPairs": 4}, context={"sessionSummary": {}},
            )
            report = RuleAnalyzer().analyze([level])
            return next(item for item in report["dimensions"] if item["key"] == "spatial")["analysis"]

        self.assertIn("其中 0 条较完整", analysis_for(False))
        self.assertIn("其中 1 条较完整", analysis_for(True))

    def test_child_quote_with_inner_quotes_avoids_nesting(self):
        """原话自带引号时外层改用「」，家长不会读到嵌套引号。"""
        chat = EvidenceEvent(
            id="ev-nested", module="chat", event_type="chat.observation-shared.v1",
            occurred_at="2026-09-17T05:42:00Z", behavior_summary="分享了一次观察或想法",
            intelligence_candidates=["intrapersonal"], raw_evidence={"turnCount": 2},
            context={"sessionSummary": {"childWords": "我想从“一个从没去过的地方”开始"}},
        )

        text = dimension_event_story(chat, "intrapersonal")

        self.assertIn("「我想从“一个从没去过的地方”开始」", text)
        self.assertNotIn("“我想从“", text)

    def test_strong_count_only_covers_records_that_write_something(self):
        """没有为某维度写下内容的记录不能算成“较完整”，否则数字会和页面卡片对不上。"""
        level_three = EvidenceEvent(
            id="level-3", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
            occurred_at="2026-09-14T08:05:00Z", behavior_summary="完成深海基地建造任务",
            intelligence_candidates=["linguistic"], session_completed=True,
            raw_evidence={"level": 3}, context={"sessionSummary": {"levelThreeReview": {}}},
        )
        story = EvidenceEvent(
            id="story-1", module="story", event_type="story.contribution-completed.v1",
            occurred_at="2026-09-14T08:20:00Z", behavior_summary="完成故事共创表达",
            intelligence_candidates=["linguistic"],
            raw_evidence={"contributionCount": 2, "storyTitle": "小Q的星空探险"},
            context={"sessionSummary": {"storyTitle": "小Q的星空探险", "storySynopsis": "小Q在舱里检查仪表。"}},
        )

        linguistic = next(item for item in RuleAnalyzer().analyze([level_three, story])["dimensions"] if item["key"] == "linguistic")

        # 记录仍要登记（家长要知道孩子参加过），但不算“较完整”。
        self.assertEqual(len(linguistic["evidence_refs"]), 2)
        self.assertIn("其中 0 条较完整", linguistic["analysis"])

    def test_session_id_alone_marks_a_completed_level(self):
        """调用方只给 session_id、没给 session_completed 时，仍能认出整场已走完。

        旧版核心服务不会回填 session_completed，只靠会话号也要得到同样的判定，
        否则家长端看到的“较完整”条数会随核心服务版本变化。
        """
        session = "session-abc"
        level_two = EvidenceEvent(
            id="level-2", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
            session_id=session, occurred_at="2026-09-14T08:05:00Z", behavior_summary="完成深海基地建造任务",
            intelligence_candidates=["spatial"], raw_evidence={"level": 2, "adjustmentCount": 14},
            context={"sessionSummary": {"levelTwoReview": {"connected": True, "rotateCount": 14}}},
        )
        session_done = EvidenceEvent(
            id="session-done", module="deep_sea", event_type="deep-sea.session-completed.v1",
            session_id=session, occurred_at="2026-09-14T08:30:00Z", behavior_summary="完成深海基地三关完整重建",
            intelligence_candidates=["spatial"], raw_evidence={"completedLevels": 3, "totalLevels": 3}, context={},
        )

        spatial = next(item for item in RuleAnalyzer().analyze([level_two, session_done])["dimensions"] if item["key"] == "spatial")

        # 合并摘要本身不出卡片，但单关记录因此被标成“较完整”。
        self.assertEqual(len(spatial["evidence_refs"]), 1)
        self.assertIn("其中 1 条较完整", spatial["analysis"])

    def test_report_never_contains_nested_quotes(self):
        """孩子原话自带引号时，整份报告的任何位置都不能出现嵌套引号。

        家长端最刺眼的问题就是读到 “我想从“一个从没去过的地方”开始”。
        这里一次性覆盖维度分析、孩子的故事、证据说明和证据明细四条渲染路径。
        """
        quoted = "我想从“一个从没去过的地方”开始"
        events = [
            EvidenceEvent(
                id="chat-quoted", module="chat", event_type="chat.observation-shared.v1",
                occurred_at="2026-09-17T05:42:00Z", behavior_summary="分享了一次观察或想法",
                intelligence_candidates=["intrapersonal"], raw_evidence={"turnCount": 3},
                context={"sessionSummary": {"childWords": quoted}},
            ),
            EvidenceEvent(
                id="chat-activity", module="chat", event_type="chat.observation-shared.v1",
                occurred_at="2026-09-17T06:05:00Z", behavior_summary="完成了一次互动小任务",
                intelligence_candidates=["interpersonal"],
                raw_evidence={"turnCount": 1, "interactionActivities": [{"activityType": "picture_choice", "response": quoted, "revisionCount": 1}]},
                context={"sessionSummary": {"childWords": quoted}},
            ),
            EvidenceEvent(
                id="story-highlight", module="story", event_type="story.contribution-completed.v1",
                occurred_at="2026-09-17T06:30:00Z", behavior_summary="完成故事共创表达",
                intelligence_candidates=["linguistic"],
                raw_evidence={"contributionCount": 2, "storyTitle": "月亮迷路了"},
                context={"sessionSummary": {"storyTitle": "月亮迷路了", "storySynopsis": "月亮在云里绕了三圈。", "childHighlight": quoted, "childIdeas": [quoted]}},
            ),
            EvidenceEvent(
                id="deep-sea-mediation", module="deep_sea", event_type="deep-sea.spatial-task-completed.v1",
                occurred_at="2026-09-17T07:10:00Z", behavior_summary="完成海洋议事厅协商",
                intelligence_candidates=["interpersonal"], session_completed=True,
                raw_evidence={"level": 3},
                context={"sessionSummary": {"levelThreeReview": {"solutionSummary": "轮流先说各自的需要。", "childUtterances": [quoted]}}},
            ),
        ]

        report = RuleAnalyzer().analyze(events)
        blob = json.dumps(report, ensure_ascii=False)

        nested = re.findall(r"“[^”]{0,80}“", blob)
        self.assertEqual(nested, [], f"报告里出现嵌套引号：{nested}")
        # 自带引号的原话应当改用「」包住，内容本身保持原样。
        self.assertIn(f"「{quoted}」", blob)


if __name__ == "__main__":
    unittest.main()
