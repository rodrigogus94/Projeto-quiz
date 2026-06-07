from __future__ import annotations

import importlib
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
import streamlit.components.v1 as components

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

import quiz_storage
import google_auth

importlib.reload(google_auth)
from google_auth import (
    clear_oauth_session,
    google_oauth_configured,
    legacy_password_enabled,
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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout():
    clear_oauth_session()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
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
LOGIN_DARK = "#1d2021"
LOGIN_INPUT_BG = "#2d3436"
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
section[data-testid="stSidebar"], header[data-testid="stHeader"], footer {{
    display: none !important;
}}
.stApp {{ background: {LOGIN_DARK} !important; }}
.main .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
    margin: 0 !important;
}}
.kahoot-login-marker {{ display: none !important; }}
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
    background: {LOGIN_DARK} !important;
    flex: 0 0 50% !important;
    width: 50% !important;
    max-width: 50% !important;
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
.kahoot-login-row > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 100% !important;
    flex: 1 1 auto !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"] {{
    max-width: 360px;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {{
    max-width: 360px;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-social-icon) {{
    max-width: 220px !important; width: auto !important;
    margin: 0 auto 0.5rem !important; gap: 1rem !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-social-icon) > [data-testid="stColumn"] {{
    flex: 0 0 auto !important; width: auto !important; max-width: none !important;
    min-height: unset !important; padding: 0 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-social-icon) > [data-testid="stColumn"]:nth-child(2) {{
    position: relative !important;
    width: 42px !important; height: 42px !important;
    min-height: 42px !important; flex: 0 0 42px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-social-icon) > [data-testid="stColumn"]:nth-child(2) > [data-testid="stVerticalBlock"] {{
    position: relative !important;
    width: 42px !important; height: 42px !important;
    min-height: 42px !important; justify-content: flex-start !important;
}}
.kahoot-google-visual {{
    width: 42px; height: 42px; border-radius: 50%;
    border: 1px solid #3d4f66; background-color: #ffffff;
    background-image: url("{GOOGLE_ICON_SVG}");
    background-size: 22px; background-repeat: no-repeat; background-position: center;
    margin: 0 auto; pointer-events: none;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-social-icon) > [data-testid="stColumn"]:nth-child(2) .element-container:has(
    iframe[title="streamlit_oauth.authorize_button"]
) {{
    position: absolute !important; top: 0 !important; left: 0 !important;
    width: 42px !important; height: 42px !important;
    opacity: 0 !important; z-index: 2 !important;
    margin: 0 !important; padding: 0 !important; overflow: visible !important;
    border: none !important; background: transparent !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(.kahoot-social-icon) iframe[title="streamlit_oauth.authorize_button"] {{
    width: 42px !important; height: 42px !important; border: none !important;
    margin: 0 !important; cursor: pointer !important;
}}
.kahoot-form-wrap {{ width: 100%; max-width: 360px; margin: 0 auto; }}
.kahoot-form-title {{
    color: #c8d6e0; font-size: 1.85rem; font-weight: 700;
    text-align: center; margin: 0 0 1.25rem;
    font-family: "Segoe UI", system-ui, sans-serif;
}}
.kahoot-form-sub {{
    color: #7f8c9a; font-size: 0.85rem; text-align: center; margin: 0 0 1rem;
}}
.kahoot-social-icon {{
    width: 42px; height: 42px; border-radius: 50%;
    background: {LOGIN_INPUT_BG}; border: 1px solid #3d4f66;
    color: #aabbc8; font-size: 0.85rem; font-weight: 600;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto;
}}
.kahoot-or-line {{
    display: flex; align-items: center; gap: 0.75rem;
    margin: 1.25rem 0; color: #6b7c93; font-size: 0.82rem;
}}
.kahoot-or-line::before, .kahoot-or-line::after {{
    content: ""; flex: 1; height: 1px; background: #3d4f66;
}}
.kahoot-footnote {{
    color: #6b7c93; font-size: 0.78rem; text-align: center;
    margin-top: 1.25rem; line-height: 1.5;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child label {{
    color: #aabbc8 !important; font-weight: 600 !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child input {{
    background: {LOGIN_INPUT_BG} !important;
    border: 1px solid #3d4f66 !important;
    color: #e8edf2 !important;
    border-radius: 8px !important;
}}
.kahoot-login-row > [data-testid="stColumn"]:last-child .stTextInput > div > div {{
    background: {LOGIN_INPUT_BG} !important;
    border: 1px solid #3d4f66 !important;
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
    background: {LOGIN_INPUT_BG} !important;
    color: #c5d0dc !important;
    border: 1px solid #3d4f66 !important;
    border-radius: 25px !important;
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


def _apply_login_styles_in_parent():
    css_json = json.dumps(LOGIN_PAGE_CSS)
    components.html(
        f"""
        <script>
        (function() {{
            function applyLoginLayout() {{
                const doc = window.parent.document;
                let style = doc.getElementById("kahoot-login-style");
                if (!style) {{
                    style = doc.createElement("style");
                    style.id = "kahoot-login-style";
                    doc.head.appendChild(style);
                }}
                style.textContent = {css_json};
                doc.querySelectorAll(".kahoot-login-marker").forEach((marker) => {{
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
        height=0,
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
    return google_auth.render_google_login_button(
        "",
        key=key,
        role_hint="unified",
        use_container_width=False,
        icon=GOOGLE_ICON_SVG,
    )


def _render_social_google_row(oauth_key: str) -> dict | None:
    profile = None
    s1, s2, s3 = st.columns([1, 1, 1], gap="small")
    with s1:
        st.markdown('<div class="kahoot-social-icon">f</div>', unsafe_allow_html=True)
    with s2:
        st.markdown('<div class="kahoot-google-visual"></div>', unsafe_allow_html=True)
        if google_oauth_configured():
            profile = render_google_icon_login(oauth_key)
    with s3:
        st.markdown('<div class="kahoot-social-icon">in</div>', unsafe_allow_html=True)
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

    st.markdown(f"<style>{LOGIN_PAGE_CSS}</style>", unsafe_allow_html=True)
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
        if view == "signup":
            render_login_signup_panel()
        else:
            render_login_signin_panel()

    _apply_login_styles_in_parent()


def render_sidebar_logout():
    user = st.session_state.get("current_user")
    if user:
        role_label = "Professor" if user.get("role") == "professor" else "Aluno"
        name = user.get("name") or user.get("email") or role_label
        st.sidebar.caption(f"**{name}** ({role_label})")
        if user.get("email"):
            st.sidebar.caption(user["email"])
    else:
        role_label = "Aluno" if st.session_state.role == "student" else "Visitante"
        st.sidebar.caption(f"Modo **{role_label}** (sem conta Google)")
    if st.sidebar.button("Sair", use_container_width=True):
        logout()


# ---------------------------
# Admin Panel
# ---------------------------
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


def render_professor_panel():
    st.set_page_config(page_title="Quiz Interativo - Professor", layout="wide")
    render_sidebar_logout()

    st.title("Painel do Professor")
    st.write("Bem-vindo ao painel de administração de quizzes!")

    tab1, tab2, tab3 = st.tabs(["Criar Material", "Gerenciar Quizzes", "Configurações"])

    with tab1:
        st.subheader("Criar novo material")
        st.write("Funcionalidade de criação de material será implementada aqui.")

    with tab2:
        st.subheader("Gerenciar quizzes")
        st.write("Funcionalidade de gerenciamento será implementada aqui.")

    with tab3:
        tab3a, tab3b = st.tabs(["Aprovações", "Autenticação"])
        with tab3a:
            render_admin_approvals_tab()
        with tab3b:
            render_auth_config_tab()


def render_student_panel():
    st.set_page_config(page_title="Quiz Interativo - Aluno", layout="wide")
    render_sidebar_logout()

    st.title("Bem-vindo ao Quiz Interativo!")
    st.write("Selecione um quiz abaixo para começar.")

    materials = get_playable_active_materials()
    if not materials:
        st.info("Nenhum quiz disponível no momento.")
        return

    for material in materials:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(material.get("title", "Quiz sem título"))
                st.write(material.get("description", ""))
            with col2:
                if st.button("Iniciar", key=f"start_{material['id']}", use_container_width=True):
                    load_student_material(material["id"])
                    reset_quiz()
                    st.rerun()


# ---------------------------
# Main
# ---------------------------
def main():
    st.set_page_config(page_title="Quiz Interativo", layout="wide", initial_sidebar_state="collapsed")
    init_session_state()

    if st.session_state.role is None:
        render_login()
        return

    if st.session_state.role == "professor":
        render_professor_panel()
    else:
        render_student_panel()


if __name__ == "__main__":
    main()