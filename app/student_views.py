from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import auth_users
from auto_grade import (
    grade_choice_answer,
    grade_justify_answer,
    summarize_answers,
)
from pdf_export import build_exam_pdf_bytes, export_filename
from pdf_parser import exam_summary, question_for_student
from quiz_storage import (
    add_exam_submission,
    get_active_exams,
    get_active_materials,
    get_exam,
    get_material,
    load_exam_submissions,
    load_leaderboard,
    load_students,
)

from app.result_transfer import (
    build_student_export,
    export_bytes as results_export_bytes,
    export_filename as results_export_filename,
)

from app.auth_ui import render_student_register_form
from app.charts import plot_student_result
from app.components import (
    inject_student_area_css,
    render_classification_badge,
    render_empty_state,
    render_flow_header,
    render_result_banner,
    render_student_hero,
)
from app.session import (
    bound_student_name,
    finish_quiz,
    get_playable_active_materials,
    load_student_material,
    on_quiz_material_changed,
    quiz_attempt_permission,
    reset_quiz,
    sync_playable_exam,
    sync_playable_material,
)


def _render_student_identity(names: list[str], picker_key: str) -> str:
    """Nome do aluno: travado quando vinculado à sessão; seleção única caso contrário."""
    bound = bound_student_name()
    if bound:
        if bound in names:
            st.text_input(
                "Seu nome",
                value=bound,
                disabled=True,
                key=f"{picker_key}_locked",
            )
            st.caption("🔒 Identificação vinculada à sua sessão.")
            return bound
        st.warning(
            f"Sua conta (**{bound}**) ainda não está na lista de alunos aprovados. "
            "Aguarde a aprovação do administrador."
        )
        return ""
    return st.selectbox(
        "Seu nome",
        options=[""] + names,
        format_func=lambda x: "— Escolha —" if x == "" else x,
        key=picker_key,
        help="Após iniciar, o nome fica vinculado à sessão e não pode ser trocado.",
    )


def approved_students() -> list:
    return [s for s in load_students() if auth_users.is_approved_student_name(s["name"])]


def _render_results_download(widget_key: str):
    """Botão para baixar o arquivo com todos os resultados do aluno."""
    name = bound_student_name() or st.session_state.get("current_student_name") or ""
    if not name.strip():
        return
    user = st.session_state.get("current_user") or {}
    payload = build_student_export(name, user.get("email"))
    if not payload["quiz_results"] and not payload["exam_submissions"]:
        return
    st.download_button(
        "📥 Baixar arquivo de resultados (enviar ao professor)",
        data=results_export_bytes(payload),
        file_name=results_export_filename(name),
        mime="application/json",
        key=widget_key,
        help=(
            "Gera um arquivo com todos os seus resultados de quizzes e provas. "
            "Envie-o ao professor para que ele registre suas notas."
        ),
    )


def _format_when(iso_ts: str | None) -> str:
    if not iso_ts:
        return "—"
    return iso_ts[:16].replace("T", " ")


def _my_identity_keys() -> tuple[str, str]:
    """(email, nome normalizado) da identidade vinculada à sessão."""
    user = st.session_state.get("current_user") or {}
    email = (user.get("email") or "").strip().lower()
    name = (bound_student_name() or "").strip().lower()
    return email, name


