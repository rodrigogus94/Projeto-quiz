from __future__ import annotations

import streamlit as st

import auth_users

from app.auth_ui import render_student_register_form


def _professor_nav_sections(show_admin_tab: bool) -> list[tuple[str, str]]:
    sections = [
        ("materials", "📚 Materiais"),
        ("edit", "✏️ Editar questões"),
        ("exams", "📝 Provas"),
        ("students", "👥 Alunos cadastrados"),
        ("results", "📊 Resultados"),
        ("config", "🔐 Contas"),
    ]
    if show_admin_tab:
        sections.append(("admin", "🛡️ Aprovações"))
    return sections


def render_professor_sidebar_nav():
    current_user = st.session_state.get("current_user") or {}
    show_admin_tab = auth_users.is_system_admin(current_user.get("email")) or bool(
        current_user.get("is_admin")
    )
    sections = _professor_nav_sections(show_admin_tab)
    section_keys = [key for key, _ in sections]
    section_labels = {key: label for key, label in sections}

    if st.session_state.professor_section not in section_keys:
        st.session_state.professor_section = section_keys[0]

    st.sidebar.markdown('<div class="kahoot-sidebar-nav-title">Navegação</div>', unsafe_allow_html=True)
    st.sidebar.radio(
        "Seção do professor",
        options=section_keys,
        format_func=lambda key: section_labels[key],
        key="professor_section",
        label_visibility="collapsed",
    )
    st.sidebar.divider()


def render_student_sidebar_nav():
    st.sidebar.markdown('<div class="kahoot-sidebar-nav-title">Navegação</div>', unsafe_allow_html=True)
    st.sidebar.radio(
        "Seção do aluno",
        options=["quiz", "exam"],
        format_func=lambda key: "🎮 Quiz" if key == "quiz" else "📝 Provas",
        key="student_section",
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    _render_student_register_sidebar()


def _render_student_register_sidebar():
    from app.student_views import approved_students

    registered = approved_students()
    with st.sidebar.expander("📝 Cadastrar-me", expanded=not registered):
        if render_student_register_form("register_in_sidebar"):
            st.rerun()
