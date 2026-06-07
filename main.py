from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import matplotlib.pyplot as plt
import pandas as pd
import pdfplumber
import streamlit as st
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

if not hasattr(auth_users, "resolve_unified_google_login"):
    st.error(
        "O arquivo `auth_users.py` no servidor está desatualizado. "
        "No Streamlit Cloud: **Manage app → Reboot** para forçar novo deploy."
    )
    st.stop()

import importlib

import quiz_storage
_ui_theme_mod = importlib.reload(importlib.import_module("ui_theme"))
apply_ui_theme = _ui_theme_mod.apply_ui_theme
finalize_ui_theme = _ui_theme_mod.finalize_ui_theme
render_theme_selector = _ui_theme_mod.render_theme_selector
from google_auth import (
    clear_oauth_session,
    google_oauth_configured,
    legacy_password_enabled,
    render_google_login_button,
    render_oauth_setup_help,
)
from pdf_export import build_exam_pdf_bytes, export_filename
from auto_grade import (
    CLASSIFICATIONS,
    LABELS,
    POINTS,
    grade_choice_answer,
    grade_justify_answer,
    summarize_answers,
)
from pdf_parser import (
    exam_summary,
    parse_exam_from_text,
    parse_questions_from_text,
    question_for_student,
)
from quiz_storage import (
    add_exam_submission,
    add_student,
    create_exam,
    create_material,
    delete_exam,
    delete_material,
    delete_student,
    get_active_exam_ids,
    get_active_exams,
    get_active_material_ids,
    get_active_materials,
    get_exam,
    get_material,
    is_exam_active,
    is_material_active,
    is_registered_student,
    leaderboard_for_material,
    list_exams,
    list_materials,
    load_leaderboard,
    load_students,
    migrate_legacy_leaderboard,
    save_leaderboard,
    student_quiz_stats,
    submissions_for_exam,
    toggle_exam_active,
    toggle_material_active,
    update_exam,
    update_exam_submission,
    update_material,
    update_professor_credentials,
    update_student,
    verify_professor,
)

EMPTY_QUESTION = {
    "question": "",
    "options": ["", "", "", ""],
    "correct": "A",
}

EXAM_FORMAT_HELP = """
**Formato do PDF da prova (com gabarito — só o professor vê):**

**Múltipla escolha:**
```
Pergunta 1: Enunciado da questão?
Alternativa A (Vermelho): texto
Alternativa B (Azul): texto (CORRETA)
Alternativa C (Amarelo): texto
Alternativa D (Verde): texto
```

**Justificativa / dissertativa:**
```
Pergunta 2: Explique o conceito X. (JUSTIFICATIVA)
Gabarito: texto esperado na correção
```
ou use `Resposta esperada:` / `Tipo: Justificativa` / enunciado com "Justifique".
"""


# ---------------------------
# Parsing
# ---------------------------
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


# ---------------------------
# Session state
# ---------------------------
def bootstrap_auth_config():
    try:
        admin_email = st.secrets.get("auth", {}).get("system_admin_email")
        if admin_email:
            cfg = quiz_storage.load_config()
            cfg["system_admin_email"] = admin_email.strip().lower()
            quiz_storage.save_config(cfg)
    except Exception:
        pass


def login_user(user: dict):
    if auth_users.is_system_admin(user.get("email")) or user.get("is_admin"):
        user = {**user, "is_admin": True}
    st.session_state.current_user = user
    st.session_state.role = user.get("role")
    if user.get("role") == "student" and user.get("name"):
        st.session_state.preferred_student_name = user["name"]
        st.session_state.current_student_name = user["name"]


def init_session_state():
    migrate_legacy_leaderboard()
    bootstrap_auth_config()
    defaults = {
        "role": None,
        "current_user": None,
        "questions": [],
        "current_material_id": None,
        "leaderboard": load_leaderboard(),
        "quiz_active": False,
        "current_q_index": 0,
        "student_answers": [],
        "current_student_name": "",
        "quiz_finished": False,
        "show_comparison": False,
        "answer_feedback": None,
        "professor_edit_id": None,
        "preferred_student_name": None,
        "selected_material_id": None,
        "selected_exam_id": None,
        "exam_mode": "select",
        "exam_submission_result": None,
        "auth_view": "signup",
        "professor_section": "materials",
        "student_section": "quiz",
        "ui_theme": "system",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _logout_requires_confirmation() -> bool:
    if st.session_state.get("quiz_active") and not st.session_state.get("quiz_finished"):
        return True
    return st.session_state.get("exam_mode") == "take"


def _logout_button_label() -> str:
    if st.session_state.get("current_user"):
        return "Sair da conta"
    return "Voltar ao início"


def _logout_confirmation_message() -> str:
    if st.session_state.get("exam_mode") == "take":
        return (
            "Você está fazendo uma prova. Se sair agora, "
            "perderá o progresso desta tentativa."
        )
    return (
        "Você está no meio de um quiz. Se sair agora, "
        "perderá o progresso desta tentativa."
    )


def _request_logout() -> None:
    if _logout_requires_confirmation():
        st.session_state.confirm_logout = True
        st.rerun()
    else:
        logout()


def logout():
    clear_oauth_session()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.logout_message = "Sessão encerrada com sucesso."
    st.rerun()


def load_student_material(material_id: str) -> dict | None:
    material = get_material(material_id)
    if material:
        st.session_state.questions = material["questions"]
        st.session_state.current_material_id = material["id"]
        st.session_state.selected_material_id = material["id"]
    return material


def get_playable_active_materials() -> list:
    return [m for m in get_active_materials() if m.get("questions")]


def reset_quiz():
    st.session_state.quiz_active = True
    st.session_state.current_q_index = 0
    st.session_state.student_answers = []
    st.session_state.quiz_finished = False
    st.session_state.show_comparison = False
    st.session_state.answer_feedback = None


def finish_quiz():
    total = len(st.session_state.questions)
    score = sum(st.session_state.student_answers)
    st.session_state.leaderboard.append(
        {
            "material_id": st.session_state.current_material_id,
            "name": st.session_state.current_student_name,
            "score": score,
            "total": total,
            "responses": st.session_state.student_answers.copy(),
        }
    )
    save_leaderboard(st.session_state.leaderboard)
    st.session_state.quiz_active = False
    st.session_state.quiz_finished = True
    st.session_state.answer_feedback = None


def name_exists_in_leaderboard(name: str, material_id: str) -> bool:
    key = name.strip().lower()
    entries = leaderboard_for_material(material_id)
    return any(e["name"].strip().lower() == key for e in entries)


# ---------------------------
# Gráficos
# ---------------------------
def _show_figure(fig):
    st.pyplot(fig)
    plt.close(fig)


def plot_student_result(answers, total):
    if total <= 0:
        st.info("Sem perguntas para exibir o gráfico.")
        return
    correct = sum(answers)
    wrong = total - correct
    fig, ax = plt.subplots()
    ax.pie(
        [correct, wrong],
        labels=["Acertos", "Erros"],
        autopct="%1.1f%%",
        colors=["#2ecc71", "#e74c3c"],
        startangle=90,
    )
    ax.axis("equal")
    _show_figure(fig)


def plot_leaderboard_comparison(leaderboard):
    if not leaderboard:
        st.info("Nenhum aluno cadastrado ainda.")
        return
    df = pd.DataFrame(leaderboard)
    df["porcentagem"] = (df["score"] / df["total"]) * 100
    df = df.sort_values("porcentagem", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(df["name"], df["porcentagem"], color="#3498db")
    ax.set_xlabel("Acertos (%)")
    ax.set_title("Comparação de Desempenho entre Alunos")
    ax.invert_yaxis()
    for i, v in enumerate(df["porcentagem"]):
        ax.text(v + 1, i, f"{v:.1f}%", va="center")
    _show_figure(fig)


def plot_question_performance(leaderboard, total_questions):
    if not leaderboard or total_questions <= 0:
        return
    pergunta_acertos = [0] * total_questions
    for aluno in leaderboard:
        for i, acertou in enumerate(aluno["responses"]):
            if i < total_questions and acertou:
                pergunta_acertos[i] += 1
    num_alunos = len(leaderboard)
    percentuais = [(acertos / num_alunos) * 100 for acertos in pergunta_acertos]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(1, total_questions + 1), percentuais, color="#f39c12")
    ax.set_xticks(range(1, total_questions + 1))
    ax.set_xlabel("Número da Pergunta")
    ax.set_ylabel("Alunos que acertaram (%)")
    ax.set_title("Taxa de Acertos por Pergunta (todos os alunos)")
    ax.set_ylim(0, 100)
    for i, p in enumerate(percentuais):
        ax.text(i + 1, p + 1, f"{p:.1f}%", ha="center")
    _show_figure(fig)


# ---------------------------
# Login — split 50/50 (referência visual)
# ---------------------------
LOGIN_TEAL = "#458588"
GOOGLE_ICON_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E"
    "%3Cpath fill='%23FFC107' d='M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8"
    "-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657"
    "C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20"
    "c0-1.341-.138-2.65-.389-3.916z'/%3E"
    "%3Cpath fill='%23FF3D00' d='m6.306 14.691 6.571 4.819C14.655 15.108 18.961 12 24 12"
    "c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4"
    " 16.318 4 9.656 8.337 6.306 14.691z'/%3E"
    "%3Cpath fill='%234CAF50' d='M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238"
    "C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025"
    "C9.505 39.556 16.227 44 24 44z'/%3E"
    "%3Cpath fill='%231976D2' d='M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571"
    "l6.19 5.238C42.022 35.026 44 30.038 44 24c0-1.341-.138-2.65-.389-3.917z'/%3E"
    "%3C/svg%3E"
)

