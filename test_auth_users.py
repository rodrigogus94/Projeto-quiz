import unittest
import uuid
from unittest.mock import patch

from auth_users import (
    approve_professor,
    approve_user,
    bootstrap_data_store,
    delete_user_account,
    import_users_from_backup,
    read_backup_csv_bytes,
    ensure_name_student_user,
    find_student_by_name,
    find_user_by_email,
    find_user_by_id,
    get_pending_professors,
    get_pending_users,
    is_system_admin,
    list_approved_students,
    register_student_request,
    resolve_professor_login,
    resolve_unified_google_login,
    sync_student_roster_from_users,
    update_user_account,
    upsert_google_user,
)
from quiz_storage import find_student_by_name as roster_find_student
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

    def test_sync_student_roster_from_users(self):
        name = f"Sync {uuid.uuid4().hex[:8]}"
        ensure_name_student_user(name, auto_approve=True)
        self.assertIsNotNone(roster_find_student(name))
        added = sync_student_roster_from_users()
        self.assertGreaterEqual(added, 0)
        approved = list_approved_students()
        self.assertTrue(any(s["name"] == name for s in approved))

    def test_bootstrap_data_store_runs(self):
        bootstrap_data_store()
        self.assertIsInstance(list_approved_students(), list)

    def test_read_backup_csv_bytes(self):
        ensure_name_student_user(f"Backup {uuid.uuid4().hex[:6]}", auto_approve=True)
        data = read_backup_csv_bytes()
        self.assertIsNotNone(data)
        self.assertIn(b"nome", data)

    def test_import_users_from_backup_merge(self):
        name = f"Import {uuid.uuid4().hex[:8]}"
        csv_text = (
            "nome;email;categoria;cadastrado_em;atualizado_em\n"
            f"{name};;Aluno;2026-06-10T00:00:00+00:00;\n"
        )
        count, err = import_users_from_backup(csv_text, merge=True)
        self.assertIsNone(err)
        self.assertEqual(count, 1)
        self.assertIsNotNone(find_student_by_name(name))


class TestRenameStudentRecords(unittest.TestCase):
    def test_rename_student_records_uses_email(self):
        from quiz_storage import rename_student_records

        board = [
            {
                "name": "Nome Antigo",
                "student_email": "aluno@test.com",
                "score": 8,
                "total": 10,
            }
        ]
        subs = [
            {
                "id": "sub-1",
                "student_name": "Nome Antigo",
                "student_email": "aluno@test.com",
                "answers": [],
            }
        ]
        students = [
            {
                "id": "stu-1",
                "name": "Nome Antigo",
                "email": "aluno@test.com",
            }
        ]
        users = [
            {
                "id": "usr-1",
                "role": "student",
                "name": "Nome Antigo",
                "email": "aluno@test.com",
                "active": True,
                "status": "approved",
            }
        ]
        with patch("quiz_storage.load_leaderboard", return_value=board), patch(
            "quiz_storage.save_leaderboard"
        ) as mock_save_board, patch(
            "quiz_storage.load_exam_submissions", return_value=subs
        ), patch("quiz_storage.save_exam_submissions") as mock_save_subs, patch(
            "quiz_storage.load_students", return_value=students
        ), patch("quiz_storage.save_students") as mock_save_students, patch(
            "auth_users.load_users", return_value=users
        ), patch("auth_users.save_users") as mock_save_users:
            stats = rename_student_records(
                old_name="Nome Antigo",
                new_name="Nome Novo",
                student_email="aluno@test.com",
            )
        self.assertEqual(stats["quiz_updated"], 1)
        self.assertEqual(stats["exam_updated"], 1)
        self.assertEqual(stats["roster_updated"], 1)
        self.assertEqual(stats["users_updated"], 1)
        self.assertEqual(board[0]["name"], "Nome Novo")
        self.assertEqual(subs[0]["student_name"], "Nome Novo")
        self.assertEqual(students[0]["name"], "Nome Novo")
        self.assertEqual(users[0]["name"], "Nome Novo")
        mock_save_board.assert_called_once()
        mock_save_subs.assert_called_once()
        mock_save_students.assert_called_once()
        mock_save_users.assert_called_once()


if __name__ == "__main__":
    unittest.main()
