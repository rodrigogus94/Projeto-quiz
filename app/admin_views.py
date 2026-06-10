from __future__ import annotations

import streamlit as st

import auth_users
import quiz_storage
from google_auth import google_oauth_configured, legacy_password_enabled
from quiz_storage import update_professor_credentials


def _render_backup_tools():
    st.markdown("---")
    st.subheader("Backup de contas")
    st.caption(
        "O arquivo `backup_aprovados.csv` guarda nome, e-mail e categoria dos usuários "
        "aprovados. Baixe para salvar uma cópia ou envie um backup salvo para restaurar "
        "contas (útil após redeploy no Streamlit Cloud)."
    )

    backup_bytes = auth_users.read_backup_csv_bytes()
    dl_col, up_col = st.columns(2, gap="large")

    with dl_col:
        if backup_bytes:
            st.download_button(
                "📥 Baixar backup",
                data=backup_bytes,
                file_name="backup_aprovados.csv",
                mime="text/csv",
                key="download_backup_csv",
                use_container_width=True,
            )
        else:
            st.info("Ainda não há usuários aprovados para gerar o backup.")

    with up_col:
        uploaded = st.file_uploader(
            "Selecione o CSV de backup",
            type=["csv"],
            key="upload_backup_csv",
            label_visibility="collapsed",
        )
        replace_existing = st.checkbox(
            "Substituir todas as contas (cuidado)",
            key="backup_replace_all",
            help="Desmarcado: só adiciona contas que ainda não existem. "
            "Marcado: apaga users.json e usa somente o arquivo enviado.",
        )
        if st.button(
            "📤 Enviar backup",
            type="primary",
            key="import_backup_csv",
            use_container_width=True,
            disabled=uploaded is None,
        ):
            count, err = auth_users.import_users_from_backup(
                uploaded.getvalue(),
                merge=not replace_existing,
            )
            if err:
                st.error(err)
            else:
                st.success(f"Backup importado: **{count}** conta(s) restaurada(s).")
                st.rerun()


def render_admin_approvals_tab():
    st.subheader("Aprovação de contas")
    st.caption(
        f"Administrador do sistema: **{auth_users.get_system_admin_email()}**. "
        "Novas contas (Google ou por nome) só acessam o sistema após aprovação."
    )

    pending = auth_users.get_pending_users()
    if not pending:
        st.success("Nenhuma solicitação pendente no momento.")
        return

    st.warning(f"{len(pending)} solicitação(ões) aguardando sua aprovação.")
    role_labels = {"professor": "Professor", "student": "Aluno"}
    for u in pending:
        with st.container(border=True):
            role_label = role_labels.get(u.get("role"), u.get("role", "—"))
            st.write(f"**{u.get('name', '—')}** — {role_label}")
            st.write(f"E-mail: {u.get('email') or '— (cadastro por nome)'}")
            st.caption(f"Via: {u.get('auth_provider', '—')}")
            if u.get("created_at"):
                st.caption(f"Solicitado em: {u['created_at']}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Aprovar", key=f"approve_{u['id']}", use_container_width=True):
                    err = auth_users.approve_user(u["id"])
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Conta de **{u.get('name')}** aprovada.")
                        st.rerun()
            with c2:
                if st.button("❌ Negar", key=f"reject_{u['id']}", use_container_width=True):
                    err = auth_users.reject_user(u["id"])
                    if err:
                        st.error(err)
                    else:
                        st.info(f"Solicitação de **{u.get('name')}** negada.")
                        st.rerun()


_ACCOUNT_STATUS_LABELS = {
    "pending": "Pendente",
    "approved": "Aprovado",
    "rejected": "Negado",
}


def _current_user_is_admin() -> bool:
    user = st.session_state.get("current_user") or {}
    return bool(
        user.get("is_admin") or auth_users.is_system_admin(user.get("email"))
    )


