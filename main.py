"""Ponto de entrada do Quiz Interativo (Streamlit)."""
from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import streamlit as st

# NÃO usar importlib.reload() aqui: com sessões concorrentes no Streamlit
# Cloud, o reload manipula sys.modules durante imports de outras threads e
# causa KeyError intermitente no importlib.
try:
    import auth_users
except ImportError as exc:
    st.error(
        "Não foi possível carregar o módulo `auth_users`. "
        "Verifique se todos os arquivos `.py` foram enviados ao GitHub."
    )
    st.code(str(exc))
    st.caption(f"Pasta do app: `{_APP_DIR}`")
    st.stop()

_REQUIRED_AUTH = (
    "resolve_unified_google_login",
    "is_approved_student_name",
)
_missing_auth = [name for name in _REQUIRED_AUTH if not hasattr(auth_users, name)]
if _missing_auth:
    st.error(
        "O arquivo `auth_users.py` no servidor está desatualizado. "
        f"Funções ausentes: {', '.join(_missing_auth)}. "
        "No Streamlit Cloud: **Manage app → Reboot** para forçar novo deploy."
    )
    st.stop()

from ui_theme import finalize_ui_theme

from app.auth_ui import render_login, render_session_controls
from app.navigation import render_professor_sidebar_nav, render_student_sidebar_nav
from app.professor_views import render_professor_panel
from app.session import init_session_state
from app.student_views import render_student_panel


def configure_streamlit_page() -> None:
    """Deve ser a primeira chamada Streamlit do script (antes de init_session_state)."""
    role = st.session_state.get("role")
    if role == "professor":
        page_title = "Quiz Interativo - Professor"
        sidebar_state = "expanded"
    elif role == "student":
        page_title = "Quiz Interativo - Aluno"
        sidebar_state = "expanded"
    else:
        page_title = "Quiz Interativo"
        sidebar_state = "collapsed"

    st.set_page_config(
        page_title=page_title,
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state=sidebar_state,
    )


def main() -> None:
    configure_streamlit_page()
    init_session_state()
    finalize_ui_theme()

    if st.session_state.role is None:
        render_login()
        return

    render_session_controls()

    if st.session_state.role == "professor":
        render_professor_sidebar_nav()
        render_professor_panel()
    else:
        render_student_sidebar_nav()
        render_student_panel()


if __name__ == "__main__":
    main()
