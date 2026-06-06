import unittest
import uuid

from auth_users import (
    approve_professor,
    ensure_name_student_user,
    find_student_by_name,
    get_pending_professors,
    is_system_admin,
    resolve_professor_login,
    upsert_google_user,
)
from quiz_storage import load_config, save_config


class TestAuthUsers(unittest.TestCase):
    def setUp(self):
        cfg = load_config()
        cfg["system_admin_email"] = "rodrigogus94@gmail.com"
        cfg["professor_allowlist"] = []
        save_config(cfg)

    def test_ensure_name_student_user(self):
        user = ensure_name_student_user("Ana Costa")
        self.assertEqual(user["role"], "student")
        self.assertIsNotNone(find_student_by_name("Ana Costa"))

    def test_is_system_admin(self):
        self.assertTrue(is_system_admin("rodrigogus94@gmail.com"))
        self.assertFalse(is_system_admin("outro@test.com"))

    def test_resolve_professor_login_pending(self):
        email = f"prof-{uuid.uuid4().hex[:8]}@escola.edu"
        profile = {
            "sub": f"gid-{uuid.uuid4().hex[:8]}",
            "email": email,
            "name": "Prof Teste",
        }
        user, err = resolve_professor_login(profile)
        self.assertIsNone(user)
        self.assertIn("Solicitação enviada", err)
        pending = get_pending_professors()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["email"], email)

    def test_resolve_professor_login_admin(self):
        profile = {
            "sub": "gid-admin",
            "email": "rodrigogus94@gmail.com",
            "name": "Admin",
        }
        user, err = resolve_professor_login(profile)
        self.assertIsNone(err)
        self.assertEqual(user["role"], "professor")
        self.assertEqual(user["status"], "approved")
        self.assertTrue(user.get("is_admin"))

    def test_approve_professor(self):
        email = f"novo-{uuid.uuid4().hex[:8]}@escola.edu"
        profile = {
            "sub": f"gid-{uuid.uuid4().hex[:8]}",
            "email": email,
            "name": "Novo Prof",
        }
        resolve_professor_login(profile)
        pending = get_pending_professors()
        self.assertEqual(len(pending), 1)
        err = approve_professor(pending[0]["id"])
        self.assertIsNone(err)
        user, err = resolve_professor_login(profile)
        self.assertIsNone(err)
        self.assertEqual(user["role"], "professor")
        self.assertEqual(user["status"], "approved")

    def test_upsert_google_student(self):
        user = upsert_google_user(
            {"sub": "g2", "email": "a@b.com", "name": "Aluno"},
            role="student",
        )
        self.assertEqual(user["role"], "student")


if __name__ == "__main__":
    unittest.main()
