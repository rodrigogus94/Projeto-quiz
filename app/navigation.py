from __future__ import annotations

import streamlit as st

import auth_users

PROFESSOR_NAV_KEY = "professor_nav_section"
STUDENT_NAV_KEY = "student_nav_section"
PROFESSOR_WIDGET_KEY = "professor_nav_widget"
STUDENT_WIDGET_KEY = "student_nav_widget"

STUDENT_SECTION_KEYS = ("quiz", "exam")


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


def _pick_valid_section(section: str | None, allowed: list[str]) -> str | None:
    if section and section in allowed:
        return section
    return None


def _sync_query_param(name: str, value: str) -> None:
    try:
        if st.query_params.get(name) != value:
            st.query_params[name] = value
    except Exception:
        pass


def _bootstrap_nav_section(
    persist_key: str,
    legacy_key: str,
    query_name: str,
    allowed: list[str],
    default: str,
) -> str:
    if persist_key not in st.session_state:
        from_query = _pick_valid_section(st.query_params.get(query_name), allowed)
        from_legacy = _pick_valid_section(st.session_state.get(legacy_key), allowed)
        st.session_state[persist_key] = from_legacy or from_query or default

    current = st.session_state[persist_key]
    if current not in allowed:
        st.session_state[persist_key] = allowed[0]
        current = st.session_state[persist_key]
    return current


def _init_nav_widget(widget_key: str, section: str) -> None:
    """Só define o widget na primeira vez; não sobrescreve clique do usuário."""
    if widget_key not in st.session_state:
        st.session_state[widget_key] = section


def _on_professor_nav_change() -> None:
    choice = st.session_state[PROFESSOR_WIDGET_KEY]
    st.session_state[PROFESSOR_NAV_KEY] = choice
    _sync_query_param("p_section", choice)


def _on_student_nav_change() -> None:
    choice = st.session_state[STUDENT_WIDGET_KEY]
    st.session_state[STUDENT_NAV_KEY] = choice
    _sync_query_param("s_section", choice)


def sync_nav_widgets_from_persist() -> None:
    """Alinha radios com a seção salva (usar só no recarregar do app)."""
    if PROFESSOR_NAV_KEY in st.session_state:
        st.session_state[PROFESSOR_WIDGET_KEY] = st.session_state[PROFESSOR_NAV_KEY]
    if STUDENT_NAV_KEY in st.session_state:
        st.session_state[STUDENT_WIDGET_KEY] = st.session_state[STUDENT_NAV_KEY]


def get_professor_section() -> str:
    return st.session_state.get(PROFESSOR_NAV_KEY, "materials")


def get_student_section() -> str:
    return st.session_state.get(STUDENT_NAV_KEY, "quiz")


def render_professor_sidebar_nav():
    current_user = st.session_state.get("current_user") or {}
    show_admin_tab = auth_users.is_system_admin(current_user.get("email")) or bool(
        current_user.get("is_admin")
    )
    sections = _professor_nav_sections(show_admin_tab)
    section_keys = [key for key, _ in sections]
    section_labels = {key: label for key, label in sections}

    current = _bootstrap_nav_section(
        PROFESSOR_NAV_KEY,
        "professor_section",
        "p_section",
        section_keys,
        section_keys[0],
    )
    _init_nav_widget(PROFESSOR_WIDGET_KEY, current)

    st.sidebar.markdown('<div class="kahoot-sidebar-nav-title">Navegação</div>', unsafe_allow_html=True)
    choice = st.sidebar.radio(
        "Seção do professor",
        options=section_keys,
        format_func=lambda key: section_labels[key],
        key=PROFESSOR_WIDGET_KEY,
        on_change=_on_professor_nav_change,
        label_visibility="collapsed",
    )
    if choice != st.session_state[PROFESSOR_NAV_KEY]:
        st.session_state[PROFESSOR_NAV_KEY] = choice
        _sync_query_param("p_section", choice)
    st.sidebar.divider()


def render_student_sidebar_nav():
    section_keys = list(STUDENT_SECTION_KEYS)
    current = _bootstrap_nav_section(
        STUDENT_NAV_KEY,
        "student_section",
        "s_section",
        section_keys,
        section_keys[0],
    )
    _init_nav_widget(STUDENT_WIDGET_KEY, current)

    st.sidebar.markdown('<div class="kahoot-sidebar-nav-title">Navegação</div>', unsafe_allow_html=True)
    choice = st.sidebar.radio(
        "Seção do aluno",
        options=section_keys,
        format_func=lambda key: "🎮 Quiz" if key == "quiz" else "📝 Provas",
        key=STUDENT_WIDGET_KEY,
        on_change=_on_student_nav_change,
        label_visibility="collapsed",
    )
    if choice != st.session_state[STUDENT_NAV_KEY]:
        st.session_state[STUDENT_NAV_KEY] = choice
        _sync_query_param("s_section", choice)
    st.sidebar.divider()
