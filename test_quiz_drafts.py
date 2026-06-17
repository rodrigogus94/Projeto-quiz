"""Testes de rascunho de quiz."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.quiz_drafts import (
    count_answered_quiz_slots,
    normalize_quiz_slots,
    pending_quiz_indices,
    quiz_attempt_number,
    slots_to_student_answers,
)
from quiz_storage import (
    QUIZ_DRAFTS_PATH,
    delete_quiz_draft,
    find_quiz_draft,
    upsert_quiz_draft,
)


class QuizDraftStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.drafts_path = Path(self.tmp.name) / "quiz_drafts.json"
        patcher = patch("quiz_storage.QUIZ_DRAFTS_PATH", self.drafts_path)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_upsert_and_find_quiz_draft(self):
        upsert_quiz_draft(
            student_name="Ana",
            student_email="ana@test.com",
            material_id="mat-1",
            attempt=1,
            slots=[{"letter": "A", "answered": True, "is_correct": True}, None],
            current_q_index=1,
            question_count=2,
        )
        draft = find_quiz_draft("Ana", "ana@test.com", "mat-1", 1)
        self.assertIsNotNone(draft)
        self.assertEqual(draft["current_q_index"], 1)

    def test_delete_quiz_draft(self):
        upsert_quiz_draft(
            student_name="Bob",
            student_email=None,
            material_id="mat-2",
            attempt=1,
            slots=[None],
            current_q_index=0,
            question_count=1,
        )
        removed = delete_quiz_draft("Bob", None, "mat-2", 1)
        self.assertEqual(removed, 1)
        self.assertIsNone(find_quiz_draft("Bob", None, "mat-2", 1))


class QuizDraftHelperTests(unittest.TestCase):
    def test_pending_and_slots_to_answers(self):
        slots = [
            {"letter": "A", "answered": True, "is_correct": True},
            None,
            {"letter": "C", "answered": True, "is_correct": False},
        ]
        self.assertEqual(count_answered_quiz_slots(slots), 2)
        self.assertEqual(pending_quiz_indices(slots), [1])
        with self.assertRaises(ValueError):
            slots_to_student_answers(slots)
        self.assertEqual(
            slots_to_student_answers(
                [
                    {"letter": "A", "answered": True, "is_correct": True},
                    {"letter": "B", "answered": True, "is_correct": False},
                ]
            ),
            [True, False],
        )

    def test_attempt_number(self):
        with patch(
            "app.quiz_drafts.leaderboard_for_material",
            return_value=[{"name": "Ana", "student_email": "a@t.com"}],
        ):
            self.assertEqual(quiz_attempt_number("Ana", "m1", "a@t.com"), 2)


if __name__ == "__main__":
    unittest.main()
