"""Gera PDF da prova no formato original com nome e respostas do aluno."""
from __future__ import annotations

import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

CHOICE_COLORS = ("Vermelho", "Azul", "Amarelo", "Verde")
_FONT_REGISTERED = False


def safe_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name)
    ascii_name = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    cleaned = re.sub(r"[^\w\s-]", "", ascii_name)
    return re.sub(r"\s+", "_", cleaned.strip()) or "aluno"


def _font_candidates() -> list[tuple[str, str]]:
    paths = []
    if sys.platform == "win32":
        win = Path("C:/Windows/Fonts")
        paths.extend(
            [
                (win / "arial.ttf", win / "arialbd.ttf"),
                (win / "calibri.ttf", win / "calibrib.ttf"),
            ]
        )
    else:
        linux = Path("/usr/share/fonts/truetype/dejavu")
        paths.extend(
            [
                (linux / "DejaVuSans.ttf", linux / "DejaVuSans-Bold.ttf"),
            ]
        )
    return [(str(r), str(b)) for r, b in paths if r.exists()]


def _setup_fonts(pdf: FPDF) -> str:
    global _FONT_REGISTERED
    for regular, bold in _font_candidates():
        try:
            pdf.add_font("AppFont", "", regular)
            if Path(bold).exists():
                pdf.add_font("AppFont", "B", bold)
            else:
                pdf.add_font("AppFont", "B", regular)
            _FONT_REGISTERED = True
            return "AppFont"
        except Exception:
            continue
    return "Helvetica"


def _write_line(pdf: FPDF, font: str, style: str, size: int, text: str, h: float = 6):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(font, style, size)
    pdf.multi_cell(pdf.epw, h, text or " ")


def _format_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def build_exam_lines(
    exam: dict, submission: dict, include_gabarito: bool = False
) -> list[str]:
    lines = [
        f"PROVA: {exam.get('title', 'Prova')}",
        f"Aluno: {submission.get('student_name', '')}",
        f"Data de envio: {_format_date(submission.get('submitted_at', ''))}",
        "",
    ]
    summary = submission.get("summary")
    if summary:
        c = summary.get("counts", {})
        lines.append(
            f"Resultado: A={c.get('A', 0)} | PA={c.get('PA', 0)} | NA={c.get('NA', 0)} "
            f"— {summary.get('total_points', 0):.1f}/{summary.get('max_points', 0):.0f} pts"
        )
        lines.append("")

    questions = exam.get("questions", [])
    answers = submission.get("answers", [])

    for i, q in enumerate(questions):
        num = i + 1
        ans = answers[i] if i < len(answers) else {}
        clf = ans.get("classification", "—")

        if q.get("type") == "choice":
            lines.append(f"Pergunta {num}: {q['question']}")
            for j, letter in enumerate("ABCD"):
                color = CHOICE_COLORS[j]
                opt = q["options"][j]
                suffix = ""
                if ans.get("selected") == letter:
                    suffix = " ← RESPOSTA DO ALUNO"
                lines.append(f"Alternativa {letter} ({color}): {opt}{suffix}")
            lines.append(f"Classificação: {clf}")
        else:
            lines.append(f"Pergunta {num}: {q['question']} (JUSTIFICATIVA)")
            lines.append(f"Resposta do aluno: {ans.get('text', '').strip() or '(sem resposta)'}")
            if include_gabarito and q.get("answer_key"):
                lines.append(f"Gabarito: {q['answer_key']}")
            lines.append(f"Classificação: {clf}")
        lines.append("")

    return lines


def build_exam_pdf_bytes(
    exam: dict, submission: dict, include_gabarito: bool = False
) -> bytes:
    pdf = FPDF()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    font = _setup_fonts(pdf)

    _write_line(pdf, font, "B", 14, exam.get("title", "Prova"), h=8)
    pdf.ln(2)
    _write_line(pdf, font, "", 11, f"Aluno: {submission.get('student_name', '')}")
    _write_line(
        pdf, font, "", 11, f"Data de envio: {_format_date(submission.get('submitted_at', ''))}"
    )

    summary = submission.get("summary")
    if summary:
        c = summary.get("counts", {})
        _write_line(
            pdf,
            font,
            "",
            11,
            f"Resultado: A={c.get('A', 0)} | PA={c.get('PA', 0)} | NA={c.get('NA', 0)} — "
            f"{summary.get('total_points', 0):.1f}/{summary.get('max_points', 0):.0f} pontos",
        )
    pdf.ln(4)

    questions = exam.get("questions", [])
    answers = submission.get("answers", [])

    for i, q in enumerate(questions):
        num = i + 1
        ans = answers[i] if i < len(answers) else {}
        clf = ans.get("classification", "—")

        if q.get("type") == "choice":
            _write_line(pdf, font, "B", 11, f"Pergunta {num}: {q['question']}")
            for j, letter in enumerate("ABCD"):
                color = CHOICE_COLORS[j]
                opt = q["options"][j]
                line = f"Alternativa {letter} ({color}): {opt}"
                if ans.get("selected") == letter:
                    line += "  ← RESPOSTA DO ALUNO"
                _write_line(pdf, font, "", 10, line, h=5)
        else:
            _write_line(
                pdf, font, "B", 11, f"Pergunta {num}: {q['question']} (JUSTIFICATIVA)"
            )
            _write_line(pdf, font, "", 10, "Resposta do aluno:")
            _write_line(
                pdf, font, "", 10, ans.get("text", "").strip() or "(sem resposta)", h=5
            )
            if include_gabarito and q.get("answer_key"):
                _write_line(pdf, font, "B", 10, f"Gabarito: {q['answer_key']}", h=5)

        _write_line(pdf, font, "B", 10, f"Classificação: {clf}", h=5)
        pdf.ln(3)

    raw = pdf.output()
    return bytes(raw) if isinstance(raw, (bytes, bytearray)) else raw.encode("latin-1")


def export_filename(exam: dict, submission: dict) -> str:
    title = safe_filename(exam.get("title", "prova"))
    student = safe_filename(submission.get("student_name", "aluno"))
    return f"prova_{title}_{student}.pdf"
