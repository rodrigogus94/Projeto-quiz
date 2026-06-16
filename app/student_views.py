from __future__ import annotations

import uuid
from datetime import datetime, timezone

import streamlit as st

import auth_users
from auto_grade import (
    grade_choice_answer,
    grade_choice_with_justify,
    grade_justify_answer,
    summarize_answers,
)
from pdf_export import build_exam_pdf_bytes, export_filename
from pdf_parser import (
    exam_question_needs_justify,
    exam_requires_justify,
    exam_summary,
    question_for_student,
)
from quiz_storage import (
    add_exam_submission,
    exam_deadline_label,
    exam_is_past_deadline,
    exam_submissions_for_student,
    get_active_exams,
    get_active_materials,
    get_exam,
    get_material,
    exam_correction_released,
    load_exam_submissions,
    load_leaderboard,
    student_submission_for_exam,
)

from app.email_sender import (
    mailto_link,
    professor_email,
    send_results_email,
    smtp_configured,
)
from app.result_transfer import (
    build_student_export,
    export_bytes as results_export_bytes,
    export_filename as results_export_filename,
    export_markdown_bytes as results_export_markdown_bytes,
)

from app.auth_ui import render_student_register_form
from app.navigation import get_student_section
from app.charts import plot_student_result
from app.components import (
    inject_student_area_css,
    render_classification_badge,
    render_exam_mc_option,
    render_empty_state,
    render_flow_header,
    render_history_empty,
    render_history_item,
    render_result_banner,
    render_student_hero,
)
from app.session import (
    bound_student_name,
    exam_attempt_permission,
    filter_exams_for_student,
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
    return auth_users.list_approved_students()


def _active_exam_id() -> str | None:
    """ID da prova em andamento — não depende do selectbox (que some no modo take)."""
    return st.session_state.get("current_exam_id") or st.session_state.get("selected_exam_id")


def _start_exam_session(exam_id: str, *, mode: str, submission: dict | None = None):
    # Não alterar selected_exam_id aqui: é chave do selectbox e o Streamlit
    # proíbe modificar após o widget já ter sido renderizado na mesma execução.
    st.session_state.current_exam_id = exam_id
    st.session_state.exam_submission_result = submission
    st.session_state.exam_mode = mode


def _clear_exam_session():
    st.session_state.exam_mode = "select"
    st.session_state.current_exam_id = None
    st.session_state.exam_submission_result = None


def _render_results_download(widget_key: str):
    """Baixar (JSON + Markdown) e/ou enviar por e-mail os resultados do aluno."""
    name = bound_student_name() or st.session_state.get("current_student_name") or ""
    if not name.strip():
        return
    user = st.session_state.get("current_user") or {}
    payload = build_student_export(name, user.get("email"))
    if not payload["quiz_results"] and not payload["exam_submissions"]:
        return
    json_bytes = results_export_bytes(payload)
    json_name = results_export_filename(name, ext="json")
    md_bytes = results_export_markdown_bytes(payload)
    md_name = results_export_filename(name, ext="md")

    st.caption("Baixe os dois formatos e envie ao professor (JSON para importação automática).")
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "📥 Baixar JSON",
            data=json_bytes,
            file_name=json_name,
            mime="application/json",
            key=f"{widget_key}_json",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            "📥 Baixar Markdown",
            data=md_bytes,
            file_name=md_name,
            mime="text/markdown",
            key=f"{widget_key}_md",
            use_container_width=True,
        )
    _render_email_to_professor(
        widget_key=f"{widget_key}_email",
        student_name=name,
        student_email=user.get("email"),
        json_bytes=json_bytes,
        json_filename=json_name,
        markdown_bytes=md_bytes,
        markdown_filename=md_name,
    )


