"""Gera PDF da prova no formato original com nome e respostas do aluno."""
from __future__ import annotations

import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

CHOICE_COLORS = ("Vermelho", "Azul", "Amarelo", "Verde")
_UNICODE_FONT = False


def safe_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name)
    ascii_name = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    cleaned = re.sub(r"[^\w\s-]", "", ascii_name)
    return re.sub(r"\s+", "_", cleaned.strip()) or "aluno"


def _matplotlib_font_paths() -> list[tuple[Path, Path]]:
    """DejaVu via matplotlib (disponível no Streamlit Cloud com requirements.txt)."""
    try:
        import matplotlib

        ttf_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        regular = ttf_dir / "DejaVuSans.ttf"
        bold = ttf_dir / "DejaVuSans-Bold.ttf"
        if regular.exists():
            return [(regular, bold if bold.exists() else regular)]
    except Exception:
        pass
    return []


def _font_candidates() -> list[tuple[Path, Path]]:
    paths: list[tuple[Path, Path]] = []
    paths.extend(_matplotlib_font_paths())

    bundled = Path(__file__).resolve().parent / "fonts"
    paths.extend(
        [
            (bundled / "DejaVuSans.ttf", bundled / "DejaVuSans-Bold.ttf"),
        ]
    )

    if sys.platform == "win32":
        win = Path("C:/Windows/Fonts")
        paths.extend(
            [
                (win / "arial.ttf", win / "arialbd.ttf"),
                (win / "calibri.ttf", win / "calibrib.ttf"),
            ]
        )
    else:
        for linux in (
            Path("/usr/share/fonts/truetype/dejavu"),
            Path("/usr/share/fonts/TTF"),
            Path("/usr/share/fonts/dejavu"),
        ):
            paths.append((linux / "DejaVuSans.ttf", linux / "DejaVuSans-Bold.ttf"))

    return [(r, b) for r, b in paths if r.exists()]


def _setup_fonts(pdf: FPDF) -> str:
    global _UNICODE_FONT
    for regular, bold in _font_candidates():
        try:
            pdf.add_font("AppFont", "", str(regular))
            pdf.add_font("AppFont", "B", str(bold if bold.exists() else regular))
            _UNICODE_FONT = True
            return "AppFont"
        except Exception:
            continue
    _UNICODE_FONT = False
    return "Helvetica"


def _pdf_text(text: str) -> str:
    """Garante texto compatível com a fonte ativa (Unicode ou Latin-1)."""
    text = (text or " ").replace("\u2014", "-").replace("\u2013", "-")
    text = text.replace("\u2190", "<-").replace("\u2022", "*")
    if _UNICODE_FONT:
        return text
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return ascii_text.encode("latin-1", "replace").decode("latin-1")


def _write_line(pdf: FPDF, font: str, style: str, size: int, text: str, h: float = 6):
    pdf.set_x(pdf.l_margin)
    pdf.set_font(font, style, size)
    pdf.multi_cell(pdf.epw, h, _pdf_text(text))


def _format_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def build_exam_lines(
    exam: dict,
    submission: dict,
    include_gabarito: bool = False,
    *,
    include_correction: bool | None = None,
) -> list[str]:
    if include_correction is None:
        include_correction = bool(submission.get("correction_released"))
    lines = [
        f"PROVA: {exam.get('title', 'Prova')}",
        f"Aluno: {submission.get('student_name', '')}",
        f"Data de envio: {_format_date(submission.get('submitted_at', ''))}",
        "",
    ]
    summary = submission.get("summary")
    if include_correction and summary:
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

        if q.get("type") in ("choice", "choice_with_justify"):
            lines.append(f"Pergunta {num}: {q['question']}")
            for j, letter in enumerate("ABCD"):
                color = CHOICE_COLORS[j]
                opt = q["options"][j]
                suffix = ""
                if ans.get("selected") == letter:
                    suffix = " ← RESPOSTA DO ALUNO"
                lines.append(f"Alternativa {letter} ({color}): {opt}{suffix}")
            if q.get("type") == "choice_with_justify":
                lines.append(
                    f"Justificativa do aluno: {ans.get('justify_text', '').strip() or '(sem resposta)'}"
                )
                if include_correction:
                    mc_ok = "Correta" if ans.get("mc_correct") else "Incorreta"
                    lines.append(f"MC: {mc_ok} | Pontos: {ans.get('points', 0):.1f}")
                    if not ans.get("mc_correct"):
                        lines.append(
                            f"Classificação da justificativa: {ans.get('justify_classification', clf)}"
                        )
            elif include_correction:
                lines.append(f"Classificação: {clf}")
        else:
            lines.append(f"Pergunta {num}: {q['question']} (JUSTIFICATIVA)")
            lines.append(f"Resposta do aluno: {ans.get('text', '').strip() or '(sem resposta)'}")
            if include_gabarito and q.get("answer_key"):
                lines.append(f"Gabarito: {q['answer_key']}")
            if include_correction:
                lines.append(f"Classificação: {clf}")
        lines.append("")

    return lines


def build_exam_pdf_bytes(
    exam: dict,
    submission: dict,
    include_gabarito: bool = False,
    *,
    include_correction: bool | None = None,
) -> bytes:
    if include_correction is None:
        include_correction = bool(submission.get("correction_released"))
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
    if include_correction and summary:
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

        if q.get("type") in ("choice", "choice_with_justify"):
            _write_line(pdf, font, "B", 11, f"Pergunta {num}: {q['question']}")
            for j, letter in enumerate("ABCD"):
                color = CHOICE_COLORS[j]
                opt = q["options"][j]
                line = f"Alternativa {letter} ({color}): {opt}"
                if ans.get("selected") == letter:
                    line += "  ← RESPOSTA DO ALUNO"
                _write_line(pdf, font, "", 10, line, h=5)
            if q.get("type") == "choice_with_justify":
                _write_line(pdf, font, "", 10, "Justificativa do aluno:")
                _write_line(
                    pdf,
                    font,
                    "",
                    10,
                    ans.get("justify_text", "").strip() or "(sem resposta)",
                    h=5,
                )
                if include_gabarito and q.get("answer_key"):
                    _write_line(
                        pdf, font, "B", 10, f"Gabarito justificativa: {q['answer_key']}", h=5
                    )
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

        if include_correction:
            if q.get("type") == "choice_with_justify":
                mc_ok = "Correta" if ans.get("mc_correct") else "Incorreta"
                _write_line(
                    pdf,
                    font,
                    "B",
                    10,
                    f"MC: {mc_ok} | Justificativa: {ans.get('justify_classification', clf)} | "
                    f"Pontos: {ans.get('points', 0):.1f}",
                    h=5,
                )
            elif q.get("type") in ("choice", "justify"):
                _write_line(pdf, font, "B", 10, f"Classificação: {clf}", h=5)
        pdf.ln(3)

    raw = pdf.output()
    return bytes(raw) if isinstance(raw, (bytes, bytearray)) else raw.encode("latin-1")


def export_filename(exam: dict, submission: dict) -> str:
    title = safe_filename(exam.get("title", "prova"))
    student = safe_filename(submission.get("student_name", "aluno"))
    return f"prova_{title}_{student}.pdf"