LOGIN_PAGE_CSS = f"""
.stApp:has(.kahoot-login-marker) section[data-testid="stSidebar"],
.stApp:has(.kahoot-login-marker) footer {{
    display: none !important;
}}
.stApp:has(.kahoot-login-marker) header[data-testid="stHeader"] {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    visibility: hidden !important;
}}
.stApp:has(.kahoot-login-marker) .main {{
    padding-top: 0 !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stDecoration"] {{
    display: none !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stHorizontalBlock"]:has(.kahoot-login-theme-marker) {{
    height: 0 !important;
    min-height: 0 !important;
    overflow: visible !important;
    margin: 0 !important;
    border: none !important;
}}
.stApp:has(.kahoot-login-marker) .main .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
    margin: 0 !important;
}}
.kahoot-login-marker {{ display: none !important; }}
.stApp:has(.kahoot-login-marker) [data-testid="stHorizontalBlock"]:has(.kahoot-login-theme-marker) {{
    position: fixed !important;
    top: 1rem !important;
    right: 1.25rem !important;
    z-index: 60 !important;
    width: auto !important;
    max-width: 11rem !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stHorizontalBlock"]:has(.kahoot-login-theme-marker) > [data-testid="stColumn"] {{
    width: auto !important;
    flex: 0 0 auto !important;
    padding: 0 !important;
    min-height: unset !important;
}}
.stApp:has(.kahoot-login-marker) [data-testid="stHorizontalBlock"]:has(.kahoot-login-theme-marker) [data-testid="stSegmentedControl"] {{
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12) !important;
}}
.kahoot-login-theme-marker {{ display: none !important; }}
.kahoot-login-row {{
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    min-height: 100vh !important;
    gap: 0 !important;
    margin: 0 !important;
    z-index: 50 !important;
    align-items: stretch !important;
}}
.kahoot-login-row > [data-testid="stColumn"] {{
    padding: 3.5rem 3rem !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    min-height: 100vh !important;
    overflow-y: auto !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child {{
    background: {LOGIN_TEAL} !important;
    flex: 0 0 50% !important;
    width: 50% !important;
    max-width: 50% !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child {{
    background: var(--kahoot-login-panel-right) !important;
    flex: 0 0 50% !important;
    width: 50% !important;
    max-width: 50% !important;
}}
.kahoot-login-row > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 100% !important;
    flex: 1 1 auto !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"],
.kahoot-login-row > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {{
    max-width: 360px;
}}
.kahoot-left-inner {{ text-align: center; max-width: 320px; }}
.kahoot-left-inner h2 {{
    color: #ffffff; font-size: 2.4rem; font-weight: 700;
    margin: 0 0 1rem; line-height: 1.2;
    font-family: "Segoe UI", system-ui, sans-serif;
}}
.kahoot-left-inner p {{
    color: rgba(255,255,255,0.95); font-size: 0.95rem; line-height: 1.7;
    margin: 0 0 2rem; font-family: "Segoe UI", system-ui, sans-serif;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child .stButton {{
    width: 100%; display: flex; justify-content: center;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child .stButton > button {{
    background: transparent !important;
    color: #ffffff !important;
    border: 2px solid #ffffff !important;
    border-radius: 25px !important;
    font-weight: 600 !important;
    padding: 0.7rem 2.8rem !important;
    letter-spacing: 0.08em !important;
    min-width: 200px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child .stButton > button:hover {{
    background: rgba(255,255,255,0.12) !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) {{
    max-width: 42px !important; width: auto !important;
    margin: 0 auto 0.5rem !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"] {{
    flex: 0 0 auto !important; width: auto !important; max-width: none !important;
    min-height: unset !important; padding: 0 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) {{
    position: relative !important;
    width: 42px !important; height: 42px !important;
    min-height: 42px !important; flex: 0 0 42px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) > [data-testid="stVerticalBlock"] {{
    position: relative !important;
    width: 42px !important; height: 42px !important;
    min-height: 42px !important; justify-content: flex-start !important;
}}
.kahoot-google-visual {{
    width: 42px; height: 42px; border-radius: 50%;
    border: 1px solid var(--kahoot-login-google-border);
    background-color: var(--kahoot-login-google-bg);
    background-image: url("{GOOGLE_ICON_SVG}");
    background-size: 22px; background-repeat: no-repeat; background-position: center;
    margin: 0 auto; pointer-events: none;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) > [data-testid="stColumn"]:nth-child(2) .element-container:has(
    iframe[title="streamlit_oauth.authorize_button"]
) {{
    position: absolute !important; top: 0 !important; left: 0 !important;
    width: 42px !important; height: 42px !important;
    opacity: 0 !important; z-index: 2 !important;
    margin: 0 !important; padding: 0 !important; overflow: visible !important;
    border: none !important; background: transparent !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-google-visual) iframe[title="streamlit_oauth.authorize_button"] {{
    width: 42px !important; height: 42px !important; border: none !important;
    margin: 0 !important; cursor: pointer !important;
}}
.kahoot-form-wrap {{ width: 100%; max-width: 360px; margin: 0 auto; }}
.kahoot-form-title {{
    color: var(--kahoot-login-form-title); font-size: 1.85rem; font-weight: 700;
    text-align: center; margin: 0 0 1.25rem;
    font-family: "Segoe UI", system-ui, sans-serif;
}}
.kahoot-form-sub {{
    color: var(--kahoot-login-form-sub); font-size: 0.85rem; text-align: center; margin: 0 0 1rem;
}}
.kahoot-or-line {{
    display: flex; align-items: center; gap: 0.75rem;
    margin: 1.25rem 0; color: var(--kahoot-login-form-muted); font-size: 0.82rem;
}}
.kahoot-or-line::before, .kahoot-or-line::after {{
    content: ""; flex: 1; height: 1px; background: var(--kahoot-login-or-line);
}}
.kahoot-footnote {{
    color: var(--kahoot-login-form-muted); font-size: 0.78rem; text-align: center;
    margin-top: 1.25rem; line-height: 1.5;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child label {{
    color: var(--kahoot-login-label) !important; font-weight: 600 !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child input {{
    background: var(--kahoot-login-input-bg) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    color: var(--kahoot-login-input-text) !important;
    border-radius: 8px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child .stTextInput > div > div {{
    background: var(--kahoot-login-input-bg) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    border-radius: 8px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stFormSubmitButton"] > button {{
    background: {LOGIN_TEAL} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 25px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    padding: 0.75rem 1.5rem !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stFormSubmitButton"] > button:hover {{
    background: #3d7a72 !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child .stButton > button[kind="secondary"] {{
    background: var(--kahoot-login-secondary-btn-bg) !important;
    color: var(--kahoot-login-secondary-btn-text) !important;
    border: 1px solid var(--kahoot-login-input-border) !important;
    border-radius: 25px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stMarkdownContainer"] p,
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stCaption"] {{
    color: var(--kahoot-login-form-muted) !important;
}}
@media (max-width: 768px) {{
    .kahoot-login-row {{
        position: relative !important;
        flex-direction: column !important;
        height: auto !important;
        min-height: 100vh !important;
    }}
    .kahoot-login-row > [data-testid="stColumn"] {{
        min-height: auto !important;
        width: 100% !important;
        max-width: 100% !important;
        flex: 1 1 auto !important;
    }}
}}
"""


