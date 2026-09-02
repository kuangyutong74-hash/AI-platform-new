import unittest
from types import SimpleNamespace

from app.services.content_guard import guard_child_input, sanitize_agent_output
from app.services.llm_service import LLMService, LLMServiceError, apply_empathy_keyword_fallback
from app.services.story_service import build_complete_story_text


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
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertTrue(guard_child_input(text).blocked)


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


class StoryStreamRegressionTests(unittest.IsolatedAsyncioTestCase):
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
