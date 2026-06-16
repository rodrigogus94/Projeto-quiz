import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.result_transfer import import_results, parse_student_export, preview_import
from quiz_storage import (
    best_submissions_for_exam,
    repair_orphan_exam_submissions,
    resolve_exam_id_for_submission,
    submissions_for_exam,
)
from system_backup import (
    FULL_BACKUP_KIND,
    BACKUP_FULL_DIR,
    BACKUP_ROOT,
    backup_bytes,
    backup_filename,
    build_full_backup,
    list_full_backups,
    parse_full_backup,
    restore_full_backup,
    run_auto_backup_if_due,
    save_timestamped_full_backup,
)


class TestSystemBackup(unittest.TestCase):
    def test_build_and_parse_roundtrip(self):
        payload = build_full_backup(source="manual")
        self.assertEqual(payload["kind"], FULL_BACKUP_KIND)
        self.assertEqual(payload["backup_source"], "manual")
        raw = backup_bytes(payload)
        parsed, err = parse_full_backup(raw)
        self.assertIsNone(err)
        self.assertEqual(parsed["checksum"], payload["checksum"])

    def test_backup_filename_has_datetime(self):
        name = backup_filename()
        self.assertTrue(name.startswith("backup_completo_"))
        self.assertTrue(name.endswith(".json"))

    def test_restore_replace(self):
        payload = build_full_backup()
        payload["data"]["leaderboard"] = [
            {
                "material_id": "mat-test",
                "name": "Aluno Teste",
                "score": 5,
                "total": 10,
                "responses": [True] * 5 + [False] * 5,
                "submitted_at": "2026-01-01T12:00:00+00:00",
            }
        ]
        payload["checksum"] = __import__("system_backup")._checksum(payload)
        with patch("system_backup.save_leaderboard") as mock_save:
            stats = restore_full_backup(payload, replace=True)
            self.assertIn("leaderboard", stats["restored"])
            mock_save.assert_called_once()

    def test_timestamped_backups_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_dir = root / "completo"
            with patch("system_backup.BACKUP_ROOT", root), patch(
                "system_backup.BACKUP_FULL_DIR", full_dir
            ), patch("system_backup.BACKUP_SNAPSHOT_DIR", root / "snapshots"), patch(
                "system_backup.build_full_backup",
                return_value={"kind": FULL_BACKUP_KIND, "backup_source": "manual", "data": {}},
            ), patch("system_backup._checksum", return_value="abc"), patch(
                "system_backup._save_data_snapshots", return_value=None
            ):
                first = save_timestamped_full_backup(source="manual")
                second = save_timestamped_full_backup(source="manual")
                self.assertNotEqual(first["filename"], second["filename"])
                self.assertEqual(len(list_full_backups()), 2)


class TestExamSubmissionLinking(unittest.TestCase):
    def test_resolve_exam_id_by_title(self):
        exams = [{"id": "new-exam", "title": "Atividade Avaliativa UC 2", "questions": []}]
        with patch("quiz_storage.list_exams", return_value=exams), patch(
            "quiz_storage.get_exam",
            side_effect=lambda eid: exams[0] if eid == "new-exam" else None,
        ):
            new_id, title = resolve_exam_id_for_submission(
                "old-exam-id",
                "Atividade Avaliativa UC 2",
            )
            self.assertEqual(new_id, "new-exam")
            self.assertEqual(title, "Atividade Avaliativa UC 2")

    def test_repair_orphan_exam_submissions(self):
        exams = [{"id": "new-exam", "title": "Prova 1", "questions": []}]
        subs = [
            {
                "id": "sub-1",
                "exam_id": "old-exam",
                "exam_title": "Prova 1",
                "student_name": "Aluno",
            }
        ]
        with patch("quiz_storage.list_exams", return_value=exams), patch(
            "quiz_storage.load_exam_submissions", return_value=subs
        ), patch("quiz_storage.save_exam_submissions") as mock_save:
            fixed = repair_orphan_exam_submissions()
            self.assertEqual(fixed, 1)
            self.assertEqual(subs[0]["exam_id"], "new-exam")
            mock_save.assert_called_once()

    def test_submissions_for_exam_matches_by_title(self):
        exams = [{"id": "new-exam", "title": "Prova 1", "questions": []}]
        subs = [
            {
                "id": "sub-1",
                "exam_id": "old-exam",
                "exam_title": "Prova 1",
                "student_name": "Aluno",
            }
        ]
        with patch("quiz_storage.list_exams", return_value=exams), patch(
            "quiz_storage.get_exam",
            return_value=exams[0],
        ), patch("quiz_storage.load_exam_submissions", return_value=subs):
            matched = submissions_for_exam("new-exam")
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0]["student_name"], "Aluno")

    def test_best_submissions_for_exam_picks_highest_score(self):
        exams = [{"id": "exam-1", "title": "Prova 1", "questions": []}]
        subs = [
            {
                "id": "sub-1",
                "exam_id": "exam-1",
                "student_name": "Aluno",
                "summary": {"total_points": 14.0, "max_points": 20, "percent": 70},
            },
            {
                "id": "sub-2",
                "exam_id": "exam-1",
                "student_name": "Aluno",
                "summary": {"total_points": 17.0, "max_points": 20, "percent": 85},
            },
        ]
        with patch("quiz_storage.list_exams", return_value=exams), patch(
            "quiz_storage.get_exam",
            return_value=exams[0],
        ), patch("quiz_storage.load_exam_submissions", return_value=subs):
            best = best_submissions_for_exam("exam-1")
            self.assertEqual(len(best), 1)
            self.assertEqual(best[0]["id"], "sub-2")


