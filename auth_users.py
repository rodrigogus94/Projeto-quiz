"""Cadastro unificado de usuários com papel (role): professor | student."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
USERS_PATH = DATA_DIR / "users.json"
ROLES = ("professor", "student")


def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data) -> None:
    _ensure_data_dir()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users() -> list:
    _ensure_data_dir()
    data = _load_json(USERS_PATH, [])
    return data if isinstance(data, list) else []


def save_users(users: list) -> None:
    _save_json(USERS_PATH, users)


def _normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def find_user_by_email(email: str) -> dict | None:
    key = _normalize_email(email)
    if not key:
        return None
    for user in load_users():
        if _normalize_email(user.get("email")) == key:
            return user
    return None


def find_user_by_google_id(google_id: str) -> dict | None:
    if not google_id:
        return None
    for user in load_users():
        if user.get("google_id") == google_id:
            return user
    return None


def find_user_by_id(user_id: str) -> dict | None:
    for user in load_users():
        if user.get("id") == user_id:
            return user
    return None


def find_student_by_name(name: str) -> dict | None:
    key = " ".join(name.strip().split()).lower()
    for user in load_users():
        if user.get("role") != "student":
            continue
        if user.get("name", "").strip().lower() == key:
            return user
    return None


def upsert_google_user(profile: dict, role: str | None = None) -> dict:
    """Cria ou atualiza usuário a partir do perfil Google OAuth."""
    google_id = profile.get("sub") or profile.get("id", "")
    email = _normalize_email(profile.get("email"))
    name = profile.get("name") or profile.get("given_name") or email.split("@")[0]

    users = load_users()
    existing = find_user_by_google_id(google_id) or find_user_by_email(email)

    if existing:
        for u in users:
            if u["id"] == existing["id"]:
                u["email"] = email or u.get("email")
                u["name"] = name or u.get("name")
                u["google_id"] = google_id
                u["picture"] = profile.get("picture", u.get("picture"))
                u["auth_provider"] = "google"
                u["updated_at"] = datetime.now(timezone.utc).isoformat()
                if role and role in ROLES:
                    u["role"] = role
                save_users(users)
                return u

    new_role = role if role in ROLES else "student"
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "google_id": google_id,
        "picture": profile.get("picture"),
        "role": new_role,
        "auth_provider": "google",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(user)
    save_users(users)
    return user


def ensure_name_student_user(name: str) -> dict:
    """Vincula cadastro por nome à tabela de usuários (role=student)."""
    name = " ".join(name.strip().split())
    existing = find_student_by_name(name)
    if existing:
        return existing
    user = {
        "id": str(uuid.uuid4()),
        "email": None,
        "name": name,
        "google_id": None,
        "picture": None,
        "role": "student",
        "auth_provider": "local",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users = load_users()
    users.append(user)
    save_users(users)
    return user


def set_user_role(user_id: str, role: str) -> str | None:
    if role not in ROLES:
        return "Papel inválido."
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["role"] = role
            u["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_users(users)
            return None
    return "Usuário não encontrado."


def list_users_by_role(role: str) -> list:
    return [u for u in load_users() if u.get("role") == role and u.get("active", True)]


def get_professor_allowlist() -> list[str]:
    from quiz_storage import load_config

    cfg = load_config()
    emails = cfg.get("professor_allowlist", [])
    return [_normalize_email(e) for e in emails if e]


def add_professor_allowlist_email(email: str) -> None:
    from quiz_storage import load_config, save_config

    email = _normalize_email(email)
    cfg = load_config()
    allowlist = cfg.get("professor_allowlist", [])
    if email not in [_normalize_email(e) for e in allowlist]:
        allowlist.append(email)
    cfg["professor_allowlist"] = allowlist
    save_config(cfg)


def remove_professor_allowlist_email(email: str) -> None:
    from quiz_storage import load_config, save_config

    email = _normalize_email(email)
    cfg = load_config()
    cfg["professor_allowlist"] = [
        e for e in cfg.get("professor_allowlist", []) if _normalize_email(e) != email
    ]
    save_config(cfg)


def can_be_professor(email: str) -> bool:
    email = _normalize_email(email)
    if not email:
        return False
    if email in get_professor_allowlist():
        return True
    user = find_user_by_email(email)
    return bool(user and user.get("role") == "professor")


def resolve_professor_login(profile: dict) -> tuple[dict | None, str | None]:
    email = _normalize_email(profile.get("email"))
    if not email:
        return None, "Conta Google sem e-mail verificado."

    user = find_user_by_email(email)
    if user and user.get("role") == "professor":
        return upsert_google_user(profile, role="professor"), None

    if can_be_professor(email):
        return upsert_google_user(profile, role="professor"), None

    return None, (
        "Este e-mail não tem permissão de professor. "
        "Peça ao administrador para adicioná-lo à lista de professores."
    )


def resolve_student_google_login(profile: dict) -> dict:
    user = find_user_by_email(profile.get("email", ""))
    if user and user.get("role") == "professor":
        return upsert_google_user(profile, role="professor")
    return upsert_google_user(profile, role="student")
