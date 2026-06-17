from __future__ import annotations

from io import BytesIO

import pdfplumber
import streamlit as st

from pdf_parser import parse_exam_from_text, parse_questions_from_text

SUPPORTED_UPLOAD_EXTENSIONS = (".pdf", ".md", ".markdown", ".txt")
UPLOAD_FILE_TYPES = ["pdf", "md", "markdown", "txt"]


def extract_text_from_pdf(pdf_file) -> str:
    with pdfplumber.open(pdf_file) as pdf:
        parts = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)


def _normalize_markdown_source(text: str) -> str:
    """Remove cercas de bloco de código comuns em arquivos .md."""
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    while lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def read_text_from_bytes(content: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        with pdfplumber.open(BytesIO(content)) as pdf:
            parts = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
            return "\n".join(parts)
    if name.endswith((".md", ".markdown", ".txt")):
        text = content.decode("utf-8-sig")
        if name.endswith((".md", ".markdown")):
            text = _normalize_markdown_source(text)
        return text
    raise ValueError(
        f"Formato não suportado ({name or 'sem extensão'}). "
        f"Use: {', '.join(SUPPORTED_UPLOAD_EXTENSIONS)}."
    )


def read_text_from_upload(uploaded_file) -> str:
    name = (getattr(uploaded_file, "name", None) or "").lower()
    uploaded_file.seek(0)
    if name.endswith(".pdf"):
        return extract_text_from_pdf(uploaded_file)
    if name.endswith((".md", ".markdown", ".txt")):
        raw = uploaded_file.read()
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
        if name.endswith((".md", ".markdown")):
            text = _normalize_markdown_source(text)
        return text
    raise ValueError(
        f"Formato não suportado ({name or 'sem extensão'}). "
        f"Use: {', '.join(SUPPORTED_UPLOAD_EXTENSIONS)}."
    )


def parse_questions_from_bytes(
    content: bytes, filename: str, show_warnings: bool = True
) -> list:
    full_text = read_text_from_bytes(content, filename)
    warnings = []
    questions = parse_questions_from_text(full_text, warnings=warnings)
    if show_warnings:
        for msg in warnings:
            st.warning(msg)
    return questions


def parse_exam_from_bytes(
    content: bytes, filename: str, show_warnings: bool = True
) -> list:
    full_text = read_text_from_bytes(content, filename)
    warnings = []
    questions = parse_exam_from_text(full_text, warnings=warnings)
    if show_warnings:
        for msg in warnings:
            st.warning(msg)
    return questions


def parse_questions_from_upload(uploaded_file, show_warnings: bool = True) -> list:
    full_text = read_text_from_upload(uploaded_file)
    warnings = []
    questions = parse_questions_from_text(full_text, warnings=warnings)
    if show_warnings:
        for msg in warnings:
            st.warning(msg)
    return questions


def parse_exam_from_upload(uploaded_file, show_warnings: bool = True) -> list:
    full_text = read_text_from_upload(uploaded_file)
    warnings = []
    questions = parse_exam_from_text(full_text, warnings=warnings)
    if show_warnings:
        for msg in warnings:
            st.warning(msg)
    return questions


def parse_questions_from_pdf(pdf_file, show_warnings: bool = True) -> list:
    return parse_questions_from_upload(pdf_file, show_warnings=show_warnings)


def parse_exam_from_pdf(pdf_file, show_warnings: bool = True) -> list:
    return parse_exam_from_upload(pdf_file, show_warnings=show_warnings)


def validate_questions(questions: list) -> tuple[list, list]:
    valid = []
    errors = []
    for i, q in enumerate(questions):
        opts = [o.strip() for o in q.get("options", [])]
        correct = q.get("correct", "A")
        text = q.get("question", "").strip()
        if not text:
            errors.append(f"Questão {i + 1}: enunciado vazio.")
            continue
        if len(opts) != 4 or any(not o for o in opts):
            errors.append(f"Questão {i + 1}: preencha as 4 alternativas.")
            continue
        if correct not in "ABCD":
            errors.append(f"Questão {i + 1}: alternativa correta inválida.")
            continue
        valid.append({"question": text, "options": opts, "correct": correct})
    return valid, errors
