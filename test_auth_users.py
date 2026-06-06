import unittest

from auth_users import (
    can_be_professor,
    ensure_name_student_user,
    find_student_by_name,
    resolve_professor_login,
    upsert_google_user,
)
from quiz_storage import load_config, save_config


class TestAuthUsers(unittest.TestCase):
    def setUp(self):
        cfg = load_config()
        cfg["professor_allowlist"] = ["prof@escola.edu"]
        save_config(cfg)

    def test_ensure_name_student_user(self):
        user = ensure_name_student_user("Ana Costa")
        self.assertEqual(user["role"], "student")
        self.assertIsNotNone(find_student_by_name("Ana Costa"))

    def test_professor_allowlist(self):
        self.assertTrue(can_be_professor("prof@escola.edu"))
        self.assertFalse(can_be_professor("aluno@escola.edu"))

    def test_resolve_professor_login(self):
        profile = {
            "sub": "gid-1",
            "email": "prof@escola.edu",
            "name": "Prof Teste",
        }
        user, err = resolve_professor_login(profile)
        self.assertIsNone(err)
        self.assertEqual(user["role"], "professor")

    def test_upsert_google_student(self):
        user = upsert_google_user(
            {"sub": "g2", "email": "a@b.com", "name": "Aluno"},
            role="student",
        )
        self.assertEqual(user["role"], "student")


if __name__ == "__main__":
    unittest.main()
