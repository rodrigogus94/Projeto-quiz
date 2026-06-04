import re

import matplotlib.pyplot as plt
import pandas as pd
import pdfplumber
import streamlit as st

import storage
from storage import (
    add_student,
    create_material,
    delete_material,
    delete_student,
    get_active_material,
    get_material,
    is_registered_student,
    leaderboard_for_material,
    list_materials,
    load_leaderboard,
    load_students,
    migrate_legacy_leaderboard,
    save_leaderboard,
    set_active_material,
    student_quiz_stats,
    update_material,
    update_professor_credentials,
    update_student,
    verify_professor,
)

PERGUNTA_HEADER = re.compile(r"Pergunta\s+(\d+):\s*", re.IGNORECASE)
ALT_START = re.compile(r"Alternativa\s+[A-D]\s*\(", re.IGNORECASE)
ALT_PATTERN = re.compile(
    r"Alternativa\s+([A-D])\s*\([^)]*\):\s*(.*?)(?=Alternativa\s+[A-D]|Pergunta\s+\d+:|$)",
    re.DOTALL | re.IGNORECASE,
)

EMPTY_QUESTION = {
    "question": "",
    "options": ["", "", "", ""],
    "correct": "A",
}


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


def parse_questions_from_text(full_text: str, warnings: list | None = None) -> list:
    def warn(msg: str):
        if warnings is not None:
            warnings.append(msg)

    matches = list(PERGUNTA_HEADER.finditer(full_text))
    questions = []

    for i, match in enumerate(matches):
        num = match.group(1)
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[match.start() : block_end]

        header_end = match.end() - match.start()
        first_alt = ALT_START.search(block, header_end)
        if first_alt:
            question_text = block[header_end : first_alt.start()]
        else:
            question_text = block[header_end:]
        question_text = re.sub(r"\s+", " ", question_text).strip()

        opts_in_block = ALT_PATTERN.findall(block)
        options = []
        correct_letter = None
        for letter, opt_text in opts_in_block[:4]:
            is_correct = "(CORRETA)" in opt_text
            opt_text = re.sub(r"\s*\(CORRETA\)", "", opt_text).strip()
            opt_text = re.sub(r"\s+", " ", opt_text)
            options.append(opt_text)
            if is_correct:
                correct_letter = letter

        if correct_letter and len(options) == 4 and question_text:
            questions.append(
                {"question": question_text, "options": options, "correct": correct_letter}
            )
        else:
            warn(
                f"Pergunta {num} ignorada: enunciado, alternativas ou resposta correta incompletos."
            )

    return questions


