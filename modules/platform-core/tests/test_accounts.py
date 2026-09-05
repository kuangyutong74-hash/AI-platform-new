import os
import base64
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path

from fastapi import HTTPException, Response


_TEMP_DIR = tempfile.TemporaryDirectory()
os.environ["AI_BOLE_DB_PATH"] = str(Path(_TEMP_DIR.name) / "accounts-test.db")

import main


def session_cookie(response: Response) -> str:
    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])
    return cookies[main.COOKIE_NAME].value


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

    def test_adult_can_bind_and_switch_only_existing_students(self):
        child_response = Response()
        child = main.register_account(main.AccountRegistrationIn(
            username=None, display_name="小舟", age=8, password="child888",
            role="student",
        ), child_response)["account"]
        self.assertRegex(child["username"], r"^s\d{8}$")

        adult_response = Response()
        adult = main.register_account(main.AccountRegistrationIn(
            username=None, display_name="舟舟妈妈", password="adult888",
            role="adult", adult_kind="parent",
        ), adult_response)["account"]
        adult_cookie = session_cookie(adult_response)
        self.assertRegex(adult["username"], r"^a\d{8}$")

        linked = main.bind_student(main.StudentLinkIn(username=child["username"]), adult_cookie)
        self.assertEqual(linked["student"]["id"], child["id"])
        self.assertEqual(linked["selected_student"]["id"], child["id"])
        self.assertEqual(len(linked["students"]), 1)
        selected = main.select_student(main.StudentContextIn(student_id=child["id"]), adult_cookie)
        self.assertEqual(selected["selected_student"]["display_name"], "小舟")
        profile = main.account_me(adult_cookie)
        self.assertEqual(profile["account"]["role"], "adult")
        self.assertEqual(profile["selected_student"]["id"], child["id"])

    def test_adult_can_register_without_parent_or_teacher_kind(self):
        adult_response = Response()
        registered = main.register_account(main.AccountRegistrationIn(
            username="observer_account", display_name="测试观察员", password="adult888",
            role="adult",
        ), adult_response)

        self.assertEqual(registered["account"]["role"], "adult")
        self.assertIsNone(registered["account"]["adult_kind"])
        session = main.account_me(session_cookie(adult_response))
        self.assertEqual(session["students"], [])
        self.assertIsNone(session["selected_student"])

    def test_adult_reads_selected_students_v1_data_but_cannot_launch_modules(self):
        child_response = Response()
        child = main.register_account(main.AccountRegistrationIn(
            username="scope_child", display_name="小域", age=9, password="child888",
            role="student",
        ), child_response)["account"]
        child_cookie = session_cookie(child_response)
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="story"), child_cookie)
        token = main.exchange_module_authorization(
            main.LaunchCodeExchangeIn(launchCode=context["launchCode"])
        )["token"]
        main.create_artifact_v1(main.ArtifactIn(
            schemaVersion="1.0", artifactId="scope-story", type="story", title="作用域故事",
            summary="只属于当前学生的作品", createdAt=main.now_iso(),
        ), f"Bearer {token}")

        adult_response = Response()
        main.register_account(main.AccountRegistrationIn(
            username="scope_adult", display_name="观察者", password="adult888", role="adult",
        ), adult_response)
        adult_cookie = session_cookie(adult_response)
        main.bind_student(main.StudentLinkIn(username=child["username"]), adult_cookie)

        artifacts = main.list_artifacts_v1(adult_cookie)["artifacts"]
        self.assertEqual(artifacts[0]["id"], "scope-story")
        with self.assertRaises(HTTPException) as forbidden:
            main.create_assessment_session(main.AssessmentSessionIn(module_id="story"), adult_cookie)
        self.assertEqual(forbidden.exception.status_code, 403)

    def test_password_reset_uses_username_and_invalidates_old_password(self):
        main.register_account(main.AccountRegistrationIn(
            username="reset_star", display_name="小重", age=7, password="before88",
            role="student",
        ), Response())
        main.reset_password(main.PasswordResetIn(
            username="reset_star", new_password="after888",
        ))
        with self.assertRaises(HTTPException):
            main.create_session(main.AccountCredentialsIn(username="reset_star", password="before88"), Response())
        logged_in = main.create_session(
            main.AccountCredentialsIn(username="reset_star", password="after888", expected_role="student"),
            Response(),
        )
        self.assertEqual(logged_in["account"]["display_name"], "小重")

    def test_generated_account_typo_is_corrected_for_login_reset_and_binding(self):
        padded = main.register_account(main.AccountRegistrationIn(
            username="S2026007", display_name="小七", age=8, password="before77",
            role="student",
        ), Response())["account"]
        self.assertEqual(padded["username"], "s20260007")
        logged_in = main.create_session(
            main.AccountCredentialsIn(username="S2026007", password="before77", expected_role="student"),
            Response(),
        )
        self.assertEqual(logged_in["account"]["id"], padded["id"])

        reset = main.reset_password(main.PasswordResetIn(username="S2026-007", new_password="after777"))
        self.assertEqual(reset["username"], "s20260007")
        main.create_session(
            main.AccountCredentialsIn(username="s2026007", password="after777", expected_role="student"),
            Response(),
        )

        adult_response = Response()
        main.register_account(main.AccountRegistrationIn(
            username="alias_adult", display_name="小七家长", password="adult888", role="adult",
        ), adult_response)
        linked = main.bind_student(main.StudentLinkIn(username="S2026007"), session_cookie(adult_response))
        self.assertEqual(linked["student"]["id"], padded["id"])

    def test_default_adult_account_is_bound_and_can_read_sample_works(self):
        adult_response = Response()
        session = main.create_session(
            main.AccountCredentialsIn(username="adult_demo", password="demo1234", expected_role="adult"),
            adult_response,
        )
        self.assertEqual(session["selected_student"]["username"], "student_demo")
        self.assertEqual([student["username"] for student in session["students"]], ["student_demo"])
        collection = main.list_artifacts_v1(session_cookie(adult_response))
        self.assertEqual(
            {work["title"] for work in collection["artifacts"]},
            {"星星邮差", "会发光的海底基地"},
        )

    def test_student_can_add_and_delete_a_manual_work(self):
        student_response = Response()
        student = main.register_account(main.AccountRegistrationIn(
            username="manual_creator", display_name="小创", age=10, password="create88",
            role="student",
        ), student_response)["account"]
        student_cookie = session_cookie(student_response)

        created = main.create_manual_work(main.ManualWorkIn(
            module="story", title="我的纸飞机", description="我画了一架飞向月亮的纸飞机。",
            source_id="story:paper-plane",
        ), student_cookie)["work"]
        self.assertEqual(created["kind"], "manual_work")
        self.assertEqual(created["title"], "我的纸飞机")
        collection = main.list_artifacts_v1(student_cookie)
        self.assertIn(created["id"], {work["id"] for work in collection["artifacts"]})
        saved = next(work for work in collection["artifacts"] if work["id"] == created["id"])
        self.assertEqual(saved["sourceResourceId"], "story:paper-plane")

        updated_result = main.create_manual_work(main.ManualWorkIn(
            module="story", title="纸飞机的新结局", description="完整的新故事正文。",
            source_id="story:paper-plane",
        ), student_cookie)
        self.assertTrue(updated_result["updated"])
        self.assertEqual(updated_result["work"]["id"], created["id"])
        self.assertEqual(
            len([work for work in main.list_artifacts_v1(student_cookie)["artifacts"]
                 if work["sourceResourceId"] == "story:paper-plane"]),
            1,
        )

        with main.connect() as db:
            evidence_count = db.execute(
                """SELECT COUNT(*) AS total FROM evidence_records er
                   JOIN source_events se ON se.id=er.source_event_id
                   JOIN assessment_sessions s ON s.id=se.session_id
                   JOIN child_profiles p ON p.id=s.child_profile_id
                   WHERE p.account_id=?""",
                (student["id"],),
            ).fetchone()["total"]
        self.assertEqual(evidence_count, 0)
        main.delete_manual_work(created["id"], student_cookie)
        self.assertNotIn(created["id"], {
            work["id"] for work in main.list_artifacts_v1(student_cookie)["artifacts"]
        })

    def test_adult_comment_is_visible_to_the_bound_student(self):
        child_response = Response()
        child = main.register_account(main.AccountRegistrationIn(
            username="comment_child", display_name="小评", age=9, password="child999",
            role="student",
        ), child_response)["account"]
        child_cookie = session_cookie(child_response)
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="story"), child_cookie)
        token = main.exchange_module_authorization(
            main.LaunchCodeExchangeIn(launchCode=context["launchCode"])
        )["token"]
        work_id = "comment-story"
        main.create_artifact_v1(main.ArtifactIn(
            schemaVersion="1.0", artifactId=work_id, type="story", title="星光故事",
            summary="小星星找到了回家的路。", sourceResourceId="story:comment",
            createdAt=main.now_iso(),
        ), f"Bearer {token}")

        adult_response = Response()
        main.register_account(main.AccountRegistrationIn(
            username="comment_parent", display_name="小评爸爸", password="adult999",
            role="adult", adult_kind="parent",
        ), adult_response)
        adult_cookie = session_cookie(adult_response)
        main.bind_student(main.StudentLinkIn(username=child["username"]), adult_cookie)
        main.select_student(main.StudentContextIn(student_id=child["id"]), adult_cookie)
        created = main.create_work_comment(main.WorkCommentIn(
            work_id=work_id, body="你把故事的结尾讲得很完整，我看见了你的耐心。",
        ), adult_cookie)
        self.assertIsNone(created["comment"]["author_kind"])

        student_collection = main.list_artifacts_v1(child_cookie)
        self.assertEqual(student_collection["artifacts"][0]["comments"][0]["body"], created["comment"]["body"])
        with self.assertRaises(HTTPException) as forbidden:
            main.create_work_comment(main.WorkCommentIn(work_id=work_id, body="学生不能点评"), child_cookie)
        self.assertEqual(forbidden.exception.status_code, 403)

    def test_v1_standard_evidence_is_reportable_and_linkable(self):
        registered = main.register_account(main.AccountRegistrationIn(username="v1_child", display_name="小河", age=9, password="secret99"), Response())
        with main.connect() as db:
            profile = main.profile_for_account(db, registered["account"]["id"])
            manifest = main.module_manifest("career")
            db.execute("INSERT INTO assessment_sessions (id,child_profile_id,module_id,module_version,status,created_at) VALUES (?,?,?,?,?,?)", ("session-v1", profile["id"], "career", manifest["version"], "completed", main.now_iso()))
            db.execute("INSERT INTO source_events (id,session_id,idempotency_key,event_type,schema_version,payload_json,occurred_at,created_at) VALUES (?,?,?,?,?,?,?,?)", ("source-v1", "session-v1", "key-v1", "career.task-completed.v1", "1.0", '{"taskKey":"doctor","attemptCount":2,"hintCount":0,"completionSeconds":30,"adjustmentCount":1}', main.now_iso(), main.now_iso()))
            db.execute("INSERT INTO evidence_records (id,source_event_id,evidence_level,constructs_json,behavior_summary,policy_version,construct_registry_version,derived_at) VALUES (?,?,?,?,?,?,?,?)", ("evidence-v1", "source-v1", "strong", '["problem_solving.planning"]', "完成职业任务并做出调整", "1.0", "1.0", main.now_iso()))
            events, evidence_ids = main.standard_events_for_report(db, profile["id"])
        self.assertEqual(events[0]["event_type"], "career.task-completed.v1")
        self.assertEqual(events[0]["intelligence_candidates"], ["logical"])
        self.assertEqual(events[0]["raw_evidence"]["attemptCount"], 2)
        self.assertEqual(events[0]["raw_evidence"]["completionSeconds"], 30)
        self.assertEqual(evidence_ids, ["evidence-v1"])

    def test_new_account_can_create_and_exchange_v1_session_once(self):
        response = Response()
        registered = main.register_account(main.AccountRegistrationIn(username="launch_child", display_name="小帆", age=9, password="secret77"), response)
        token = response.headers["set-cookie"].split("ai_bole_session=", 1)[1].split(";", 1)[0]
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="career"), token)
        self.assertTrue(context["launchCode"])
        self.assertEqual(context["student"], {"id": registered["account"]["id"], "displayName": "小帆", "age": 9})
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
        snapshot = main.create_snapshot(
            main.SnapshotIn(dataUrl="data:image/jpeg;base64," + base64.b64encode(b"test-jpeg").decode("ascii")),
            header,
        )
        self.addCleanup(lambda: (main.SNAPSHOT_DIR / f"{snapshot['id']}.jpg").unlink(missing_ok=True))
        artifact = main.ArtifactIn(schemaVersion="1.0", artifactId="career-artifact", type="other", title="小医生的一天", summary="完成职业体验", previewResourceId=snapshot["id"], sourceResourceId="career:demo", createdAt=main.now_iso())
        main.create_artifact_v1(artifact, header)
        changed = main.change_assessment_session(context["sessionId"], main.SessionStatusIn(status="completed", summary={"stages": 3}), header)
        self.assertFalse(changed["duplicate"])
        self.assertEqual(main.list_artifacts_v1(cookie)["artifacts"][0]["id"], "career-artifact")
        timeline = main.timeline_v1(cookie)
        self.assertEqual(timeline["sessions"][0]["evidenceCount"], 1)
        self.assertEqual(timeline["moduleSummaries"][0]["completedCount"], 1)
        self.assertTrue(timeline["moduleSummaries"][0]["firstUsedAt"])
        self.assertEqual(timeline["moduleSummaries"][0]["lastUsedAt"], main.read_assessment_session(context["sessionId"], cookie)["endedAt"])
        self.assertEqual(main.read_assessment_session(context["sessionId"], cookie)["summary"], {"stages": 3})
        self.assertEqual(main.read_snapshot(snapshot["id"], cookie).media_type, "image/jpeg")

    def test_v1_batch_is_atomic_and_interrupted_session_can_still_complete(self):
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
        # 中断（如页面刷新触发的 pagehide 中断）后允许补记完成
        late_completed = main.change_assessment_session(context["sessionId"], main.SessionStatusIn(status="completed"), header)
        self.assertFalse(late_completed["duplicate"])
        # 完成后模块授权被撤销：不能再回退状态，也不能再补写证据
        with self.assertRaises(HTTPException) as revoked:
            main.change_assessment_session(context["sessionId"], main.SessionStatusIn(status="active"), header)
        self.assertEqual(revoked.exception.status_code, 401)
        with self.assertRaises(HTTPException) as revoked_evidence:
            main.create_evidence_events_v1(main.EvidenceBatchIn(events=[valid]), header)
        self.assertEqual(revoked_evidence.exception.status_code, 401)

    def test_v1_evidence_records_and_talents_are_derived_from_standard_evidence(self):
        response = Response()
        main.register_account(main.AccountRegistrationIn(username="talent_child", display_name="小林", age=8, password="secret77"), response)
        cookie = response.headers["set-cookie"].split("ai_bole_session=", 1)[1].split(";", 1)[0]
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="career"), cookie)
        token = main.exchange_module_authorization(main.LaunchCodeExchangeIn(launchCode=context["launchCode"]))["token"]
        event = main.EvidenceEnvelopeIn(schemaVersion="1.0", eventId="talent-event", idempotencyKey="talent-event", eventType="career.task-completed.v1", occurredAt=main.now_iso(), payload={"taskKey":"doctor","attemptCount":2,"hintCount":0,"completionSeconds":30,"adjustmentCount":1})
        header = f"Bearer {token}"
        main.create_evidence_events_v1(main.EvidenceBatchIn(events=[event]), header)
        main.change_assessment_session(context["sessionId"], main.SessionStatusIn(status="completed", summary={"stages":1}), header)
        records = main.list_evidence_records_v1(500, cookie)["records"]
        talents = {item["key"]: item for item in main.list_talents_v1(cookie)["talents"]}
        self.assertEqual(records[0]["reportDimensions"], ["logical"])
        self.assertFalse(talents["logical"]["eligible"])
        self.assertEqual(talents["logical"]["strongCount"], 1)
        self.assertTrue(talents["intrapersonal"]["eligible"])

    def test_completed_experience_unlocks_dimensions_with_reference_evidence(self):
        response = Response()
        main.register_account(main.AccountRegistrationIn(username="completed_child", display_name="小满", age=8, password="secret77"), response)
        cookie = response.headers["set-cookie"].split("ai_bole_session=", 1)[1].split(";", 1)[0]
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="chat"), cookie)
        token = main.exchange_module_authorization(main.LaunchCodeExchangeIn(launchCode=context["launchCode"]))["token"]
        header = f"Bearer {token}"
        event = main.EvidenceEnvelopeIn(schemaVersion="1.0", eventId="completed-chat", idempotencyKey="completed-chat", eventType="chat.observation-shared.v1", occurredAt=main.now_iso(), payload={"turnCount":3,"topicKey":"animals"})
        main.create_evidence_events_v1(main.EvidenceBatchIn(events=[event]), header)
        main.change_assessment_session(context["sessionId"], main.SessionStatusIn(status="completed", summary={"turnCount":3}), header)
        talents = {item["key"]: item for item in main.list_talents_v1(cookie)["talents"]}
        self.assertTrue(talents["interpersonal"]["eligible"])
        self.assertFalse(talents["naturalistic"]["eligible"])
        self.assertFalse(talents["intrapersonal"]["eligible"])
        self.assertEqual(talents["naturalistic"]["strongCount"], 0)
        self.assertEqual(talents["naturalistic"]["completedModules"], [])

    def test_deep_sea_level_one_populates_naturalistic_evidence(self):
        response = Response()
        main.register_account(main.AccountRegistrationIn(username="nature_child", display_name="小森", age=8, password="secret77"), response)
        cookie = response.headers["set-cookie"].split("ai_bole_session=", 1)[1].split(";", 1)[0]
        context = main.create_assessment_session(main.AssessmentSessionIn(module_id="deep_sea"), cookie)
        token = main.exchange_module_authorization(main.LaunchCodeExchangeIn(launchCode=context["launchCode"]))["token"]
        header = f"Bearer {token}"
        level_one = main.EvidenceEnvelopeIn(
            schemaVersion="1.0", eventId="nature-level-one", idempotencyKey="nature-level-one",
            eventType="deep-sea.spatial-task-completed.v1", occurredAt=main.now_iso(),
            payload={"level":1,"completionSeconds":25,"adjustmentCount":1,"successfulPairs":4,"totalPairs":4,"checkAttempts":2,"accuracyPercent":100},
        )
        main.create_evidence_events_v1(main.EvidenceBatchIn(events=[level_one]), header)
        records = main.list_evidence_records_v1(500, cookie)["records"]
        talents = {item["key"]: item for item in main.list_talents_v1(cookie)["talents"]}
        self.assertIn("naturalistic", records[0]["reportDimensions"])
        self.assertEqual(talents["naturalistic"]["referenceCount"], 1)
        self.assertEqual(talents["naturalistic"]["recentEvidenceRecordId"], records[0]["id"])


if __name__ == "__main__":
    unittest.main()
