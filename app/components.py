"""Componentes visuais reutilizáveis."""
from __future__ import annotations

import streamlit as st

from auto_grade import CLASSIFICATIONS, LABELS
from ui_theme import classification_badge_colors

_STUDENT_AREA_CSS = """
.kahoot-student-hero {
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid var(--kahoot-border);
    border-radius: 12px;
    background: color-mix(in srgb, var(--secondary-background-color) 55%, transparent);
}
.kahoot-student-hero h3 {
    margin: 0 0 0.35rem 0;
    font-size: 1.15rem;
    color: var(--text-color);
}
.kahoot-student-hero p {
    margin: 0;
    color: var(--kahoot-text-muted);
    font-size: 0.92rem;
    line-height: 1.5;
}
.kahoot-empty-state {
    text-align: center;
    padding: 3rem 2rem;
    margin: 1.5rem auto 0;
    max-width: 540px;
    border: 1px solid var(--kahoot-border);
    border-radius: 14px;
    background: color-mix(in srgb, var(--secondary-background-color) 50%, transparent);
}
.kahoot-empty-icon {
    font-size: 2.75rem;
    line-height: 1;
    margin-bottom: 0.75rem;
}
.kahoot-empty-title {
    margin: 0 0 0.5rem 0;
    font-size: 1.2rem;
    color: var(--text-color);
}
.kahoot-empty-message {
    margin: 0;
    color: var(--kahoot-text-muted);
    font-size: 0.95rem;
    line-height: 1.55;
}
.kahoot-empty-hint {
    margin: 1rem 0 0 0;
    padding-top: 1rem;
    border-top: 1px solid var(--kahoot-border);
    color: var(--kahoot-text-subtle);
    font-size: 0.85rem;
}
.kahoot-quiz-pill {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    margin-right: 0.35rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--primary-color);
    background: color-mix(in srgb, var(--primary-color) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--primary-color) 35%, transparent);
}
.kahoot-config-title {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--kahoot-text-subtle);
    margin-bottom: 0.75rem;
}
.kahoot-flow-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    margin-bottom: 0.75rem;
    font-size: 0.88rem;
    color: var(--kahoot-text-muted);
}
.kahoot-flow-meta strong {
    color: var(--text-color);
}
.kahoot-question-card {
    padding: 1.25rem 1.35rem;
    margin: 0.75rem 0 1rem;
    border: 1px solid var(--kahoot-border);
    border-radius: 12px;
    background: color-mix(in srgb, var(--secondary-background-color) 40%, transparent);
}
.kahoot-question-card h4 {
    margin: 0 0 0.85rem 0;
    font-size: 1.05rem;
    line-height: 1.45;
    color: var(--text-color);
}
.kahoot-result-banner {
    padding: 1.1rem 1.35rem;
    margin-bottom: 1rem;
    border-radius: 12px;
    border: 1px solid var(--kahoot-alert-success-border);
    background: var(--kahoot-alert-success-bg);
    color: var(--kahoot-alert-success-text);
}
.kahoot-result-banner h3 {
    margin: 0 0 0.25rem 0;
    font-size: 1.15rem;
}
.kahoot-result-banner p {
    margin: 0;
    font-size: 0.92rem;
    opacity: 0.9;
}
.kahoot-exam-q {
    padding: 0.25rem 0 0.5rem;
}
"""


def inject_student_area_css() -> None:
    st.markdown(f"<style>{_STUDENT_AREA_CSS}</style>", unsafe_allow_html=True)


def render_empty_state(
    *,
    icon: str,
    title: str,
    message: str,
    hint: str | None = None,
) -> None:
    hint_html = (
        f'<p class="kahoot-empty-hint">{hint}</p>' if hint else ""
    )
    st.markdown(
        f"""
        <div class="kahoot-empty-state">
            <div class="kahoot-empty-icon">{icon}</div>
            <h3 class="kahoot-empty-title">{title}</h3>
            <p class="kahoot-empty-message">{message}</p>
            {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_flow_header(
    *,
    label: str,
    current: int,
    total: int,
    student_name: str | None = None,
) -> None:
    pct = (current / total) if total > 0 else 0.0
    name_html = (
        f'<span><strong>Aluno:</strong> {student_name}</span>'
        if student_name
        else ""
    )
    st.markdown(
        f"""
        <div class="kahoot-flow-meta">
            <span><strong>{label}</strong></span>
            {name_html}
            <span><strong>Progresso:</strong> {current} de {total}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(pct)


def render_result_banner(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="kahoot-result-banner">
            <h3>{title}</h3>
            <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_student_hero(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="kahoot-student-hero">
            <h3>{title}</h3>
            <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_classification_badge(classification: str) -> None:
    colors = classification_badge_colors()
    clf = classification if classification in CLASSIFICATIONS else "NA"
    st.markdown(
        f'<span style="background:{colors[clf]};color:white;padding:4px 10px;'
        f'border-radius:6px;font-weight:bold;">{LABELS[clf]}</span>',
        unsafe_allow_html=True,
    )
