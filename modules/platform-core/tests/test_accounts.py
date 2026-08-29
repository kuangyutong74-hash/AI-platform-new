import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException, Response


_TEMP_DIR = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ["AI_BOLE_DB_PATH"] = str(Path(_TEMP_DIR.name) / "accounts-test.db")

import main


class AccountTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        _TEMP_DIR.cleanup()

    def test_registration_and_login_are_separate_and_profile_is_stable(self):
        registered = main.register_account(
            main.AccountRegistrationIn(
                username="Little_Star",
                display_name="小星",
                age=8,
                password="secret88",
            ),
            Response(),
        )
        self.assertTrue(registered["created"])
        self.assertEqual(registered["account"]["username"], "little_star")
        self.assertEqual(registered["account"]["display_name"], "小星")
        with main.connect() as db:
            profile = db.execute("SELECT * FROM child_profiles WHERE account_id=?", (registered["account"]["id"],)).fetchone()
        self.assertIsNotNone(profile)

        logged_in = main.create_session(
            main.AccountCredentialsIn(username="LITTLE_STAR", password="secret88"),
            Response(),
        )
        self.assertFalse(logged_in["created"])
        self.assertEqual(logged_in["account"]["display_name"], "小星")
        self.assertEqual(logged_in["account"]["age"], 8)

    def test_duplicate_registration_and_wrong_password_are_rejected(self):
        payload = main.AccountRegistrationIn(
            username="moon_child",
            display_name="小月",
            age=9,
            password="planet99",
        )
        main.register_account(payload, Response())
        with self.assertRaises(HTTPException) as duplicate:
            main.register_account(payload, Response())
        self.assertEqual(duplicate.exception.status_code, 409)

        with self.assertRaises(HTTPException) as wrong_password:
            main.create_session(
                main.AccountCredentialsIn(username="moon_child", password="wrong999"),
                Response(),
            )
        self.assertEqual(wrong_password.exception.status_code, 401)

    def test_v1_standard_evidence_is_reportable_and_linkable(self):
        registered = main.register_account(main.AccountRegistrationIn(username="v1_child", display_name="小河", age=9, password="secret99"), Response())
        with main.connect() as db:
            profile = main.profile_for_account(db, registered["account"]["id"])
            manifest = main.module_manifest("career")
            db.execute("INSERT INTO assessment_sessions (id,child_profile_id,module_id,module_version,status,created_at) VALUES (?,?,?,?,?,?)", ("session-v1", profile["id"], "career", manifest["version"], "completed", main.now_iso()))
            db.execute("INSERT INTO source_events (id,session_id,idempotency_key,event_type,schema_version,payload_json,occurred_at,created_at) VALUES (?,?,?,?,?,?,?,?)", ("source-v1", "session-v1", "key-v1", "career.task-completed.v1", "1.0", '{"taskKey":"doctor","attemptCount":2,"hintCount":0,"completionSeconds":30,"adjustmentCount":1}', main.now_iso(), main.now_iso()))
            db.execute("INSERT INTO evidence_records (id,source_event_id,evidence_level,constructs_json,behavior_summary,policy_version,construct_registry_version,derived_at) VALUES (?,?,?,?,?,?,?,?)", ("evidence-v1", "source-v1", "strong", '["problem_solving.planning"]', "完成职业任务并做出调整", "1.0", "1.0", main.now_iso()))
            events, evidence_ids = main.standard_events_for_report(db, profile["id"])
        self.assertEqual(events[0]["event_type"], "workday_process_summary")
        self.assertEqual(events[0]["intelligence_candidates"], ["logical"])
        self.assertEqual(evidence_ids, ["evidence-v1"])

    def test_new_account_can_create_and_exchange_v1_session_once(self):
        response = Response()
        registered = main.register_account(main.AccountRegistrationIn(username="launch_child", display_name="小帆", age=9, password="secret77"), response)
        token = response.headers["set-cookie"].split("ai_bole_session=", 1)[1].split(";", 1)[0]
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="career"), token)
        self.assertTrue(context["launchCode"])
        exchanged = main.exchange_module_authorization(main.LaunchCodeExchangeIn(launchCode=context["launchCode"]))
        self.assertTrue(exchanged["token"])
        with self.assertRaises(HTTPException) as repeated:
            main.exchange_module_authorization(main.LaunchCodeExchangeIn(launchCode=context["launchCode"]))
        self.assertEqual(repeated.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
