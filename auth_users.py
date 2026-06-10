"""Cadastro unificado de usuários com papel (role): professor | student."""
from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
USERS_PATH = DATA_DIR / "users.json"
BACKUP_APPROVED_PATH = DATA_DIR / "backup_aprovados.csv"
ROLES = ("professor", "student")
ACCOUNT_STATUSES = ("pending", "approved", "rejected")
PROFESSOR_STATUSES = ACCOUNT_STATUSES
DEFAULT_ADMIN_EMAIL = "rodrigogus94@gmail.com"
ROLE_LABELS = {"professor": "Professor", "student": "Aluno"}


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


def _write_approved_backup(users: list) -> None:
    """Backup local (CSV) dos usuários já cadastrados e aprovados.

    Regenerado a cada alteração no cadastro; serve como cópia de segurança
    com nome, e-mail e categoria, legível em Excel/planilhas.
    """
    try:
        _ensure_data_dir()
        approved = [
            u
            for u in users
            if u.get("active", True) and u.get("status", "approved") == "approved"
        ]
        with BACKUP_APPROVED_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["nome", "email", "categoria", "cadastrado_em", "atualizado_em"])
            for u in sorted(approved, key=lambda x: (x.get("role", ""), (x.get("name") or "").lower())):
                writer.writerow(
                    [
                        u.get("name") or "",
                        u.get("email") or "",
                        ROLE_LABELS.get(u.get("role"), u.get("role") or ""),
                        u.get("created_at") or "",
                        u.get("updated_at") or "",
                    ]
                )
    except OSError:
        # O backup nunca deve quebrar o fluxo principal de cadastro.
        pass


def save_users(users: list) -> None:
    _save_json(USERS_PATH, users)
    _write_approved_backup(users)


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


def get_system_admin_email() -> str:
    try:
        import streamlit as st

        email = st.secrets.get("auth", {}).get("system_admin_email")
        if email:
            return _normalize_email(email)
    except Exception:
        pass
    from quiz_storage import load_config

    cfg = load_config()
    return _normalize_email(cfg.get("system_admin_email", DEFAULT_ADMIN_EMAIL))


def is_system_admin(email: str | None) -> bool:
    key = _normalize_email(email)
    return bool(key and key == get_system_admin_email())


def user_account_status(user: dict | None) -> str:
    if not user:
        return "approved"
    return user.get("status", "approved")


def is_user_approved(user: dict | None) -> bool:
    if not user or not user.get("active", True):
        return False
    if is_system_admin(user.get("email")) or user.get("is_admin"):
        return True
    return user_account_status(user) == "approved"


def is_approved_professor(user: dict | None) -> bool:
    if not user or user.get("role") != "professor":
        return False
    return is_user_approved(user)


def is_approved_student_name(name: str) -> bool:
    user = find_student_by_name(name)
    if not user:
        from quiz_storage import find_student_by_name as find_roster_student

        return find_roster_student(name) is not None
    return is_user_approved(user)


def get_pending_users() -> list:
    return [
        u
        for u in load_users()
        if user_account_status(u) == "pending" and u.get("active", True)
    ]


def get_pending_professors() -> list:
    return [u for u in get_pending_users() if u.get("role") == "professor"]


def _sync_approved_student_to_roster(name: str) -> None:
    from quiz_storage import add_student, find_student_by_name

    clean = " ".join(name.strip().split())
    if clean and not find_student_by_name(clean):
        add_student(clean)


