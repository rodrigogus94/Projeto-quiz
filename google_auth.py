"""Login com Google OAuth para Streamlit."""
from __future__ import annotations

import streamlit as st

try:
    import requests
except ImportError:
    requests = None

try:
    from streamlit_oauth import OAuth2Component
except ImportError:
    OAuth2Component = None


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = "openid email profile"


def _get_secret_section(key: str) -> dict:
    try:
        return dict(st.secrets.get(key, {}))
    except Exception:
        return {}


def google_oauth_configured() -> bool:
    cfg = _get_secret_section("google_oauth")
    return bool(cfg.get("client_id") and cfg.get("client_secret") and cfg.get("redirect_uri"))


def legacy_password_enabled() -> bool:
    cfg = _get_secret_section("auth")
    return cfg.get("allow_legacy_professor_login", True)


def get_oauth_component() -> OAuth2Component | None:
    if OAuth2Component is None:
        return None
    cfg = _get_secret_section("google_oauth")
    if not google_oauth_configured():
        return None
    return OAuth2Component(
        cfg["client_id"],
        cfg["client_secret"],
        GOOGLE_AUTH_URL,
        GOOGLE_TOKEN_URL,
        GOOGLE_REVOKE_URL,
        GOOGLE_TOKEN_URL,
    )


def fetch_google_profile(token: dict) -> dict | None:
    if not requests:
        return None
    access = token.get("access_token")
    if not access:
        return None
    try:
        response = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def render_google_login_button(
    label: str,
    key: str,
    *,
    role_hint: str = "professor",
) -> dict | None:
    """
    Exibe botão Google e retorna perfil do usuário se login concluído.
    role_hint guarda contexto na sessão (professor/student).
    """
    if not google_oauth_configured():
        return None

    oauth = get_oauth_component()
    if oauth is None:
        st.warning("Pacote streamlit-oauth não instalado.")
        return None

    cfg = _get_secret_section("google_oauth")
    st.session_state["_oauth_role_hint"] = role_hint

    result = oauth.authorize_button(
        label,
        cfg["redirect_uri"],
        SCOPES,
        key=key,
        use_container_width=True,
    )
    if not result or "token" not in result:
        return None

    profile = fetch_google_profile(result["token"])
    if profile:
        st.session_state["oauth_token"] = result["token"]
    return profile


def clear_oauth_session():
    st.session_state.pop("oauth_token", None)
    st.session_state.pop("_oauth_role_hint", None)
