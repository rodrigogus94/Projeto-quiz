from __future__ import annotations

import pandas as pd
import streamlit as st

import auth_users
from auto_grade import CLASSIFICATIONS, LABELS, POINTS, summarize_answers
from pdf_export import build_exam_pdf_bytes, export_filename
from pdf_parser import exam_summary
from quiz_storage import (
    add_student,
    create_exam,
    create_material,
    delete_exam,
    delete_material,
    delete_student,
    get_active_exam_ids,
    get_active_material_ids,
    get_exam,
    get_material,
    is_material_active,
    leaderboard_for_material,
    list_exams,
    list_materials,
    load_students,
    save_leaderboard,
    student_quiz_stats,
    submissions_for_exam,
    toggle_exam_active,
    toggle_material_active,
    update_exam_submission,
    update_material,
    update_student,
)

from app.admin_views import render_admin_approvals_tab, render_auth_config_tab
from app.charts import (
    plot_attempts_comparison,
    plot_completion_donut,
    plot_leaderboard_comparison,
    plot_question_performance,
    plot_score_distribution,
)
from app.session import QUIZ_SECOND_CHANCE_MIN_SCORE
from app.components import render_classification_badge
from app.constants import EMPTY_QUESTION, EXAM_FORMAT_HELP
from app.pdf_helpers import (
    UPLOAD_FILE_TYPES,
    parse_exam_from_upload,
    parse_questions_from_upload,
    validate_questions,
)


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
                auth_users.ensure_name_student_user(new_name.strip(), auto_approve=True)
                st.success(f"Aluno **{new_name.strip()}** cadastrado e liberado.")
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
    st.subheader("Provas (PDF ou Markdown com gabarito)")
    st.caption("O gabarito fica só com o professor. Os alunos veem apenas as questões.")
    with st.expander("📋 Formato esperado do arquivo"):
        st.markdown(EXAM_FORMAT_HELP)

    exams = list_exams()
    active_ids = set(get_active_exam_ids())

    new_title = st.text_input("Título da prova", placeholder="Ex.: Prova 1 — Lógica", key="exam_title")
    uploaded = st.file_uploader(
        "Arquivo da prova (PDF ou Markdown, com gabarito)",
        type=UPLOAD_FILE_TYPES,
        key="exam_pdf",
    )

    if st.button("📄 Importar prova", type="primary") and uploaded and new_title.strip():
        questions = parse_exam_from_upload(uploaded)
        if questions:
            create_exam(new_title.strip(), questions)
            summary = exam_summary(questions)
            st.success(
                f"Prova criada: {summary['total']} questões "
                f"({summary['choice']} múltipla escolha, {summary['justify']} justificativas)."
            )
            st.rerun()
        else:
            st.error("Nenhuma questão identificada. Verifique o formato do arquivo.")

    if not exams:
        st.info("Nenhuma prova cadastrada. Importe um PDF ou Markdown acima.")
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


