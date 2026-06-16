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

# Recuperação por justificativa em questões UC2 com MC errada.
UC2_RECOVERY_POINTS = {"A": 0.5, "PA": 0.25, "NA": 0.0}

# Meta da prova (1ª tentativa): 17+ acertos na MC e nota A (17+ pts em prova de 20).
EXAM_RECOVERY_MIN_MC = 17
EXAM_RECOVERY_MIN_POINTS = 17
EXAM_MAX_ATTEMPTS = 2


def exam_passing_minimum(total_questions: int) -> int:
    """Limite mínimo de acertos/nota A, proporcional se a prova tiver menos de 17 questões."""
    return min(EXAM_RECOVERY_MIN_MC, max(1, int(total_questions)))


def exam_needs_recovery(summary: dict, total_questions: int) -> bool:
    """True se o aluno pode fazer recuperação (não atingiu 17 MC ou nota A)."""
    minimum = exam_passing_minimum(total_questions)
    total_points = float(summary.get("total_points", 0))
    if summary.get("grading_model") == "uc2_recovery":
        mc_correct = int(summary.get("mc_correct", 0))
        return mc_correct < minimum or total_points < minimum
    counts = summary.get("counts") or {}
    a_count = int(counts.get("A", 0))
    return a_count < minimum or total_points < minimum


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


def grade_choice_with_justify(
    selected: str, correct: str, justify_text: str, answer_key: str
) -> dict:
    """Questão composta UC2: MC vale 1 pt; justificativa recupera até 0,5 se MC errada."""
    mc_clf = classify_choice(selected, correct)
    justify_clf = classify_justify(justify_text, answer_key)
    mc_correct = mc_clf == "A"
    mc_points = 1.0 if mc_correct else 0.0
    recovery = 0.0 if mc_correct else UC2_RECOVERY_POINTS.get(justify_clf, 0.0)

    return {
        "type": "choice_with_justify",
        "selected": selected,
        "justify_text": justify_text.strip(),
        "mc_correct": mc_correct,
        "mc_classification": mc_clf,
        "justify_classification": justify_clf,
        "classification": mc_clf if mc_correct else justify_clf,
        "mc_points": mc_points,
        "recovery_points": recovery,
        "points": mc_points + recovery,
        "reviewed": True,
        "auto_graded": True,
    }


def apply_answer_classification(ans: dict, classification: str) -> dict:
    """Atualiza classificação manual do professor e recalcula pontos da resposta."""
    clf = classification if classification in CLASSIFICATIONS else "NA"
    updated = {**ans, "classification": clf, "reviewed": True, "auto_graded": False}

    if ans.get("type") == "choice_with_justify":
        mc_correct = bool(ans.get("mc_correct"))
        updated["justify_classification"] = clf if not mc_correct else ans.get(
            "justify_classification", classify_justify(ans.get("justify_text", ""), "")
        )
        if mc_correct:
            updated["mc_points"] = 1.0
            updated["recovery_points"] = 0.0
            updated["points"] = 1.0
        else:
            updated["recovery_points"] = UC2_RECOVERY_POINTS.get(clf, 0.0)
            updated["points"] = updated["recovery_points"]
        return updated

    updated["points"] = POINTS[clf]
    if ans.get("type") == "choice":
        updated["correct"] = clf == "A"
    return updated


def _summarize_uc2_exam(answers: list) -> dict:
    mc_points = sum(float(a.get("mc_points", 0)) for a in answers)
    recovery_raw = sum(float(a.get("recovery_points", 0)) for a in answers)
    max_points = float(len(answers))
    gap = max(0.0, max_points - mc_points)
    recovery_capped = min(recovery_raw, gap)
    total_points = mc_points + recovery_capped

    counts = {"A": 0, "PA": 0, "NA": 0}
    mc_correct_count = 0
    for a in answers:
        if a.get("mc_correct"):
            mc_correct_count += 1
        jclf = a.get("justify_classification", "NA")
        if not a.get("mc_correct") and jclf in counts:
            counts[jclf] += 1

    return {
        "counts": counts,
        "mc_correct": mc_correct_count,
        "mc_points": mc_points,
        "recovery_points": recovery_capped,
        "recovery_raw": recovery_raw,
        "total_points": total_points,
        "max_points": max_points,
        "percent": (total_points / max_points * 100) if max_points else 0,
        "mc_percent": (mc_points / max_points * 100) if max_points else 0,
        "grading_model": "uc2_recovery",
    }


def summarize_answers(answers: list) -> dict:
    if any(a.get("type") == "choice_with_justify" for a in answers):
        return _summarize_uc2_exam(answers)

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
