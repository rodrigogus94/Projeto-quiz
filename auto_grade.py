"""Correção automática com classificação A (acertou), PA (parcial), NA (não acertou)."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

CLASSIFICATIONS = ("A", "PA", "NA")
POINTS = {"A": 1.0, "PA": 0.5, "NA": 0.0}
LABELS = {
    "A": "A — Acertou",
    "PA": "PA — Parcialmente acertou",
    "NA": "NA — Não acertou",
}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keywords(text: str) -> list[str]:
    words = _normalize(text).split()
    keys = [w for w in words if len(w) >= 3]
    return keys if keys else words


def classify_justify(student_text: str, answer_key: str) -> str:
    student = student_text.strip()
    if not student:
        return "NA"
    if not answer_key.strip():
        return "PA"

    student_norm = _normalize(student)
    key_norm = _normalize(answer_key)
    keys = _keywords(answer_key)

    if not keys:
        return "PA"

    hits = sum(1 for w in keys if w in student_norm)
    coverage = hits / len(keys)
    similarity = SequenceMatcher(None, student_norm, key_norm).ratio()
    score = 0.55 * coverage + 0.45 * similarity

    if score >= 0.62:
        return "A"
    if score >= 0.32:
        return "PA"
    return "NA"


def classify_choice(selected: str, correct: str) -> str:
    return "A" if selected == correct else "NA"


def grade_choice_answer(selected: str, correct: str) -> dict:
    clf = classify_choice(selected, correct)
    return {
        "type": "choice",
        "selected": selected,
        "correct": clf == "A",
        "classification": clf,
        "points": POINTS[clf],
        "reviewed": True,
        "auto_graded": True,
    }


def grade_justify_answer(student_text: str, answer_key: str) -> dict:
    clf = classify_justify(student_text, answer_key)
    return {
        "type": "justify",
        "text": student_text.strip(),
        "classification": clf,
        "points": POINTS[clf],
        "reviewed": True,
        "auto_graded": True,
    }


def summarize_answers(answers: list) -> dict:
    counts = {"A": 0, "PA": 0, "NA": 0}
    total_points = 0.0
    for ans in answers:
        clf = ans.get("classification", "NA")
        if clf not in counts:
            clf = "NA"
        counts[clf] += 1
        total_points += ans.get("points", POINTS.get(clf, 0))
    max_points = float(len(answers))
    return {
        "counts": counts,
        "total_points": total_points,
        "max_points": max_points,
        "percent": (total_points / max_points * 100) if max_points else 0,
    }
