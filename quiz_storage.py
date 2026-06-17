"""Persistência local (evita conflito com o pacote PyPI 'storage')."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

BRASILIA_TZ = timezone(timedelta(hours=-3))

DATA_DIR = Path(__file__).parent / "data"
MATERIALS_PATH = DATA_DIR / "materials.json"
CONFIG_PATH = DATA_DIR / "config.json"
LEADERBOARD_PATH = DATA_DIR / "leaderboard.json"
STUDENTS_PATH = DATA_DIR / "students.json"
EXAMS_PATH = DATA_DIR / "exams.json"
EXAM_SUBMISSIONS_PATH = DATA_DIR / "exam_submissions.json"
EXAM_DRAFTS_PATH = DATA_DIR / "exam_drafts.json"

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
    created = create_materials_bulk([(title, questions)])
    return created[0]


def create_materials_bulk(entries: list[tuple[str, list]]) -> list[dict]:
    """Cria vários materiais em uma única gravação."""
    if not entries:
        return []

    store = load_materials_store()
    had_materials = bool(store.get("materials"))
    created: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for title, questions in entries:
        material = {
            "id": str(uuid.uuid4()),
            "title": title.strip() or "Material sem título",
            "questions": questions,
            "created_at": now,
        }
        store["materials"].append(material)
        created.append(material)

    if created and not had_materials:
        store.setdefault("active_material_ids", []).append(created[0]["id"])

    save_materials_store(store)
    return created


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


def append_leaderboard_entry(entry: dict) -> list:
    """Acrescenta um resultado lendo o arquivo na hora (evita sobrescrever
    resultados salvos por outras sessões com uma cópia desatualizada)."""
    board = load_leaderboard()
    board.append(entry)
    save_leaderboard(board)
    return board


def clear_leaderboard_for_material(material_id: str) -> list:
    board = [e for e in load_leaderboard() if e.get("material_id") != material_id]
    save_leaderboard(board)
    return board


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


def find_student_by_id(student_id: str) -> dict | None:
    for s in load_students():
        if s.get("id") == student_id:
            return s
    return None


def find_student_by_email(email: str | None) -> dict | None:
    key = (email or "").strip().lower()
    if not key:
        return None
    for s in load_students():
        if (s.get("email") or "").strip().lower() == key:
            return s
    return None


def resolve_roster_student_email(student: dict) -> str | None:
    """E-mail canônico do aluno na lista (students.json ou users.json)."""
    email = (student.get("email") or "").strip().lower()
    if email:
        return email
    from auth_users import find_user_for_roster_student

    user = find_user_for_roster_student(student)
    if user and user.get("email"):
        return user["email"].strip().lower()
    return None


def rename_student_records(
    *,
    old_name: str,
    new_name: str,
    student_email: str | None = None,
) -> dict:
    """Propaga o novo nome para quizzes, provas, lista e conta (prioriza e-mail)."""
    old_key = _normalize_name(old_name)
    new_name = " ".join(new_name.strip().split())
    email_key = (student_email or "").strip().lower() or None
    stats = {"quiz_updated": 0, "exam_updated": 0, "roster_updated": 0, "users_updated": 0}

    def _matches(name: str | None, email: str | None) -> bool:
        if email_key and (email or "").strip().lower() == email_key:
            return True
        return bool(old_key) and _normalize_name(name or "") == old_key

    board = load_leaderboard()
    for entry in board:
        if _matches(entry.get("name"), entry.get("student_email")):
            entry["name"] = new_name
            if email_key:
                entry["student_email"] = email_key
            stats["quiz_updated"] += 1
    if stats["quiz_updated"]:
        save_leaderboard(board)

    subs = load_exam_submissions()
    for sub in subs:
        if _matches(sub.get("student_name"), sub.get("student_email")):
            sub["student_name"] = new_name
            if email_key:
                sub["student_email"] = email_key
            stats["exam_updated"] += 1
    if stats["exam_updated"]:
        save_exam_submissions(subs)

    drafts = load_exam_drafts()
    draft_changed = False
    for draft in drafts:
        if _matches(draft.get("student_name"), draft.get("student_email")):
            draft["student_name"] = new_name
            if email_key:
                draft["student_email"] = email_key
            draft_changed = True
    if draft_changed:
        save_exam_drafts(drafts)

    students = load_students()
    roster_changed = False
    for student in students:
        if _matches(student.get("name"), student.get("email")):
            student["name"] = new_name
            if email_key:
                student["email"] = email_key
            stats["roster_updated"] += 1
            roster_changed = True
    if roster_changed:
        save_students(students)

    from auth_users import rename_student_user_account

    stats["users_updated"] = rename_student_user_account(
        old_name=old_name,
        new_name=new_name,
        student_email=email_key,
    )
    return stats


def add_student(name: str, email: str | None = None) -> tuple[dict | None, str | None]:
    name = " ".join(name.strip().split())
    email_key = (email or "").strip().lower() or None
    if not name:
        return None, "Informe o nome do aluno."
    if find_student_by_name(name):
        return None, "Já existe um aluno com este nome."
    if email_key and find_student_by_email(email_key):
        return None, "Já existe um aluno com este e-mail."
    student = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    students = load_students()
    students.append(student)
    save_students(students)
    return student, None


def update_student(student_id: str, name: str, email: str | None = None) -> str | None:
    name = " ".join(name.strip().split())
    if not name:
        return "Informe o nome do aluno."
    students = load_students()
    key = _normalize_name(name)
    email_key = (email or "").strip().lower() if email is not None else None
    for other in students:
        if other["id"] != student_id and _normalize_name(other["name"]) == key:
            return "Já existe outro aluno com este nome."
        if email_key and other["id"] != student_id and (other.get("email") or "").strip().lower() == email_key:
            return "Já existe outro aluno com este e-mail."
    for s in students:
        if s["id"] == student_id:
            old_name = s["name"]
            s["name"] = name
            if email is not None:
                s["email"] = email_key
            elif not s.get("email"):
                linked = resolve_roster_student_email(s)
                if linked:
                    s["email"] = linked
            s.pop("identifier", None)
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_students(students)
            if _normalize_name(old_name) != _normalize_name(name):
                rename_student_records(
                    old_name=old_name,
                    new_name=name,
                    student_email=s.get("email"),
                )
            return None
    return "Aluno não encontrado."


def purge_student_results(student_name: str, student_email: str | None = None) -> dict:
    """Remove todos os resultados (quizzes e provas) de um aluno.

    Usado quando o aluno é excluído, para não deixar dados órfãos.
    """
    name_key = _normalize_name(student_name)
    email_key = (student_email or "").strip().lower()

    def _is_target(name: str | None, email: str | None) -> bool:
        if name_key and _normalize_name(name or "") == name_key:
            return True
        return bool(email_key) and (email or "").strip().lower() == email_key

    board = load_leaderboard()
    kept_board = [
        e for e in board if not _is_target(e.get("name"), e.get("student_email"))
    ]
    quiz_removed = len(board) - len(kept_board)
    if quiz_removed:
        save_leaderboard(kept_board)

    subs = load_exam_submissions()
    kept_subs = [
        s for s in subs if not _is_target(s.get("student_name"), s.get("student_email"))
    ]
    exam_removed = len(subs) - len(kept_subs)
    if exam_removed:
        save_exam_submissions(kept_subs)

    drafts = load_exam_drafts()
    kept_drafts = [
        d for d in drafts if not _is_target(d.get("student_name"), d.get("student_email"))
    ]
    draft_removed = len(drafts) - len(kept_drafts)
    if draft_removed:
        save_exam_drafts(kept_drafts)

    return {
        "quiz_removed": quiz_removed,
        "exam_removed": exam_removed,
        "draft_removed": draft_removed,
    }


def delete_student(student_id: str) -> None:
    students = load_students()
    target = next((s for s in students if s["id"] == student_id), None)
    save_students([s for s in students if s["id"] != student_id])
    if target:
        purge_student_results(target["name"], resolve_roster_student_email(target))


def student_quiz_stats(student_name: str, student_email: str | None = None) -> dict:
    name_key = _normalize_name(student_name)
    email_key = (student_email or "").strip().lower()
    entries = [
        e
        for e in load_leaderboard()
        if (email_key and (e.get("student_email") or "").strip().lower() == email_key)
        or _normalize_name(e.get("name", "")) == name_key
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
    from pdf_parser import normalize_exam_questions

    for e in list_exams():
        if e["id"] == exam_id:
            questions = normalize_exam_questions(e.get("questions") or [])
            if questions != e.get("questions"):
                e = {**e, "questions": questions}
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


def parse_deadline_date_br(text: str) -> date | None:
    """Interpreta data no formato DD/MM/AAAA (ou DD/MM/AA)."""
    clean = (text or "").strip()
    if not clean:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    return None


def parse_deadline_time_br(text: str) -> time | None:
    """Interpreta hora no formato HH:MM (24h)."""
    clean = (text or "").strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", clean)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return time(hour, minute)
    return None


def format_deadline_br(value: str | datetime | None) -> str | None:
    """Formata prazo para exibição em Brasília (DD/MM/AAAA HH:MM)."""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = _parse_iso_datetime(value if isinstance(value, str) else None)
    if not dt:
        return None
    local = dt.astimezone(BRASILIA_TZ)
    return local.strftime("%d/%m/%Y %H:%M")


def today_brasilia() -> date:
    return datetime.now(BRASILIA_TZ).date()


def exam_deadline_date_value(exam: dict) -> date | None:
    dt = exam_deadline_dt(exam)
    if not dt:
        return None
    return dt.astimezone(BRASILIA_TZ).date()


def exam_deadline_time_text(exam: dict) -> str:
    dt = exam_deadline_dt(exam)
    if not dt:
        return "23:59"
    return dt.astimezone(BRASILIA_TZ).strftime("%H:%M")


def exam_deadline_parts(exam: dict) -> tuple[str, str]:
    """Retorna (data, hora) do prazo em Brasília para preencher formulários."""
    d = exam_deadline_date_value(exam)
    return (d.strftime("%d/%m/%Y") if d else ""), exam_deadline_time_text(exam)


def build_deadline_from_inputs(
    deadline_date: date | None, time_text: str
) -> tuple[str | None, str | None]:
    """Valida data (calendário) + HH:MM digitado (Brasília)."""
    if not deadline_date:
        return None, "Selecione a data limite."
    deadline_time = parse_deadline_time_br(time_text)
    if not deadline_time:
        return None, "Hora inválida. Digite no formato HH:MM (ex.: 22:00)."
    return build_deadline_iso(deadline_date, deadline_time), None


def build_deadline_from_br_strings(
    date_text: str, time_text: str
) -> tuple[str | None, str | None]:
    """Valida DD/MM/AAAA + HH:MM (Brasília) e retorna (ISO UTC, mensagem de erro)."""
    deadline_date = parse_deadline_date_br(date_text)
    if not deadline_date:
        return None, "Data inválida. Use o formato DD/MM/AAAA (ex.: 15/06/2026)."
    deadline_time = parse_deadline_time_br(time_text)
    if not deadline_time:
        return None, "Hora inválida. Digite no formato HH:MM (ex.: 22:00)."
    return build_deadline_iso(deadline_date, deadline_time), None


def build_deadline_iso(deadline_date, deadline_time=None) -> str | None:
    """Combina data/hora informadas pelo professor (Brasília UTC-3) em ISO UTC."""
    if not deadline_date:
        return None
    t = deadline_time or time(23, 59)
    dt = datetime.combine(deadline_date, t, tzinfo=BRASILIA_TZ)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def exam_deadline_dt(exam: dict) -> datetime | None:
    return _parse_iso_datetime(exam.get("deadline_at"))


def exam_is_past_deadline(exam: dict, *, now: datetime | None = None) -> bool:
    deadline = exam_deadline_dt(exam)
    if not deadline:
        return False
    ref = now or datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return ref > deadline


def exam_deadline_label(exam: dict) -> str | None:
    return format_deadline_br(exam.get("deadline_at"))


def _student_submission_key(sub: dict) -> str:
    email = (sub.get("student_email") or "").strip().lower()
    if email:
        return f"email:{email}"
    return f"name:{_normalize_name(sub.get('student_name', ''))}"


def exam_submissions_for_student(
    student_name: str, exam_id: str, student_email: str | None = None
) -> list[dict]:
    """Todas as tentativas do aluno nesta prova, em ordem de envio."""
    name_key = _normalize_name(student_name)
    email_key = (student_email or "").strip().lower()
    matches = []
    for s in load_exam_submissions():
        if s.get("exam_id") != exam_id:
            continue
        if name_key and _normalize_name(s.get("student_name", "")) == name_key:
            matches.append(s)
        elif email_key and (s.get("student_email") or "").strip().lower() == email_key:
            matches.append(s)
    matches.sort(key=lambda s: s.get("submitted_at") or "")
    return matches


def student_submission_for_exam(
    student_name: str, exam_id: str, student_email: str | None = None
) -> dict | None:
    attempts = exam_submissions_for_student(student_name, exam_id, student_email)
    return attempts[-1] if attempts else None


def _submission_total_points(sub: dict) -> float:
    summary = sub.get("summary") or {}
    if summary.get("total_points") is not None:
        return float(summary["total_points"])
    return sum(float(a.get("points", 0)) for a in sub.get("answers") or [])


def best_submissions_for_exam(exam_id: str) -> list[dict]:
    """Uma entrada por aluno — a tentativa com maior nota."""
    grouped: dict[str, list[dict]] = {}
    for sub in submissions_for_exam(exam_id):
        grouped.setdefault(_student_submission_key(sub), []).append(sub)
    return [max(subs, key=_submission_total_points) for subs in grouped.values()]


def repair_exams_questions() -> int:
    """Atualiza questões salvas para o formato com justificativa, quando aplicável."""
    from pdf_parser import merge_exam_questions, normalize_exam_questions

    store = load_exams_store()
    fixed_count = 0
    for exam in store.get("exams") or []:
        original = exam.get("questions") or []
        normalized = normalize_exam_questions(original)
        if normalized != original:
            exam["questions"] = normalized
            fixed_count += 1
    if fixed_count:
        save_exams_store(store)
    fixed_count += rehydrate_exam_questions_from_store()
    return fixed_count


def rehydrate_exam_questions_from_store() -> int:
    """Copia gabaritos de justificativa entre provas com o mesmo título."""
    from pdf_parser import _exam_question_richness, merge_exam_questions

    store = load_exams_store()
    exams = store.get("exams") or []
    by_title: dict[str, list[dict]] = {}
    for exam in exams:
        title_key = (exam.get("title") or "").strip().lower()
        if title_key:
            by_title.setdefault(title_key, []).append(exam)

    fixed = 0
    for group in by_title.values():
        if len(group) < 2:
            continue
        richest = max(group, key=lambda e: _exam_question_richness(e.get("questions", [])))
        best_questions = richest.get("questions") or []
        if not best_questions:
            continue
        for exam in group:
            if exam["id"] == richest["id"]:
                continue
            merged = merge_exam_questions(exam.get("questions", []), best_questions)
            if merged != exam.get("questions"):
                exam["questions"] = merged
                fixed += 1
    if fixed:
        save_exams_store(store)
    return fixed


def _submission_justify_richness(submission: dict) -> int:
    return sum(
        1
        for ans in submission.get("answers") or []
        if (ans.get("justify_text") or "").strip()
    )


def merge_exam_submission(existing: dict, incoming: dict) -> dict:
    """Prefere o envio com mais justificativas e respostas completas."""
    if _submission_justify_richness(incoming) >= _submission_justify_richness(existing):
        return {**existing, **incoming}
    return existing


def create_exam(title: str, questions: list, deadline_at: str | None = None) -> dict:
    created = create_exams_bulk([(title, questions)], deadline_at=deadline_at)
    return created[0]


def create_exams_bulk(
    entries: list[tuple[str, list]],
    *,
    deadline_at: str | None = None,
) -> list[dict]:
    """Cria várias provas em uma única gravação (evita perder envios no lote)."""
    from pdf_parser import normalize_exam_questions

    if not entries:
        return []

    store = load_exams_store()
    had_exams = bool(store.get("exams"))
    created: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for title, questions in entries:
        exam = {
            "id": str(uuid.uuid4()),
            "title": title.strip() or "Prova sem título",
            "questions": normalize_exam_questions(questions),
            "created_at": now,
            "deadline_at": deadline_at,
        }
        store["exams"].append(exam)
        created.append(exam)

    if created and not had_exams:
        store.setdefault("active_exam_ids", []).append(created[0]["id"])

    save_exams_store(store)
    return created


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


def update_exam_deadline(exam_id: str, deadline_at: str | None) -> bool:
    store = load_exams_store()
    for e in store["exams"]:
        if e["id"] == exam_id:
            if deadline_at:
                e["deadline_at"] = deadline_at
            else:
                e.pop("deadline_at", None)
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
    delete_exam_drafts_for_exam(exam_id)


def load_exam_submissions() -> list:
    _ensure_data_dir()
    data = _load_json(EXAM_SUBMISSIONS_PATH, [])
    return data if isinstance(data, list) else []


def save_exam_submissions(submissions: list) -> None:
    _save_json(EXAM_SUBMISSIONS_PATH, submissions)


def resolve_exam_id_for_submission(
    exam_id: str | None,
    exam_title: str | None = None,
) -> tuple[str | None, str | None]:
    """Associa um envio à prova atual (por ID ou título)."""
    exams = list_exams()
    if not exams:
        return exam_id, exam_title

    known_ids = {e["id"] for e in exams}
    if exam_id and exam_id in known_ids:
        exam = get_exam(exam_id)
        title = exam_title or (exam.get("title") if exam else None)
        return exam_id, title

    title_key = (exam_title or "").strip().lower()
    if title_key:
        for exam in exams:
            if exam["title"].strip().lower() == title_key:
                return exam["id"], exam["title"]

    if len(exams) == 1:
        return exams[0]["id"], exams[0]["title"]

    return exam_id, exam_title


def repair_orphan_exam_submissions() -> int:
    """Reconecta envios importados cujo exam_id antigo não existe mais."""
    exams = list_exams()
    if not exams:
        return 0

    known_ids = {e["id"] for e in exams}
    fixed = 0
    subs = load_exam_submissions()
    changed = False
    for sub in subs:
        current_id = sub.get("exam_id")
        if current_id in known_ids:
            continue
        new_id, title = resolve_exam_id_for_submission(current_id, sub.get("exam_title"))
        if not new_id or new_id not in known_ids:
            continue
        sub["exam_id"] = new_id
        if title:
            sub["exam_title"] = title
        changed = True
        fixed += 1
    if changed:
        save_exam_submissions(subs)
    return fixed


def count_orphan_exam_submissions() -> int:
    known_ids = {e["id"] for e in list_exams()}
    return sum(
        1
        for s in load_exam_submissions()
        if s.get("exam_id") not in known_ids
    )


def submissions_for_exam(exam_id: str) -> list:
    exam = get_exam(exam_id)
    if not exam:
        return []

    title_key = exam["title"].strip().lower()
    known_ids = {e["id"] for e in list_exams()}
    matched: list[dict] = []
    seen_ids: set[str] = set()
    for sub in load_exam_submissions():
        sub_id = sub.get("id")
        if sub_id and sub_id in seen_ids:
            continue
        if sub.get("exam_id") == exam_id:
            matched.append(sub)
            if sub_id:
                seen_ids.add(sub_id)
            continue
        sub_title = (sub.get("exam_title") or "").strip().lower()
        old_id = sub.get("exam_id")
        if sub_title == title_key and old_id not in known_ids:
            matched.append(sub)
            if sub_id:
                seen_ids.add(sub_id)
    return matched


def add_exam_submission(submission: dict) -> None:
    submissions = load_exam_submissions()
    submissions.append(submission)
    save_exam_submissions(submissions)


def load_exam_drafts() -> list:
    _ensure_data_dir()
    data = _load_json(EXAM_DRAFTS_PATH, [])
    return data if isinstance(data, list) else []


def save_exam_drafts(drafts: list) -> None:
    _save_json(EXAM_DRAFTS_PATH, drafts)


def _draft_identity_matches(
    draft: dict,
    student_name: str,
    student_email: str | None,
) -> bool:
    name_key = _normalize_name(student_name)
    email_key = (student_email or "").strip().lower()
    draft_email = (draft.get("student_email") or "").strip().lower()
    if email_key and draft_email == email_key:
        return True
    return bool(name_key) and _normalize_name(draft.get("student_name", "")) == name_key


def find_exam_draft(
    student_name: str,
    student_email: str | None,
    exam_id: str,
    attempt: int,
) -> dict | None:
    for draft in load_exam_drafts():
        if draft.get("exam_id") != exam_id:
            continue
        if int(draft.get("attempt") or 1) != int(attempt):
            continue
        if _draft_identity_matches(draft, student_name, student_email):
            return draft
    return None


def upsert_exam_draft(
    *,
    student_name: str,
    student_email: str | None,
    exam_id: str,
    attempt: int,
    answers: dict,
    question_count: int,
) -> dict:
    """Grava ou atualiza rascunho da prova (respostas parciais)."""
    now = datetime.now(timezone.utc).isoformat()
    email_key = (student_email or "").strip().lower() or None
    drafts = load_exam_drafts()
    existing = None
    for draft in drafts:
        if (
            draft.get("exam_id") == exam_id
            and int(draft.get("attempt") or 1) == int(attempt)
            and _draft_identity_matches(draft, student_name, student_email)
        ):
            existing = draft
            break

    if existing:
        existing["answers"] = answers
        existing["question_count"] = question_count
        existing["updated_at"] = now
        save_exam_drafts(drafts)
        return existing

    created = {
        "id": str(uuid.uuid4()),
        "exam_id": exam_id,
        "student_name": student_name.strip(),
        "student_email": email_key,
        "attempt": int(attempt),
        "answers": answers,
        "question_count": question_count,
        "started_at": now,
        "updated_at": now,
    }
    drafts.append(created)
    save_exam_drafts(drafts)
    return created


def delete_exam_draft(
    student_name: str,
    student_email: str | None,
    exam_id: str,
    attempt: int | None = None,
) -> int:
    drafts = load_exam_drafts()
    kept = []
    removed = 0
    for draft in drafts:
        if draft.get("exam_id") != exam_id:
            kept.append(draft)
            continue
        if attempt is not None and int(draft.get("attempt") or 1) != int(attempt):
            kept.append(draft)
            continue
        if _draft_identity_matches(draft, student_name, student_email):
            removed += 1
            continue
        kept.append(draft)
    if removed:
        save_exam_drafts(kept)
    return removed


def delete_exam_drafts_for_exam(exam_id: str) -> int:
    drafts = load_exam_drafts()
    kept = [d for d in drafts if d.get("exam_id") != exam_id]
    removed = len(drafts) - len(kept)
    if removed:
        save_exam_drafts(kept)
    return removed


def update_exam_submission(
    submission_id: str,
    answers: list,
    summary: dict | None = None,
    *,
    correction_released: bool | None = None,
) -> bool:
    submissions = load_exam_submissions()
    for s in submissions:
        if s["id"] == submission_id:
            s["answers"] = answers
            if summary is not None:
                s["summary"] = summary
            if correction_released is not None:
                s["correction_released"] = correction_released
                if correction_released:
                    s["correction_released_at"] = datetime.now(timezone.utc).isoformat()
                else:
                    s.pop("correction_released_at", None)
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_exam_submissions(submissions)
            return True
    return False


def set_exam_correction_released(submission_id: str, released: bool = True) -> bool:
    submissions = load_exam_submissions()
    for s in submissions:
        if s["id"] == submission_id:
            s["correction_released"] = released
            if released:
                s["correction_released_at"] = datetime.now(timezone.utc).isoformat()
            else:
                s.pop("correction_released_at", None)
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_exam_submissions(submissions)
            return True
    return False


def exam_correction_released(submission: dict | None) -> bool:
    return bool((submission or {}).get("correction_released"))
