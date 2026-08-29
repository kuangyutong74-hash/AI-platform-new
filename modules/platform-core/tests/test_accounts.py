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

    def test_v1_event_artifact_and_completion_are_profile_scoped(self):
        response = Response()
        registered = main.register_account(main.AccountRegistrationIn(username="artifact_child", display_name="小岸", age=8, password="secret77"), response)
        cookie = response.headers["set-cookie"].split("ai_bole_session=", 1)[1].split(";", 1)[0]
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="career"), cookie)
        authorization = main.exchange_module_authorization(main.LaunchCodeExchangeIn(launchCode=context["launchCode"]))["token"]
        header = f"Bearer {authorization}"
        event = main.EvidenceEnvelopeIn(schemaVersion="1.0", eventId="career-event", idempotencyKey="career-event", eventType="career.task-completed.v1", occurredAt=main.now_iso(), payload={"taskKey":"doctor","attemptCount":2,"hintCount":0,"completionSeconds":30,"adjustmentCount":1})
        saved = main.create_evidence_events_v1(main.EvidenceBatchIn(events=[event]), header)
        self.assertFalse(saved["saved"][0]["duplicate"])
        artifact = main.ArtifactIn(schemaVersion="1.0", artifactId="career-artifact", type="other", title="小医生的一天", summary="完成职业体验", sourceResourceId="career:demo", createdAt=main.now_iso())
        main.create_artifact_v1(artifact, header)
        changed = main.change_assessment_session(context["sessionId"], main.SessionStatusIn(status="completed", summary={"stages": 3}), header)
        self.assertFalse(changed["duplicate"])
        self.assertEqual(main.list_artifacts_v1(cookie)["artifacts"][0]["id"], "career-artifact")
        self.assertEqual(main.timeline_v1(cookie)["sessions"][0]["evidenceCount"], 1)
        self.assertEqual(main.read_assessment_session(context["sessionId"], cookie)["summary"], {"stages": 3})

    def test_v1_batch_is_atomic_and_invalid_transition_is_rejected(self):
        response = Response()
        main.register_account(main.AccountRegistrationIn(username="atomic_child", display_name="小舟", age=8, password="secret77"), response)
        cookie = response.headers["set-cookie"].split("ai_bole_session=", 1)[1].split(";", 1)[0]
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="career"), cookie)
        token = main.exchange_module_authorization(main.LaunchCodeExchangeIn(launchCode=context["launchCode"]))["token"]
        header = f"Bearer {token}"
        valid = main.EvidenceEnvelopeIn(schemaVersion="1.0", eventId="atomic-valid", idempotencyKey="atomic-valid", eventType="career.task-completed.v1", occurredAt=main.now_iso(), payload={"taskKey":"doctor","attemptCount":1,"hintCount":0,"completionSeconds":3,"adjustmentCount":0})
        invalid = main.EvidenceEnvelopeIn(schemaVersion="1.0", eventId="atomic-invalid", idempotencyKey="atomic-invalid", eventType="career.task-completed.v1", occurredAt=main.now_iso(), payload={"taskKey":"doctor"})
        with self.assertRaises(HTTPException) as rejected:
            main.create_evidence_events_v1(main.EvidenceBatchIn(events=[valid, invalid]), header)
        self.assertEqual(rejected.exception.status_code, 422)
        with main.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM source_events WHERE session_id=?", (context["sessionId"],)).fetchone()["n"], 0)
        main.change_assessment_session(context["sessionId"], main.SessionStatusIn(status="interrupted", reason="test"), header)
        with self.assertRaises(HTTPException) as transition:
            main.change_assessment_session(context["sessionId"], main.SessionStatusIn(status="completed"), header)
        self.assertEqual(transition.exception.status_code, 409)

    def test_legacy_backfill_is_idempotent_and_auditable(self):
        response = Response()
        main.register_account(main.AccountRegistrationIn(username="migrate_child", display_name="小林", age=8, password="secret77"), response)
        cookie = response.headers["set-cookie"].split("ai_bole_session=", 1)[1].split(";", 1)[0]
        legacy = main.create_evidence(main.EvidenceIn(module="chat", event_type="narrative_evidence", evidence_level="reference", intelligence_candidates=["linguistic"], behavior_summary="分享了一段完整的聊天观察。", raw_evidence={"turn_count": 2, "topic": "rain"}, context={"idempotency_key": "migration-legacy"}), cookie)
        with main.connect() as db:
            db.execute("DELETE FROM evidence_records WHERE source_event_id=?", (legacy["event_id"],))
            db.execute("DELETE FROM source_events WHERE id=?", (legacy["event_id"],))
            db.execute("DELETE FROM assessment_sessions WHERE id=?", (str(main.uuid.uuid5(main.uuid.NAMESPACE_URL, f"legacy-v1:{legacy['event_id']}")),))
            result = main.apply_pending_data_migrations(db, source="test")
            repeated = main.apply_pending_data_migrations(db, source="test")
        self.assertTrue(result["applied"])
        self.assertGreaterEqual(result["migrated"], 1)
        self.assertFalse(repeated["applied"])


if __name__ == "__main__":
    unittest.main()
