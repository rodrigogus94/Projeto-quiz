"""Exportação/importação de resultados de alunos via arquivo.

O aluno baixa um arquivo .json com todos os seus resultados (quizzes e provas)
e envia ao professor. O professor importa o arquivo: o aluno é identificado
automaticamente, o professor confirma a quem os resultados pertencem e os
dados são adicionados sem duplicar o que já existe.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from quiz_storage import (
    add_exam_submission,
    get_exam,
    get_material,
    load_exam_submissions,
    load_leaderboard,
    save_leaderboard,
)

RESULT_FILE_KIND = "projeto-quiz-resultados"
RESULT_FILE_VERSION = 1
# Sal usado no checksum para detectar arquivos editados manualmente.
_CHECKSUM_SALT = "projeto-quiz-2026-resultados-v1"


def _checksum(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "checksum"}
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((canonical + _CHECKSUM_SALT).encode("utf-8")).hexdigest()


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


def build_student_export(name: str, email: str | None) -> dict:
    """Reúne todos os resultados (quizzes e provas) do aluno em um payload."""
    name_key = _norm(name)
    email_key = _norm(email)

    quiz_results = []
    for e in load_leaderboard():
        if (email_key and _norm(e.get("student_email")) == email_key) or (
            name_key and _norm(e.get("name")) == name_key
        ):
            entry = dict(e)
            mat = get_material(e.get("material_id") or "")
            entry["material_title"] = mat["title"] if mat else None
            quiz_results.append(entry)

    exam_submissions = []
    for s in load_exam_submissions():
        if (name_key and _norm(s.get("student_name")) == name_key) or (
            email_key and _norm(s.get("student_email")) == email_key
        ):
            sub = dict(s)
            exam = get_exam(s.get("exam_id") or "")
            sub["exam_title"] = exam["title"] if exam else None
            exam_submissions.append(sub)

    payload = {
        "kind": RESULT_FILE_KIND,
        "version": RESULT_FILE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "student": {"name": name.strip(), "email": (email or "").strip().lower() or None},
        "quiz_results": quiz_results,
        "exam_submissions": exam_submissions,
    }
    payload["checksum"] = _checksum(payload)
    return payload


def export_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _format_when(iso_ts: str | None) -> str:
    if not iso_ts:
        return "—"
    return iso_ts[:16].replace("T", " ") + " UTC"


def export_markdown(payload: dict) -> str:
    """Versão legível dos resultados (o professor importa o arquivo .json)."""
    student = payload.get("student") or {}
    lines = [
        f"# Resultados — {student.get('name', 'Aluno')}",
        "",
        f"- **E-mail:** {student.get('email') or '—'}",
        f"- **Gerado em:** {_format_when(payload.get('generated_at'))}",
        f"- **Código de verificação:** `{payload.get('checksum', '')}`",
        "",
        "> Para registrar no sistema, o professor deve importar o arquivo **.json** "
        "correspondente (aba Resultados → Importar arquivo de resultados).",
        "",
    ]

    quiz_results = payload.get("quiz_results") or []
    if quiz_results:
        lines += ["## Quizzes", ""]
        for e in quiz_results:
            total = e.get("total") or 0
            score = e.get("score", 0)
            pct = (score / total * 100) if total else 0.0
            title = e.get("material_title") or "(material desconhecido)"
            lines += [
                f"### {title}",
                f"- Acertos: **{score}/{total}** ({pct:.1f}%)",
                f"- Quando: {_format_when(e.get('submitted_at'))}",
                "",
            ]

    exam_submissions = payload.get("exam_submissions") or []
    if exam_submissions:
        lines += ["## Provas", ""]
        for s in exam_submissions:
            title = s.get("exam_title") or "(prova desconhecida)"
            summary = s.get("summary") or {}
            counts = summary.get("counts", {})
            pct = summary.get("percent")
            pct_txt = f"{pct:.0f}%" if pct is not None else "—"
            lines += [
                f"### {title}",
                f"- Pontuação: **{summary.get('total_points', 0):.1f}** / "
                f"{summary.get('max_points', 0):.0f} ({pct_txt})",
                f"- A: {counts.get('A', 0)} · PA: {counts.get('PA', 0)} · "
                f"NA: {counts.get('NA', 0)}",
                f"- Enviada em: {_format_when(s.get('submitted_at'))}",
                "",
            ]

    if not quiz_results and not exam_submissions:
        lines.append("_Nenhum resultado registrado._")
    return "\n".join(lines)


def export_markdown_bytes(payload: dict) -> bytes:
    return export_markdown(payload).encode("utf-8")


def _export_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _norm(name)).strip("-") or "aluno"


def export_filename(name: str, *, ext: str = "json") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return f"resultados_{_export_slug(name)}_{stamp}.{ext}"


def parse_student_export(raw: bytes) -> tuple[dict | None, str | None]:
    """Lê e valida um arquivo de resultados. Retorna (payload, erro)."""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "Arquivo inválido: não é um JSON de resultados gerado pelo app."

    if not isinstance(payload, dict) or payload.get("kind") != RESULT_FILE_KIND:
        return None, "Arquivo inválido: não é um arquivo de resultados deste app."
    student = payload.get("student") or {}
    if not student.get("name"):
        return None, "Arquivo inválido: identificação do aluno ausente."
    if not isinstance(payload.get("quiz_results"), list) or not isinstance(
        payload.get("exam_submissions"), list
    ):
        return None, "Arquivo inválido: estrutura de resultados ausente."
    if payload.get("checksum") != _checksum(payload):
        return None, (
            "Arquivo corrompido ou alterado manualmente: o código de verificação não confere. "
            "Peça ao aluno para gerar um novo arquivo."
        )
    return payload, None


def _quiz_dedupe_key(entry: dict) -> tuple:
    return (
        entry.get("material_id"),
        _norm(entry.get("name")),
        entry.get("score"),
        entry.get("total"),
        entry.get("submitted_at"),
    )


def preview_import(payload: dict, target_name: str) -> dict:
    """Verifica, antes de importar, o que é novo e o que já está no sistema."""
    name_key = _norm(target_name)

    existing_quiz = {_quiz_dedupe_key(e) for e in load_leaderboard()}
    quiz_new = quiz_existing = 0
    for raw in payload.get("quiz_results", []):
        key = (
            raw.get("material_id"),
            name_key,
            raw.get("score"),
            raw.get("total"),
            raw.get("submitted_at"),
        )
        if key in existing_quiz:
            quiz_existing += 1
        else:
            quiz_new += 1

    existing_sub_ids = {s.get("id") for s in load_exam_submissions()}
    exam_new = exam_existing = 0
    for raw in payload.get("exam_submissions", []):
        if raw.get("id") in existing_sub_ids:
            exam_existing += 1
        else:
            exam_new += 1

    return {
        "quiz_new": quiz_new,
        "quiz_existing": quiz_existing,
        "exam_new": exam_new,
        "exam_existing": exam_existing,
        "has_new": (quiz_new + exam_new) > 0,
    }


def import_results(payload: dict, target_name: str, target_email: str | None) -> dict:
    """Adiciona os resultados do arquivo ao aluno confirmado pelo professor.

    Resultados já existentes (mesma tentativa/envio) são ignorados.
    """
    target_name = target_name.strip()
    target_email = _norm(target_email) or None

    board = load_leaderboard()
    existing_quiz = {_quiz_dedupe_key(e) for e in board}
    quiz_added = quiz_skipped = 0
    for raw_entry in payload.get("quiz_results", []):
        entry = {
            "material_id": raw_entry.get("material_id"),
            "name": target_name,
            "score": raw_entry.get("score", 0),
            "total": raw_entry.get("total", 0),
            "responses": raw_entry.get("responses", []),
            "student_email": target_email or _norm(raw_entry.get("student_email")) or None,
            "student_user_id": raw_entry.get("student_user_id"),
            "submitted_at": raw_entry.get("submitted_at"),
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
        key = _quiz_dedupe_key(entry)
        if key in existing_quiz:
            quiz_skipped += 1
            continue
        existing_quiz.add(key)
        board.append(entry)
        quiz_added += 1
    if quiz_added:
        save_leaderboard(board)

    existing_sub_ids = {s.get("id") for s in load_exam_submissions()}
    exam_added = exam_skipped = 0
    for raw_sub in payload.get("exam_submissions", []):
        if raw_sub.get("id") in existing_sub_ids:
            exam_skipped += 1
            continue
        sub = {k: v for k, v in raw_sub.items() if k != "exam_title"}
        sub["student_name"] = target_name
        sub["student_email"] = target_email or _norm(raw_sub.get("student_email")) or None
        sub["imported_at"] = datetime.now(timezone.utc).isoformat()
        add_exam_submission(sub)
        existing_sub_ids.add(sub.get("id"))
        exam_added += 1

    return {
        "quiz_added": quiz_added,
        "quiz_skipped": quiz_skipped,
        "exam_added": exam_added,
        "exam_skipped": exam_skipped,
    }
