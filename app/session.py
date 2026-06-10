from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

import auth_users
import quiz_storage
from google_auth import clear_oauth_session
from quiz_storage import (
    append_leaderboard_entry,
    get_active_materials,
    get_material,
    leaderboard_for_material,
    load_leaderboard,
    migrate_legacy_leaderboard,
)


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


def bound_student_name() -> str | None:
    """Nome do aluno vinculado à sessão: conta Google ou primeira identificação.

    Quando definido, o aluno não pode mais trocar de nome no quiz/prova.
    """
    user = st.session_state.get("current_user")
    if user and user.get("role") == "student" and user.get("name"):
        return user["name"]
    return st.session_state.get("preferred_student_name") or None


def load_student_material(material_id: str) -> dict | None:
    # Não escrever em st.session_state.selected_material_id aqui: é a key do
    # selectbox "Escolha o quiz" e modificá-la após o widget ser instanciado
    # (ex.: clique em "Iniciar quiz") lança StreamlitAPIException.
    material = get_material(material_id)
    if material:
        st.session_state.questions = material["questions"]
        st.session_state.current_material_id = material["id"]
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
    if st.session_state.get("quiz_finished"):
        return
    total = len(st.session_state.questions)
    score = sum(st.session_state.student_answers)
    user = st.session_state.get("current_user") or {}
    entry = {
        "material_id": st.session_state.current_material_id,
        "name": st.session_state.current_student_name,
        "score": score,
        "total": total,
        "responses": st.session_state.student_answers.copy(),
        # Identidade da conta (Google) — permite recuperar o histórico do aluno
        # mesmo após recarregar a página ou abrir nova sessão.
        "student_email": (user.get("email") or "").strip().lower() or None,
        "student_user_id": user.get("id"),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    # Append atômico direto no arquivo: a cópia da sessão pode estar
    # desatualizada e sobrescreveria resultados de outros alunos.
    st.session_state.leaderboard = append_leaderboard_entry(entry)
    st.session_state.quiz_active = False
    st.session_state.quiz_finished = True
    st.session_state.answer_feedback = None


# Acertos a partir dos quais o quiz é considerado concluído (sem nova tentativa).
QUIZ_SECOND_CHANCE_MIN_SCORE = 7
QUIZ_MAX_ATTEMPTS = 2


def quiz_attempts_for(name: str, material_id: str) -> list:
    key = name.strip().lower()
    return [
        e
        for e in leaderboard_for_material(material_id)
        if e["name"].strip().lower() == key
    ]


def quiz_attempt_permission(name: str, material_id: str) -> tuple[bool, str]:
    """Regra de tentativas: 2ª oportunidade apenas para quem fez < 7 acertos.

    Retorna (pode_jogar, mensagem). A mensagem é informativa quando pode jogar
    (segunda oportunidade) ou explica o bloqueio quando não pode.
    """
    attempts = quiz_attempts_for(name, material_id)
    if not attempts:
        return True, ""

    best = max(attempts, key=lambda e: e.get("score", 0))
    best_score = best.get("score", 0)
    best_total = best.get("total", 0)
    # Em quizzes com menos de 7 perguntas, a nota máxima conta como concluído.
    target = min(QUIZ_SECOND_CHANCE_MIN_SCORE, best_total or QUIZ_SECOND_CHANCE_MIN_SCORE)

    if best_score >= target:
        return False, (
            f"Você já concluiu este quiz com **{best_score} de {best_total}** acertos. "
            "Bom trabalho!"
        )
    if len(attempts) >= QUIZ_MAX_ATTEMPTS:
        return False, (
            f"Você já usou suas {QUIZ_MAX_ATTEMPTS} tentativas neste quiz "
            f"(melhor resultado: **{best_score} de {best_total}**)."
        )
    return True, (
        f"Segunda oportunidade: você acertou **{best_score} de {best_total}** "
        "na primeira tentativa. Boa sorte!"
    )


def sync_playable_material(playable: list) -> str | None:
    """Garante material válido selecionado sem disparar rerun."""
    if not playable:
        return None
    playable_ids = [m["id"] for m in playable]
    if st.session_state.selected_material_id not in playable_ids:
        st.session_state.selected_material_id = playable_ids[0]
    load_student_material(st.session_state.selected_material_id)
    return st.session_state.selected_material_id


def on_quiz_material_changed() -> None:
    """Callback do selectbox de quiz — evita loop de rerun no render."""
    load_student_material(st.session_state.selected_material_id)
    st.session_state.quiz_active = False
    st.session_state.quiz_finished = False


def sync_playable_exam(playable_exams: list) -> str | None:
    """Garante prova válida selecionada sem disparar rerun."""
    if not playable_exams:
        return None
    playable_ids = [e["id"] for e in playable_exams]
    if st.session_state.selected_exam_id not in playable_ids:
        st.session_state.selected_exam_id = playable_ids[0]
    return st.session_state.selected_exam_id