def _account_user_summary(u: dict) -> str:
    status = _ACCOUNT_STATUS_LABELS.get(
        auth_users.user_account_status(u),
        auth_users.user_account_status(u),
    )
    email = u.get("email") or "sem e-mail"
    admin_mark = " · admin" if u.get("is_admin") or auth_users.is_system_admin(u.get("email")) else ""
    return f"{u.get('name', '—')} ({email}) — {status}{admin_mark}"


def render_account_role_manager(role: str):
    role_label = "professor" if role == "professor" else "aluno"
    role_plural = "professores" if role == "professor" else "alunos"
    users = sorted(
        auth_users.list_users_by_role(role),
        key=lambda u: (u.get("name") or "").lower(),
    )

    if not users:
        st.info(f"Nenhum {role_label} cadastrado no momento.")
        return

    st.caption(f"**{len(users)}** {role_plural} · edite os dados ou remova contas abaixo.")

    current_user_id = (st.session_state.get("current_user") or {}).get("id")

    for u in users:
        is_admin_account = bool(
            u.get("is_admin") or auth_users.is_system_admin(u.get("email"))
        )
        with st.expander(_account_user_summary(u), expanded=False):
            st.caption(
                f"Login: {u.get('auth_provider', '—')}"
                + (f" · criado em {u['created_at'][:10]}" if u.get("created_at") else "")
            )

            with st.form(f"edit_account_{role}_{u['id']}"):
                new_name = st.text_input("Nome", value=u.get("name", ""))
                new_email = st.text_input(
                    "E-mail",
                    value=u.get("email") or "",
                    disabled=role == "student" and not u.get("email"),
                    help="Alunos cadastrados só por nome não possuem e-mail.",
                )
                status_options = list(auth_users.ACCOUNT_STATUSES)
                current_status = auth_users.user_account_status(u)
                new_status = st.selectbox(
                    "Status da conta",
                    options=status_options,
                    index=status_options.index(current_status),
                    format_func=lambda s: _ACCOUNT_STATUS_LABELS.get(s, s),
                    disabled=is_admin_account,
                )
                if st.form_submit_button("💾 Salvar alterações", type="primary"):
                    err = auth_users.update_user_account(
                        u["id"],
                        name=new_name,
                        email=new_email,
                        status=new_status,
                    )
                    if err:
                        st.error(err)
                    else:
                        st.success("Conta atualizada.")
                        st.rerun()

            if is_admin_account:
                st.caption("Conta do administrador do sistema — não pode ser excluída.")
            elif u["id"] == current_user_id:
                st.caption("Você não pode excluir a conta da sessão ativa.")
            elif st.button(
                "🗑️ Excluir conta",
                key=f"delete_account_{role}_{u['id']}",
                type="secondary",
            ):
                err = auth_users.delete_user_account(u["id"])
                if err:
                    st.error(err)
                else:
                    st.success(f"Conta de **{u.get('name')}** removida.")
                    st.rerun()


def render_auth_config_tab():
    st.subheader("Gerenciar contas")
    user = st.session_state.get("current_user")
    if user:
        st.write(f"**Sessão atual:** {user.get('name')} — `{user.get('role')}`")
        if user.get("email"):
            st.write(f"E-mail: {user['email']}")

    is_admin = _current_user_is_admin()
    if is_admin:
        st.success(f"Administrador do sistema: **{auth_users.get_system_admin_email()}**")
        st.caption(
            "Novas contas aguardam aprovação na aba **Aprovações**. "
            "Aqui você edita ou remove professores e alunos já cadastrados."
        )
        _render_backup_tools()
        tab_prof, tab_stud = st.tabs(["👨‍🏫 Professores", "👨‍🎓 Alunos"])
        with tab_prof:
            render_account_role_manager("professor")
        with tab_stud:
            render_account_role_manager("student")
    else:
        st.caption(
            "Entrada com Google ou pelo nome (alunos). "
            "Somente o administrador pode editar contas nesta seção."
        )

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