def parse_questions_from_pdf(pdf_file, show_warnings: bool = True) -> list:
    full_text = extract_text_from_pdf(pdf_file)
    warnings = []
    questions = parse_questions_from_text(full_text, warnings=warnings)
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
def init_session_state():
    migrate_legacy_leaderboard()
    defaults = {
        "role": None,
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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def sync_student_material():
    material = get_active_material()
    if material:
        st.session_state.questions = material["questions"]
        st.session_state.current_material_id = material["id"]
    else:
        st.session_state.questions = []
        st.session_state.current_material_id = None


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
# Login
# ---------------------------
def render_student_register_form(form_key: str, button_label: str = "Cadastrar-me") -> bool:
    """Formulário de auto-cadastro. Retorna True se cadastrou com sucesso."""
    with st.form(form_key):
        name = st.text_input("Nome completo", placeholder="Ex.: Maria Silva")
        identifier = st.text_input("Matrícula / ID (opcional)", placeholder="Ex.: 20240042")
        submitted = st.form_submit_button(button_label, use_container_width=True)
        if submitted:
            _, err = add_student(name, identifier)
            if err:
                st.error(err)
            else:
                st.session_state.preferred_student_name = " ".join(name.strip().split())
                st.success(f"Cadastro realizado! Bem-vindo(a), **{st.session_state.preferred_student_name}**.")
                return True
    return False


def render_login():
    st.title("🎮 Quiz Interativo")
    st.markdown("Escolha como deseja entrar na plataforma.")

    col_aluno, col_prof = st.columns(2)

    with col_aluno:
        st.subheader("👨‍🎓 Área do Aluno")
        tab_entrar, tab_cadastro = st.tabs(["Entrar", "Cadastrar-me"])

        with tab_entrar:
            st.markdown("Responda ao quiz ativo definido pelo professor.")
            if st.button("Entrar como aluno", type="primary", use_container_width=True):
                st.session_state.role = "student"
                sync_student_material()
                st.rerun()

        with tab_cadastro:
            st.markdown("Primeiro acesso? Crie seu cadastro para fazer o quiz.")
            if render_student_register_form("register_on_login"):
                st.session_state.role = "student"
                sync_student_material()
                st.rerun()

    with col_prof:
        st.subheader("👨‍🏫 Área do Professor")
        with st.form("professor_login"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar como professor", use_container_width=True)
            if submitted:
                if verify_professor(username, password):
                    st.session_state.role = "professor"
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")


def render_sidebar_logout():
    role_label = "Professor" if st.session_state.role == "professor" else "Aluno"
    st.sidebar.caption(f"Conectado como **{role_label}**")
    if st.sidebar.button("Sair", use_container_width=True):
        logout()


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
        c1, c2 = st.columns([2, 1])
        with c1:
            new_name = st.text_input("Nome completo", placeholder="Ex.: Maria Silva")
        with c2:
            new_id = st.text_input("Matrícula / ID (opcional)", placeholder="Ex.: 20240042")
        if st.form_submit_button("➕ Cadastrar aluno", type="primary"):
            _, err = add_student(new_name, new_id)
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
                "Matrícula": s.get("identifier") or "—",
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
            edit_id = st.text_input(
                "Matrícula / ID",
                value=s.get("identifier", ""),
                key=f"student_ident_{s['id']}",
            )
            ec1, ec2 = st.columns(2)
            with ec1:
                if st.button("💾 Salvar", key=f"save_student_{s['id']}"):
                    err = update_student(s["id"], edit_name, edit_id)
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


def render_professor_panel():
    st.title("👨‍🏫 Painel do Professor")
    render_sidebar_logout()

    tab_mat, tab_edit, tab_students, tab_results, tab_config = st.tabs(
        [
            "📚 Materiais",
            "✏️ Editar questões",
            "👥 Alunos cadastrados",
            "📊 Resultados",
            "🔐 Conta",
        ]
    )

    materials = list_materials()
    store = storage.load_materials_store()
    active_id = store.get("active_material_id")

    with tab_mat:
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
                is_active = m["id"] == active_id
                label = f"{'🟢 ' if is_active else ''}{m['title']} ({len(m['questions'])} perguntas)"
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    st.write(label)
                with c2:
                    if not is_active and st.button("Ativar", key=f"act_{m['id']}"):
                        set_active_material(m["id"])
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

    with tab_edit:
        if not materials:
            st.info("Crie um material na aba Materiais primeiro.")
        else:
            options = {m["title"]: m["id"] for m in materials}
            default_id = st.session_state.professor_edit_id or active_id
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
                if st.button("🟢 Definir como quiz ativo para alunos"):
                    set_active_material(material_id)
                    st.success("Quiz ativado para os alunos.")
                    st.rerun()

    with tab_students:
        render_students_tab()

    with tab_results:
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

    with tab_config:
        st.subheader("Alterar login do professor")
        cfg = storage.load_config()
        new_user = st.text_input("Novo usuário", value=cfg["professor_username"])
        new_pass = st.text_input("Nova senha", type="password")
        new_pass2 = st.text_input("Confirmar nova senha", type="password")
        if st.button("Salvar credenciais"):
            if not new_pass:
                st.error("Informe a nova senha.")
            elif new_pass != new_pass2:
                st.error("As senhas não coincidem.")
            elif len(new_pass) < 6:
                st.error("Use pelo menos 6 caracteres.")
            else:
                update_professor_credentials(new_user, new_pass)
                st.success("Credenciais atualizadas.")


# ---------------------------
# Aluno
# ---------------------------
def render_student_panel():
    sync_student_material()
    material = get_active_material()

    st.title("👨‍🎓 Área do Aluno")
    render_sidebar_logout()

    with st.sidebar:
        st.header("Quiz")
        registered = load_students()
        if material:
            st.write(f"**Atividade:** {material['title']}")
            st.write(f"**Perguntas:** {len(material['questions'])}")
            if registered:
                names = sorted(s["name"] for s in registered)
                preferred = st.session_state.preferred_student_name
                default_index = 0
                if preferred and preferred in names:
                    default_index = names.index(preferred) + 1
                selected_name = st.selectbox(
                    "Selecione seu nome",
                    options=[""] + names,
                    index=default_index,
                    format_func=lambda x: "— Escolha —" if x == "" else x,
                    key="student_name_select",
                )
                if (
                    st.button("🆕 Iniciar quiz", use_container_width=True)
                    and selected_name
                    and material["questions"]
                ):
                    if not is_registered_student(selected_name):
                        st.error("Nome não encontrado no cadastro.")
                    else:
                        mid = st.session_state.current_material_id
                        if name_exists_in_leaderboard(selected_name, mid):
                            st.warning(
                                "Você já tem um resultado neste quiz. "
                                "Um novo será adicionado ao refazer."
                            )
                        st.session_state.current_student_name = selected_name
                        st.session_state.preferred_student_name = selected_name
                        reset_quiz()
                        st.rerun()
            else:
                st.info("Cadastre-se abaixo para começar.")
        else:
            st.warning("Nenhum quiz ativo. Aguarde o professor publicar um material.")

        st.markdown("---")
        with st.expander("📝 Cadastrar-me", expanded=not registered):
            if render_student_register_form("register_in_sidebar"):
                st.rerun()

    if not material or not material["questions"]:
        st.info(
            "O professor ainda não definiu um quiz ativo com perguntas. "
            "Volte mais tarde ou peça para ativar um material."
        )
        return

    if not load_students():
        st.subheader("Cadastro de aluno")
        st.markdown(
            "Faça seu cadastro para participar do quiz. "
            "Use o formulário na barra lateral ou abaixo."
        )
        if render_student_register_form("register_main"):
            st.rerun()
        return

    if not st.session_state.quiz_active and not st.session_state.quiz_finished:
        st.markdown(f"### {material['title']}")
        st.markdown(
            "Selecione seu nome na barra lateral (ou cadastre-se em **Cadastrar-me**) "
            "e clique em **Iniciar quiz**."
        )
        return

    if st.session_state.quiz_active and not st.session_state.quiz_finished:
        _render_quiz_flow()
    elif st.session_state.quiz_finished:
        _render_quiz_results()


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
def main():
    st.set_page_config(page_title="Quiz Interativo", layout="wide", initial_sidebar_state="expanded")
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