class TestExamResultImport(unittest.TestCase):
    SAMPLE = {
        "kind": "projeto-quiz-resultados",
        "version": 1,
        "generated_at": "2026-06-12T23:06:09.690674+00:00",
        "student": {
            "name": "Leandro Siqueira",
            "email": "leandrosiqueira00798@gmail.com",
        },
        "quiz_results": [],
        "exam_submissions": [
            {
                "id": "9be8e371-c546-4c6d-b9a7-2480a7bc2166",
                "exam_id": "d3a1f2db-0c45-404a-964f-1e445ef9d3e5",
                "student_name": "Leandro Siqueira",
                "student_email": "leandrosiqueira00798@gmail.com",
                "answers": [],
                "summary": {
                    "counts": {"A": 0, "PA": 1, "NA": 5},
                    "total_points": 14.25,
                    "max_points": 20.0,
                    "percent": 71.25,
                },
                "submitted_at": "2026-06-12T23:04:36.170696+00:00",
                "correction_released": False,
                "exam_title": "Atividade Avaliativa UC 2",
            }
        ],
    }

    def setUp(self):
        from app.result_transfer import _checksum

        self.SAMPLE["checksum"] = _checksum(self.SAMPLE)
        self.raw = json.dumps(self.SAMPLE, ensure_ascii=False).encode("utf-8")

    def test_parse_student_export(self):
        payload, err = parse_student_export(self.raw)
        self.assertIsNone(err)
        self.assertEqual(len(payload["exam_submissions"]), 1)

    def test_remove_payload_duplicates_from_store(self):
        from app.result_transfer import _remove_payload_duplicates_from_store

        payload, _ = parse_student_export(self.raw)
        with patch("app.result_transfer.load_exam_submissions") as mock_load, patch(
            "app.result_transfer.save_exam_submissions"
        ) as mock_save, patch(
            "app.result_transfer.load_leaderboard", return_value=[]
        ):
            mock_load.return_value = [
                {
                    "id": "9be8e371-c546-4c6d-b9a7-2480a7bc2166",
                    "student_name": "Leandro Siqueira",
                }
            ]
            removed = _remove_payload_duplicates_from_store(payload, "Leandro Siqueira")
            self.assertEqual(removed["exam_removed"], 1)
            mock_save.assert_called_once_with([])

    @patch("app.result_transfer.load_exam_submissions", return_value=[])
    @patch("app.result_transfer.load_leaderboard", return_value=[])
    @patch("app.result_transfer.add_exam_submission")
    def test_import_exam_submission(self, mock_add, _lb, _subs):
        payload, _ = parse_student_export(self.raw)
        preview = preview_import(payload, "Leandro Siqueira")
        self.assertEqual(preview["exam_new"], 1)
        stats = import_results(payload, "Leandro Siqueira", "leandrosiqueira00798@gmail.com")
        self.assertEqual(stats["exam_added"], 1)
        mock_add.assert_called_once()


class TestAutoBackup(unittest.TestCase):
    def test_run_auto_backup_if_due(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_dir = root / "completo"
            with patch("system_backup.BACKUP_ROOT", root), patch(
                "system_backup.BACKUP_FULL_DIR", full_dir
            ), patch("system_backup.BACKUP_SNAPSHOT_DIR", root / "snapshots"), patch(
                "system_backup.AUTO_BACKUP_STAMP_PATH", root / ".last_auto_backup"
            ), patch(
                "system_backup.save_timestamped_full_backup",
                return_value={"filename": "backup_auto_20260101_120000.json"},
            ):
                self.assertTrue(run_auto_backup_if_due(force=True))
                self.assertTrue((root / ".last_auto_backup").is_file())


if __name__ == "__main__":
    unittest.main()