def _render_my_quiz_history():
    """Resultados salvos do aluno — recuperados pela conta (e-mail) ou nome."""
    email, name_key = _my_identity_keys()
    if not email and not name_key:
        return

    mine = [
        e
        for e in load_leaderboard()
        if (email and (e.get("student_email") or "").strip().lower() == email)
        or (name_key and e.get("name", "").strip().lower() == name_key)
    ]

    st.markdown("#### 📜 Meus resultados")
    if not mine:
        st.caption("Você ainda não concluiu nenhum quiz.")
        return
    rows = []
    for e in mine:
        mat = get_material(e.get("material_id") or "")
        pct = (e["score"] / e["total"] * 100) if e.get("total") else 0.0
        rows.append(
            {
                "Quiz": mat["title"] if mat else "(material removido)",
                "Acertos": f"{e['score']}/{e['total']}",
                "% Acertos": round(pct, 1),
                "Quando (UTC)": _format_when(e.get("submitted_at")),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    _render_results_download("dl_results_quiz_history")


def _render_my_exam_history():
    """Provas já enviadas pelo aluno — persistidas entre sessões."""
    email, name_key = _my_identity_keys()
    if not name_key and not email:
        return

    mine = [
        s
        for s in load_exam_submissions()
        if (name_key and s.get("student_name", "").strip().lower() == name_key)
        or (email and (s.get("student_email") or "").strip().lower() == email)
    ]

    st.markdown("#### 📜 Minhas provas enviadas")
    if not mine:
        st.caption("Você ainda não enviou nenhuma prova.")
        return
    rows = []
    for s in mine:
        exam = get_exam(s.get("exam_id") or "")
        counts = (s.get("summary") or {}).get("counts", {})
        rows.append(
            {
                "Prova": exam["title"] if exam else "(prova removida)",
                "A": counts.get("A", 0),
                "PA": counts.get("PA", 0),
                "NA": counts.get("NA", 0),
                "Enviada em (UTC)": _format_when(s.get("submitted_at")),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_student_panel():
    inject_student_area_css()
    section = st.session_state.student_section
    section_label = "Quiz" if section == "quiz" else "Provas"

    st.title("👨‍🎓 Área do Aluno")
    st.caption(f"**{section_label}** · use a navegação na barra lateral para trocar de seção.")

    if section == "quiz":
        render_student_quiz_tab()
    else:
        render_student_exam_tab()


def _render_registration_gate():
    render_empty_state(
        icon="👋",
        title="Bem-vindo!",
        message="Cadastre-se para participar dos quizzes e provas da turma.",
        hint="Após o cadastro, o administrador precisa aprovar seu acesso.",
    )
    with st.container(border=True):
        if render_student_register_form("register_main", button_label="Solicitar acesso"):
            st.rerun()


def render_student_quiz_tab():
    playable = get_playable_active_materials()
    active_all = get_active_materials()
    selected_id = sync_playable_material(playable)
    material = get_material(selected_id) if selected_id else None
    registered = approved_students()

    if not registered:
        _render_registration_gate()
        return

    if st.session_state.quiz_active and not st.session_state.quiz_finished:
        _render_quiz_flow()
        return

    if st.session_state.quiz_finished:
        _render_quiz_results()
        return

    if not active_all:
        render_empty_state(
            icon="📭",
            title="Nenhum quiz disponível",
            message="O professor ainda não ativou nenhum quiz para a turma.",
            hint="Volte mais tarde ou peça ao professor para ativar um material.",
        )
        return

    if not playable:
        render_empty_state(
            icon="🛠️",
            title="Quizzes em preparação",
            message="Há materiais ativos, mas eles ainda não possuem perguntas cadastradas.",
            hint="Aguarde o professor finalizar o conteúdo.",
        )
        return

    col_cfg, col_main = st.columns([1, 2], gap="large")
    with col_cfg:
        with st.container(border=True):
            st.markdown('<div class="kahoot-config-title">Começar</div>', unsafe_allow_html=True)
            playable_by_id = {m["id"]: m for m in playable}
            st.selectbox(
                "Escolha o quiz",
                options=list(playable_by_id.keys()),
                format_func=lambda mid: playable_by_id[mid]["title"],
                key="selected_material_id",
                on_change=on_quiz_material_changed,
            )
            picked_id = st.session_state.selected_material_id
            mat = get_material(picked_id)
            if mat:
                st.caption(f"**{len(mat['questions'])}** perguntas neste quiz")

            names = sorted(s["name"] for s in registered)
            selected_name = _render_student_identity(names, "student_name_select")
            st.divider()

            can_play, attempt_msg, needs_confirm = (
                quiz_attempt_permission(selected_name, picked_id)
                if selected_name and mat
                else (True, "", False)
            )
            if attempt_msg:
                if not can_play:
                    st.warning(attempt_msg)
                elif needs_confirm:
                    st.warning(attempt_msg)
                else:
                    st.info(attempt_msg)

            confirm_ok = True
            if can_play and needs_confirm and selected_name:
                confirm_ok = st.checkbox(
                    "Sim, quero refazer mesmo assim.",
                    key=f"retry_confirm_{picked_id}",
                )

            if (
                st.button(
                    "🆕 Iniciar quiz",
                    use_container_width=True,
                    type="primary",
                    disabled=bool(selected_name) and (not can_play or not confirm_ok),
                )
                and selected_name
                and mat
                and can_play
                and confirm_ok
            ):
                load_student_material(picked_id)
                st.session_state.current_student_name = selected_name
                st.session_state.preferred_student_name = selected_name
                reset_quiz()
                st.rerun()
            elif not selected_name:
                st.caption("Selecione seu nome para habilitar o início.")

    with col_main:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Quizzes ativos", len(playable))
        with m2:
            q_count = len(material["questions"]) if material else 0
            st.metric("Perguntas", q_count)
        with m3:
            st.metric("Alunos", len(registered))

        if material:
            render_student_hero(
                material["title"],
                f"Responda {len(material['questions'])} perguntas de múltipla escolha "
                "e veja seu desempenho ao final.",
            )

        if len(playable) > 1:
            st.markdown("#### Outros quizzes disponíveis")
            for m in playable:
                selected = m["id"] == selected_id
                marker = "✓ " if selected else ""
                with st.container(border=True):
                    st.markdown(
                        f"**{marker}{m['title']}**  "
                        f'<span class="kahoot-quiz-pill">{len(m["questions"])} perguntas</span>',
                        unsafe_allow_html=True,
                    )
        else:
            st.caption("Configure o quiz à esquerda e clique em **Iniciar quiz** para começar.")

        st.divider()
        _render_my_quiz_history()


def get_playable_active_exams() -> list:
    return [e for e in get_active_exams() if e.get("questions")]


def render_student_exam_tab():
    playable_exams = get_playable_active_exams()
    registered = approved_students()

    if not registered:
        render_empty_state(
            icon="📝",
            title="Cadastro necessário",
            message="Cadastre-se na barra lateral e aguarde a aprovação do administrador.",
            hint="Depois de aprovado, as provas aparecerão aqui.",
        )
        return

    if st.session_state.exam_mode == "done" and st.session_state.exam_submission_result:
        _render_exam_results()
        return

    if st.session_state.exam_mode == "take":
        _render_exam_flow()
        return

    if not playable_exams:
        render_empty_state(
            icon="📋",
            title="Nenhuma prova disponível",
            message="O professor ainda não publicou provas ativas para a turma.",
            hint="Quando uma prova for ativada, ela aparecerá nesta seção.",
        )
        return

    col_cfg, col_main = st.columns([1, 2], gap="large")
    sync_playable_exam(playable_exams)
    exams_by_id = {e["id"]: e for e in playable_exams}
    picked_id = st.session_state.selected_exam_id
    exam = get_exam(picked_id)

    with col_cfg:
        with st.container(border=True):
            st.markdown('<div class="kahoot-config-title">Abrir prova</div>', unsafe_allow_html=True)
            st.selectbox(
                "Escolha a prova",
                options=list(exams_by_id.keys()),
                format_func=lambda eid: exams_by_id[eid]["title"],
                key="selected_exam_id",
            )
            if exam:
                summary = exam_summary(exam["questions"])
                st.caption(
                    f"**{summary['total']}** questões · "
                    f"{summary['choice']} múltipla escolha · {summary['justify']} justificativas"
                )

            names = sorted(s["name"] for s in registered)
            student_name = _render_student_identity(names, "exam_student_name")
            st.divider()
            if st.button("📋 Abrir prova", type="primary", use_container_width=True) and student_name:
                st.session_state.current_student_name = student_name
                st.session_state.preferred_student_name = student_name
                st.session_state.exam_mode = "take"
                st.rerun()
            elif not student_name:
                st.caption("Selecione seu nome para abrir a prova.")

    with col_main:
        if exam:
            summary = exam_summary(exam["questions"])
            render_student_hero(
                exam["title"],
                f"Prova com {summary['total']} questões. Responda com calma e envie ao final.",
            )
        st.metric("Provas ativas", len(playable_exams))

        st.divider()
        _render_my_exam_history()


def _render_quiz_flow():
    q_index = st.session_state.current_q_index
    total_q = len(st.session_state.questions)
    if q_index < total_q:
        q_data = st.session_state.questions[q_index]
        render_flow_header(
            label="Quiz em andamento",
            current=q_index + 1,
            total=total_q,
            student_name=st.session_state.current_student_name,
        )

        feedback = st.session_state.answer_feedback
        with st.container(border=True):
            st.markdown(
                f'<div class="kahoot-question-card"><h4>{q_data["question"]}</h4></div>',
                unsafe_allow_html=True,
            )
            if feedback is not None:
                if feedback["is_correct"]:
                    st.success("✅ Resposta correta!")
                else:
                    st.error(
                        f"❌ Resposta incorreta. A alternativa correta era **{feedback['correct']}**."
                    )
                label = "Ver resultado" if q_index + 1 >= total_q else "Próxima pergunta"
                if st.button(f"➡️ {label}", key="next_question", type="primary"):
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
                if st.button("✅ Responder", key="submit_answer", type="primary"):
                    is_correct = selected_letter == q_data["correct"]
                    st.session_state.student_answers.append(is_correct)
                    st.session_state.answer_feedback = {
                        "is_correct": is_correct,
                        "correct": q_data["correct"],
                    }
                    st.rerun()
    elif not st.session_state.get("quiz_finished"):
        finish_quiz()
        st.rerun()


def _render_quiz_results():
    total = len(st.session_state.questions)
    acertos = sum(st.session_state.student_answers)
    erros = total - acertos
    pct = (acertos / total * 100) if total > 0 else 0.0

    render_result_banner(
        f"Parabéns, {st.session_state.current_student_name}!",
        f"Você concluiu o quiz com {pct:.0f}% de acertos.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Acertos", acertos)
    with c2:
        st.metric("Erros", erros)
    with c3:
        st.metric("Pontuação", f"{acertos}/{total}", delta=f"{pct:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Desempenho visual")
        plot_student_result(st.session_state.student_answers, total)
    with col2:
        st.subheader("Resumo")
        st.write(f"✅ Você acertou **{acertos}** de **{total}** perguntas.")
        st.write(f"❌ Errou **{erros}** perguntas.")
        if pct >= 70:
            st.success("Ótimo resultado! Continue assim.")
        elif pct >= 40:
            st.info("Bom esforço — vale revisar o conteúdo e tentar de novo.")
        else:
            st.warning("Não desanime — refaça o quiz para fixar o conteúdo.")

    _render_results_download("dl_results_quiz_done")

    can_retry, retry_msg, needs_confirm = quiz_attempt_permission(
        st.session_state.current_student_name,
        st.session_state.current_material_id or "",
    )
    if can_retry and needs_confirm:
        st.info(retry_msg)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📝 Sim, refazer o quiz", type="primary", use_container_width=True):
                reset_quiz()
                st.rerun()
        with c2:
            if st.button("🏠 Não, manter meu resultado", type="secondary", use_container_width=True):
                st.session_state.quiz_finished = False
                st.session_state.quiz_active = False
                st.rerun()
    elif can_retry:
        if retry_msg:
            st.info(retry_msg)
        if st.button("📝 Fazer quiz novamente", type="primary"):
            st.session_state.quiz_finished = False
            st.session_state.quiz_active = False
            st.rerun()
    else:
        st.info(retry_msg)
        if st.button("🏠 Voltar ao início", type="secondary"):
            st.session_state.quiz_finished = False
            st.session_state.quiz_active = False
            st.rerun()


def _render_exam_flow():
    exam = get_exam(st.session_state.selected_exam_id)
    if not exam:
        st.session_state.exam_mode = "select"
        st.warning("Prova não encontrada ou foi removida.")
        return

    total_q = len(exam["questions"])
    render_flow_header(
        label=exam["title"],
        current=total_q,
        total=total_q,
        student_name=st.session_state.current_student_name,
    )
    st.caption("Responda todas as questões e envie ao final. O gabarito não é exibido.")

    with st.form("exam_submit_form"):
        answers_input = []
        for i, q in enumerate(exam["questions"]):
            q_view = question_for_student(q)
            tipo = "Múltipla escolha" if q_view["type"] == "choice" else "Justificativa"
            with st.container(border=True):
                st.markdown(
                    f'<div class="kahoot-exam-q"><strong>Questão {i + 1}</strong> · {tipo}</div>',
                    unsafe_allow_html=True,
                )
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
                        placeholder="Escreva sua justificativa aqui…",
                    )
                    answers_input.append(("justify", text))

        if st.form_submit_button("📤 Enviar prova", type="primary", use_container_width=True):
            graded = []
            for (kind, value), q_full in zip(answers_input, exam["questions"]):
                if kind == "choice":
                    graded.append(grade_choice_answer(value, q_full["correct"]))
                else:
                    graded.append(
                        grade_justify_answer(value, q_full.get("answer_key", ""))
                    )

            summary = summarize_answers(graded)
            user = st.session_state.get("current_user") or {}
            submission = {
                "id": str(uuid.uuid4()),
                "exam_id": exam["id"],
                "student_name": st.session_state.current_student_name,
                "student_email": (user.get("email") or "").strip().lower() or None,
                "answers": graded,
                "summary": summary,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
            add_exam_submission(submission)
            st.session_state.exam_submission_result = submission
            st.session_state.exam_mode = "done"
            st.rerun()

    if st.button("Cancelar prova", type="secondary"):
        st.session_state.exam_mode = "select"
        st.rerun()


def _render_exam_results():
    result = st.session_state.exam_submission_result
    summary = result.get("summary", summarize_answers(result["answers"]))
    counts = summary["counts"]

    render_result_banner(
        f"Prova enviada, {result['student_name']}!",
        f"Correção automática: {summary['total_points']:.1f} de {summary['max_points']:.0f} pontos "
        f"({summary['percent']:.0f}%).",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Pontuação", f"{summary['total_points']:.1f}/{summary['max_points']:.0f}")
    with c2:
        st.metric("A — Acertou", counts["A"])
    with c3:
        st.metric("PA — Parcial", counts["PA"])
    with c4:
        st.metric("NA — Não acertou", counts["NA"])

    st.subheader("Resultado por questão")
    for i, ans in enumerate(result["answers"]):
        clf = ans.get("classification", "NA")
        tipo = "Múltipla escolha" if ans.get("type") == "choice" else "Justificativa"
        with st.container(border=True):
            st.markdown(f"**Questão {i + 1}** · {tipo}")
            render_classification_badge(clf)

    exam_for_pdf = get_exam(result.get("exam_id"))
    if exam_for_pdf:
        st.download_button(
            "📥 Baixar minha prova em PDF",
            data=build_exam_pdf_bytes(exam_for_pdf, result, include_gabarito=False),
            file_name=export_filename(exam_for_pdf, result),
            mime="application/pdf",
            key="student_download_exam_pdf",
            use_container_width=True,
        )

    _render_results_download("dl_results_exam_done")

    if st.button("↩️ Voltar às provas", type="primary"):
        st.session_state.exam_mode = "select"
        st.session_state.exam_submission_result = None
        st.rerun()
