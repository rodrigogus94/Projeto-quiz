"""Persistência local (evita conflito com o pacote PyPI 'storage')."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MATERIALS_PATH = DATA_DIR / "materials.json"
CONFIG_PATH = DATA_DIR / "config.json"
LEADERBOARD_PATH = DATA_DIR / "leaderboard.json"
STUDENTS_PATH = DATA_DIR / "students.json"
EXAMS_PATH = DATA_DIR / "exams.json"
EXAM_SUBMISSIONS_PATH = DATA_DIR / "exam_submissions.json"

DEFAULT_USERNAME = "professor"
DEFAULT_PASSWORD = "professor123"


def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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


def load_config() -> dict:
    _ensure_data_dir()
    config = _load_json(
        CONFIG_PATH,
        {
            "professor_username": DEFAULT_USERNAME,
            "professor_password_hash": hash_password(DEFAULT_PASSWORD),
            "professor_allowlist": [],
            "system_admin_email": "rodrigogus94@gmail.com",
        },
    )
    if "professor_password_hash" not in config:
        config["professor_password_hash"] = hash_password(DEFAULT_PASSWORD)
    if "professor_username" not in config:
        config["professor_username"] = DEFAULT_USERNAME
    if "professor_allowlist" not in config:
        config["professor_allowlist"] = []
    if "system_admin_email" not in config:
        config["system_admin_email"] = "rodrigogus94@gmail.com"
    return config


def save_config(config: dict) -> None:
    _save_json(CONFIG_PATH, config)


def verify_professor(username: str, password: str) -> bool:
    config = load_config()
    return (
        username.strip() == config["professor_username"]
        and hash_password(password) == config["professor_password_hash"]
    )


def update_professor_credentials(username: str, new_password: str) -> None:
    config = load_config()
    config["professor_username"] = username.strip()
    config["professor_password_hash"] = hash_password(new_password)
    save_config(config)


def _migrate_active_ids(store: dict) -> None:
    if "active_material_ids" not in store:
        old = store.pop("active_material_id", None)
        store["active_material_ids"] = [old] if old else []
    if store.get("active_material_ids") is None:
        store["active_material_ids"] = []


def load_materials_store() -> dict:
    _ensure_data_dir()
    store = _load_json(MATERIALS_PATH, {"materials": [], "active_material_ids": []})
    if "materials" not in store:
        store["materials"] = []
    _migrate_active_ids(store)
    return store


def save_materials_store(store: dict) -> None:
    _save_json(MATERIALS_PATH, store)


def list_materials() -> list:
    return load_materials_store()["materials"]


def get_material(material_id: str) -> dict | None:
    for m in list_materials():
        if m["id"] == material_id:
            return m
    return None


def get_active_material_ids() -> list:
    store = load_materials_store()
    return list(store.get("active_material_ids") or [])


def is_material_active(material_id: str) -> bool:
    return material_id in get_active_material_ids()


def get_active_materials() -> list:
    active_ids = set(get_active_material_ids())
    return [m for m in list_materials() if m["id"] in active_ids]


def toggle_material_active(material_id: str) -> bool:
    """Alterna ativação do material. Retorna True se ficou ativo."""
    store = load_materials_store()
    ids = store.setdefault("active_material_ids", [])
    if material_id in ids:
        ids.remove(material_id)
        active = False
    else:
        ids.append(material_id)
        active = True
    save_materials_store(store)
    return active


def create_material(title: str, questions: list) -> dict:
    material = {
        "id": str(uuid.uuid4()),
        "title": title.strip() or "Material sem título",
        "questions": questions,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    store = load_materials_store()
    store["materials"].append(material)
    if len(store["materials"]) == 1:
        store.setdefault("active_material_ids", []).append(material["id"])
    save_materials_store(store)
    return material


def update_material(material_id: str, title: str, questions: list) -> bool:
    store = load_materials_store()
    for m in store["materials"]:
        if m["id"] == material_id:
            m["title"] = title.strip() or m["title"]
            m["questions"] = questions
            m["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_materials_store(store)
            return True
    return False


def delete_material(material_id: str) -> None:
    store = load_materials_store()
    store["materials"] = [m for m in store["materials"] if m["id"] != material_id]
    active_ids = store.setdefault("active_material_ids", [])
    if material_id in active_ids:
        active_ids.remove(material_id)
    save_materials_store(store)


def load_leaderboard() -> list:
    _ensure_data_dir()
    data = _load_json(LEADERBOARD_PATH, [])
    return data if isinstance(data, list) else []


def save_leaderboard(leaderboard: list) -> None:
    _save_json(LEADERBOARD_PATH, leaderboard)


def leaderboard_for_material(material_id: str) -> list:
    return [e for e in load_leaderboard() if e.get("material_id") == material_id]


def migrate_legacy_leaderboard():
    """Move leaderboard.json da raiz do projeto para data/."""
    legacy = Path(__file__).parent / "leaderboard.json"
    if legacy.exists() and not LEADERBOARD_PATH.exists():
        _ensure_data_dir()
        legacy.rename(LEADERBOARD_PATH)


def load_students() -> list:
    _ensure_data_dir()
    data = _load_json(STUDENTS_PATH, [])
    return data if isinstance(data, list) else []


def save_students(students: list) -> None:
    _save_json(STUDENTS_PATH, students)


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split()).lower()


def find_student_by_name(name: str) -> dict | None:
    key = _normalize_name(name)
    for s in load_students():
        if _normalize_name(s["name"]) == key:
            return s
    return None


def add_student(name: str) -> tuple[dict | None, str | None]:
    name = " ".join(name.strip().split())
    if not name:
        return None, "Informe o nome do aluno."
    if find_student_by_name(name):
        return None, "Já existe um aluno com este nome."
    student = {
        "id": str(uuid.uuid4()),
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    students = load_students()
    students.append(student)
    save_students(students)
    return student, None


def update_student(student_id: str, name: str) -> str | None:
    name = " ".join(name.strip().split())
    if not name:
        return "Informe o nome do aluno."
    students = load_students()
    key = _normalize_name(name)
    for other in students:
        if other["id"] != student_id and _normalize_name(other["name"]) == key:
            return "Já existe outro aluno com este nome."
    for s in students:
        if s["id"] == student_id:
            s["name"] = name
            s.pop("identifier", None)
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_students(students)
            return None
    return "Aluno não encontrado."


def delete_student(student_id: str) -> None:
    students = [s for s in load_students() if s["id"] != student_id]
    save_students(students)


def student_quiz_stats(student_name: str) -> dict:
    key = _normalize_name(student_name)
    entries = [
        e for e in load_leaderboard() if _normalize_name(e.get("name", "")) == key
    ]
    if not entries:
        return {"attempts": 0, "avg_pct": None, "last_score": None}
    pcts = [(e["score"] / e["total"]) * 100 for e in entries if e.get("total", 0) > 0]
    last = entries[-1]
    return {
        "attempts": len(entries),
        "avg_pct": sum(pcts) / len(pcts) if pcts else None,
        "last_score": f"{last['score']}/{last['total']}" if last else None,
    }


def is_registered_student(name: str) -> bool:
    return find_student_by_name(name) is not None


# ---------------------------
# Provas
# ---------------------------
def load_exams_store() -> dict:
    _ensure_data_dir()
    store = _load_json(EXAMS_PATH, {"exams": [], "active_exam_ids": []})
    if "exams" not in store:
        store["exams"] = []
    if store.get("active_exam_ids") is None:
        store["active_exam_ids"] = []
    return store


def save_exams_store(store: dict) -> None:
    _save_json(EXAMS_PATH, store)


def list_exams() -> list:
    return load_exams_store()["exams"]


def get_exam(exam_id: str) -> dict | None:
    for e in list_exams():
        if e["id"] == exam_id:
            return e
    return None


def get_active_exam_ids() -> list:
    return list(load_exams_store().get("active_exam_ids") or [])


def get_active_exams() -> list:
    active_ids = set(get_active_exam_ids())
    return [e for e in list_exams() if e["id"] in active_ids]


def is_exam_active(exam_id: str) -> bool:
    return exam_id in get_active_exam_ids()


def toggle_exam_active(exam_id: str) -> bool:
    store = load_exams_store()
    ids = store.setdefault("active_exam_ids", [])
    if exam_id in ids:
        ids.remove(exam_id)
        active = False
    else:
        ids.append(exam_id)
        active = True
    save_exams_store(store)
    return active


def create_exam(title: str, questions: list) -> dict:
    exam = {
        "id": str(uuid.uuid4()),
        "title": title.strip() or "Prova sem título",
        "questions": questions,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    store = load_exams_store()
    store["exams"].append(exam)
    if len(store["exams"]) == 1:
        store.setdefault("active_exam_ids", []).append(exam["id"])
    save_exams_store(store)
    return exam


def update_exam(exam_id: str, title: str, questions: list) -> bool:
    store = load_exams_store()
    for e in store["exams"]:
        if e["id"] == exam_id:
            e["title"] = title.strip() or e["title"]
            e["questions"] = questions
            e["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_exams_store(store)
            return True
    return False


def delete_exam(exam_id: str) -> None:
    store = load_exams_store()
    store["exams"] = [e for e in store["exams"] if e["id"] != exam_id]
    active_ids = store.setdefault("active_exam_ids", [])
    if exam_id in active_ids:
        active_ids.remove(exam_id)
    save_exams_store(store)
    submissions = [
        s for s in load_exam_submissions() if s.get("exam_id") != exam_id
    ]
    save_exam_submissions(submissions)


def load_exam_submissions() -> list:
    _ensure_data_dir()
    data = _load_json(EXAM_SUBMISSIONS_PATH, [])
    return data if isinstance(data, list) else []


def save_exam_submissions(submissions: list) -> None:
    _save_json(EXAM_SUBMISSIONS_PATH, submissions)


def submissions_for_exam(exam_id: str) -> list:
    return [s for s in load_exam_submissions() if s.get("exam_id") == exam_id]


def add_exam_submission(submission: dict) -> None:
    submissions = load_exam_submissions()
    submissions.append(submission)
    save_exam_submissions(submissions)


def update_exam_submission(
    submission_id: str, answers: list, summary: dict | None = None
) -> bool:
    submissions = load_exam_submissions()
    for s in submissions:
        if s["id"] == submission_id:
            s["answers"] = answers
            if summary is not None:
                s["summary"] = summary
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_exam_submissions(submissions)
            return True
    return False
