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
    from streamlit_oauth import OAuth2Component
except ImportError:
    OAuth2Component = None

PROJECT_DIR = Path(__file__).parent
DEFAULT_CLIENT_SECRET_FILE = PROJECT_DIR / ".streamlit" / "google_client_secret.json"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = "openid email profile"

_PLACEHOLDER_MARKERS = (
    "COLE_AQUI",
    "SEU_CLIENT",
    "SEU_CLIENT_SECRET",
    "your_client",
    "changeme",
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
    redirect_uri = _resolve_redirect_uri(
        from_json.get("redirect_uris", []),
        secrets_cfg.get("redirect_uri", ""),
    )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "client_secret_file": str(json_path),
        "project_id": from_json.get("project_id"),
    }


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


def render_google_login_button(
    label: str,
    key: str,
    *,
    role_hint: str = "professor",
) -> dict | None:
    if not google_oauth_configured():
        return None

    oauth = get_oauth_component()
    if oauth is None:
        st.warning("Pacote streamlit-oauth não instalado.")
        return None

    cfg = get_google_oauth_config()
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
