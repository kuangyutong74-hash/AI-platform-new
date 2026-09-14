import unittest

from main import REPORT_ANALYSIS_VERSION, REPORT_QUESTION_VERSION, fallback_report_questions, report_has_current_reflection


class ReportReflectionCacheTests(unittest.TestCase):
    def report(self, evidence_refs, dimension_questions):
        dimensions = [{"key": f"d{index}", "evidence_refs": evidence_refs if index == 0 else []} for index in range(6)]
        return {
            "analysis_version": REPORT_ANALYSIS_VERSION,
            "dimensions": dimensions,
            "questions": {
                "question_version": REPORT_QUESTION_VERSION,
                "dimension_questions": dimension_questions,
                "global_questions": [{}, {}, {}],
            },
        }

    def test_old_empty_questions_are_regenerated_when_evidence_exists(self) -> None:
        self.assertFalse(report_has_current_reflection(self.report(["chat-1"], [])))

    def test_dimension_question_keeps_cache_valid(self) -> None:
        self.assertTrue(report_has_current_reflection(self.report(["chat-1"], [{"id": "d1"}])))

    def test_no_evidence_report_can_still_be_cached(self) -> None:
        self.assertTrue(report_has_current_reflection(self.report([], [])))

    def test_core_fallback_uses_module_specific_question(self) -> None:
        report = {"dimensions": [{"key": "linguistic", "evidence_refs": ["story-1"], "analysis": "完成故事表达"}], "evidence_explanations": []}
        events = [{"id": "story-1", "module": "story"}]

        questions = fallback_report_questions("小新", report, events)

        self.assertEqual(questions["dimension_questions"][0]["lead"], "聊聊这次故事")
        self.assertEqual(len(questions["global_questions"]), 3)

    def test_previous_generic_question_bank_is_regenerated(self) -> None:
        report = self.report(["chat-1"], [{"id": "d1"}])
        report["questions"].pop("question_version")

        self.assertFalse(report_has_current_reflection(report))


if __name__ == "__main__":
    unittest.main()
