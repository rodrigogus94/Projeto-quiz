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
        },
    )
    if "professor_password_hash" not in config:
        config["professor_password_hash"] = hash_password(DEFAULT_PASSWORD)
    if "professor_username" not in config:
        config["professor_username"] = DEFAULT_USERNAME
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


def load_materials_store() -> dict:
    _ensure_data_dir()
    store = _load_json(MATERIALS_PATH, {"materials": [], "active_material_id": None})
    if "materials" not in store:
        store["materials"] = []
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


def get_active_material() -> dict | None:
    store = load_materials_store()
    active_id = store.get("active_material_id")
    if not active_id:
        return None
    return get_material(active_id)


def set_active_material(material_id: str) -> None:
    store = load_materials_store()
    store["active_material_id"] = material_id
    save_materials_store(store)


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
        store["active_material_id"] = material["id"]
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
    if store.get("active_material_id") == material_id:
        store["active_material_id"] = (
            store["materials"][0]["id"] if store["materials"] else None
        )
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


# ---------------------------
# Alunos cadastrados
# ---------------------------
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
    """Resumo de tentativas do aluno em todos os materiais."""
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
