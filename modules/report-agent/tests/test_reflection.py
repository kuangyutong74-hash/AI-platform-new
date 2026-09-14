import unittest

from reflection import fallback_questions, normalize_questions


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


if __name__ == "__main__":
    unittest.main()
