"""Backup completo do sistema (materiais, provas, resultados, contas)."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from auth_users import USERS_PATH, load_users, save_users
from quiz_storage import (
    CONFIG_PATH,
    DATA_DIR,
    EXAM_DRAFTS_PATH,
    EXAM_SUBMISSIONS_PATH,
    EXAMS_PATH,
    LEADERBOARD_PATH,
    MATERIALS_PATH,
    STUDENTS_PATH,
    load_config,
    load_exam_submissions,
    load_exams_store,
    load_leaderboard,
    load_materials_store,
    load_students,
    merge_exam_submission,
    save_config,
    save_exam_submissions,
    save_exams_store,
    save_leaderboard,
    save_materials_store,
    save_students,
)

FULL_BACKUP_KIND = "projeto-quiz-backup-completo"
FULL_BACKUP_VERSION = 1
_CHECKSUM_SALT = "projeto-quiz-2026-backup-completo-v1"

BACKUP_ROOT = DATA_DIR / "backups"
BACKUP_FULL_DIR = BACKUP_ROOT / "completo"
BACKUP_SNAPSHOT_DIR = BACKUP_ROOT / "snapshots"
BACKUP_ACCOUNTS_DIR = BACKUP_ROOT / "contas"
AUTO_BACKUP_STAMP_PATH = BACKUP_ROOT / ".last_auto_backup"
AUTO_BACKUP_INTERVAL_HOURS = 6
AUTO_BACKUP_MAX_HISTORY = 30

_BACKUP_FILE_GLOB = "backup_*.json"

_BACKUP_PATHS: dict[str, Path] = {
    "materials": MATERIALS_PATH,
    "config": CONFIG_PATH,
    "leaderboard": LEADERBOARD_PATH,
    "students": STUDENTS_PATH,
    "exams": EXAMS_PATH,
    "exam_submissions": EXAM_SUBMISSIONS_PATH,
    "exam_drafts": EXAM_DRAFTS_PATH,
    "users": USERS_PATH,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def backup_stamp(when: datetime | None = None) -> str:
    return (when or utc_now()).strftime("%Y%m%d_%H%M%S")


def backup_filename(*, prefix: str = "backup_completo", when: datetime | None = None) -> str:
    return f"{prefix}_{backup_stamp(when)}.json"


def _unique_backup_path(
    directory: Path,
    stem: str,
    suffix: str,
    stamp: str,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{stem}_{stamp}{suffix}"
    if not candidate.exists():
        return candidate
    for seq in range(1, 1000):
        alt = directory / f"{stem}_{stamp}_{seq:03d}{suffix}"
        if not alt.exists():
            return alt
    raise OSError("Não foi possível gerar nome único para o backup.")


def _checksum(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "checksum"}
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((canonical + _CHECKSUM_SALT).encode("utf-8")).hexdigest()


def _snapshot_data() -> dict:
    return {
        "materials": load_materials_store(),
        "config": load_config(),
        "leaderboard": load_leaderboard(),
        "students": load_students(),
        "exams": load_exams_store(),
        "exam_submissions": load_exam_submissions(),
        "users": load_users(),
    }


def build_full_backup(*, when: datetime | None = None, source: str = "manual") -> dict:
    moment = when or utc_now()
    payload = {
        "kind": FULL_BACKUP_KIND,
        "version": FULL_BACKUP_VERSION,
        "generated_at": moment.isoformat(),
        "backup_stamp": backup_stamp(moment),
        "backup_source": source,
        "data": _snapshot_data(),
    }
    payload["checksum"] = _checksum(payload)
    return payload


def backup_bytes(payload: dict | None = None) -> bytes:
    data = payload or build_full_backup()
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def parse_full_backup(raw: bytes) -> tuple[dict | None, str | None]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "Arquivo inválido: não é um JSON de backup."

    if not isinstance(payload, dict) or payload.get("kind") != FULL_BACKUP_KIND:
        return None, "Arquivo inválido: não é um backup completo deste app."
    data = payload.get("data")
    if not isinstance(data, dict):
        return None, "Arquivo inválido: dados do backup ausentes."
    if payload.get("checksum") != _checksum(payload):
        return None, (
            "Backup corrompido ou alterado manualmente: o código de verificação não confere."
        )
    return payload, None


def _save_data_snapshots(stamp: str) -> Path | None:
    """Cópia datada dos arquivos JSON de dados — nunca sobrescreve pastas anteriores."""
    snap_dir = BACKUP_SNAPSHOT_DIR / stamp
    if snap_dir.exists():
        return snap_dir
    snap_dir.mkdir(parents=True, exist_ok=True)
    saved_any = False
    for path in _BACKUP_PATHS.values():
        if path.exists():
            shutil.copy2(path, snap_dir / path.name)
            saved_any = True
    if not saved_any:
        try:
            snap_dir.rmdir()
        except OSError:
            pass
        return None
    return snap_dir


def _restore_section(key: str, value) -> None:
    if key == "materials":
        save_materials_store(value)
    elif key == "config":
        save_config(value)
    elif key == "leaderboard":
        save_leaderboard(value)
    elif key == "students":
        save_students(value)
    elif key == "exams":
        save_exams_store(value)
    elif key == "exam_submissions":
        save_exam_submissions(value)
    elif key == "users":
        save_users(value)


def _quiz_dedupe_key(entry: dict) -> tuple:
    return (
        entry.get("material_id"),
        (entry.get("name") or "").strip().lower(),
        entry.get("score"),
        entry.get("total"),
        entry.get("submitted_at"),
    )


def restore_full_backup(payload: dict, *, replace: bool = True) -> dict:
    """Restaura backup completo. Com replace=False, mescla listas sem duplicar IDs."""
    data = payload.get("data") or {}
    stats = {"restored": [], "merged": [], "skipped": []}

    for key in _BACKUP_PATHS:
        incoming = data.get(key)
        if incoming is None:
            stats["skipped"].append(key)
            continue

        if replace:
            _restore_section(key, incoming)
            stats["restored"].append(key)
            continue

        if key == "materials":
            current = load_materials_store()
            cur_ids = {m["id"] for m in current.get("materials", [])}
            for mat in incoming.get("materials", []):
                if mat.get("id") not in cur_ids:
                    current.setdefault("materials", []).append(mat)
            for mid in incoming.get("active_material_ids", []):
                if mid not in current.get("active_material_ids", []):
                    current.setdefault("active_material_ids", []).append(mid)
            save_materials_store(current)
        elif key == "exams":
            from pdf_parser import merge_exam_questions

            current = load_exams_store()
            exams_list = current.setdefault("exams", [])
            by_id = {e["id"]: e for e in exams_list}
            by_title = {
                (e.get("title") or "").strip().lower(): e
                for e in exams_list
                if (e.get("title") or "").strip()
            }
            for exam in incoming.get("exams", []):
                eid = exam.get("id")
                title_key = (exam.get("title") or "").strip().lower()
                if eid and eid in by_id:
                    existing = by_id[eid]
                    merged_q = merge_exam_questions(
                        existing.get("questions", []), exam.get("questions", [])
                    )
                    if merged_q != existing.get("questions"):
                        existing["questions"] = merged_q
                    continue
                if title_key and title_key in by_title:
                    existing = by_title[title_key]
                    merged_q = merge_exam_questions(
                        existing.get("questions", []), exam.get("questions", [])
                    )
                    if merged_q != existing.get("questions"):
                        existing["questions"] = merged_q
                    continue
                exams_list.append(exam)
                if eid:
                    by_id[eid] = exam
                if title_key:
                    by_title[title_key] = exam
            for eid in incoming.get("active_exam_ids", []):
                if eid not in current.get("active_exam_ids", []):
                    current.setdefault("active_exam_ids", []).append(eid)
            save_exams_store(current)
        elif key == "leaderboard":
            board = load_leaderboard()
            existing = {_quiz_dedupe_key(e) for e in board}
            for entry in incoming:
                key_tuple = _quiz_dedupe_key(entry)
                if key_tuple not in existing:
                    board.append(entry)
                    existing.add(key_tuple)
            save_leaderboard(board)
        elif key == "exam_submissions":
            subs = load_exam_submissions()
            by_id = {s.get("id"): s for s in subs if s.get("id")}
            no_id = [s for s in subs if not s.get("id")]
            for sub in incoming:
                sid = sub.get("id")
                if not sid:
                    no_id.append(sub)
                    continue
                if sid in by_id:
                    by_id[sid] = merge_exam_submission(by_id[sid], sub)
                else:
                    by_id[sid] = sub
            save_exam_submissions(list(by_id.values()) + no_id)
        elif key == "students":
            current = load_students()
            cur_ids = {s["id"] for s in current}
            for student in incoming:
                if student.get("id") not in cur_ids:
                    current.append(student)
            save_students(current)
        elif key == "users":
            current = load_users()
            cur_ids = {u["id"] for u in current}
            cur_emails = {
                (u.get("email") or "").strip().lower()
                for u in current
                if u.get("email")
            }
            for user in incoming:
                if user.get("id") in cur_ids:
                    continue
                email = (user.get("email") or "").strip().lower()
                if email and email in cur_emails:
                    continue
                current.append(user)
                cur_ids.add(user.get("id"))
                if email:
                    cur_emails.add(email)
            save_users(current)
        elif key == "config":
            save_config({**load_config(), **incoming})
        stats["merged"].append(key)

    from quiz_storage import rehydrate_exam_questions_from_store, repair_orphan_exam_submissions

    stats["exam_questions_rehydrated"] = rehydrate_exam_questions_from_store()
    stats["exam_submissions_relinked"] = repair_orphan_exam_submissions()
    return stats


def backup_summary(payload: dict) -> dict:
    data = payload.get("data") or {}
    return {
        "materials": len((data.get("materials") or {}).get("materials", [])),
        "exams": len((data.get("exams") or {}).get("exams", [])),
        "quiz_results": len(data.get("leaderboard") or []),
        "exam_submissions": len(data.get("exam_submissions") or []),
        "students": len(data.get("students") or []),
        "users": len(data.get("users") or []),
        "generated_at": payload.get("generated_at"),
        "backup_stamp": payload.get("backup_stamp"),
    }


def _backup_entry(path: Path) -> dict:
    stat = path.stat()
    generated_at = None
    summary = {}
    backup_source = "desconhecido"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        generated_at = payload.get("generated_at")
        backup_source = payload.get("backup_source") or (
            "auto" if path.name.startswith("backup_auto_") else "manual"
        )
        summary = backup_summary(payload)
    except (json.JSONDecodeError, OSError):
        if path.name.startswith("backup_auto_"):
            backup_source = "auto"
        elif path.name.startswith("backup_manual_"):
            backup_source = "manual"
    stamp = path.stem
    for prefix in ("backup_auto_", "backup_manual_", "backup_completo_"):
        if stamp.startswith(prefix):
            stamp = stamp[len(prefix):]
            break
    label = stamp.replace("_", " ")
    return {
        "filename": path.name,
        "path": str(path),
        "stamp": stamp,
        "label": label,
        "generated_at": generated_at,
        "backup_source": backup_source,
        "size_kb": round(stat.st_size / 1024, 1),
        "summary": summary,
        "mtime": stat.st_mtime,
    }


def list_full_backups() -> list[dict]:
    if not BACKUP_FULL_DIR.is_dir():
        return []
    files = sorted(
        BACKUP_FULL_DIR.glob(_BACKUP_FILE_GLOB),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [_backup_entry(path) for path in files]


def read_full_backup_file(filename: str) -> bytes | None:
    safe_name = Path(filename).name
    path = BACKUP_FULL_DIR / safe_name
    if path.is_file() and path.name.startswith("backup_") and path.suffix == ".json":
        return path.read_bytes()
    return None


def read_latest_full_backup_bytes() -> bytes | None:
    backups = list_full_backups()
    if not backups:
        return None
    return read_full_backup_file(backups[0]["filename"])


def save_timestamped_full_backup(
    *,
    source: str = "manual",
    when: datetime | None = None,
    save_snapshots: bool = True,
) -> dict:
    """Grava um novo backup datado sem substituir arquivos anteriores."""
    moment = when or utc_now()
    stamp = backup_stamp(moment)
    stem = f"backup_{source}" if source in {"auto", "manual"} else "backup_completo"
    path = _unique_backup_path(BACKUP_FULL_DIR, stem, ".json", stamp)

    payload = build_full_backup(when=moment, source=source)
    path.write_bytes(backup_bytes(payload))
    snapshot_dir = _save_data_snapshots(stamp) if save_snapshots else None

    return {
        "filename": path.name,
        "path": str(path),
        "stamp": stamp,
        "generated_at": payload.get("generated_at"),
        "snapshot_dir": str(snapshot_dir) if snapshot_dir else None,
        "source": source,
    }


def _prune_auto_backups() -> None:
    auto_files = [
        BACKUP_FULL_DIR / entry["filename"]
        for entry in list_full_backups()
        if entry.get("backup_source") == "auto"
    ]
    for old in auto_files[AUTO_BACKUP_MAX_HISTORY:]:
        try:
            old.unlink()
        except OSError:
            pass


def run_auto_backup_if_due(*, force: bool = False) -> bool:
    """Grava backup automático datado (nunca sobrescreve cópias anteriores)."""
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    now = utc_now()

    if not force and AUTO_BACKUP_STAMP_PATH.is_file():
        try:
            last = datetime.fromisoformat(
                AUTO_BACKUP_STAMP_PATH.read_text(encoding="utf-8").strip()
            )
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            elapsed_h = (now - last).total_seconds() / 3600
            if elapsed_h < AUTO_BACKUP_INTERVAL_HOURS:
                return False
        except (ValueError, OSError):
            pass

    save_timestamped_full_backup(source="auto", when=now)
    AUTO_BACKUP_STAMP_PATH.write_text(now.isoformat(), encoding="utf-8")
    _prune_auto_backups()
    return True


def auto_backup_info() -> dict:
    backups = list_full_backups()
    snapshots = (
        sorted(
            (p for p in BACKUP_SNAPSHOT_DIR.iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if BACKUP_SNAPSHOT_DIR.is_dir()
        else []
    )
    account_backups = (
        sorted(
            BACKUP_ACCOUNTS_DIR.glob("backup_aprovados_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if BACKUP_ACCOUNTS_DIR.is_dir()
        else []
    )
    last_at = None
    if AUTO_BACKUP_STAMP_PATH.is_file():
        try:
            last_at = AUTO_BACKUP_STAMP_PATH.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return {
        "last_at": last_at,
        "history_count": len(backups),
        "latest_filename": backups[0]["filename"] if backups else None,
        "latest_generated_at": backups[0].get("generated_at") if backups else None,
        "snapshot_count": len(snapshots),
        "account_backup_count": len(account_backups),
        "backups": backups[:15],
    }


# Compatibilidade com código antigo
AUTO_BACKUP_DIR = BACKUP_FULL_DIR
AUTO_BACKUP_LATEST = BACKUP_FULL_DIR / "_deprecated_latest.json"


def read_auto_backup_latest_bytes() -> bytes | None:
    return read_latest_full_backup_bytes()
