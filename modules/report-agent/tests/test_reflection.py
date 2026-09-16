import unittest

from reflection import fallback_questions, normalize_questions, normalize_suggestions


class ReflectionQuestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dimensions = [{
            "key": "intrapersonal",
            "status": "采集行为较少",
            "analysis": "孩子在一次聊天中表达了自己的感受。",
            "evidence_brief": [{
                "evidence_ref": "chat-1",
                "module": "chat",
                "text": "孩子说出了自己的感受",
            }],
        }]

    def test_single_evidence_dimension_gets_fallback_question(self) -> None:
        questions = fallback_questions("小新", self.dimensions)

        self.assertEqual(len(questions["dimension_questions"]), 1)
        self.assertEqual(questions["dimension_questions"][0]["evidence_ref"], "chat-1")
        self.assertEqual(questions["dimension_questions"][0]["lead"], "聊聊日常表达")
        self.assertIn("告诉您", questions["dimension_questions"][0]["question"])

    def test_each_played_module_gets_its_predefined_question(self) -> None:
        dimensions = []
        for index, module in enumerate(("story", "chat", "deep_sea", "career")):
            dimensions.append({
                "key": f"dimension-{index}",
                "status": "采集行为较少",
                "analysis": "一次真实活动",
                "evidence_brief": [{"evidence_ref": f"e-{index}", "module": module, "text": "孩子完成了一次活动"}],
            })

        questions = fallback_questions("小新", dimensions)

        self.assertEqual([item["module"] for item in questions["dimension_questions"]], ["story", "chat", "deep_sea", "career"])
        self.assertEqual(len({item["question"] for item in questions["dimension_questions"]}), 4)

    def test_single_evidence_dimension_accepts_model_question(self) -> None:
        candidate = {
            "dimension_questions": [{
                "key": "intrapersonal",
                "evidence_ref": "chat-1",
                "lead": "在家看看——",
                "question": "在家里也会说出自己的感受吗？",
                "options": ["经常会", "偶尔会", "很少会", "没注意过"],
                "placeholder": "可以补充一个例子",
            }],
        }

        questions = normalize_questions(candidate, "小新", self.dimensions)

        self.assertEqual(len(questions["dimension_questions"]), 1)
        self.assertEqual(questions["dimension_questions"][0]["module"], "chat")

    def test_dimension_without_evidence_stays_ineligible(self) -> None:
        dimensions = [{"key": "logical", "status": "采集行为较少", "evidence_brief": []}]

        questions = fallback_questions("小新", dimensions)

        self.assertEqual(questions["dimension_questions"], [])

    def test_suggestion_sources_only_keep_real_answer_ids(self) -> None:
        result = normalize_suggestions({
            "family_suggestions": ["周末一起画一张故事地图。"],
            "family_suggestion_sources": [["g1", "missing", "g2"]],
        }, "小新", [
            {"question_id": "g1", "selected": "爸爸妈妈", "text": "周末一起读书"},
            {"question_id": "g2", "selected": "没注意过", "text": ""},
        ])

        self.assertEqual(result["family_suggestion_sources"], [["g1"]])

    def test_answer_based_fallback_keeps_attributions_without_model(self) -> None:
        result = normalize_suggestions({}, "小新", [
            {"question_id": "g1", "selected": "爸爸妈妈", "text": "周末一起读书"},
            {"question_id": "g2", "selected": "动手解决", "text": ""},
            {"question_id": "g3", "selected": "遇难反应", "text": ""},
        ])

        self.assertEqual(len(result["family_suggestions"]), 2)
        self.assertEqual(result["teacher_suggestions"], [])
        self.assertIn("爸爸妈妈", result["family_suggestions"][0])
        self.assertIn("拼搭", result["family_suggestions"][1])
        self.assertEqual(result["family_suggestion_sources"], [["g1"], ["g2"]])

    def test_grandparents_answer_becomes_a_natural_dimension_activity(self) -> None:
        result = normalize_suggestions({}, "小新", [
            {"question_id": "g1", "selected": "祖辈家人", "text": ""},
        ], [{"id": "g1", "category": "家庭陪伴"}], {"key": "logical"})

        self.assertIn("爷爷奶奶", result["family_suggestions"][0])
        self.assertIn("做饭", result["family_suggestions"][0])
        self.assertEqual(result["family_suggestion_sources"], [["g1"]])

    def test_parent_concern_changes_the_observation_focus(self) -> None:
        result = normalize_suggestions({}, "小新", [
            {"question_id": "g3", "selected": "遇难反应", "text": ""},
        ], [{"id": "g3", "category": "在意"}], {"key": "spatial"})

        self.assertIn("任务卡住时", result["family_suggestions"][0])
        self.assertIn("换办法、求助还是暂停", result["family_suggestions"][0])


if __name__ == "__main__":
    unittest.main()
