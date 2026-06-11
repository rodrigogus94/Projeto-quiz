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
.kahoot-mc-option {
    display: block;
    padding: 0.55rem 0.85rem;
    margin: 0.35rem 0;
    border-radius: 8px;
    border: 1px solid var(--kahoot-border);
    font-size: 0.95rem;
    line-height: 1.4;
    color: var(--text-color);
}
.kahoot-mc-option--neutral {
    background: color-mix(in srgb, var(--secondary-background-color) 35%, transparent);
}
.kahoot-mc-option--yours {
    border-color: #3b82f6;
    background: color-mix(in srgb, #3b82f6 12%, var(--background-color));
    font-weight: 600;
}
.kahoot-mc-option--correct {
    border-color: #16a34a;
    background: color-mix(in srgb, #16a34a 14%, var(--background-color));
    font-weight: 600;
}
.kahoot-mc-option--wrong {
    border-color: #dc2626;
    background: color-mix(in srgb, #dc2626 10%, var(--background-color));
    font-weight: 600;
}
.kahoot-mc-tag {
    display: inline-block;
    margin-left: 0.5rem;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 700;
    vertical-align: middle;
}
.kahoot-mc-tag--yours { background: #3b82f6; color: #fff; }
.kahoot-mc-tag--correct { background: #16a34a; color: #fff; }
.kahoot-mc-tag--wrong { background: #dc2626; color: #fff; }
.kahoot-import-flash {
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
    border-radius: 10px;
    border: 1px solid var(--kahoot-alert-success-border);
    background: var(--kahoot-alert-success-bg);
    color: var(--kahoot-alert-success-text);
    font-weight: 600;
}
.kahoot-history-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 0.7rem 1rem;
    margin-bottom: 0.5rem;
    border: 1px solid var(--kahoot-border);
    border-radius: 10px;
    background: color-mix(in srgb, var(--secondary-background-color) 45%, transparent);
}
.kahoot-history-title {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-color);
    line-height: 1.35;
}
.kahoot-history-meta {
    margin: 0.15rem 0 0 0;
    font-size: 0.8rem;
    color: var(--kahoot-text-subtle);
}
.kahoot-history-badge {
    flex-shrink: 0;
    padding: 0.3rem 0.85rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 700;
    white-space: nowrap;
}
.kahoot-history-badge.good {
    color: #16a34a;
    background: rgba(34, 197, 94, 0.14);
    border: 1px solid rgba(34, 197, 94, 0.45);
}
.kahoot-history-badge.mid {
    color: #d97706;
    background: rgba(234, 179, 8, 0.14);
    border: 1px solid rgba(234, 179, 8, 0.5);
}
.kahoot-history-badge.bad {
    color: #dc2626;
    background: rgba(239, 68, 68, 0.13);
    border: 1px solid rgba(239, 68, 68, 0.45);
}
.kahoot-history-badge.neutral {
    color: var(--primary-color);
    background: color-mix(in srgb, var(--primary-color) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--primary-color) 35%, transparent);
}
.kahoot-history-empty {
    padding: 1.1rem 1.25rem;
    margin-bottom: 0.5rem;
    border: 1px dashed var(--kahoot-border);
    border-radius: 10px;
    text-align: center;
    color: var(--kahoot-text-muted);
    font-size: 0.9rem;
    background: color-mix(in srgb, var(--secondary-background-color) 30%, transparent);
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


def render_history_item(
    *,
    title: str,
    meta: str,
    badge_text: str,
    badge_tone: str = "neutral",
) -> None:
    """Linha de histórico (resultado de quiz ou prova) em formato de cartão."""
    tone = badge_tone if badge_tone in {"good", "mid", "bad", "neutral"} else "neutral"
    st.markdown(
        f"""
        <div class="kahoot-history-item">
            <div>
                <p class="kahoot-history-title">{title}</p>
                <p class="kahoot-history-meta">{meta}</p>
            </div>
            <span class="kahoot-history-badge {tone}">{badge_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_history_empty(message: str) -> None:
    st.markdown(
        f'<div class="kahoot-history-empty">{message}</div>',
        unsafe_allow_html=True,
    )


def render_import_flash(message: str) -> None:
    st.markdown(f'<div class="kahoot-import-flash">✅ {message}</div>', unsafe_allow_html=True)


def render_exam_mc_option(
    letter: str,
    text: str,
    *,
    show_correction: bool = False,
    is_selected: bool = False,
    is_correct: bool = False,
) -> None:
    """Exibe alternativa de prova com destaque visual (sua resposta / gabarito)."""
    css = "kahoot-mc-option--neutral"
    tags: list[str] = []
    if show_correction:
        if is_correct and is_selected:
            css = "kahoot-mc-option--correct"
            tags.append('<span class="kahoot-mc-tag kahoot-mc-tag--correct">✓ Sua resposta — correta</span>')
        elif is_correct:
            css = "kahoot-mc-option--correct"
            tags.append('<span class="kahoot-mc-tag kahoot-mc-tag--correct">✓ Alternativa correta</span>')
        elif is_selected:
            css = "kahoot-mc-option--wrong"
            tags.append('<span class="kahoot-mc-tag kahoot-mc-tag--wrong">✗ Sua escolha</span>')
    elif is_selected:
        css = "kahoot-mc-option--yours"
        tags.append('<span class="kahoot-mc-tag kahoot-mc-tag--yours">Sua resposta</span>')

    tag_html = "".join(tags)
    st.markdown(
        f'<div class="kahoot-mc-option {css}">'
        f"<strong>{letter})</strong> {text}{tag_html}</div>",
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
