import os
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path

from fastapi import HTTPException, Response


_TEMP_DIR = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
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

    def test_student_can_add_and_delete_a_manual_work(self):
        student_response = Response()
        student = main.register_account(main.AccountRegistrationIn(
            username="manual_creator", display_name="小创", age=10, password="create88",
            role="student",
        ), student_response)["account"]
        student_cookie = session_cookie(student_response)

        created = main.create_manual_work(main.ManualWorkIn(
            module="story", title="我的纸飞机", description="我画了一架飞向月亮的纸飞机。",
        ), student_cookie)["work"]
        self.assertEqual(created["kind"], "manual_work")
        self.assertEqual(created["title"], "我的纸飞机")
        collection = main.explorer_collection(student_cookie)
        self.assertIn(created["id"], {work["id"] for work in collection["works"]})

        with main.connect() as db:
            evidence_count = db.execute(
                "SELECT COUNT(*) AS total FROM evidence_events WHERE account_id=?", (student["id"],)
            ).fetchone()["total"]
        self.assertEqual(evidence_count, 0)
        main.delete_manual_work(created["id"], student_cookie)
        self.assertNotIn(created["id"], {
            work["id"] for work in main.explorer_collection(student_cookie)["works"]
        })

    def test_adult_comment_is_visible_to_the_bound_student(self):
        child_response = Response()
        child = main.register_account(main.AccountRegistrationIn(
            username="comment_child", display_name="小评", age=9, password="child999",
            role="student",
        ), child_response)["account"]
        child_cookie = session_cookie(child_response)
        main.create_evidence(main.EvidenceIn(
            module="story", event_type="story_contribution", evidence_level="strong",
            intelligence_candidates=["linguistic"], behavior_summary="完成了一篇星光故事",
            raw_evidence={"completed": True, "title": "星光故事", "work_content": "小星星找到了回家的路。"},
            context={"activity_id": "comment-story", "idempotency_key": "comment-story:completed"},
        ), child_cookie)
        work_id = main.explorer_collection(child_cookie)["works"][0]["id"]

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

        student_collection = main.explorer_collection(child_cookie)
        self.assertEqual(student_collection["works"][0]["comments"][0]["body"], created["comment"]["body"])
        with self.assertRaises(HTTPException) as forbidden:
            main.create_work_comment(main.WorkCommentIn(work_id=work_id, body="学生不能点评"), child_cookie)
        self.assertEqual(forbidden.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
