"""Rascunhos de quiz — autosave, navegação e recuperação."""

from __future__ import annotations

import streamlit as st

from quiz_storage import (
    delete_quiz_draft,
    find_quiz_draft,
    leaderboard_for_material,
    upsert_quiz_draft,
)


def quiz_attempt_number(
    student_name: str, material_id: str, student_email: str | None
) -> int:
    name_key = student_name.strip().lower()
    email_key = (student_email or "").strip().lower()
    attempts = [
        e
        for e in leaderboard_for_material(material_id)
        if (email_key and (e.get("student_email") or "").strip().lower() == email_key)
        or e["name"].strip().lower() == name_key
    ]
    return len(attempts) + 1


def quiz_radio_key(index: int) -> str:
    return f"q_{index}"


def empty_quiz_slots(count: int) -> list:
    return [None] * count


def normalize_quiz_slots(slots: list | None, count: int) -> list:
    base = empty_quiz_slots(count)
    if not slots:
        return base
    for i, slot in enumerate(slots[:count]):
        if slot:
            base[i] = slot
    return base


def ensure_quiz_slots(count: int) -> list:
    slots = st.session_state.get("quiz_answer_slots")
    if not isinstance(slots, list) or len(slots) != count:
        slots = empty_quiz_slots(count)
        st.session_state.quiz_answer_slots = slots
    return slots


def apply_quiz_draft_to_session(draft: dict | None, question_count: int) -> int:
    if not draft:
        return 0
    if int(draft.get("question_count") or 0) != question_count:
        return 0

    slots = normalize_quiz_slots(draft.get("slots"), question_count)
    st.session_state.quiz_answer_slots = slots
    st.session_state.current_q_index = min(
        int(draft.get("current_q_index") or 0),
        max(question_count - 1, 0),
    )
    st.session_state.quiz_active = True
    st.session_state.quiz_finished = False
    st.session_state.answer_feedback = None

    restored = 0
    for i, slot in enumerate(slots):
        if slot and slot.get("letter") and quiz_radio_key(i) not in st.session_state:
            st.session_state[quiz_radio_key(i)] = slot["letter"]
            restored += 1
    return restored


def count_answered_quiz_slots(slots: list) -> int:
    return sum(1 for slot in slots if slot and slot.get("answered"))


def pending_quiz_indices(slots: list) -> list[int]:
    return [i for i, slot in enumerate(slots) if not slot or not slot.get("answered")]


def slots_to_student_answers(slots: list) -> list[bool]:
    answers: list[bool] = []
    for slot in slots:
        if not slot or not slot.get("answered"):
            raise ValueError("Quiz incompleto")
        answers.append(bool(slot.get("is_correct")))
    return answers


def collect_quiz_slots_from_session(question_count: int) -> list:
    slots = ensure_quiz_slots(question_count)
    for i in range(question_count):
        letter = st.session_state.get(quiz_radio_key(i))
        if not letter:
            continue
        existing = slots[i] if i < len(slots) else None
        if existing and existing.get("answered"):
            continue
        slots[i] = {
            "letter": letter,
            "answered": False,
            "is_correct": existing.get("is_correct") if existing else None,
        }
    st.session_state.quiz_answer_slots = slots
    return slots


def autosave_quiz_draft(
    *,
    material_id: str,
    student_name: str,
    student_email: str | None,
    question_count: int,
) -> dict | None:
    if not material_id or not student_name.strip() or question_count <= 0:
        return None
    attempt = quiz_attempt_number(student_name, material_id, student_email)
    slots = collect_quiz_slots_from_session(question_count)
    has_data = any(
        (slot and (slot.get("answered") or slot.get("letter")))
        for slot in slots
    ) or st.session_state.get("current_q_index", 0) > 0
    if not has_data:
        return find_quiz_draft(student_name, student_email, material_id, attempt)
    return upsert_quiz_draft(
        student_name=student_name,
        student_email=student_email,
        material_id=material_id,
        attempt=attempt,
        slots=slots,
        current_q_index=int(st.session_state.get("current_q_index") or 0),
        question_count=question_count,
    )


def clear_quiz_draft_for_attempt(
    *,
    student_name: str,
    student_email: str | None,
    material_id: str,
    attempt: int,
) -> None:
    delete_quiz_draft(student_name, student_email, material_id, attempt)


def load_quiz_draft_for_attempt(
    *,
    student_name: str,
    student_email: str | None,
    material_id: str,
    attempt: int,
) -> dict | None:
    return find_quiz_draft(student_name, student_email, material_id, attempt)


def start_quiz_from_draft_or_fresh(
    *,
    material_id: str,
    student_name: str,
    student_email: str | None,
    question_count: int,
) -> bool:
    """Restaura rascunho se existir. Retorna True se recuperou progresso."""
    attempt = quiz_attempt_number(student_name, material_id, student_email)
    draft = load_quiz_draft_for_attempt(
        student_name=student_name,
        student_email=student_email,
        material_id=material_id,
        attempt=attempt,
    )
    if draft:
        apply_quiz_draft_to_session(draft, question_count)
        return True
    st.session_state.quiz_answer_slots = empty_quiz_slots(question_count)
    st.session_state.current_q_index = 0
    st.session_state.student_answers = []
    st.session_state.quiz_active = True
    st.session_state.quiz_finished = False
    st.session_state.show_comparison = False
    st.session_state.answer_feedback = None
    return False
