"""Rascunhos de prova — autosave e recuperação após queda de conexão."""

from __future__ import annotations

import streamlit as st

from pdf_parser import exam_requires_justify, question_for_student
from quiz_storage import (
    delete_exam_draft,
    exam_submissions_for_student,
    find_exam_draft,
    upsert_exam_draft,
)


def exam_attempt_number(student_name: str, exam_id: str, student_email: str | None) -> int:
    return len(exam_submissions_for_student(student_name, exam_id, student_email)) + 1


def _mc_key(index: int) -> str:
    return f"exam_q_{index}_mc"


def _justify_key(index: int) -> str:
    return f"exam_q_{index}_justify"


def _text_key(index: int) -> str:
    return f"exam_q_{index}"


def _question_layout(q: dict, needs_justify_exam: bool) -> tuple[str, bool]:
    q_view = question_for_student(q)
    show_justify = (
        q_view["type"] == "choice_with_justify"
        or (needs_justify_exam and q_view["type"] == "choice")
    )
    if show_justify or q_view["type"] == "choice_with_justify":
        kind = "choice_with_justify"
    elif q_view["type"] == "choice":
        kind = "choice"
    else:
        kind = "justify"
    return kind, show_justify


def apply_exam_draft_to_session(draft: dict | None, questions: list) -> int:
    """Preenche widgets da prova a partir do rascunho salvo. Retorna questões restauradas."""
    if not draft:
        return 0
    answers = draft.get("answers") or {}
    if draft.get("question_count") and int(draft["question_count"]) != len(questions):
        return 0

    needs_justify_exam = exam_requires_justify(questions)
    restored = 0
    for i, q in enumerate(questions):
        saved = answers.get(str(i)) or answers.get(i)
        if not saved:
            continue
        kind, show_justify = _question_layout(q, needs_justify_exam)
        mc = saved.get("mc")
        if mc and kind in ("choice", "choice_with_justify") and _mc_key(i) not in st.session_state:
            st.session_state[_mc_key(i)] = mc
            restored += 1
        justify = saved.get("justify") or ""
        if show_justify and justify and _justify_key(i) not in st.session_state:
            st.session_state[_justify_key(i)] = justify
            restored += 1
        text = saved.get("text") or ""
        if kind == "justify" and text and _text_key(i) not in st.session_state:
            st.session_state[_text_key(i)] = text
            restored += 1
    return restored


def collect_exam_answers_from_session(questions: list) -> dict:
    needs_justify_exam = exam_requires_justify(questions)
    answers: dict[str, dict] = {}
    for i, q in enumerate(questions):
        kind, show_justify = _question_layout(q, needs_justify_exam)
        entry: dict = {"kind": kind}
        if kind in ("choice", "choice_with_justify"):
            entry["mc"] = st.session_state.get(_mc_key(i))
        if show_justify:
            entry["justify"] = (st.session_state.get(_justify_key(i)) or "").strip()
        if kind == "justify":
            entry["text"] = (st.session_state.get(_text_key(i)) or "").strip()
        if entry.get("mc") or entry.get("justify") or entry.get("text"):
            answers[str(i)] = entry
    return answers


def count_answered_questions(answers: dict, total: int) -> int:
    answered = 0
    for i in range(total):
        saved = answers.get(str(i)) or answers.get(i)
        if not saved:
            continue
        kind = saved.get("kind")
        if kind in ("choice", "choice_with_justify") and saved.get("mc"):
            answered += 1
        elif kind == "justify" and (saved.get("text") or "").strip():
            answered += 1
    return answered


def autosave_exam_draft(
    *,
    exam: dict,
    student_name: str,
    student_email: str | None,
) -> dict | None:
    questions = exam.get("questions") or []
    if not questions or not student_name.strip():
        return None
    attempt = exam_attempt_number(student_name, exam["id"], student_email)
    answers = collect_exam_answers_from_session(questions)
    if not answers:
        return find_exam_draft(student_name, student_email, exam["id"], attempt)
    return upsert_exam_draft(
        student_name=student_name,
        student_email=student_email,
        exam_id=exam["id"],
        attempt=attempt,
        answers=answers,
        question_count=len(questions),
    )


def clear_exam_draft_for_attempt(
    *,
    student_name: str,
    student_email: str | None,
    exam_id: str,
    attempt: int,
) -> None:
    delete_exam_draft(student_name, student_email, exam_id, attempt)


def load_exam_draft_for_attempt(
    *,
    student_name: str,
    student_email: str | None,
    exam_id: str,
    attempt: int,
) -> dict | None:
    return find_exam_draft(student_name, student_email, exam_id, attempt)


def build_answers_input_from_session(questions: list) -> list:
    """Monta tuplas de resposta para correção a partir do session_state."""
    needs_justify_exam = exam_requires_justify(questions)
    answers_input: list = []
    for i, q in enumerate(questions):
        kind, show_justify = _question_layout(q, needs_justify_exam)
        if kind == "choice_with_justify":
            answers_input.append(
                (
                    "choice_with_justify",
                    st.session_state.get(_mc_key(i)),
                    st.session_state.get(_justify_key(i)) or "",
                )
            )
        elif kind == "choice":
            answers_input.append(("choice", st.session_state.get(_mc_key(i))))
        else:
            answers_input.append(("justify", st.session_state.get(_text_key(i)) or ""))
    return answers_input
