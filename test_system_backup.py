import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.result_transfer import import_results, parse_student_export, preview_import
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
