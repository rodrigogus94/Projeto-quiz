"""Testes de rascunho de prova (autosave)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.exam_drafts import (
    apply_exam_draft_to_session,
    collect_exam_answers_from_session,
    count_answered_questions,
    exam_attempt_number,
)
from quiz_storage import (
    EXAM_DRAFTS_PATH,
    delete_exam_draft,
    find_exam_draft,
    upsert_exam_draft,
)


class ExamDraftStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.drafts_path = Path(self.tmp.name) / "exam_drafts.json"
        patcher = patch("quiz_storage.EXAM_DRAFTS_PATH", self.drafts_path)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_upsert_and_find_draft(self):
        upsert_exam_draft(
            student_name="Ana",
            student_email="ana@test.com",
            exam_id="exam-1",
            attempt=1,
            answers={"0": {"kind": "choice", "mc": "B"}},
            question_count=5,
        )
        draft = find_exam_draft("Ana", "ana@test.com", "exam-1", 1)
        self.assertIsNotNone(draft)
        self.assertEqual(draft["answers"]["0"]["mc"], "B")

    def test_upsert_updates_existing(self):
        upsert_exam_draft(
            student_name="Ana",
            student_email="ana@test.com",
            exam_id="exam-1",
            attempt=1,
            answers={"0": {"kind": "choice", "mc": "A"}},
            question_count=2,
        )
        upsert_exam_draft(
            student_name="Ana",
            student_email="ana@test.com",
            exam_id="exam-1",
            attempt=1,
            answers={"0": {"kind": "choice", "mc": "C"}, "1": {"kind": "choice", "mc": "D"}},
            question_count=2,
        )
        draft = find_exam_draft("Ana", "ana@test.com", "exam-1", 1)
        self.assertEqual(draft["answers"]["0"]["mc"], "C")
        self.assertEqual(draft["answers"]["1"]["mc"], "D")

    def test_delete_draft(self):
        upsert_exam_draft(
            student_name="Bob",
            student_email=None,
            exam_id="exam-2",
            attempt=1,
            answers={"0": {"kind": "justify", "text": "ok"}},
            question_count=1,
        )
        removed = delete_exam_draft("Bob", None, "exam-2", 1)
        self.assertEqual(removed, 1)
        self.assertIsNone(find_exam_draft("Bob", None, "exam-2", 1))

    def test_attempt_number(self):
        with patch(
            "app.exam_drafts.exam_submissions_for_student",
            return_value=[{"id": "s1"}],
        ):
            self.assertEqual(exam_attempt_number("Ana", "e1", "a@t.com"), 2)


class ExamDraftSessionTests(unittest.TestCase):
    def test_count_answered_questions(self):
        answers = {
            "0": {"kind": "choice", "mc": "A"},
            "2": {"kind": "justify", "text": "texto"},
        }
        self.assertEqual(count_answered_questions(answers, 4), 2)

    def test_apply_and_collect_roundtrip(self):
        import streamlit as st

        questions = [
            {
                "type": "choice",
                "question": "Q1",
                "options": ["a", "b", "c", "d"],
                "correct": "A",
            },
            {
                "type": "justify",
                "question": "Q2",
                "answer_key": "x",
            },
        ]
        draft = {
            "answers": {
                "0": {"kind": "choice", "mc": "B"},
                "1": {"kind": "justify", "text": "minha resposta"},
            },
            "question_count": 2,
        }
        with patch.object(st, "session_state", {}):
            restored = apply_exam_draft_to_session(draft, questions)
            self.assertEqual(restored, 2)
            collected = collect_exam_answers_from_session(questions)
            self.assertEqual(collected["0"]["mc"], "B")
            self.assertEqual(collected["1"]["text"], "minha resposta")


if __name__ == "__main__":
    unittest.main()