def approve_user(user_id: str) -> str | None:
    users = load_users()
    for u in users:
        if u["id"] != user_id:
            continue
        if user_account_status(u) != "pending":
            return "Esta solicitação não está pendente."
        u["status"] = "approved"
        u["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_users(users)
        if u.get("role") == "student":
            _sync_approved_student_to_roster(u.get("name", ""))
        return None
    return "Usuário não encontrado."


def reject_user(user_id: str) -> str | None:
    users = load_users()
    for u in users:
        if u["id"] != user_id:
            continue
        if user_account_status(u) != "pending":
            return "Esta solicitação não está pendente."
        u["status"] = "rejected"
        u["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_users(users)
        return None
    return "Usuário não encontrado."


def approve_professor(user_id: str) -> str | None:
    return approve_user(user_id)


def reject_professor(user_id: str) -> str | None:
    return reject_user(user_id)


def upsert_google_user(
    profile: dict,
    role: str | None = None,
    status: str | None = None,
    is_admin: bool | None = None,
) -> dict:
    """Cria ou atualiza usuário a partir do perfil Google OAuth."""
    google_id = profile.get("sub") or profile.get("id", "")
    email = _normalize_email(profile.get("email"))
    name = profile.get("name") or profile.get("given_name") or email.split("@")[0]
    admin_flag = is_admin if is_admin is not None else is_system_admin(email)

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
                if status in ACCOUNT_STATUSES:
                    u["status"] = status
                elif "status" not in u:
                    u["status"] = "approved"
                if admin_flag:
                    u["is_admin"] = True
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
    if status in ACCOUNT_STATUSES:
        user["status"] = status
    elif admin_flag:
        user["status"] = "approved"
    elif new_role == "professor":
        user["status"] = "pending"
    else:
        user["status"] = "pending"
    if admin_flag:
        user["is_admin"] = True
    users.append(user)
    save_users(users)
    return user


def register_student_request(name: str) -> tuple[dict | None, str | None]:
    """Solicita cadastro de aluno por nome — fica pendente até o admin aprovar."""
    name = " ".join(name.strip().split())
    if not name:
        return None, "Informe o nome."
    existing = find_student_by_name(name)
    if existing:
        status = user_account_status(existing)
        if status == "pending":
            return None, "Seu cadastro já está aguardando aprovação do administrador."
        if status == "approved":
            return None, "Já existe uma conta com este nome."
        if status == "rejected":
            return None, "Seu cadastro foi negado. Contate o administrador do sistema."
    user = {
        "id": str(uuid.uuid4()),
        "email": None,
        "name": name,
        "google_id": None,
        "picture": None,
        "role": "student",
        "auth_provider": "local",
        "status": "pending",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users = load_users()
    users.append(user)
    save_users(users)
    return user, None


def ensure_name_student_user(name: str, *, auto_approve: bool = False) -> dict:
    """Vincula cadastro por nome à tabela de usuários (role=student)."""
    name = " ".join(name.strip().split())
    existing = find_student_by_name(name)
    if existing:
        if auto_approve and user_account_status(existing) != "approved":
            users = load_users()
            for u in users:
                if u["id"] == existing["id"]:
                    u["status"] = "approved"
                    u["updated_at"] = datetime.now(timezone.utc).isoformat()
                    save_users(users)
                    existing = u
                    break
        return existing
    user = {
        "id": str(uuid.uuid4()),
        "email": None,
        "name": name,
        "google_id": None,
        "picture": None,
        "role": "student",
        "auth_provider": "local",
        "status": "approved" if auto_approve else "pending",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users = load_users()
    users.append(user)
    save_users(users)
    if auto_approve:
        _sync_approved_student_to_roster(name)
    return user


def set_user_role(user_id: str, role: str) -> str | None:
    if role not in ROLES:
        return "Papel inválido."
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["role"] = role
            if role == "professor":
                u["status"] = "approved"
            else:
                u["status"] = "approved"
                _sync_approved_student_to_roster(u.get("name", ""))
            u["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_users(users)
            return None
    return "Usuário não encontrado."


def _rename_student_roster(old_name: str, new_name: str) -> None:
    from quiz_storage import find_student_by_name, update_student

    roster = find_student_by_name(old_name)
    if roster:
        update_student(roster["id"], new_name)


def _remove_student_roster(name: str) -> None:
    from quiz_storage import delete_student, find_student_by_name

    roster = find_student_by_name(name)
    if roster:
        delete_student(roster["id"])


def update_user_account(
    user_id: str,
    *,
    name: str | None = None,
    email: str | None = None,
    status: str | None = None,
) -> str | None:
    users = load_users()
    target = next((u for u in users if u["id"] == user_id), None)
    if not target:
        return "Usuário não encontrado."

    old_name = target.get("name", "")
    if name is not None:
        clean_name = " ".join(name.strip().split())
        if not clean_name:
            return "Informe o nome."
        if target.get("role") == "student":
            duplicate = find_student_by_name(clean_name)
            if duplicate and duplicate["id"] != user_id:
                return "Já existe outro aluno com este nome."
        target["name"] = clean_name

    if email is not None:
        clean_email = _normalize_email(email) if email.strip() else None
        if clean_email:
            other = find_user_by_email(clean_email)
            if other and other["id"] != user_id:
                return "Este e-mail já está em uso por outra conta."
        target["email"] = clean_email

    if status is not None:
        if status not in ACCOUNT_STATUSES:
            return "Status inválido."
        if is_system_admin(target.get("email")) and status != "approved":
            return "O administrador do sistema deve permanecer aprovado."
        target["status"] = status
        if status == "approved" and target.get("role") == "student":
            _sync_approved_student_to_roster(target.get("name", ""))

    if target.get("role") == "student" and target.get("name") != old_name:
        _rename_student_roster(old_name, target.get("name", ""))

    target["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_users(users)
    return None


def delete_user_account(user_id: str) -> str | None:
    target = find_user_by_id(user_id)
    if not target:
        return "Usuário não encontrado."
    if is_system_admin(target.get("email")) or target.get("is_admin"):
        return "Não é possível excluir o administrador do sistema."

    if target.get("role") == "student":
        _remove_student_roster(target.get("name", ""))
        # Remove também os resultados (quizzes/provas), inclusive os gravados
        # apenas com o e-mail da conta, para não deixar dados órfãos.
        from quiz_storage import purge_student_results

        purge_student_results(target.get("name", ""), target.get("email"))

    users = [u for u in load_users() if u["id"] != user_id]
    save_users(users)
    return None


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

    admin_email = get_system_admin_email()

    if is_system_admin(email):
        return (
            upsert_google_user(
                profile,
                role="professor",
                status="approved",
                is_admin=True,
            ),
            None,
        )

    user = find_user_by_email(email)
    if user and user.get("role") == "professor":
        status = user.get("status", "approved")
        if status == "approved":
            return upsert_google_user(profile, role="professor", status="approved"), None
        if status == "pending":
            upsert_google_user(profile, role="professor", status="pending")
            return (
                None,
                "Sua solicitação de professor está aguardando aprovação do administrador.",
            )
        if status == "rejected":
            return (
                None,
                "Seu acesso como professor foi negado. Contate o administrador do sistema.",
            )

    upsert_google_user(profile, role="professor", status="pending")
    return (
        None,
        f"Solicitação enviada! O administrador ({admin_email}) precisa aprovar seu acesso como professor.",
    )


def resolve_student_google_login(profile: dict) -> dict:
    user = find_user_by_email(profile.get("email", ""))
    if is_approved_professor(user):
        return upsert_google_user(profile, role="professor", status="approved")
    return upsert_google_user(profile, role="student")


def resolve_unified_google_login(profile: dict) -> tuple[dict | None, str | None]:
    """Login único com Google: só entra após aprovação do administrador."""
    email = _normalize_email(profile.get("email"))
    if not email:
        return None, "Conta Google sem e-mail verificado."

    admin_email = get_system_admin_email()

    if is_system_admin(email):
        return (
            upsert_google_user(
                profile,
                role="professor",
                status="approved",
                is_admin=True,
            ),
            None,
        )

    user = find_user_by_email(email)
    if user:
        status = user_account_status(user)
        if status == "pending":
            upsert_google_user(profile, status="pending")
            return (
                None,
                "Sua conta ainda aguarda aprovação do administrador.",
            )
        if status == "rejected":
            return (
                None,
                "Seu acesso foi negado. Contate o administrador do sistema.",
            )
        if user.get("role") == "professor" and status == "approved":
            return upsert_google_user(profile, role="professor", status="approved"), None
        if user.get("role") == "student" and status == "approved":
            approved = upsert_google_user(profile, role="student", status="approved")
            _sync_approved_student_to_roster(approved.get("name", ""))
            return approved, None

    upsert_google_user(profile, role="student", status="pending")
    return (
        None,
        f"Conta criada! O administrador ({admin_email}) precisa aprovar seu acesso.",
    )