APP_CHROME_CSS = """
footer { visibility: hidden; }
"""

APP_HIDE_TOOLBAR_CSS = """
header[data-testid="stHeader"] [data-testid="stMainMenu"],
header[data-testid="stHeader"] [data-testid="stToolbarActions"] {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: var(--background-color) !important;
    border-bottom: 1px solid var(--kahoot-border) !important;
    box-shadow: none !important;
}
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] button,
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button {
    color: var(--kahoot-chrome-btn-icon) !important;
    background: var(--kahoot-chrome-btn-bg) !important;
    border: 1.5px solid var(--kahoot-chrome-btn-border) !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1) !important;
}
[data-testid="stExpandSidebarButton"] span,
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stExpandSidebarButton"] path,
[data-testid="stExpandSidebarButton"] *,
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapseButton"] path,
[data-testid="stSidebarCollapseButton"] * {
    color: var(--kahoot-chrome-btn-icon) !important;
    fill: var(--kahoot-chrome-btn-icon) !important;
    stroke: var(--kahoot-chrome-btn-icon) !important;
    -webkit-text-fill-color: var(--kahoot-chrome-btn-icon) !important;
}
"""

SIDEBAR_SESSION_CSS = f"""
section[data-testid="stSidebar"]:has(.kahoot-sidebar-shell) {{
    padding-top: 0.25rem !important;
}}
section[data-testid="stSidebar"] .kahoot-sidebar-account-block {{
    margin-top: 0.65rem;
    padding: 0.75rem 0.35rem 0.5rem;
    border-top: 1px solid var(--kahoot-border);
}}
section[data-testid="stSidebar"]:has(.kahoot-sidebar-shell) .kahoot-account-menu-anchor ~ [data-testid="stVerticalBlock"] [data-testid="stPopover"],
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] {{
    width: 100% !important;
    opacity: 1 !important;
    visibility: visible !important;
    margin-bottom: 0.15rem !important;
}}
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] > button,
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] .stButton > button,
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button {{
    background: var(--background-color) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.86rem !important;
    line-height: 1.2 !important;
    padding: 0.5rem 0.8rem !important;
    min-height: 2.5rem !important;
    width: 100% !important;
    letter-spacing: 0 !important;
    opacity: 1 !important;
    visibility: visible !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.45rem !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
}}
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] .stButton {{
    width: 100% !important;
}}
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button [data-testid="stIconMaterial"],
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button span[data-testid="stIconMaterial"] {{
    color: {LOGIN_TEAL} !important;
}}
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] > button:hover,
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] .stButton > button:hover,
section[data-testid="stSidebar"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button:hover {{
    background: color-mix(in srgb, {LOGIN_TEAL} 9%, var(--background-color)) !important;
    color: var(--text-color) !important;
    border-color: {LOGIN_TEAL} !important;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.07) !important;
}}
section[data-testid="stSidebar"] .kahoot-account-menu-anchor {{
    display: none !important;
}}
/* Sidebar recolhida: só ícone do menu, centralizado */
section[data-testid="stSidebar"][aria-expanded="false"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button {{
    padding: 0.45rem !important;
    min-width: 2.5rem !important;
    width: 2.5rem !important;
    min-height: 2.5rem !important;
    border-radius: 0.65rem !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button p,
section[data-testid="stSidebar"][aria-expanded="false"]:has(.kahoot-account-menu-anchor) [data-testid="stPopover"] button span:not([data-testid="stIconMaterial"]) {{
    display: none !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"] .kahoot-sidebar-account-block {{
    display: none !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"]:has(.kahoot-sidebar-shell) hr {{
    display: none !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) [data-testid="stSegmentedControl"] {{
    width: 100% !important;
    margin-bottom: 0.35rem !important;
}}
.kahoot-session-bar {{
    display: flex;
    align-items: center;
    gap: 0.85rem;
    min-width: 0;
}}
.kahoot-session-avatar {{
    flex: 0 0 auto;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    color: #ffffff;
    background: linear-gradient(135deg, {LOGIN_TEAL} 0%, #3d7a72 100%);
    border: 2px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
}}
.kahoot-session-info {{
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
    flex: 1 1 auto;
}}
.kahoot-session-line {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
}}
.kahoot-session-name {{
    color: var(--text-color, #31333F);
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.2;
}}
.kahoot-session-email {{
    color: var(--kahoot-text-muted, #5c6370);
    font-size: 0.78rem;
    line-height: 1.25;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.kahoot-session-role {{
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: color-mix(in srgb, var(--primary-color) 18%, transparent);
    color: var(--primary-color) !important;
    border: 1px solid color-mix(in srgb, var(--primary-color) 45%, transparent);
}}
.kahoot-session-role--student {{
    background: var(--kahoot-student-role-bg);
    color: var(--kahoot-student-role-text);
    border-color: var(--kahoot-student-role-border);
}}
section[data-testid="stSidebar"] .kahoot-logout-confirm {{
    margin-top: 0.65rem;
    padding-top: 0.65rem;
    border-top: 1px solid var(--kahoot-border);
}}
section[data-testid="stSidebar"] .kahoot-sidebar-nav-title {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--kahoot-text-subtle, #6b7280);
    margin: 0.35rem 0 0.5rem;
}}
.kahoot-menu-panel {{
    min-width: 12.5rem;
    padding: 0.1rem 0 0.15rem;
}}
.kahoot-menu-account-name {{
    color: var(--text-color, #31333F);
    font-size: 0.92rem;
    font-weight: 700;
    line-height: 1.25;
    margin-bottom: 0.2rem;
}}
.kahoot-menu-role {{
    color: var(--kahoot-text-muted, #5c6370);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.15rem;
}}
.kahoot-menu-email {{
    color: var(--kahoot-text-muted, #5c6370);
    font-size: 0.78rem;
    line-height: 1.3;
    word-break: break-word;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) {{
    min-width: 13rem !important;
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) .stButton > button {{
    background-color: var(--secondary-background-color) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--kahoot-border-strong) !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) .element-container:has(.kahoot-menu-logout-marker) + .element-container .stButton > button {{
    background: transparent !important;
    color: var(--kahoot-danger) !important;
    border: 1px solid color-mix(in srgb, var(--kahoot-danger) 55%, transparent) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 1rem !important;
    min-height: 2.75rem !important;
    height: 2.75rem !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) .element-container:has(.kahoot-menu-logout-marker) + .element-container .stButton > button:hover {{
    background: var(--kahoot-danger-bg-hover) !important;
    border-color: var(--kahoot-danger) !important;
    color: var(--kahoot-danger-hover) !important;
}}
.kahoot-menu-section-title {{
    color: var(--kahoot-text-subtle, #6b7280);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 0.15rem 0 0.35rem;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) [data-testid="stRadio"] label {{
    font-size: 0.84rem !important;
}}
[data-testid="stPopoverBody"]:has(.kahoot-menu-panel) .element-container:has(.kahoot-menu-action-marker) + .element-container .stButton > button {{
    min-height: 2.5rem !important;
    font-size: 0.82rem !important;
}}
"""


def _user_initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    if parts:
        return parts[0][:2].upper()
    return "?"


def _session_profile_html(name: str, role_label: str, role_badge_class: str, email_html: str) -> str:
    return (
        f'<div class="kahoot-session-bar">'
        f'<div class="kahoot-session-avatar">{_user_initials(name)}</div>'
        f'<div class="kahoot-session-info">'
        f'<div class="kahoot-session-line">'
        f'<span class="kahoot-session-name">{name}</span>'
        f'<span class="{role_badge_class}">{role_label}</span>'
        f"</div>"
        f"{email_html}"
        f"</div>"
        f"</div>"
    )


def _session_menu_account_html(name: str, role_label: str, email: str | None) -> str:
    if email:
        email_html = f'<div class="kahoot-menu-email">{email}</div>'
    elif not st.session_state.get("current_user"):
        email_html = '<div class="kahoot-menu-email">Sem conta Google vinculada</div>'
    else:
        email_html = ""
    return (
        f'<div class="kahoot-menu-panel">'
        f'<div class="kahoot-menu-account-name">{name}</div>'
        f'<div class="kahoot-menu-role">{role_label}</div>'
        f"{email_html}"
        f"</div>"
    )


