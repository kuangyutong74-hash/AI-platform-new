import unittest
from types import SimpleNamespace

from app.services.content_guard import guard_child_input, sanitize_agent_output
from app.services.llm_service import (
    LLMService, LLMServiceError, apply_empathy_keyword_fallback,
    fallback_writing_cards,
)
from app.services.story_service import build_complete_story_text
from app.prompts.story_director import build_system_prompt, should_ask_director_question


class _FakeStream:
    def __init__(self, parts):
        self.parts = parts

    def __aiter__(self):
        async def iterate():
            for part in self.parts:
                yield SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=part))]
                )
        return iterate()


def _llm_with_stream(parts):
    service = object.__new__(LLMService)

    async def create(**_kwargs):
        return _FakeStream(parts)

    service.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    service.model = "test-model"
    return service


class ContentGuardRegressionTests(unittest.TestCase):
    def test_fictional_details_in_agent_story_are_not_privacy_redacted(self):
        story_text = "小鹿叫露露，住在彩虹森林的月亮街12号。"
        self.assertEqual(sanitize_agent_output(story_text), story_text)

    def test_normal_school_story_context_is_not_privacy(self):
        for text in ("班级图书角", "整理图书角", "学校里的故事"):
            with self.subTest(text=text):
                result = guard_child_input(text)
                self.assertFalse(result.blocked)
                self.assertFalse(result.has_privacy)

    def test_explicit_private_information_is_still_blocked(self):
        samples = (
            "我家住幸福小区8栋",
            "我的电话是13812345678",
            "我在三年级2班",
            "我的学校是南开日新学校",
            "我的登录密码是abc12345",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertTrue(guard_child_input(text).blocked)

    def test_age_and_general_location_are_allowed(self):
        for text in (
            "我今年10岁",
            "我住在天津市",
            "我来自河北省石家庄市",
        ):
            with self.subTest(text=text):
                result = guard_child_input(text)
                self.assertFalse(result.blocked)
                self.assertFalse(result.has_privacy)

    def test_story_language_is_left_to_the_director(self):
        samples = (
            "我准备让桥下冒出一个会打喷嚏的小水泡，噗地炸开吓小星一跳。",
            "恶龙挥着刀冲过来，勇士打败了它。",
            "反派气得骂了一句，转身跑进恐怖森林。",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertFalse(guard_child_input(text).blocked)

    def test_agent_story_language_is_not_mechanically_rewritten(self):
        story_text = "恶龙举起刀，水泡突然炸开，吓得它转身逃跑。"
        self.assertEqual(sanitize_agent_output(story_text), story_text)


class EmpathyRecognitionRegressionTests(unittest.TestCase):
    def test_listening_apology_and_cooperation_are_recognized(self):
        text = "亮亮停下来听对方解释，发现只是拿错了零件，于是互相道歉，一起把机器修好了。"
        result = apply_empathy_keyword_fallback({
            "empathy_emotion": 0,
            "empathy_perspective": 0,
            "empathy_prosocial": 0,
            "empathy_conflict": 0,
            "dimension_evidence": {},
        }, text)
        self.assertGreater(result["empathy_perspective"], 0)
        self.assertGreater(result["empathy_prosocial"], 0)
        self.assertGreater(result["empathy_conflict"], 0)
        self.assertIn(text, result["evidence"])

    def test_existing_model_score_is_not_overwritten(self):
        result = apply_empathy_keyword_fallback({
            "empathy_emotion": 0,
            "empathy_perspective": 5,
            "empathy_prosocial": 0,
            "empathy_conflict": 0,
            "dimension_evidence": {},
        }, "他先听对方解释。")
        self.assertEqual(result["empathy_perspective"], 5)


class StoryPresentationRegressionTests(unittest.TestCase):
    def test_completed_work_is_continuous_story_not_role_dialogue(self):
        messages = [
            SimpleNamespace(role="ai", turn_number=1, content="开场。\n\n接下来呢？", ai_raw_response='{"narrative":"开场。","question":"接下来呢？"}'),
            SimpleNamespace(role="child", turn_number=2, content="让小船去月亮。", ai_raw_response=None),
            SimpleNamespace(role="ai", turn_number=2, content="小船飞向月亮。\n\n然后呢？", ai_raw_response='{"narrative":"小船飞向月亮。","question":"然后呢？"}'),
            SimpleNamespace(role="child", turn_number=3, content="最后大家平安回家。", ai_raw_response=None),
        ]
        story = build_complete_story_text(messages)
        self.assertEqual(story, "开场。\n\n小船飞向月亮。\n\n最后大家平安回家。")
        self.assertNotIn("故事导演", story)
        self.assertNotIn("接下来呢", story)

    def test_child_text_is_kept_when_an_old_ai_turn_was_saved_empty(self):
        messages = [
            SimpleNamespace(role="child", turn_number=2, content="他们一起驶向了月亮。", ai_raw_response=None),
            SimpleNamespace(role="ai", turn_number=2, content="", ai_raw_response='{"narrative":""}'),
        ]
        self.assertEqual(build_complete_story_text(messages), "他们一起驶向了月亮。")


class WritingToolboxRegressionTests(unittest.TestCase):
    def test_every_tool_returns_three_short_editable_cards_offline(self):
        for tool in ("next", "detail", "twist", "question"):
            with self.subTest(tool=tool):
                cards = fallback_writing_cards(tool, "海底城市", "泡泡")
                self.assertEqual(len(cards), 3)
                self.assertTrue(all(8 <= len(card) <= 90 for card in cards))
                self.assertTrue(all(card.startswith(("我想让", "我决定", "我准备", "我希望")) for card in cards))
                self.assertTrue(all("？" not in card and "?" not in card for card in cards))

    def test_custom_cards_keep_the_childs_requested_direction(self):
        cards = fallback_writing_cards(
            "custom", "星空", "小鹿", "更神秘一点，但不要太吓人",
        )
        self.assertEqual(len(cards), 3)
        self.assertTrue(all("更神秘一点，但不要太吓人" in card for card in cards))


class StoryStreamRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_markdown_json_fences_are_not_emitted_as_story_text(self):
        service = _llm_with_stream([
            '```json\n',
            '{"type":"narrative","text":"小船终于靠岸了。"}\n',
            '{"type":"question","text":"你觉得岸边有什么呢？"}\n',
            '{"type":"done"}\n',
            '```',
        ])
        events = [event async for event in service.generate_turn([])]
        self.assertEqual(events, [
            {"type": "narrative_chunk", "text": "小船终于靠岸了。"},
            {"type": "question", "text": "你觉得岸边有什么呢？"},
            {"type": "done"},
        ])
        self.assertNotIn("```json", "".join(str(event) for event in events))

    def test_question_schedule_is_varied_retry_stable_and_never_used_for_ending(self):
        decisions = [should_ask_director_question(7, turn) for turn in range(1, 9)]
        self.assertIn(True, decisions)
        self.assertIn(False, decisions)
        self.assertEqual(decisions, [should_ask_director_question(7, turn) for turn in range(1, 9)])
        self.assertFalse(should_ask_director_question(7, 1, force_ending=True))

    def test_director_prompt_can_pause_without_asking_a_question(self):
        prompt = build_system_prompt(ask_question=False)
        self.assertIn("本轮禁止输出 question", prompt)
        self.assertIn("本轮不要提问", prompt)

    async def test_question_event_is_filtered_when_this_turn_does_not_ask(self):
        service = _llm_with_stream([
            '{"type":"narrative","text":"小船停在发光的礁石边。"}\n',
            '{"type":"question","text":"接下来要去哪里？"}\n',
            '{"type":"done"}\n',
        ])
        events = [event async for event in service.generate_turn([], ask_question=False)]
        self.assertFalse(any(event["type"] == "question" for event in events))

    async def test_final_json_line_without_newline_is_not_dropped(self):
        service = _llm_with_stream([
            '{"type":"narrative","text":"小船终于靠岸了。"}'
        ])
        events = [event async for event in service.generate_turn([])]
        self.assertEqual(events[0], {
            "type": "narrative_chunk",
            "text": "小船终于靠岸了。",
        })
        self.assertEqual(events[-1], {"type": "done"})

    async def test_empty_provider_stream_is_reported_as_error(self):
        service = _llm_with_stream([])
        with self.assertRaisesRegex(LLMServiceError, "没有返回故事正文"):
            _ = [event async for event in service.generate_turn([])]


if __name__ == "__main__":
    unittest.main()