def render_results_tab(materials: list):
    st.subheader("Resultados dos quizzes")
    if not materials:
        st.info("Sem materiais para analisar.")
        return

    mat_options = {m["title"]: m["id"] for m in materials}
    res_title = st.selectbox("Material", list(mat_options.keys()), key="res_mat")
    res_id = mat_options[res_title]
    material = get_material(res_id)
    entries = leaderboard_for_material(res_id)
    total_q = len(material["questions"]) if material else 0

    if not entries:
        st.info("Nenhum aluno finalizou este quiz ainda.")
        return

    df = pd.DataFrame(entries)
    df["pct"] = df.apply(
        lambda r: (r["score"] / r["total"] * 100) if r["total"] else 0.0, axis=1
    )
    df["Tentativa"] = df.groupby("name").cumcount() + 1

    # Melhor tentativa de cada aluno
    best = df.loc[df.groupby("name")["score"].idxmax()].copy()
    attempts_by_name = df.groupby("name").size()
    target = min(QUIZ_SECOND_CHANCE_MIN_SCORE, total_q) if total_q else QUIZ_SECOND_CHANCE_MIN_SCORE

    responders = len(best)
    completed = int((best["score"] >= target).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Alunos que responderam", responders)
    m2.metric("Tentativas registradas", len(df))
    m3.metric("Média de acertos", f"{df['pct'].mean():.0f}%")
    m4.metric(f"Concluíram ({target}+ acertos)", f"{completed}/{responders}")

    tab_rank, tab_q, tab_dist, tab_aprov, tab_tent = st.tabs(
        [
            "🏆 Ranking",
            "🎯 Por pergunta",
            "📊 Distribuição",
            "✅ Aproveitamento",
            "🔁 1ª vs 2ª tentativa",
        ]
    )
    with tab_rank:
        st.caption("Melhor resultado de cada aluno.")
        plot_leaderboard_comparison(best.to_dict("records"))
    with tab_q:
        st.caption("Percentual de tentativas que acertaram cada pergunta.")
        if total_q:
            plot_question_performance(entries, total_q)
        else:
            st.info("Material sem perguntas cadastradas.")
    with tab_dist:
        st.caption("Quantos alunos ficaram em cada nota (melhor tentativa).")
        plot_score_distribution(
            [int(s) for s in best["score"]],
            total_q or int(df["total"].max()),
        )
    with tab_aprov:
        st.caption(f"Alunos que atingiram {target}+ acertos vs abaixo da meta.")
        plot_completion_donut(completed, responders - completed, target)
    with tab_tent:
        st.caption("Alunos que usaram a segunda oportunidade.")
        plot_attempts_comparison(entries)

    st.markdown("#### 👥 Todos os alunos que responderam")

    def _status(row) -> str:
        if row["score"] >= target:
            return "✅ Concluído"
        if attempts_by_name.get(row["name"], 0) >= 2:
            return "⛔ Tentativas esgotadas"
        return "🔁 Pode refazer"

    summary = pd.DataFrame(
        {
            "Aluno": best["name"],
            "Tentativas": best["name"].map(attempts_by_name).astype(int),
            "Melhor nota": best.apply(
                lambda r: f"{int(r['score'])}/{int(r['total'])}", axis=1
            ),
            "% Acertos": best["pct"].round(1),
            "Situação": best.apply(_status, axis=1),
        }
    ).sort_values("% Acertos", ascending=False)
    st.dataframe(summary, use_container_width=True, hide_index=True)

    with st.expander(f"📄 Todas as tentativas ({len(df)})"):
        detail = df[["name", "Tentativa", "score", "total", "pct"]].rename(
            columns={
                "name": "Aluno",
                "score": "Acertos",
                "total": "Total",
                "pct": "% Acertos",
            }
        )
        detail["% Acertos"] = detail["% Acertos"].round(1)
        st.dataframe(
            detail.sort_values(["Aluno", "Tentativa"]),
            use_container_width=True,
            hide_index=True,
        )

    responder_keys = {n.strip().lower() for n in best["name"]}
    pending_names = [
        s["name"]
        for s in load_students()
        if s["name"].strip().lower() not in responder_keys
    ]
    with st.expander(f"💤 Ainda não responderam ({len(pending_names)})"):
        if pending_names:
            st.write(", ".join(sorted(pending_names)))
        else:
            st.write("Todos os alunos cadastrados já responderam este quiz. 🎉")

    st.divider()
    if st.button("🗑️ Limpar resultados deste material"):
        st.session_state.leaderboard = [
            e
            for e in st.session_state.leaderboard
            if e.get("material_id") != res_id
        ]
        save_leaderboard(st.session_state.leaderboard)
        st.success("Resultados removidos.")
        st.rerun()


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
        uploaded = st.file_uploader(
            "Importar perguntas (PDF, .md ou .markdown)",
            type=UPLOAD_FILE_TYPES,
            key="prof_pdf",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("➕ Criar material vazio") and new_title.strip():
                create_material(new_title.strip(), [])
                st.success("Material criado.")
                st.rerun()
        with col_b:
            if st.button("📄 Criar a partir do arquivo") and uploaded and new_title.strip():
                questions = parse_questions_from_upload(uploaded)
                if questions:
                    create_material(new_title.strip(), questions)
                    st.success(f"Material criado com {len(questions)} perguntas.")
                    st.rerun()
                else:
                    st.error("Não foi possível extrair perguntas do arquivo.")

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
                "Substituir todas as perguntas via PDF ou Markdown",
                type=UPLOAD_FILE_TYPES,
                key="prof_pdf_replace",
            )
            if pdf_update and st.button("Importar arquivo neste material"):
                parsed = parse_questions_from_upload(pdf_update)
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
        render_results_tab(materials)

    elif section == "config":
        render_auth_config_tab()

    elif section == "admin" and show_admin_tab:
        render_admin_approvals_tab()