def _apply_app_chrome(*, hide_toolbar: bool = False):
    css = APP_CHROME_CSS + (APP_HIDE_TOOLBAR_CSS if hide_toolbar else "")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _render_account_settings_menu():
    render_theme_selector(compact=True)
    st.markdown('<span class="kahoot-menu-action-marker"></span>', unsafe_allow_html=True)
    if st.button("Recarregar aplicativo", key="account_menu_rerun", use_container_width=True):
        st.rerun()


def _clear_login_page_styles():
    """Remove CSS da login (impede tema claro após autenticar)."""
    st.html(
        """
        <script>
        (function () {
            const style = document.getElementById("kahoot-login-style");
            if (style) style.remove();
            document.querySelectorAll(".kahoot-login-row").forEach((row) => {
                row.classList.remove("kahoot-login-row");
            });
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def _apply_login_styles_in_parent():
    css_json = json.dumps(LOGIN_PAGE_CSS)
    st.html(
        f"""
        <script>
        (function() {{
            function applyLoginLayout() {{
                let style = document.getElementById("kahoot-login-style");
                if (!style) {{
                    style = document.createElement("style");
                    style.id = "kahoot-login-style";
                    document.head.appendChild(style);
                }}
                style.textContent = {css_json};
                document.querySelectorAll(".kahoot-login-marker").forEach((marker) => {{
                    const row = marker.closest('[data-testid="stHorizontalBlock"]');
                    if (row) row.classList.add("kahoot-login-row");
                }});
            }}
            applyLoginLayout();
            setTimeout(applyLoginLayout, 50);
            setTimeout(applyLoginLayout, 300);
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def _register_student_name(name: str) -> tuple[bool, str]:
    _, err = add_student(name)
    if err:
        st.error(err)
        return False, ""
    clean = " ".join(name.strip().split())
    auth_users.ensure_name_student_user(clean)
    st.session_state.preferred_student_name = clean
    return True, clean


def render_student_register_form(form_key: str, button_label: str = "Cadastrar-me") -> bool:
    with st.form(form_key):
        name = st.text_input("Nome completo", placeholder="Ex.: Maria Silva")
        submitted = st.form_submit_button(button_label, use_container_width=True)
        if submitted:
            ok, clean = _register_student_name(name)
            if ok:
                st.success(f"Cadastro realizado! Bem-vindo(a), **{clean}**.")
                return True
    return False


def _handle_unified_google(profile: dict):
    user, err = auth_users.resolve_unified_google_login(profile)
    if err:
        if "aguarda aprovação" in err:
            st.info(err)
        else:
            st.error(err)
    else:
        login_user(user)
        st.rerun()


def render_google_icon_login(key: str) -> dict | None:
    if not google_oauth_configured():
        return None
    return render_google_login_button(
        "",
        key=key,
        role_hint="unified",
        use_container_width=False,
    )


def _render_social_google_row(oauth_key: str) -> dict | None:
    profile = None
    _, col, _ = st.columns([1, 1, 1], gap="small")
    with col:
        st.markdown('<div class="kahoot-google-visual"></div>', unsafe_allow_html=True)
        if google_oauth_configured():
            profile = render_google_icon_login(oauth_key)
    return profile


def render_login_signup_panel():
    st.markdown('<div class="kahoot-form-wrap">', unsafe_allow_html=True)
    st.markdown('<p class="kahoot-form-title">Criar conta</p>', unsafe_allow_html=True)

    if google_oauth_configured():
        profile = _render_social_google_row("oauth_signup")
        if profile:
            _handle_unified_google(profile)
        st.markdown('<p class="kahoot-form-sub">ou use o Google para se registrar</p>', unsafe_allow_html=True)
        st.markdown('<div class="kahoot-or-line">ou use seu nome</div>', unsafe_allow_html=True)
    else:
        render_oauth_setup_help()

    with st.form("register_on_login"):
        name = st.text_input("Nome", placeholder="Nome completo")
        submitted = st.form_submit_button("CADASTRAR-SE", use_container_width=True, type="primary")
        if submitted:
            ok, _ = _register_student_name(name)
            if ok:
                st.session_state.role = "student"
                st.session_state.current_user = None
                st.rerun()

    st.markdown(
        '<p class="kahoot-footnote">Já tem conta? Clique em <b>ENTRAR</b> no painel esquerdo.</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_login_signin_panel():
    st.markdown('<div class="kahoot-form-wrap">', unsafe_allow_html=True)
    st.markdown('<p class="kahoot-form-title">Entrar</p>', unsafe_allow_html=True)

    if google_oauth_configured():
        profile = _render_social_google_row("oauth_signin")
        if profile:
            _handle_unified_google(profile)
        st.markdown('<p class="kahoot-form-sub">ou use o Google para acessar</p>', unsafe_allow_html=True)
        st.markdown('<div class="kahoot-or-line">ou</div>', unsafe_allow_html=True)
    else:
        render_oauth_setup_help()
        if legacy_password_enabled():
            with st.expander("Login legado (desenvolvimento)"):
                with st.form("professor_login"):
                    username = st.text_input("Usuário")
                    password = st.text_input("Senha", type="password")
                    submitted = st.form_submit_button("Entrar (legado)", use_container_width=True)
                    if submitted:
                        if verify_professor(username, password):
                            login_user(
                                {
                                    "id": "legacy-professor",
                                    "name": username,
                                    "email": None,
                                    "role": "professor",
                                    "auth_provider": "legacy",
                                }
                            )
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")

    if st.button(
        "Continuar sem conta Google",
        use_container_width=True,
        key="student_no_google",
        type="secondary",
    ):
        st.session_state.role = "student"
        st.session_state.current_user = None
        st.rerun()

    st.markdown(
        f'<p class="kahoot-footnote">O administrador ({auth_users.get_system_admin_email()}) '
        "libera professores na aba Aprovações.</p></div>",
        unsafe_allow_html=True,
    )


def render_login():
    logout_message = st.session_state.pop("logout_message", None)

    view = st.session_state.auth_view
    if view == "signup":
        left_title = "Bem-vindo de volta!"
        left_desc = (
            "Para continuar no quiz, entre com sua conta Google ou pelo nome cadastrado."
        )
        switch_label = "ENTRAR"
        switch_key = "go_signin"
        switch_target = "signin"
    else:
        left_title = "Novo por aqui?"
        left_desc = "Crie sua conta em segundos e comece a responder os quizzes agora mesmo."
        switch_label = "CADASTRAR-SE"
        switch_key = "go_signup"
        switch_target = "signup"

    _apply_app_chrome()
    st.markdown(f"<style>{LOGIN_PAGE_CSS}</style>", unsafe_allow_html=True)
    _, theme_col = st.columns([4, 1])
    with theme_col:
        st.markdown('<span class="kahoot-login-theme-marker"></span>', unsafe_allow_html=True)
        render_theme_selector(compact=True, icon_only=True)

    col_left, col_right = st.columns(2, gap="small")

    with col_left:
        st.markdown('<span class="kahoot-login-marker"></span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="kahoot-left-inner">'
            f"<h2>{left_title}</h2>"
            f"<p>{left_desc}</p></div>",
            unsafe_allow_html=True,
        )
        if st.button(switch_label, key=switch_key, use_container_width=False):
            st.session_state.auth_view = switch_target
            st.rerun()

    with col_right:
        if logout_message:
            st.success(logout_message)
        if view == "signup":
            render_login_signup_panel()
        else:
            render_login_signin_panel()

    _apply_login_styles_in_parent()


def _session_user_display() -> tuple[str, str, str | None]:
    user = st.session_state.get("current_user")
    if user:
        role_label = "Professor" if user.get("role") == "professor" else "Aluno"
        name = user.get("name") or user.get("email") or role_label
        return name, role_label, user.get("email")

    role_label = "Aluno" if st.session_state.role == "student" else "Visitante"
    name = st.session_state.get("preferred_student_name") or st.session_state.get("current_student_name")
    if name:
        return name, role_label, None
    return role_label, role_label, None


def render_session_controls():
    """Conta, menu e logout na barra lateral esquerda."""
    name, role_label, email = _session_user_display()
    role_badge_class = (
        "kahoot-session-role"
        if role_label == "Professor"
        else "kahoot-session-role kahoot-session-role--student"
    )
    logout_label = _logout_button_label()

    _apply_app_chrome(hide_toolbar=True)
    st.markdown(f"<style>{SIDEBAR_SESSION_CSS}</style>", unsafe_allow_html=True)
    _clear_login_page_styles()

    if email:
        email_html = f'<div class="kahoot-session-email">{email}</div>'
    elif not st.session_state.get("current_user"):
        email_html = '<div class="kahoot-session-email">Sem conta Google vinculada</div>'
    else:
        email_html = ""

    profile_html = _session_profile_html(name, role_label, role_badge_class, email_html)
    menu_account_html = _session_menu_account_html(name, role_label, email)

    with st.sidebar:
        st.markdown('<span class="kahoot-sidebar-shell"></span>', unsafe_allow_html=True)
        if st.session_state.get("confirm_logout"):
            st.markdown(
                f'<div class="kahoot-sidebar-account-block">{profile_html}</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="kahoot-logout-confirm"></div>', unsafe_allow_html=True)
            st.warning(_logout_confirmation_message())
            if st.button("Cancelar", key="logout_cancel", use_container_width=True):
                st.session_state.confirm_logout = False
                st.rerun()
            if st.button(
                logout_label,
                key="logout_confirm",
                use_container_width=True,
                type="primary",
            ):
                logout()
        else:
            st.markdown('<span class="kahoot-account-menu-anchor"></span>', unsafe_allow_html=True)
            with st.popover(
                "Menu",
                help="Conta, aparência, recarregar e sair",
                key="kahoot_account_menu",
                icon=":material/menu:",
                type="secondary",
                use_container_width=True,
            ):
                st.markdown(menu_account_html, unsafe_allow_html=True)
                st.divider()
                _render_account_settings_menu()
                st.divider()
                st.markdown(
                    '<span class="kahoot-menu-logout-marker"></span>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    logout_label,
                    key="logout_menu",
                    use_container_width=True,
                    type="secondary",
                ):
                    _request_logout()
            st.markdown(
                f'<div class="kahoot-sidebar-account-block">{profile_html}</div>',
                unsafe_allow_html=True,
            )

        st.divider()


def _professor_nav_sections(show_admin_tab: bool) -> list[tuple[str, str]]:
    sections = [
        ("materials", "📚 Materiais"),
        ("edit", "✏️ Editar questões"),
        ("exams", "📝 Provas"),
        ("students", "👥 Alunos cadastrados"),
        ("results", "📊 Resultados"),
        ("config", "🔐 Conta"),
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
    render_student_register_sidebar()


def render_admin_approvals_tab():
    st.subheader("Aprovação de professores")
    st.caption(f"Administrador do sistema: **{auth_users.get_system_admin_email()}**")

    pending = auth_users.get_pending_professors()
    if not pending:
        st.success("Nenhuma solicitação pendente no momento.")
        return

    st.warning(f"{len(pending)} solicitação(ões) aguardando sua aprovação.")
    for u in pending:
        with st.container(border=True):
            st.write(f"**{u.get('name', '—')}**")
            st.write(f"E-mail: {u.get('email', '—')}")
            if u.get("created_at"):
                st.caption(f"Solicitado em: {u['created_at']}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Aprovar", key=f"approve_{u['id']}", use_container_width=True):
                    err = auth_users.approve_professor(u["id"])
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Professor **{u.get('name')}** aprovado.")
                        st.rerun()
            with c2:
                if st.button("❌ Negar", key=f"reject_{u['id']}", use_container_width=True):
                    err = auth_users.reject_professor(u["id"])
                    if err:
                        st.error(err)
                    else:
                        st.info(f"Solicitação de **{u.get('name')}** negada.")
                        st.rerun()


def render_auth_config_tab():
    st.subheader("Usuários e autenticação")
    st.caption(
        "Todos entram com Google ou pelo nome (alunos). Você libera professores na aba "
        "**Aprovações** ou alterando o papel abaixo."
    )

    user = st.session_state.get("current_user")
    if user:
        st.write(f"**Sessão atual:** {user.get('name')} — `{user.get('role')}`")
        if user.get("email"):
            st.write(f"E-mail: {user['email']}")
        if user.get("is_admin") or auth_users.is_system_admin(user.get("email")):
            st.success(f"Você é o administrador do sistema ({auth_users.get_system_admin_email()}).")

    st.markdown("---")
    st.markdown("#### Usuários cadastrados")
    users = auth_users.load_users()
    if not users:
        st.info("Nenhum usuário na tabela ainda. Professores entram via Google; alunos ao se cadastrarem.")
    else:
        rows = []
        for u in users:
            status = u.get("status", "—") if u.get("role") == "professor" else "—"
            rows.append(
                {
                    "Nome": u.get("name", "—"),
                    "E-mail": u.get("email") or "—",
                    "Papel": u.get("role", "—"),
                    "Status": status,
                    "Login": u.get("auth_provider", "—"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("##### Alterar papel de um usuário")
        user_options = {
            f"{u.get('name', '—')} ({u.get('email') or 'sem e-mail'})": u["id"]
            for u in users
            if u.get("email")
        }
        if user_options:
            pick = st.selectbox("Usuário", list(user_options.keys()))
            new_role = st.selectbox("Novo papel", list(auth_users.ROLES))
            if st.button("Salvar papel"):
                err = auth_users.set_user_role(user_options[pick], new_role)
                if err:
                    st.error(err)
                else:
                    st.success("Papel atualizado.")
                    st.rerun()

    if not google_oauth_configured() and legacy_password_enabled():
        st.markdown("---")
        st.subheader("Login legado (sem Google)")
        cfg = quiz_storage.load_config()
        new_user = st.text_input("Usuário local", value=cfg["professor_username"])
        new_pass = st.text_input("Nova senha local", type="password")
        new_pass2 = st.text_input("Confirmar senha local", type="password")
        if st.button("Salvar credenciais locais"):
            if not new_pass:
                st.error("Informe a nova senha.")
            elif new_pass != new_pass2:
                st.error("As senhas não coincidem.")
            elif len(new_pass) < 6:
                st.error("Use pelo menos 6 caracteres.")
            else:
                update_professor_credentials(new_user, new_pass)
                st.success("Credenciais locais atualizadas.")


# ---------------------------
# Professor
# ---------------------------
def render_question_editor(questions: list, key_prefix: str) -> list:
    edited = []
    for i, q in enumerate(questions):
        with st.expander(f"Questão {i + 1}", expanded=len(questions) <= 3):
            question_text = st.text_area(
                "Enunciado",
                value=q.get("question", ""),
                key=f"{key_prefix}_q_{i}",
            )
            opts = q.get("options", ["", "", "", ""])
            while len(opts) < 4:
                opts.append("")
            new_opts = []
            for j, letter in enumerate("ABCD"):
                new_opts.append(
                    st.text_input(
                        f"Alternativa {letter}",
                        value=opts[j] if j < len(opts) else "",
                        key=f"{key_prefix}_opt_{i}_{letter}",
                    )
                )
            correct = st.selectbox(
                "Alternativa correta",
                options=list("ABCD"),
                index=list("ABCD").index(q.get("correct", "A")),
                key=f"{key_prefix}_correct_{i}",
            )
            edited.append(
                {"question": question_text, "options": new_opts, "correct": correct}
            )
    return edited


def render_students_tab():
    st.subheader("Alunos cadastrados")
    st.caption(
        "Alunos podem se cadastrar na área do aluno ou você pode adicioná-los aqui."
    )

    with st.form("add_student_form", clear_on_submit=True):
        new_name = st.text_input("Nome completo", placeholder="Ex.: Maria Silva")
        if st.form_submit_button("➕ Cadastrar aluno", type="primary"):
            _, err = add_student(new_name)
            if err:
                st.error(err)
            else:
                st.success(f"Aluno **{new_name.strip()}** cadastrado.")
                st.rerun()

    students = load_students()
    if not students:
        st.info("Nenhum aluno cadastrado. Adicione alunos pelo formulário acima.")
        return

    st.markdown(f"**Total:** {len(students)} aluno(s)")
    rows = []
    for s in sorted(students, key=lambda x: x["name"].lower()):
        stats = student_quiz_stats(s["name"])
        rows.append(
            {
                "Nome": s["name"],
                "Tentativas": stats["attempts"],
                "Média %": f"{stats['avg_pct']:.1f}" if stats["avg_pct"] is not None else "—",
                "Último resultado": stats["last_score"] or "—",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Editar ou remover")
    for s in students:
        with st.expander(s["name"]):
            edit_name = st.text_input(
                "Nome",
                value=s["name"],
                key=f"student_name_{s['id']}",
            )
            ec1, ec2 = st.columns(2)
            with ec1:
                if st.button("💾 Salvar", key=f"save_student_{s['id']}"):
                    err = update_student(s["id"], edit_name)
                    if err:
                        st.error(err)
                    else:
                        st.success("Aluno atualizado.")
                        st.rerun()
            with ec2:
                if st.button("🗑️ Remover", key=f"del_student_{s['id']}"):
                    delete_student(s["id"])
                    st.success("Aluno removido.")
                    st.rerun()


def render_classification_badge(classification: str):
    colors = {"A": "#2ecc71", "PA": "#f39c12", "NA": "#e74c3c"}
    clf = classification if classification in CLASSIFICATIONS else "NA"
    st.markdown(
        f'<span style="background:{colors[clf]};color:white;padding:4px 10px;'
        f'border-radius:6px;font-weight:bold;">{LABELS[clf]}</span>',
        unsafe_allow_html=True,
    )


def render_exam_question_preview(questions: list, show_gabarito: bool = True):
    for i, q in enumerate(questions):
        tipo = "Múltipla escolha" if q.get("type") == "choice" else "Justificativa"
        st.markdown(f"**{i + 1}. [{tipo}]** {q['question']}")
        if q.get("type") == "choice":
            for j, letter in enumerate("ABCD"):
                mark = " ✅" if show_gabarito and q.get("correct") == letter else ""
                st.write(f"&nbsp;&nbsp;{letter}) {q['options'][j]}{mark}", unsafe_allow_html=True)
        elif show_gabarito:
            st.caption(f"Gabarito: {q.get('answer_key') or '(não informado)'}")


def render_exams_tab():
    st.subheader("Provas (PDF com gabarito)")
    st.caption("O gabarito fica só com o professor. Os alunos veem apenas as questões.")
    with st.expander("📋 Formato esperado do PDF"):
        st.markdown(EXAM_FORMAT_HELP)

    exams = list_exams()
    active_ids = set(get_active_exam_ids())

    new_title = st.text_input("Título da prova", placeholder="Ex.: Prova 1 — Lógica", key="exam_title")
    uploaded = st.file_uploader("PDF da prova (com gabarito)", type="pdf", key="exam_pdf")

    if st.button("📄 Importar prova do PDF", type="primary") and uploaded and new_title.strip():
        questions = parse_exam_from_pdf(uploaded)
        if questions:
            create_exam(new_title.strip(), questions)
            summary = exam_summary(questions)
            st.success(
                f"Prova criada: {summary['total']} questões "
                f"({summary['choice']} múltipla escolha, {summary['justify']} justificativas)."
            )
            st.rerun()
        else:
            st.error("Nenhuma questão identificada. Verifique o formato do PDF.")

    if not exams:
        st.info("Nenhuma prova cadastrada. Importe um PDF acima.")
        return

    st.markdown("---")
    st.subheader("Provas cadastradas")
    for ex in exams:
        summary = exam_summary(ex["questions"])
        is_active = ex["id"] in active_ids
        label = (
            f"{'🟢 ' if is_active else ''}{ex['title']} — "
            f"{summary['total']} questões "
            f"({summary['choice']} MC, {summary['justify']} just.)"
        )
        c1, c2, c3 = st.columns([4, 1, 1])
        with c1:
            st.write(label)
        with c2:
            btn = "Desativar" if is_active else "Ativar"
            if st.button(btn, key=f"exam_toggle_{ex['id']}"):
                toggle_exam_active(ex["id"])
                st.rerun()
        with c3:
            if st.button("Excluir", key=f"exam_del_{ex['id']}"):
                delete_exam(ex["id"])
                st.rerun()

    st.markdown("---")
    st.subheader("Pré-visualização (com gabarito)")
    preview_options = {ex["title"]: ex["id"] for ex in exams}
    prev_title = st.selectbox("Prova", list(preview_options.keys()), key="exam_preview_sel")
    prev_exam = get_exam(preview_options[prev_title])
    if prev_exam:
        render_exam_question_preview(prev_exam["questions"], show_gabarito=True)

    st.markdown("---")
    st.subheader("Resultados e revisão (A / PA / NA)")
    st.caption(
        "Correção automática: **A** = acertou, **PA** = parcialmente acertou, **NA** = não acertou. "
        "Você pode ajustar manualmente."
    )
    corr_options = {ex["title"]: ex["id"] for ex in exams}
    corr_title = st.selectbox("Prova", list(corr_options.keys()), key="exam_corr_sel")
    corr_id = corr_options[corr_title]
    corr_exam = get_exam(corr_id)
    submissions = submissions_for_exam(corr_id)

    if not submissions:
        st.info("Nenhuma prova enviada pelos alunos ainda.")
        return

    st.markdown("#### Exportar PDF")
    st.caption("PDF no formato da prova com nome completo e respostas do aluno.")
    export_names = [s["student_name"] for s in submissions]
    pick_name = st.selectbox("Aluno para exportar", export_names, key="export_pick_student")
    pick_sub = next(s for s in submissions if s["student_name"] == pick_name)
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "📥 PDF — respostas do aluno",
            data=build_exam_pdf_bytes(corr_exam, pick_sub, include_gabarito=False),
            file_name=export_filename(corr_exam, pick_sub),
            mime="application/pdf",
            key="export_student_pdf",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            "📥 PDF — com gabarito (professor)",
            data=build_exam_pdf_bytes(corr_exam, pick_sub, include_gabarito=True),
            file_name=export_filename(corr_exam, pick_sub).replace(".pdf", "_gabarito.pdf"),
            mime="application/pdf",
            key="export_teacher_pdf",
            use_container_width=True,
        )

    st.markdown("---")

    for sub in submissions:
        summary = sub.get("summary") or summarize_answers(sub["answers"])
        c = summary["counts"]
        label = (
            f"{sub['student_name']} — "
            f"A:{c['A']} | PA:{c['PA']} | NA:{c['NA']} — "
            f"{summary['total_points']:.1f}/{summary['max_points']:.0f} pts"
        )
        with st.expander(label):
            if not corr_exam:
                continue
            new_answers = []
            for i, (ans, q_full) in enumerate(zip(sub["answers"], corr_exam["questions"])):
                tipo = "MC" if ans.get("type") == "choice" else "Justificativa"
                st.markdown(f"**{i + 1}. [{tipo}]** {q_full['question']}")
                if ans.get("type") == "choice":
                    st.write(f"Resposta: **{ans.get('selected', '—')}**")
                else:
                    st.write(f"Resposta do aluno: {ans.get('text', '')}")
                    if q_full.get("answer_key"):
                        st.caption(f"Gabarito: {q_full['answer_key']}")
                current = ans.get("classification", "NA")
                if current not in CLASSIFICATIONS:
                    current = "NA"
                render_classification_badge(current)
                if ans.get("auto_graded"):
                    st.caption("Classificação automática")
                new_clf = st.selectbox(
                    "Ajustar classificação",
                    options=list(CLASSIFICATIONS),
                    index=list(CLASSIFICATIONS).index(current),
                    format_func=lambda x: LABELS[x],
                    key=f"clf_{sub['id']}_{i}",
                )
                updated = {
                    **ans,
                    "classification": new_clf,
                    "points": POINTS[new_clf],
                    "reviewed": True,
                    "auto_graded": ans.get("auto_graded", False) and new_clf == current,
                }
                if new_clf != current:
                    updated["auto_graded"] = False
                new_answers.append(updated)
            if st.button("💾 Salvar revisão", key=f"save_corr_{sub['id']}"):
                sub_summary = summarize_answers(new_answers)
                update_exam_submission(sub["id"], new_answers, sub_summary)
                st.success("Revisão salva.")
                st.rerun()

            st.download_button(
                "📥 Baixar PDF deste aluno",
                data=build_exam_pdf_bytes(corr_exam, sub, include_gabarito=False),
                file_name=export_filename(corr_exam, sub),
                mime="application/pdf",
                key=f"dl_sub_{sub['id']}",
            )


def render_professor_panel():
    st.title("👨‍🏫 Painel do Professor")

    current_user = st.session_state.get("current_user") or {}
    show_admin_tab = auth_users.is_system_admin(current_user.get("email")) or bool(
        current_user.get("is_admin")
    )
    section = st.session_state.professor_section

    materials = list_materials()
    active_ids = set(get_active_material_ids())

    if section == "materials":
        st.caption("Vários materiais podem ficar ativos ao mesmo tempo para os alunos.")
        st.subheader("Gerenciar materiais")
        new_title = st.text_input("Título do novo material", placeholder="Ex.: Lógica - Aula 3")
        uploaded = st.file_uploader("Importar perguntas de PDF", type="pdf", key="prof_pdf")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("➕ Criar material vazio") and new_title.strip():
                create_material(new_title.strip(), [])
                st.success("Material criado.")
                st.rerun()
        with col_b:
            if st.button("📄 Criar a partir do PDF") and uploaded and new_title.strip():
                questions = parse_questions_from_pdf(uploaded)
                if questions:
                    create_material(new_title.strip(), questions)
                    st.success(f"Material criado com {len(questions)} perguntas.")
                    st.rerun()
                else:
                    st.error("Não foi possível extrair perguntas do PDF.")

        if not materials:
            st.info("Nenhum material cadastrado. Crie um material acima.")
        else:
            st.markdown("---")
            for m in materials:
                is_active = m["id"] in active_ids
                label = f"{'🟢 ' if is_active else ''}{m['title']} ({len(m['questions'])} perguntas)"
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    st.write(label)
                with c2:
                    btn_label = "Desativar" if is_active else "Ativar"
                    if st.button(btn_label, key=f"toggle_{m['id']}"):
                        toggle_material_active(m["id"])
                        st.rerun()
                with c3:
                    if st.button("Editar", key=f"edit_{m['id']}"):
                        st.session_state.professor_edit_id = m["id"]
                        st.rerun()
                with c4:
                    if st.button("Excluir", key=f"del_{m['id']}"):
                        delete_material(m["id"])
                        if st.session_state.professor_edit_id == m["id"]:
                            st.session_state.professor_edit_id = None
                        st.rerun()

    elif section == "edit":
        if not materials:
            st.info("Crie um material na aba Materiais primeiro.")
        else:
            options = {m["title"]: m["id"] for m in materials}
            default_id = st.session_state.professor_edit_id or (
                next(iter(active_ids), None) if active_ids else None
            )
            default_title = next(
                (t for t, mid in options.items() if mid == default_id),
                list(options.keys())[0],
            )
            selected_title = st.selectbox(
                "Material para editar",
                options=list(options.keys()),
                index=list(options.keys()).index(default_title),
            )
            material_id = options[selected_title]
            material = get_material(material_id)
            if not material:
                st.error("Material não encontrado.")
                return

            title = st.text_input("Título do material", value=material["title"])
            questions = material["questions"]

            if st.button("➕ Adicionar pergunta"):
                questions = questions + [EMPTY_QUESTION.copy()]
                update_material(material_id, title, questions)
                st.session_state.professor_edit_id = material_id
                st.rerun()

            pdf_update = st.file_uploader(
                "Substituir todas as perguntas via PDF",
                type="pdf",
                key="prof_pdf_replace",
            )
            if pdf_update and st.button("Importar PDF neste material"):
                parsed = parse_questions_from_pdf(pdf_update)
                if parsed:
                    update_material(material_id, title, parsed)
                    st.success(f"{len(parsed)} perguntas importadas.")
                    st.rerun()

            edited = render_question_editor(questions, key_prefix=f"mat_{material_id}")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Salvar alterações", type="primary"):
                    valid, errors = validate_questions(edited)
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        update_material(material_id, title, valid)
                        st.success("Material salvo.")
                        st.rerun()
            with c2:
                active_now = is_material_active(material_id)
                toggle_label = "🔴 Desativar para alunos" if active_now else "🟢 Ativar para alunos"
                if st.button(toggle_label):
                    now_active = toggle_material_active(material_id)
                    if now_active:
                        st.success("Material ativado para os alunos.")
                    else:
                        st.success("Material desativado.")
                    st.rerun()

    elif section == "exams":
        render_exams_tab()

    elif section == "students":
        render_students_tab()

    elif section == "results":
        if not materials:
            st.info("Sem materiais para analisar.")
        else:
            mat_options = {m["title"]: m["id"] for m in materials}
            res_title = st.selectbox("Material", list(mat_options.keys()), key="res_mat")
            res_id = mat_options[res_title]
            material = get_material(res_id)
            entries = leaderboard_for_material(res_id)

            if not entries:
                st.info("Nenhum aluno finalizou este quiz ainda.")
            else:
                plot_leaderboard_comparison(entries)
                if material:
                    plot_question_performance(entries, len(material["questions"]))
                df_rank = pd.DataFrame(entries)
                df_rank["% Acertos"] = (df_rank["score"] / df_rank["total"]) * 100
                st.dataframe(
                    df_rank[["name", "score", "total", "% Acertos"]].sort_values(
                        "% Acertos", ascending=False
                    )
                )
                if st.button("🗑️ Limpar resultados deste material"):
                    st.session_state.leaderboard = [
                        e
                        for e in st.session_state.leaderboard
                        if e.get("material_id") != res_id
                    ]
                    save_leaderboard(st.session_state.leaderboard)
                    st.success("Resultados removidos.")
                    st.rerun()

    elif section == "config":
        render_auth_config_tab()

    elif section == "admin" and show_admin_tab:
        render_admin_approvals_tab()


# ---------------------------
# Aluno
# ---------------------------
def render_student_register_sidebar():
    registered = load_students()
    with st.sidebar.expander("📝 Cadastrar-me", expanded=not registered):
        if render_student_register_form("register_in_sidebar"):
            st.rerun()


def render_student_panel():
    st.title("👨‍🎓 Área do Aluno")

    if st.session_state.student_section == "quiz":
        render_student_quiz_tab()
    else:
        render_student_exam_tab()


def render_student_quiz_tab():
    playable = get_playable_active_materials()
    active_all = get_active_materials()
    selected_id = st.session_state.selected_material_id
    if playable and selected_id not in [m["id"] for m in playable]:
        selected_id = playable[0]["id"]
        st.session_state.selected_material_id = selected_id
    elif playable and not selected_id:
        st.session_state.selected_material_id = playable[0]["id"]
        selected_id = playable[0]["id"]

    material = get_material(selected_id) if selected_id else None
    registered = load_students()

    if not load_students():
        st.subheader("Cadastro de aluno")
        st.markdown("Faça seu cadastro para participar.")
        if render_student_register_form("register_main"):
            st.rerun()
        return

    col_cfg, col_main = st.columns([1, 2])
    with col_cfg:
        st.subheader("Configuração")
        if not active_all:
            st.warning("Nenhum quiz ativo.")
        elif not playable:
            st.warning("Materiais ativos sem perguntas.")
        else:
            mat_options = {m["title"]: m["id"] for m in playable}
            titles = list(mat_options.keys())
            default_title = next(
                (t for t, mid in mat_options.items() if mid == selected_id),
                titles[0],
            )
            picked_title = st.selectbox(
                "Escolha o quiz",
                options=titles,
                index=titles.index(default_title),
                key="student_material_select",
            )
            picked_id = mat_options[picked_title]
            if picked_id != st.session_state.selected_material_id:
                load_student_material(picked_id)
                st.session_state.quiz_active = False
                st.session_state.quiz_finished = False
                st.rerun()

            mat = get_material(picked_id)
            if mat:
                st.write(f"**Perguntas:** {len(mat['questions'])}")

            names = sorted(s["name"] for s in registered)
            preferred = st.session_state.preferred_student_name
            default_index = 0
            if preferred and preferred in names:
                default_index = names.index(preferred) + 1
            selected_name = st.selectbox(
                "Seu nome",
                options=[""] + names,
                index=default_index,
                format_func=lambda x: "— Escolha —" if x == "" else x,
                key="student_name_select",
            )
            if (
                st.button("🆕 Iniciar quiz", use_container_width=True)
                and selected_name
                and mat
            ):
                load_student_material(picked_id)
                mid = st.session_state.current_material_id
                if name_exists_in_leaderboard(selected_name, mid):
                    st.warning("Um novo resultado será adicionado ao refazer.")
                st.session_state.current_student_name = selected_name
                st.session_state.preferred_student_name = selected_name
                reset_quiz()
                st.rerun()

    with col_main:
        if not playable:
            st.info("Nenhum quiz disponível no momento.")
            return

        if st.session_state.quiz_active and not st.session_state.quiz_finished:
            _render_quiz_flow()
        elif st.session_state.quiz_finished:
            _render_quiz_results()
        else:
            if len(playable) > 1:
                st.markdown("### Quizzes disponíveis")
                for m in playable:
                    st.write(f"- **{m['title']}** — {len(m['questions'])} perguntas")
            if material:
                st.markdown(f"### {material['title']}")
            st.markdown("Escolha o quiz e clique em **Iniciar quiz**.")


def get_playable_active_exams() -> list:
    return [e for e in get_active_exams() if e.get("questions")]


def render_student_exam_tab():
    playable_exams = get_playable_active_exams()
    registered = load_students()

    if not load_students():
        st.info("Cadastre-se na barra lateral para fazer provas.")
        return

    if st.session_state.exam_mode == "done" and st.session_state.exam_submission_result:
        result = st.session_state.exam_submission_result
        summary = result.get("summary", summarize_answers(result["answers"]))
        counts = summary["counts"]
        st.success(f"Prova enviada, {result['student_name']}!")
        st.metric(
            "Pontuação automática",
            f"{summary['total_points']:.1f} / {summary['max_points']:.0f}",
            delta=f"{summary['percent']:.0f}%",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("A — Acertou", counts["A"])
        with c2:
            st.metric("PA — Parcial", counts["PA"])
        with c3:
            st.metric("NA — Não acertou", counts["NA"])

        st.subheader("Resultado por questão")
        for i, ans in enumerate(result["answers"]):
            clf = ans.get("classification", "NA")
            tipo = "Múltipla escolha" if ans.get("type") == "choice" else "Justificativa"
            st.write(f"**Questão {i + 1}** ({tipo})")
            render_classification_badge(clf)

        exam_for_pdf = get_exam(result.get("exam_id"))
        if exam_for_pdf:
            st.download_button(
                "📥 Baixar minha prova em PDF",
                data=build_exam_pdf_bytes(exam_for_pdf, result, include_gabarito=False),
                file_name=export_filename(exam_for_pdf, result),
                mime="application/pdf",
                key="student_download_exam_pdf",
            )

        if st.button("Voltar às provas"):
            st.session_state.exam_mode = "select"
            st.session_state.exam_submission_result = None
            st.rerun()
        return

    if st.session_state.exam_mode == "take":
        exam = get_exam(st.session_state.selected_exam_id)
        if not exam:
            st.session_state.exam_mode = "select"
            st.rerun()
            return

        st.subheader(exam["title"])
        st.caption("Responda todas as questões e envie ao final. Gabarito não é exibido.")

        with st.form("exam_submit_form"):
            answers_input = []
            for i, q in enumerate(exam["questions"]):
                q_view = question_for_student(q)
                st.markdown(f"**Questão {i + 1}**")
                st.write(q_view["question"])
                if q_view["type"] == "choice":
                    opts = {letter: q_view["options"][j] for j, letter in enumerate("ABCD")}
                    picked = st.radio(
                        "Alternativa",
                        options=list(opts.keys()),
                        format_func=lambda x: f"{x}) {opts[x]}",
                        key=f"exam_q_{i}",
                        label_visibility="collapsed",
                    )
                    answers_input.append(("choice", picked))
                else:
                    text = st.text_area(
                        "Sua resposta (justifique)",
                        key=f"exam_q_{i}",
                        height=120,
                    )
                    answers_input.append(("justify", text))

            if st.form_submit_button("📤 Enviar prova", type="primary"):
                graded = []
                for (kind, value), q_full in zip(answers_input, exam["questions"]):
                    if kind == "choice":
                        graded.append(
                            grade_choice_answer(value, q_full["correct"])
                        )
                    else:
                        graded.append(
                            grade_justify_answer(
                                value, q_full.get("answer_key", "")
                            )
                        )

                summary = summarize_answers(graded)
                submission = {
                    "id": str(uuid.uuid4()),
                    "exam_id": exam["id"],
                    "student_name": st.session_state.current_student_name,
                    "answers": graded,
                    "summary": summary,
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                }
                add_exam_submission(submission)
                st.session_state.exam_submission_result = submission
                st.session_state.exam_mode = "done"
                st.rerun()

        if st.button("Cancelar"):
            st.session_state.exam_mode = "select"
            st.rerun()
        return

    if not playable_exams:
        st.info("Nenhuma prova ativa disponível. Aguarde o professor.")
        return

    st.subheader("Provas disponíveis")
    exam_options = {e["title"]: e["id"] for e in playable_exams}
    titles = list(exam_options.keys())
    default_exam = st.session_state.selected_exam_id
    default_title = next(
        (t for t, eid in exam_options.items() if eid == default_exam),
        titles[0],
    )
    picked_title = st.selectbox("Escolha a prova", titles, index=titles.index(default_title))
    picked_id = exam_options[picked_title]
    st.session_state.selected_exam_id = picked_id

    exam = get_exam(picked_id)
    if exam:
        summary = exam_summary(exam["questions"])
        st.write(
            f"**{summary['total']}** questões — "
            f"{summary['choice']} múltipla escolha, {summary['justify']} justificativas"
        )

    names = sorted(s["name"] for s in registered)
    preferred = st.session_state.preferred_student_name
    name_index = 0
    if preferred and preferred in names:
        name_index = names.index(preferred) + 1
    student_name = st.selectbox(
        "Seu nome",
        [""] + names,
        index=name_index,
        format_func=lambda x: "— Escolha —" if x == "" else x,
        key="exam_student_name",
    )

    if st.button("📋 Abrir prova", type="primary") and student_name:
        st.session_state.current_student_name = student_name
        st.session_state.preferred_student_name = student_name
        st.session_state.exam_mode = "take"
        st.rerun()


def _render_quiz_flow():
    q_index = st.session_state.current_q_index
    total_q = len(st.session_state.questions)
    if q_index < total_q:
        q_data = st.session_state.questions[q_index]
        st.header(f"Questão {q_index + 1} de {total_q}")
        st.subheader(q_data["question"])

        feedback = st.session_state.answer_feedback
        if feedback is not None:
            if feedback["is_correct"]:
                st.success("✅ Resposta correta!")
            else:
                st.error(
                    f"❌ Resposta incorreta. A alternativa correta era **{feedback['correct']}**."
                )
            if st.button("➡️ Próxima pergunta", key="next_question"):
                st.session_state.answer_feedback = None
                if q_index + 1 < total_q:
                    st.session_state.current_q_index += 1
                    st.rerun()
                else:
                    finish_quiz()
                    st.rerun()
        else:
            option_map = {chr(65 + i): opt for i, opt in enumerate(q_data["options"])}
            selected_letter = st.radio(
                "Escolha uma alternativa:",
                options=list(option_map.keys()),
                format_func=lambda x: f"{x}: {option_map[x]}",
                key=f"q_{q_index}",
            )
            if st.button("✅ Responder", key="submit_answer"):
                is_correct = selected_letter == q_data["correct"]
                st.session_state.student_answers.append(is_correct)
                st.session_state.answer_feedback = {
                    "is_correct": is_correct,
                    "correct": q_data["correct"],
                }
                st.rerun()
    else:
        finish_quiz()
        st.rerun()


def _render_quiz_results():
    st.success(f"Quiz finalizado, {st.session_state.current_student_name}!")
    total = len(st.session_state.questions)
    acertos = sum(st.session_state.student_answers)
    pct = f"{acertos / total * 100:.1f}%" if total > 0 else "N/A"
    st.metric("Pontuação", f"{acertos} / {total}", delta=pct)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Seu desempenho")
        plot_student_result(st.session_state.student_answers, total)
    with col2:
        st.subheader("Resumo")
        st.write(f"✅ Acertos: {acertos}")
        st.write(f"❌ Erros: {total - acertos}")

    if st.button("📝 Fazer quiz novamente"):
        st.session_state.quiz_finished = False
        st.session_state.quiz_active = False
        st.rerun()


# ---------------------------
# Main
# ---------------------------
def configure_streamlit_page():
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


def main():
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
