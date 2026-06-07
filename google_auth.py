"""Login com Google OAuth para Streamlit."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

try:
    import requests
except ImportError:
    requests = None

try:
    from streamlit_oauth import OAuth2Component, StreamlitOauthError
except ImportError:
    OAuth2Component = None
    StreamlitOauthError = Exception  # type: ignore

PROJECT_DIR = Path(__file__).parent
DEFAULT_CLIENT_SECRET_FILE = PROJECT_DIR / ".streamlit" / "google_client_secret.json"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = "openid email profile"

GOOGLE_ICON_DATA_URI = (
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

_PLACEHOLDER_MARKERS = (
    "COLE_AQUI",
    "SEU_CLIENT",
    "SEU_CLIENT_SECRET",
    "your_client",
    "changeme",
)


def is_streamlit_cloud() -> bool:
    import os

    return bool(
        os.environ.get("STREAMLIT_SHARING_MODE")
        or os.environ.get("STREAMLIT_RUNTIME_ENV") == "cloud"
        or os.environ.get("STREAMLIT_SERVER_ADDRESS") == "0.0.0.0"
    )


def _get_secret_section(key: str) -> dict:
    try:
        return dict(st.secrets.get(key, {}))
    except Exception:
        return {}


def _is_placeholder(value: str) -> bool:
    upper = (value or "").upper()
    return any(marker in upper for marker in _PLACEHOLDER_MARKERS)


def load_oauth_from_json(path: Path) -> dict | None:
    """Lê client_id, client_secret e redirect_uris do JSON do Google Cloud."""
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    web = data.get("web") or data.get("installed") or {}
    client_id = web.get("client_id", "")
    client_secret = web.get("client_secret", "")
    if not client_id or not client_secret:
        return None

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uris": list(web.get("redirect_uris") or []),
        "project_id": web.get("project_id"),
    }


def _resolve_redirect_uri(redirect_uris: list[str], override: str = "") -> str:
    if override and not _is_placeholder(override):
        return override.strip()

    if not redirect_uris:
        return "http://localhost:8501"
    if len(redirect_uris) == 1:
        return redirect_uris[0]

    import os

    on_streamlit_cloud = bool(
        os.environ.get("STREAMLIT_SHARING_MODE")
        or os.environ.get("STREAMLIT_RUNTIME_ENV") == "cloud"
    )
    if on_streamlit_cloud:
        for uri in redirect_uris:
            if "streamlit.app" in uri:
                return uri
    for uri in redirect_uris:
        if "localhost" in uri:
            return uri
    return redirect_uris[0]


def get_google_oauth_config() -> dict:
    """
    Monta config OAuth2 mesclando secrets.toml e JSON do Google Cloud.
    Prioridade: secrets.toml sobrescreve campos do JSON.
    """
    secrets_cfg = _get_secret_section("google_oauth")
    json_rel = secrets_cfg.get("client_secret_file", ".streamlit/google_client_secret.json")
    json_path = Path(json_rel)
    if not json_path.is_absolute():
        json_path = PROJECT_DIR / json_path

    from_json = load_oauth_from_json(json_path) or {}

    client_id = secrets_cfg.get("client_id") or from_json.get("client_id", "")
    client_secret = secrets_cfg.get("client_secret") or from_json.get("client_secret", "")
    redirect_uris = list(from_json.get("redirect_uris") or [])
    deploy_url = ""
    try:
        deploy_url = st.secrets.get("deployment", {}).get("url", "")
    except Exception:
        pass

    if secrets_cfg.get("redirect_uri") and not _is_placeholder(secrets_cfg["redirect_uri"]):
        redirect_uri = secrets_cfg["redirect_uri"].strip()
    elif deploy_url and not _is_placeholder(deploy_url):
        redirect_uri = deploy_url.strip().rstrip("/")
    else:
        redirect_uri = _resolve_redirect_uri(redirect_uris, "")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "client_secret_file": str(json_path),
        "project_id": from_json.get("project_id"),
    }


def oauth_diagnosis() -> list[str]:
    """Lista o que falta para o Google OAuth funcionar (sem expor segredos)."""
    issues = []
    secrets_cfg = _get_secret_section("google_oauth")
    cfg = get_google_oauth_config()

    if not secrets_cfg and not load_oauth_from_json(DEFAULT_CLIENT_SECRET_FILE):
        issues.append("Nenhuma credencial OAuth encontrada.")

    if not cfg.get("client_id"):
        issues.append("Falta `client_id` (em Secrets ou no JSON local).")
    if not cfg.get("client_secret"):
        issues.append("Falta `client_secret` (em Secrets ou no JSON local).")
    if not cfg.get("redirect_uri"):
        issues.append("Falta `redirect_uri` (URL do app, ex.: https://seu-app.streamlit.app).")

    if is_streamlit_cloud():
        json_exists = Path(cfg.get("client_secret_file", "")).exists()
        if not json_exists and not secrets_cfg.get("client_id"):
            issues.append(
                "Streamlit Cloud: o arquivo JSON local NÃO vai no deploy. "
                "Cole `client_id`, `client_secret` e `redirect_uri` em "
                "**Manage app → Settings → Secrets**."
            )

    if OAuth2Component is None:
        issues.append("Pacote `streamlit-oauth` não instalado (veja requirements.txt).")

    return issues


def google_oauth_configured() -> bool:
    cfg = get_google_oauth_config()
    client_id = cfg.get("client_id", "")
    client_secret = cfg.get("client_secret", "")
    redirect_uri = cfg.get("redirect_uri", "")
    if not (client_id and client_secret and redirect_uri):
        return False
    if _is_placeholder(client_id) or _is_placeholder(client_secret):
        return False
    return True


def legacy_password_enabled() -> bool:
    cfg = _get_secret_section("auth")
    return cfg.get("allow_legacy_professor_login", True)


def get_oauth_component() -> OAuth2Component | None:
    if OAuth2Component is None:
        return None
    if not google_oauth_configured():
        return None
    cfg = get_google_oauth_config()
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


def _clear_oauth_state_keys(button_key: str | None = None):
    if button_key:
        st.session_state.pop(f"state-{button_key}", None)
        st.session_state.pop(f"pkce-{button_key}", None)
        return
    for k in list(st.session_state.keys()):
        if k.startswith("state-") or k.startswith("pkce-"):
            st.session_state.pop(k, None)


def render_google_login_button(
    label: str,
    key: str,
    *,
    role_hint: str = "professor",
    use_container_width: bool = True,
    icon: str | None = None,
) -> dict | None:
    if not google_oauth_configured():
        return None

    oauth = get_oauth_component()
    if oauth is None:
        st.warning("Pacote streamlit-oauth não instalado.")
        return None

    cfg = get_google_oauth_config()
    st.session_state["_oauth_role_hint"] = role_hint

    try:
        result = oauth.authorize_button(
            label,
            cfg["redirect_uri"],
            SCOPES,
            key=key,
            use_container_width=use_container_width,
            icon=icon,
        )
    except StreamlitOauthError:
        _clear_oauth_state_keys(key)
        st.warning(
            "A sessão do Google expirou ou foi interrompida. "
            "Clique em **Entrar com Google** novamente."
        )
        return None

    if not result or "token" not in result:
        return None

    profile = fetch_google_profile(result["token"])
    if profile:
        st.session_state["oauth_token"] = result["token"]
    return profile


def clear_oauth_session():
    _clear_oauth_state_keys()
    st.session_state.pop("oauth_token", None)
    st.session_state.pop("_oauth_role_hint", None)


CLOUD_SECRETS_TEMPLATE = """
[google_oauth]
client_id = "SEU_CLIENT_ID.apps.googleusercontent.com"
client_secret = "GOCSPX-SEU_CLIENT_SECRET"
redirect_uri = "https://projeto-quiz-rbbnbrjptykghaaz7bdwwf.streamlit.app"

[auth]
system_admin_email = "rodrigogus94@gmail.com"
allow_legacy_professor_login = false
"""


def render_oauth_setup_help():
    """Instruções quando OAuth não está configurado."""
    if is_streamlit_cloud():
        st.warning(
            "Você está no **Streamlit Cloud**. As credenciais do PC "
            "(`google_client_secret.json`) **não** vêm no deploy do GitHub."
        )
        st.markdown("**Passos:**")
        st.markdown(
            "1. Abra o app no Cloud → **Manage app** → **Settings** → **Secrets**\n"
            "2. Cole o bloco abaixo (com seu `client_secret` e e-mail)\n"
            "3. Salve e clique em **Reboot app**"
        )
        st.code(CLOUD_SECRETS_TEMPLATE.strip(), language="toml")
    else:
        st.info(
            "Local: coloque o JSON em `.streamlit/google_client_secret.json` "
            "e configure `.streamlit/secrets.toml` (ambos ignorados pelo Git)."
        )

    issues = oauth_diagnosis()
    if issues:
        with st.expander("Diagnóstico OAuth"):
            for item in issues:
                st.write(f"- {item}")