def _render_email_to_professor(
    *,
    widget_key: str,
    student_name: str,
    student_email: str | None,
    json_bytes: bytes,
    json_filename: str,
    markdown_bytes: bytes,
    markdown_filename: str,
):
    """E-mail pré-pronto ao professor com anexos fixos gerados pelo app."""
    dest = professor_email()
    if not dest:
        return

    with st.expander("✉️ Enviar por e-mail ao professor"):
        if smtp_configured():
            st.markdown(f"**Para:** `{dest}`")
            st.markdown(f"**Assunto:** [Projeto Quiz] Resultados de {student_name}")
            st.markdown(f"**📎 Anexos:** `{json_filename}` e `{markdown_filename}`")
            st.caption(
                "🔒 Os anexos são gerados automaticamente pelo app. "
                "Não é possível adicionar outros arquivos."
            )
            note = st.text_area(
                "Mensagem adicional (opcional)",
                key=f"{widget_key}_note",
                placeholder="Ex.: Professor, segue meu resultado da semana.",
                max_chars=500,
            )
            if st.button(
                "✉️ Enviar e-mail",
                type="primary",
                key=f"{widget_key}_btn",
                use_container_width=True,
            ):
                with st.spinner("Enviando e-mail..."):
                    err = send_results_email(
                        student_name=student_name,
                        student_email=student_email,
                        json_bytes=json_bytes,
                        json_filename=json_filename,
                        markdown_bytes=markdown_bytes,
                        markdown_filename=markdown_filename,
                        extra_note=note or "",
                    )
                if err:
                    st.error(err)
                else:
                    st.success(f"✅ E-mail enviado para {dest}!")
                    st.toast("✉️ Resultados enviados ao professor!")
        else:
            st.caption(
                "O envio automático não está ativo. Use o link abaixo para abrir "
                "seu aplicativo de e-mail já preenchido e **anexe os arquivos JSON e Markdown** "
                "baixados acima."
            )
            st.markdown(
                f"[✉️ Abrir e-mail pré-pronto para o professor]({mailto_link(student_name, student_email)})"
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
        render_history_empty(
            "🎯 Você ainda não concluiu nenhum quiz.<br>"
            "Seu histórico aparecerá aqui assim que você terminar o primeiro."
        )
        return

    pcts = [
        (e["score"] / e["total"] * 100) for e in mine if e.get("total")
    ]
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Quizzes concluídos", len(mine))
    with m2:
        st.metric("Melhor resultado", f"{max(pcts):.0f}%" if pcts else "—")
    with m3:
        st.metric("Média geral", f"{sum(pcts) / len(pcts):.0f}%" if pcts else "—")

    for e in reversed(mine):
        mat = get_material(e.get("material_id") or "")
        total = e.get("total") or 0
        pct = (e["score"] / total * 100) if total else 0.0
        tone = "good" if pct >= 70 else ("mid" if pct >= 40 else "bad")
        render_history_item(
            title=mat["title"] if mat else "(material removido)",
            meta=f"🕑 {_format_when(e.get('submitted_at'))} (UTC)",
            badge_text=f"{e['score']}/{total} · {pct:.0f}%",
            badge_tone=tone,
        )
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
        render_history_empty(
            "📄 Você ainda não enviou nenhuma prova.<br>"
            "Assim que enviar, o histórico aparecerá aqui."
        )
        return
    for s in reversed(mine):
        exam = get_exam(s.get("exam_id") or "")
        attempt = s.get("attempt") or 1
        title = exam["title"] if exam else "(prova removida)"
        if attempt > 1:
            title = f"{title} · tentativa {attempt}"
        render_history_item(
            title=title,
            meta=f"🕑 {_format_when(s.get('submitted_at'))} (UTC)",
            badge_text="Enviada",
            badge_tone="neutral",
        )


def render_student_panel():
    inject_student_area_css()
    section = get_student_section()
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
    all_playable_exams = get_playable_active_exams()
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

    if st.session_state.exam_mode == "review":
        _render_exam_review()
        return

    if st.session_state.exam_mode == "take":
        _render_exam_flow()
        return

    if not all_playable_exams:
        render_empty_state(
            icon="📋",
            title="Nenhuma prova disponível",
            message="O professor ainda não publicou provas ativas para a turma.",
            hint="Quando uma prova for ativada, ela aparecerá nesta seção.",
        )
        return

    col_cfg, col_main = st.columns([1, 2], gap="large")
    user = st.session_state.get("current_user") or {}
    names = sorted(s["name"] for s in registered)

    with col_cfg:
        with st.container(border=True):
            st.markdown('<div class="kahoot-config-title">Abrir prova</div>', unsafe_allow_html=True)

            student_name = _render_student_identity(names, "exam_student_name")

            visible_exams = (
                filter_exams_for_student(
                    all_playable_exams, student_name, user.get("email")
                )
                if student_name
                else []
            )

            if not student_name:
                st.caption("Selecione seu nome para ver as provas disponíveis.")
            elif not visible_exams:
                st.info(
                    "Você não tem provas pendentes no momento. "
                    "Provas já enviadas (e concluídas) ficam em **Minhas provas enviadas** abaixo."
                )
            else:
                sync_playable_exam(visible_exams)
                exams_by_id = {e["id"]: e for e in visible_exams}
                picked_id = st.session_state.selected_exam_id
                exam = get_exam(picked_id)

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
                    dl = exam_deadline_label(exam)
                    if dl:
                        if exam_is_past_deadline(exam):
                            st.warning(f"⏰ Prazo encerrado em **{dl}** — somente revisão.")
                        else:
                            st.info(f"⏰ Prazo para envio: **{dl}**")

                st.divider()

                existing = (
                    student_submission_for_exam(student_name, picked_id, user.get("email"))
                    if exam
                    else None
                )
                past = exam_is_past_deadline(exam) if exam else False
                can_recover = False
                recover_msg = ""
                if existing and exam and not past:
                    if exam_correction_released(existing):
                        can_recover, recover_msg, _ = exam_attempt_permission(
                            student_name, picked_id, user.get("email"), exam
                        )
                    else:
                        recover_msg = (
                            "Após o professor **devolver a prova corrigida**, você verá aqui "
                            "se tem direito à recuperação."
                        )
                if existing and can_recover:
                    btn_label = "🔄 Fazer recuperação"
                elif existing:
                    btn_label = "👁️ Ver prova enviada"
                elif past:
                    btn_label = "👁️ Revisar prova (somente leitura)"
                else:
                    btn_label = "📋 Responder prova"

                if can_recover and recover_msg:
                    st.info(recover_msg)
                elif existing and recover_msg and not past and not exam_correction_released(existing):
                    st.caption(recover_msg)

                if st.button(btn_label, type="primary", use_container_width=True) and exam:
                    st.session_state.current_student_name = student_name
                    st.session_state.preferred_student_name = student_name
                    if past or (existing and not can_recover):
                        _start_exam_session(picked_id, mode="review", submission=existing)
                    else:
                        _start_exam_session(picked_id, mode="take")
                    st.rerun()

    picker_name = st.session_state.get("exam_student_name") or bound_student_name() or ""
    visible_for_student = (
        filter_exams_for_student(all_playable_exams, picker_name, user.get("email"))
        if picker_name
        else []
    )

    with col_main:
        if visible_for_student:
            exam = get_exam(st.session_state.selected_exam_id)
            if exam and exam["id"] in {e["id"] for e in visible_for_student}:
                summary = exam_summary(exam["questions"])
                render_student_hero(
                    exam["title"],
                    f"Prova com {summary['total']} questões. Responda com calma e envie ao final.",
                )
        elif picker_name:
            render_empty_state(
                icon="✅",
                title="Nenhuma prova pendente",
                message=(
                    "Você já concluiu as provas disponíveis ou está aguardando a devolução "
                    "do professor para saber se tem recuperação."
                ),
                hint="Consulte **Minhas provas enviadas** abaixo para revisar o que já enviou.",
            )

        st.metric(
            "Provas pendentes" if picker_name else "Provas ativas",
            len(visible_for_student) if picker_name else len(all_playable_exams),
        )

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


def _render_exam_questions_readonly(
    exam: dict,
    submission: dict | None = None,
    *,
    show_correction: bool = False,
):
    """Exibe questões sem permitir edição (revisão após o prazo ou prova enviada)."""
    answers = (submission or {}).get("answers") or []
    for i, q in enumerate(exam["questions"]):
        q_view = question_for_student(q)
        if q_view["type"] == "choice_with_justify":
            tipo = "Múltipla escolha + justificativa"
        elif q_view["type"] == "choice":
            tipo = "Múltipla escolha"
        else:
            tipo = "Justificativa"
        ans = answers[i] if i < len(answers) else None
        with st.container(border=True):
            st.markdown(f"**Questão {i + 1}** · {tipo}")
            st.write(q_view["question"])
            if q_view["type"] in ("choice", "choice_with_justify"):
                correct_letter = q.get("correct") if show_correction else None
                selected = (ans or {}).get("selected")
                for j, letter in enumerate("ABCD"):
                    opt = q_view["options"][j]
                    render_exam_mc_option(
                        letter,
                        opt,
                        show_correction=show_correction,
                        is_selected=selected == letter,
                        is_correct=show_correction and letter == correct_letter,
                    )
            if q_view["type"] == "choice_with_justify" and ans and ans.get("justify_text"):
                st.markdown("**Sua justificativa:**")
                st.write(ans["justify_text"])
            elif q_view["type"] == "justify" and ans and ans.get("text"):
                st.markdown("**Sua resposta:**")
                st.write(ans["text"])
            if show_correction and ans:
                if ans.get("type") == "choice_with_justify":
                    if ans.get("mc_correct"):
                        st.success("✅ Múltipla escolha correta")
                    else:
                        st.error("❌ Múltipla escolha incorreta")
                        st.caption("A alternativa correta está destacada em verde acima.")
                        render_classification_badge(ans.get("justify_classification", "NA"))
                elif ans.get("type") == "choice":
                    render_classification_badge(ans.get("classification", "NA"))
                else:
                    render_classification_badge(ans.get("classification", "NA"))


def _render_exam_review():
    exam = get_exam(_active_exam_id())
    if not exam:
        _clear_exam_session()
        st.warning("Prova não encontrada ou foi removida.")
        return

    submission = st.session_state.exam_submission_result
    if not submission:
        submission = student_submission_for_exam(
            st.session_state.current_student_name,
            exam["id"],
            (st.session_state.get("current_user") or {}).get("email"),
        )
        st.session_state.exam_submission_result = submission

    past = exam_is_past_deadline(exam)
    dl = exam_deadline_label(exam)

    if submission:
        _render_exam_results(read_only=True)
        return

    render_student_hero(
        exam["title"],
        "Modo revisão — as respostas não podem ser alteradas.",
    )
    if past and dl:
        st.warning(f"⏰ O prazo de envio encerrou em **{dl}**. Você não enviou esta prova.")
    else:
        st.info("Você ainda não enviou esta prova. As questões abaixo são apenas para consulta.")

    _render_exam_questions_readonly(exam)
    _render_results_download("dl_results_exam_review")

    if st.button("↩️ Voltar às provas", type="primary"):
        _clear_exam_session()
        st.rerun()


def _render_exam_flow():
    exam = get_exam(_active_exam_id())
    if not exam:
        _clear_exam_session()
        st.warning("Prova não encontrada ou foi removida.")
        return

    if exam_is_past_deadline(exam):
        st.session_state.exam_mode = "review"
        st.rerun()

    user = st.session_state.get("current_user") or {}
    prior = student_submission_for_exam(
        st.session_state.current_student_name,
        exam["id"],
        user.get("email"),
    )
    if prior:
        can_recover, _, _ = exam_attempt_permission(
            st.session_state.current_student_name,
            exam["id"],
            user.get("email"),
            exam,
        )
        if not can_recover:
            st.session_state.exam_submission_result = prior
            st.session_state.exam_mode = "review"
            st.rerun()

    total_q = len(exam["questions"])
    render_flow_header(
        label=exam["title"],
        current=total_q,
        total=total_q,
        student_name=st.session_state.current_student_name,
    )
    questions = exam["questions"]
    needs_justify_exam = exam_requires_justify(questions)
    if needs_justify_exam:
        st.caption(
            "Marque a alternativa e **justifique** cada resposta. A nota principal vem da "
            "múltipla escolha; se errar, uma boa justificativa pode recuperar até metade do ponto."
        )
    else:
        st.caption("Responda todas as questões e envie ao final. O gabarito não é exibido.")

    with st.form("exam_submit_form"):
        answers_input = []
        for i, q in enumerate(questions):
            q_view = question_for_student(q)
            show_justify = (
                q_view["type"] == "choice_with_justify"
                or (needs_justify_exam and q_view["type"] == "choice")
            )
            if show_justify or q_view["type"] == "choice_with_justify":
                tipo = "Múltipla escolha + justificativa"
            elif q_view["type"] == "choice":
                tipo = "Múltipla escolha"
            else:
                tipo = "Justificativa"
            with st.container(border=True):
                st.markdown(
                    f'<div class="kahoot-exam-q"><strong>Questão {i + 1}</strong> · {tipo}</div>',
                    unsafe_allow_html=True,
                )
                st.write(q_view["question"])
                if q_view["type"] in ("choice", "choice_with_justify"):
                    opts = {letter: q_view["options"][j] for j, letter in enumerate("ABCD")}
                    picked = st.radio(
                        "Alternativa",
                        options=list(opts.keys()),
                        format_func=lambda x: f"{x}) {opts[x]}",
                        key=f"exam_q_{i}_mc",
                        label_visibility="visible",
                    )
                    if show_justify:
                        justify = st.text_area(
                            "Justifique sua resposta",
                            key=f"exam_q_{i}_justify",
                            height=100,
                            placeholder="Explique o conceito por trás da alternativa escolhida…",
                        )
                        answers_input.append(("choice_with_justify", picked, justify))
                    else:
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
            for item, q_full in zip(answers_input, questions):
                kind = item[0]
                if kind == "choice":
                    graded.append(grade_choice_answer(item[1], q_full["correct"]))
                elif kind == "choice_with_justify":
                    graded.append(
                        grade_choice_with_justify(
                            item[1],
                            q_full["correct"],
                            item[2],
                            q_full.get("answer_key", ""),
                        )
                    )
                else:
                    graded.append(
                        grade_justify_answer(item[1], q_full.get("answer_key", ""))
                    )

            summary = summarize_answers(graded)
            user = st.session_state.get("current_user") or {}
            prior_count = len(
                exam_submissions_for_student(
                    st.session_state.current_student_name,
                    exam["id"],
                    user.get("email"),
                )
            )
            submission = {
                "id": str(uuid.uuid4()),
                "exam_id": exam["id"],
                "student_name": st.session_state.current_student_name,
                "student_email": (user.get("email") or "").strip().lower() or None,
                "answers": graded,
                "summary": summary,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "correction_released": False,
                "attempt": prior_count + 1,
                "is_recovery": prior_count >= 1,
            }
            add_exam_submission(submission)
            st.session_state.exam_submission_result = submission
            st.session_state.current_exam_id = exam["id"]
            st.session_state.exam_mode = "done"
            st.rerun()

def _reload_exam_submission(result: dict | None) -> dict | None:
    """Atualiza envio da sessão com dados persistidos (ex.: correção liberada)."""
    if not result:
        return None
    exam_id = result.get("exam_id")
    if not exam_id:
        return result
    fresh = student_submission_for_exam(
        result.get("student_name", ""),
        exam_id,
        result.get("student_email"),
    )
    if fresh:
        st.session_state.exam_submission_result = fresh
        return fresh
    return result


def _render_exam_results(*, read_only: bool = False):
    result = _reload_exam_submission(st.session_state.exam_submission_result)
    if not result:
        st.warning("Nenhum envio encontrado para esta prova.")
        return

    released = exam_correction_released(result)
    title = (
        f"Prova enviada, {result['student_name']}!"
        if not read_only
        else f"Prova enviada — {result['student_name']}"
    )
    if released:
        summary = result.get("summary") or summarize_answers(result.get("answers") or [])
        msg = (
            f"Correção liberada pelo professor — "
            f"nota: {summary['total_points']:.1f}/{summary['max_points']:.0f} "
            f"({summary['percent']:.0f}%)"
        )
    elif not read_only:
        msg = (
            "Suas respostas foram registradas. A correção ficará disponível "
            "quando o professor devolver a prova."
        )
    else:
        msg = (
            "Modo somente leitura — você pode consultar o que enviou. "
            "A correção ainda não foi liberada pelo professor."
        )
    render_result_banner(title, msg)
    if not released:
        st.info("⏳ Aguardando correção do professor. Você verá acertos e notas após a devolução.")

    exam_for_view = get_exam(result.get("exam_id"))
    if exam_for_view:
        st.subheader("Suas respostas" if not released else "Prova corrigida")
        _render_exam_questions_readonly(exam_for_view, result, show_correction=released)

    exam_for_pdf = get_exam(result.get("exam_id"))
    if exam_for_pdf:
        st.download_button(
            "📥 Baixar minha prova em PDF",
            data=build_exam_pdf_bytes(
                exam_for_pdf,
                result,
                include_gabarito=False,
                include_correction=released,
            ),
            file_name=export_filename(exam_for_pdf, result),
            mime="application/pdf",
            key="student_download_exam_pdf",
            use_container_width=True,
        )

    st.divider()
    st.markdown("#### 📤 Enviar resultados ao professor")
    st.caption(
        "Baixe os arquivos JSON e Markdown ou envie por e-mail com os resultados "
        "desta prova e dos quizzes concluídos."
    )
    _render_results_download("dl_results_exam_done")

    exam_obj = get_exam(result.get("exam_id"))
    can_recover, recover_msg, _ = exam_attempt_permission(
        result.get("student_name", ""),
        result.get("exam_id", ""),
        result.get("student_email"),
        exam_obj,
    )
    if released:
        if can_recover:
            st.warning(recover_msg)
            if st.button(
                "🔄 Fazer recuperação da prova",
                type="primary",
                key="exam_recovery_retry",
                use_container_width=True,
            ):
                _start_exam_session(result["exam_id"], mode="take")
                st.rerun()
        elif recover_msg:
            st.info(recover_msg)
    elif not read_only:
        st.caption(
            "Após o professor **devolver a prova corrigida**, você verá aqui "
            "se tem direito à recuperação (meta: 17+ acertos na MC e nota A)."
        )

    if read_only:
        if st.button("↩️ Voltar às provas", type="primary", key="exam_results_back"):
            _clear_exam_session()
            st.rerun()
