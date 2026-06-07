import unittest
import uuid

from auth_users import (
    approve_professor,
    approve_user,
    delete_user_account,
    ensure_name_student_user,
    find_student_by_name,
    find_user_by_email,
    find_user_by_id,
    get_pending_professors,
    get_pending_users,
    is_system_admin,
    register_student_request,
    resolve_professor_login,
    resolve_unified_google_login,
    update_user_account,
    upsert_google_user,
)
from quiz_storage import load_config, save_config


class TestAuthUsers(unittest.TestCase):
    def setUp(self):
        cfg = load_config()
        cfg["system_admin_email"] = "rodrigogus94@gmail.com"
        cfg["professor_allowlist"] = []
        save_config(cfg)

    def test_ensure_name_student_user_auto_approve(self):
        name = f"Aluno {uuid.uuid4().hex[:8]}"
        user = ensure_name_student_user(name, auto_approve=True)
        self.assertEqual(user["role"], "student")
        self.assertEqual(user["status"], "approved")
        self.assertIsNotNone(find_student_by_name(name))

    def test_register_student_request_pending(self):
        name = f"Pedro {uuid.uuid4().hex[:8]}"
        user, err = register_student_request(name)
        self.assertIsNone(err)
        self.assertEqual(user["status"], "pending")
        pending = get_pending_users()
        self.assertTrue(any(u["name"] == name for u in pending))

    def test_approve_student_user(self):
        user, _ = register_student_request(f"Carla {uuid.uuid4().hex[:8]}")
        err = approve_user(user["id"])
        self.assertIsNone(err)
        approved = find_student_by_name(user["name"])
        self.assertEqual(approved["status"], "approved")

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
        pending = [u for u in get_pending_professors() if u["email"] == email]
        self.assertEqual(len(pending), 1)

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
        pending = [u for u in get_pending_professors() if u["email"] == email]
        self.assertEqual(len(pending), 1)
        err = approve_professor(pending[0]["id"])
        self.assertIsNone(err)
        user, err = resolve_professor_login(profile)
        self.assertIsNone(err)
        self.assertEqual(user["role"], "professor")
        self.assertEqual(user["status"], "approved")

    def test_resolve_unified_google_login_student_pending(self):
        email = f"aluno-{uuid.uuid4().hex[:8]}@escola.edu"
        profile = {
            "sub": f"gid-{uuid.uuid4().hex[:8]}",
            "email": email,
            "name": "Aluno Novo",
        }
        user, err = resolve_unified_google_login(profile)
        self.assertIsNone(user)
        self.assertIn("aprovar", err.lower())
        pending = get_pending_users()
        self.assertTrue(any(u["email"] == email for u in pending))

    def test_resolve_unified_google_login_student_after_approval(self):
        email = f"aluno-{uuid.uuid4().hex[:8]}@escola.edu"
        profile = {
            "sub": f"gid-{uuid.uuid4().hex[:8]}",
            "email": email,
            "name": "Aluno Aprovado",
        }
        resolve_unified_google_login(profile)
        pending = get_pending_users()
        student = next(u for u in pending if u["email"] == email)
        approve_user(student["id"])
        user, err = resolve_unified_google_login(profile)
        self.assertIsNone(err)
        self.assertEqual(user["role"], "student")
        self.assertEqual(user["status"], "approved")

    def test_resolve_unified_google_login_admin(self):
        profile = {
            "sub": "gid-admin-unified",
            "email": "rodrigogus94@gmail.com",
            "name": "Admin",
        }
        user, err = resolve_unified_google_login(profile)
        self.assertIsNone(err)
        self.assertEqual(user["role"], "professor")
        self.assertTrue(user.get("is_admin"))

    def test_upsert_google_student(self):
        user = upsert_google_user(
            {"sub": "g2", "email": "a@b.com", "name": "Aluno"},
            role="student",
        )
        self.assertEqual(user["role"], "student")

    def test_update_and_delete_student_account(self):
        user, _ = register_student_request(f"Temp {uuid.uuid4().hex[:6]}")
        new_name = f"Editado {uuid.uuid4().hex[:6]}"
        err = update_user_account(user["id"], name=new_name, status="approved")
        self.assertIsNone(err)
        updated = find_user_by_id(user["id"])
        self.assertEqual(updated["name"], new_name)
        self.assertEqual(updated["status"], "approved")
        err = delete_user_account(user["id"])
        self.assertIsNone(err)
        self.assertIsNone(find_user_by_id(user["id"]))

    def test_cannot_delete_system_admin(self):
        admin = find_user_by_email("rodrigogus94@gmail.com")
        if admin:
            err = delete_user_account(admin["id"])
            self.assertIsNotNone(err)


if __name__ == "__main__":
    unittest.main()
