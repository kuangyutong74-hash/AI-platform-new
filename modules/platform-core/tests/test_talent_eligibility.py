import json
import sqlite3
import unittest

from main import build_talent_eligibility


class TalentEligibilityTests(unittest.TestCase):
    def row(self, event_id, module, candidates, level):
        return {
            "id": event_id,
            "module": module,
            "intelligence_candidates": json.dumps(candidates),
            "evidence_level": level,
        }

    def test_normalizes_logical_and_keeps_latest_strong_reference(self):
        talents = build_talent_eligibility([
            self.row("evt-1", "story", ["linguistic", "logical_mathematical"], "strong"),
            self.row("evt-2", "career", ["logical_mathematical"], "strong"),
            self.row("evt-3", "story", ["linguistic"], "reference"),
        ])
        by_key = {item["key"]: item for item in talents}
        self.assertEqual(len(talents), 6)
        self.assertTrue(by_key["linguistic"]["eligible"])
        self.assertEqual(by_key["linguistic"]["strong_count"], 1)
        self.assertEqual(by_key["linguistic"]["reference_count"], 1)
        self.assertEqual(by_key["linguistic"]["source_modules"], ["story"])
        self.assertTrue(by_key["logical"]["eligible"])
        self.assertEqual(by_key["logical"]["strong_count"], 2)
        self.assertEqual(by_key["logical"]["recent_evidence_id"], "evt-2")


if __name__ == "__main__":
    unittest.main()
