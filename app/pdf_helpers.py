from __future__ import annotations

import pdfplumber
import streamlit as st

from pdf_parser import parse_exam_from_text, parse_questions_from_text


def extract_text_from_pdf(pdf_file) -> str:
    with pdfplumber.open(pdf_file) as pdf:
        parts = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)


def parse_questions_from_pdf(pdf_file, show_warnings: bool = True) -> list:
    full_text = extract_text_from_pdf(pdf_file)
    warnings = []
    questions = parse_questions_from_text(full_text, warnings=warnings)
    if show_warnings:
        for msg in warnings:
            st.warning(msg)
    return questions


def parse_exam_from_pdf(pdf_file, show_warnings: bool = True) -> list:
    full_text = extract_text_from_pdf(pdf_file)
    warnings = []
    questions = parse_exam_from_text(full_text, warnings=warnings)
    if show_warnings:
        for msg in warnings:
            st.warning(msg)
    return questions


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
