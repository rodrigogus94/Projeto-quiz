from __future__ import annotations

import streamlit as st

import auth_users
from google_auth import (
    google_oauth_configured,
    legacy_password_enabled,
    render_google_login_button,
    render_oauth_setup_help,
)
from quiz_storage import verify_professor
import ui_theme

from app.session import (
    _logout_button_label,
    _logout_confirmation_message,
    _request_logout,
    login_user,
    logout,
)


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


def _render_account_settings_menu():
    ui_theme.render_theme_selector(compact=True)
    st.markdown('<span class="kahoot-menu-action-marker"></span>', unsafe_allow_html=True)
    if st.button("Recarregar aplicativo", key="account_menu_rerun", use_container_width=True):
        st.rerun()


def _register_student_name(name: str) -> tuple[bool, str]:
    clean = " ".join(name.strip().split())
    _, err = auth_users.register_student_request(clean)
    if err:
        if "aguardando aprovação" in err:
            st.info(err)
        else:
            st.error(err)
        return False, ""
    return True, clean


def render_student_register_form(form_key: str, button_label: str = "Cadastrar-me") -> bool:
    with st.form(form_key):
        name = st.text_input("Nome completo", placeholder="Ex.: Maria Silva")
        submitted = st.form_submit_button(button_label, use_container_width=True)
        if submitted:
            ok, clean = _register_student_name(name)
            if ok:
                admin_email = auth_users.get_system_admin_email()
                st.success(
                    f"Solicitação enviada para **{clean}**! "
                    f"O administrador ({admin_email}) precisa aprovar seu acesso."
                )
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
            _register_student_name(name)

    st.markdown(
        '<p class="kahoot-footnote">Já tem conta? Use o botão <b>ENTRAR</b> para alternar.</p>'
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
        '<p class="kahoot-footnote">Novo por aqui? Use o botão <b>CADASTRAR-SE</b> para alternar.</p>'
        f'<p class="kahoot-footnote">O administrador ({auth_users.get_system_admin_email()}) '
        "aprova novas contas na aba Aprovações.</p></div>",
        unsafe_allow_html=True,
    )


def _set_auth_view(target: str) -> None:
    st.session_state.auth_view = target


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

    ui_theme.inject_app_chrome(hide_toolbar=True)
    ui_theme.inject_login_page_css()

    if logout_message:
        st.markdown(
            f'<div class="kahoot-login-toast">{logout_message}</div>',
            unsafe_allow_html=True,
        )

    col_left, col_right = st.columns(2, gap="small")

    with col_left:
        st.markdown('<span class="kahoot-login-marker"></span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="kahoot-left-panel">'
            f'<div class="kahoot-left-inner">'
            f"<h2>{left_title}</h2>"
            f"<p>{left_desc}</p>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown('<span class="kahoot-login-switch-marker"></span>', unsafe_allow_html=True)
        st.button(
            switch_label,
            key=switch_key,
            use_container_width=True,
            type="primary",
            on_click=_set_auth_view,
            args=(switch_target,),
        )

    with col_right:
        st.markdown('<span class="kahoot-login-form-marker" style="display:none"></span>', unsafe_allow_html=True)
        if view == "signup":
            render_login_signup_panel()
        else:
            render_login_signin_panel()

    ui_theme.inject_login_layout_script()
    ui_theme.inject_login_switch_button_css()


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

    ui_theme.inject_app_chrome(hide_toolbar=True)
    ui_theme.inject_sidebar_session_css()
    clear_login = getattr(ui_theme, "clear_login_page_styles", None)
    if clear_login:
        clear_login()

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
                icon=":material/menu:",
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
