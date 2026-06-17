"""Parser de PDF para quiz (múltipla escolha) e provas (com gabarito e justificativas)."""
from __future__ import annotations

import re

PERGUNTA_HEADER = re.compile(r"Pergunta\s+(\d+):\s*", re.IGNORECASE)
QUESTAO_HEADER_MD = re.compile(r"^#{0,3}\s*Questão\s+(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
OPTION_LINE_MD = re.compile(r"^([A-D])\)\s*(.+?)\s*$", re.MULTILINE)
RESPOSTA_CORRETA_MD = re.compile(r"Resposta\s+Correta\s*:\s*([A-D])", re.IGNORECASE)
ALT_START = re.compile(r"Alternativa\s+[A-D]\s*[\(:]", re.IGNORECASE)
ALT_PATTERN = re.compile(
    r"Alternativa\s+([A-D])\s*(?:\([^)]*\))?\s*:?\s*(.*?)(?=Alternativa\s+[A-D]|Gabarito\s*:|Resposta\s+esperada\s*:|Pergunta\s+\d+:|$)",
    re.DOTALL | re.IGNORECASE,
)
JUSTIFY_MARKER = re.compile(
    r"\(JUSTIFICATIVA\)|\(DISSERTATIVA\)|\(DISCURSIVA\)|"
    r"Tipo\s*:\s*(Justificativa|Dissertativa|Discursiva)",
    re.IGNORECASE,
)
GABARITO_LINE = re.compile(
    r"(?:Gabarito|Resposta\s+esperada)\s*:\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)
CORRECTA_MARK = re.compile(r"\(CORRETA\)", re.IGNORECASE)

# Formato Kahoot: "## Pergunta 1" / "Pergunta 1" (sem dois-pontos), campos em
# bullets ("● Pergunta:", "* **Alternativas:**") e correta via "[X]" ou
# "(Alternativa Correta)".
KAHOOT_HEADER = re.compile(r"^#{0,6}\s*Pergunta\s+(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
KAHOOT_FIELD = re.compile(
    r"^[*\-●○•]\s*\*{0,2}(Pergunta|Tempo\s+limite|Alternativas|Justificativa)\s*:?\*{0,2}\s*(.*)$",
    re.IGNORECASE,
)
KAHOOT_OPTION = re.compile(
    r"^(?:[*\-●○•]\s*)?(?:\[\s*([xX])?\s*\]\s*)?([A-D])\)\s*(.*)$"
)
ALT_CORRETA_MARK = re.compile(r"\(\s*Alternativa\s+Correta\s*\)", re.IGNORECASE)

# Formato UC2 (Atividade avaliativa): Questão N, a) b) c) d), Justificativa:,
# gabarito em tabela GABARITO OFICIAL no final do arquivo.
UC2_QUESTAO_HEADER = re.compile(
    r"^#{0,6}\s*Quest[aã]o\s+(\d+)\s*:?\s*$", re.MULTILINE | re.IGNORECASE
)
UC2_OPTION_LINE = re.compile(
    r"^(?:[*\-●○•]\s*)?([A-Da-d])\)\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)
UC2_JUSTIFICATIVA_LINE = re.compile(
    r"^(?:\*\*)?Justificativa(?:\*\*)?\s*:\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)
UC2_GABARITO_SECTION = re.compile(r"GABARITO(?:\s+OFICIAL)?", re.IGNORECASE)
UC2_GABARITO_ROW = re.compile(
    r"(?:^|\n)\s*(\d{1,2})\s+([A-Da-d])\b"
)
MD_GABARITO_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([A-Da-d])\s*\|",
    re.MULTILINE | re.IGNORECASE,
)


def _warn(warnings: list | None, msg: str):
    if warnings is not None:
        warnings.append(msg)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_display_markers(text: str) -> str:
    text = JUSTIFY_MARKER.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_markdown_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def _parse_markdown_choice_block(block: str) -> dict | None:
    correct_match = RESPOSTA_CORRETA_MD.search(block)
    if not correct_match:
        return None

    correct = correct_match.group(1).upper()
    option_matches = list(OPTION_LINE_MD.finditer(block))
    if len(option_matches) < 4:
        return None

    first_opt = option_matches[0]
    question_raw = block[: first_opt.start()].strip()
    question_text = _clean_text(_strip_markdown_inline(question_raw))
    if not question_text:
        return None

    options = [
        _clean_text(_strip_markdown_inline(m.group(2)))
        for m in option_matches[:4]
    ]
    if len(options) != 4 or any(not o for o in options) or correct not in "ABCD":
        return None

    return {
        "question": question_text,
        "options": options,
        "correct": correct,
    }


def _parse_markdown_quiz_questions(full_text: str, warnings: list | None = None) -> list:
    matches = list(QUESTAO_HEADER_MD.finditer(full_text))
    if not matches:
        return []

    questions = []
    for i, match in enumerate(matches):
        num = match.group(1)
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[match.end() : block_end]

        parsed = _parse_markdown_choice_block(block)
        if parsed:
            questions.append(parsed)
        else:
            _warn(
                warnings,
                f"Questão {num} ignorada: enunciado, 4 opções (A-D) ou Resposta Correta incompletos.",
            )

    return questions


def _extract_markdown_justify_key(block: str) -> str:
    match = re.search(
        r"(?:\*\*)?Justificativa(?:\*\*)?\s*:\s*(.+?)(?=\n\s*#{1,6}\s*Quest|\Z)",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    text = match.group(1).strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return _clean_text(text)


def _parse_markdown_composite_block(block: str) -> dict | None:
    """Markdown com 4 opções, Resposta Correta e bloco Justificativa: (formato UC2)."""
    parsed = _parse_markdown_choice_block(block)
    if not parsed:
        return None
    answer_key = _extract_markdown_justify_key(block)
    if not answer_key:
        return None
    return {
        "type": "choice_with_justify",
        "question": parsed["question"],
        "options": parsed["options"],
        "correct": parsed["correct"],
        "answer_key": answer_key,
    }


def _parse_markdown_exam_questions(full_text: str, warnings: list | None = None) -> list:
    matches = list(QUESTAO_HEADER_MD.finditer(full_text))
    if not matches:
        return []

    questions = []
    for i, match in enumerate(matches):
        num = match.group(1)
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[match.end() : block_end]

        parsed = _parse_markdown_composite_block(block)
        if not parsed:
            parsed = _parse_markdown_choice_block(block)
            if parsed:
                parsed = {
                    "type": "choice",
                    "question": parsed["question"],
                    "options": parsed["options"],
                    "correct": parsed["correct"],
                }
        if parsed:
            questions.append(parsed)
        else:
            _warn(
                warnings,
                f"Questão {num} ignorada: enunciado, 4 opções (A-D) ou Resposta Correta incompletos.",
            )

    return questions


def _parse_kahoot_question_block(block: str) -> dict | None:
    question_parts: list[str] = []
    options: list[list[str]] = []
    justify_parts: list[str] = []
    correct: str | None = None
    current: str | None = None

    for raw in block.splitlines():
        line = raw.strip()
        if not line or set(line) <= {"-"}:
            continue

        field_match = KAHOOT_FIELD.match(line)
        if field_match:
            field = field_match.group(1).lower()
            rest = field_match.group(2).strip()
            if field == "pergunta":
                current = "question"
                if rest:
                    question_parts.append(rest)
            elif field == "justificativa":
                current = "justify"
                if rest:
                    justify_parts.append(_strip_markdown_inline(rest))
            else:
                # "Alternativas:" abre a lista; "Tempo limite" é ignorado.
                current = None
            continue

        opt_match = KAHOOT_OPTION.match(line)
        if opt_match:
            checked, letter, text = opt_match.groups()
            letter = letter.upper()
            is_correct = bool(checked) or bool(ALT_CORRETA_MARK.search(text))
            text = ALT_CORRETA_MARK.sub("", text).strip()
            options.append([letter, text])
            if is_correct:
                correct = letter
            current = "option"
            continue

        # Linha de continuação (texto quebrado em várias linhas, comum em PDF).
        if current == "question":
            question_parts.append(line)
        elif current == "justify":
            justify_parts.append(_strip_markdown_inline(line))
        elif current == "option" and options:
            if ALT_CORRETA_MARK.search(line):
                correct = options[-1][0]
            extra = ALT_CORRETA_MARK.sub("", line).strip()
            if extra:
                options[-1][1] = f"{options[-1][1]} {extra}".strip()

    question_text = _clean_text(_strip_markdown_inline(" ".join(question_parts)))
    opts = [_clean_text(_strip_markdown_inline(text)) for _, text in options[:4]]
    letters = [letter for letter, _ in options[:4]]

    if (
        not question_text
        or len(opts) != 4
        or any(not o for o in opts)
        or letters != ["A", "B", "C", "D"]
        or correct not in "ABCD"
    ):
        return None

    result: dict = {"question": question_text, "options": opts, "correct": correct}
    if justify_parts:
        result["answer_key"] = _clean_text(" ".join(justify_parts))
    return result


def _parse_kahoot_exam_questions(full_text: str, warnings: list | None = None) -> list:
    """Pergunta N estilo Kahoot/Markdown com [X], Justificativa e gabarito em tabela."""
    matches = list(KAHOOT_HEADER.finditer(full_text))
    if not matches:
        return []

    gabarito = _parse_uc2_gabarito_table(full_text)
    questions = []
    for i, match in enumerate(matches):
        num = match.group(1)
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[match.end() : block_end]
        if UC2_GABARITO_SECTION.search(block):
            block = UC2_GABARITO_SECTION.split(block, maxsplit=1)[0]

        parsed = _parse_kahoot_question_block(block)
        if not parsed:
            _warn(
                warnings,
                f"Pergunta {num} ignorada: enunciado, 4 opções (A-D) ou marcação "
                "da correta ([X] / (Alternativa Correta)) incompletos.",
            )
            continue

        q = {
            "question": parsed["question"],
            "options": parsed["options"],
            "correct": gabarito.get(num, parsed["correct"]),
        }
        answer_key = parsed.get("answer_key", "")
        if answer_key:
            q["type"] = "choice_with_justify"
            q["answer_key"] = answer_key
        else:
            q["type"] = "choice"
        questions.append(q)

    return questions


def _parse_kahoot_questions(full_text: str, warnings: list | None = None) -> list:
    matches = list(KAHOOT_HEADER.finditer(full_text))
    if not matches:
        return []

    questions = []
    for i, match in enumerate(matches):
        num = match.group(1)
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[match.end() : block_end]

        parsed = _parse_kahoot_question_block(block)
        if parsed:
            questions.append(parsed)
        else:
            _warn(
                warnings,
                f"Pergunta {num} ignorada: enunciado, 4 opções (A-D) ou marcação "
                "da correta ([X] / (Alternativa Correta)) incompletos.",
            )

    return questions


def _extract_gabarito(block: str) -> str:
    match = GABARITO_LINE.search(block)
    if not match:
        return ""
    gabarito = match.group(1).strip()
    gabarito = re.split(r"Pergunta\s+\d+:", gabarito, maxsplit=1, flags=re.IGNORECASE)[0]
    return _clean_text(gabarito)


def _parse_choice_block(block: str, header_end: int) -> dict | None:
    first_alt = ALT_START.search(block, header_end)
    if not first_alt:
        return None

    question_text = _strip_display_markers(block[header_end : first_alt.start()])
    opts_in_block = ALT_PATTERN.findall(block)
    options = []
    correct_letter = None

    for letter, opt_text in opts_in_block[:4]:
        is_correct = bool(CORRECTA_MARK.search(opt_text))
        opt_text = CORRECTA_MARK.sub("", opt_text).strip()
        opt_text = _clean_text(opt_text)
        options.append(opt_text)
        if is_correct:
            correct_letter = letter

    if correct_letter and len(options) == 4 and question_text:
        return {
            "type": "choice",
            "question": question_text,
            "options": options,
            "correct": correct_letter,
        }
    return None


def _parse_justify_block(block: str, header_end: int) -> dict | None:
    first_alt = ALT_START.search(block, header_end)
    gabarito = _extract_gabarito(block)

    if first_alt:
        question_text = _strip_display_markers(block[header_end : first_alt.start()])
    else:
        body = block[header_end:]
        body = GABARITO_LINE.sub("", body)
        question_text = _strip_display_markers(body)

    if not question_text:
        return None

    return {
        "type": "justify",
        "question": question_text,
        "answer_key": gabarito,
    }


def _is_justify_block(block: str, header_end: int) -> bool:
    header_zone = block[header_end : header_end + 200]
    if JUSTIFY_MARKER.search(block):
        return True
    if GABARITO_LINE.search(block) and not _parse_choice_block(block, header_end):
        return True
    if "justifique" in header_zone.lower() and not ALT_START.search(block, header_end):
        return True
    return False


def _parse_uc2_gabarito_table(full_text: str) -> dict[str, str]:
    """Extrai letras corretas da tabela de gabarito ({num: letra})."""
    answers: dict[str, str] = {}
    section = UC2_GABARITO_SECTION.search(full_text)
    tail = full_text[section.end() :] if section else full_text[-2500:]
    for num, letter in UC2_GABARITO_ROW.findall(tail):
        answers[num] = letter.upper()
    for num, letter in MD_GABARITO_ROW.findall(tail):
        answers.setdefault(num, letter.upper())
    return answers


def _parse_uc2_question_block(block: str, correct_letter: str | None) -> dict | None:
    """Bloco de uma questão UC2: enunciado + 4 opções + texto de justificativa."""
    question_lines: list[str] = []
    options: list[str | None] = [None, None, None, None]
    justify_parts: list[str] = []
    mode = "question"

    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("--") or line.startswith(">"):
            continue
        if line.startswith("#"):
            continue

        opt_match = UC2_OPTION_LINE.match(line)
        if opt_match:
            idx = ord(opt_match.group(1).lower()) - ord("a")
            options[idx] = _clean_text(opt_match.group(2))
            mode = "options"
            continue

        just_match = UC2_JUSTIFICATIVA_LINE.match(line)
        if just_match:
            mode = "justify"
            rest = just_match.group(1).strip()
            if rest:
                justify_parts.append(rest)
            continue

        if mode == "question":
            question_lines.append(line)
        elif mode == "justify":
            if UC2_GABARITO_SECTION.search(line):
                break
            justify_parts.append(line)

    clean_options: list[str] = []
    inferred_correct: str | None = None
    for j, opt in enumerate(options):
        if opt is None:
            continue
        text = opt
        if CORRECTA_MARK.search(text):
            inferred_correct = chr(ord("A") + j)
            text = CORRECTA_MARK.sub("", text).strip()
        clean_options.append(_clean_text(text))

    question = _clean_text(" ".join(question_lines))
    if len(clean_options) != 4 or any(not o for o in clean_options) or not question:
        return None

    letter = (correct_letter or inferred_correct or "").upper()
    if letter not in "ABCD":
        return None

    return {
        "type": "choice_with_justify",
        "question": question,
        "options": clean_options,
        "correct": letter,
        "answer_key": _clean_text(" ".join(justify_parts)),
    }


def _parse_uc2_exam_questions(full_text: str, warnings: list | None = None) -> list:
    matches = list(UC2_QUESTAO_HEADER.finditer(full_text))
    if not matches:
        return []

    gabarito = _parse_uc2_gabarito_table(full_text)
    questions = []
    for i, match in enumerate(matches):
        num = match.group(1)
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[match.end() : block_end]
        if UC2_GABARITO_SECTION.search(block):
            block = UC2_GABARITO_SECTION.split(block, maxsplit=1)[0]

        parsed = _parse_uc2_question_block(block, gabarito.get(num))
        if parsed:
            questions.append(parsed)
        else:
            _warn(
                warnings,
                f"Questão {num} ignorada: enunciado, 4 opções (a-d), justificativa "
                "ou gabarito oficial incompletos.",
            )
    return questions


def parse_exam_from_text(full_text: str, warnings: list | None = None) -> list:
    """
    Extrai questões de prova com gabarito.
    Tipos: choice, justify e choice_with_justify (formato UC2).
    """
    # Formato Kahoot/Markdown (## Pergunta N + [X] + Justificativa).
    if KAHOOT_HEADER.search(full_text):
        kahoot_exam = _parse_kahoot_exam_questions(full_text, warnings)
        if kahoot_exam:
            return normalize_exam_questions(kahoot_exam)

    # Formato UC2 (Questão N + a-d + Justificativa + GABARITO OFICIAL).
    uc2_signals = UC2_QUESTAO_HEADER.search(full_text) and (
        UC2_GABARITO_SECTION.search(full_text) or "Justificativa:" in full_text
    )
    if uc2_signals:
        uc2 = _parse_uc2_exam_questions(full_text, warnings)
        if uc2:
            return normalize_exam_questions(uc2)

    matches = list(PERGUNTA_HEADER.finditer(full_text))
    if not matches:
        kahoot_exam = _parse_kahoot_exam_questions(full_text, warnings)
        if kahoot_exam:
            return normalize_exam_questions(kahoot_exam)
        kahoot = _parse_kahoot_questions(full_text, warnings)
        if kahoot:
            return [{"type": "choice", **q} for q in kahoot]
        md = _parse_markdown_exam_questions(full_text, warnings)
        if md:
            return md
        return _parse_uc2_exam_questions(full_text, warnings)

    gabarito_table = _parse_uc2_gabarito_table(full_text)
    questions = []

    for i, match in enumerate(matches):
        num = match.group(1)
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[match.start() : block_end]
        header_end = match.end() - match.start()
        body = block[header_end:]

        parsed = None
        if UC2_OPTION_LINE.search(body) or UC2_JUSTIFICATIVA_LINE.search(body):
            parsed = _parse_uc2_question_block(body, gabarito_table.get(num))
        if not parsed and _is_justify_block(block, header_end):
            parsed = _parse_justify_block(block, header_end)
        if not parsed:
            parsed = _parse_choice_block(block, header_end)
            if not parsed and GABARITO_LINE.search(block):
                parsed = _parse_justify_block(block, header_end)

        if parsed:
            questions.append(parsed)
        else:
            _warn(
                warnings,
                f"Pergunta {num} ignorada: não foi possível identificar o tipo "
                "(múltipla escolha com 4 alternativas e CORRETA, ou justificativa com gabarito).",
            )

    return normalize_exam_questions(questions)


def parse_questions_from_text(full_text: str, warnings: list | None = None) -> list:
    """Parser de quiz — múltipla escolha (formato PDF ou Markdown)."""
    matches = list(PERGUNTA_HEADER.finditer(full_text))
    if matches:
        questions = []
        for i, match in enumerate(matches):
            num = match.group(1)
            block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            block = full_text[match.start() : block_end]
            header_end = match.end() - match.start()

            parsed = _parse_choice_block(block, header_end)
            if parsed:
                questions.append(
                    {
                        "question": parsed["question"],
                        "options": parsed["options"],
                        "correct": parsed["correct"],
                    }
                )
            else:
                _warn(
                    warnings,
                    f"Pergunta {num} ignorada: enunciado, alternativas ou resposta correta incompletos.",
                )
        if questions:
            return questions

    kahoot = _parse_kahoot_questions(full_text, warnings)
    if kahoot:
        return kahoot

    kahoot_exam = _parse_kahoot_exam_questions(full_text, warnings)
    if kahoot_exam:
        return [
            {
                "question": q["question"],
                "options": q["options"],
                "correct": q["correct"],
            }
            for q in kahoot_exam
        ]

    return _parse_markdown_quiz_questions(full_text, warnings)


def normalize_exam_question(q: dict) -> dict:
    """Garante tipo correto ao salvar/carregar (ex.: provas importadas antes da correção)."""
    if not q or not q.get("options"):
        return q
    if q.get("type") == "justify" or "options" not in q:
        return q
    if q.get("answer_key") or q.get("type") == "choice_with_justify":
        normalized = {**q, "type": "choice_with_justify"}
        if not normalized.get("answer_key"):
            normalized["answer_key"] = ""
        return normalized
    if q.get("type") in (None, "choice") and q.get("correct"):
        return {**q, "type": "choice"}
    return q


def normalize_exam_questions(questions: list) -> list:
    return [normalize_exam_question(q) for q in questions]


def _exam_question_richness(questions: list) -> int:
    return sum(
        1
        for q in questions or []
        if (q.get("answer_key") or "").strip() or q.get("type") == "choice_with_justify"
    )


def merge_exam_question_fields(current: dict, backup: dict) -> dict:
    """Mescla metadados da questão, priorizando gabarito/justificativa do backup."""
    merged = {**current}
    backup = backup or {}
    if backup.get("type") == "choice_with_justify":
        merged["type"] = "choice_with_justify"
    backup_key = (backup.get("answer_key") or "").strip()
    if backup_key:
        merged["answer_key"] = backup_key
    if backup.get("correct") and not merged.get("correct"):
        merged["correct"] = backup["correct"]
    if backup.get("question") and not (merged.get("question") or "").strip():
        merged["question"] = backup["question"]
    if backup.get("options") and len(backup.get("options") or []) >= len(
        merged.get("options") or []
    ):
        merged["options"] = backup["options"]
    return normalize_exam_question(merged)


def merge_exam_questions(current: list, backup: list) -> list:
    """Une questões atuais com as do backup, recuperando answer_key e justificativas."""
    current = current or []
    backup = backup or []
    if not backup:
        return normalize_exam_questions(current)
    if not current:
        return normalize_exam_questions(backup)
    if _exam_question_richness(backup) > _exam_question_richness(current) and len(backup) != len(
        current
    ):
        return normalize_exam_questions(backup)
    merged = []
    for i, cq in enumerate(current):
        bq = backup[i] if i < len(backup) else {}
        merged.append(merge_exam_question_fields(cq, bq))
    for extra in backup[len(current) :]:
        merged.append(normalize_exam_question(extra))
    return merged


def exam_question_needs_justify(q: dict) -> bool:
    """Questão de prova que exige justificativa além da alternativa marcada."""
    q = normalize_exam_question(q)
    if q.get("type") == "choice_with_justify":
        return True
    return bool(
        q.get("type") in (None, "choice")
        and q.get("answer_key")
        and q.get("options")
    )


def exam_requires_justify(questions: list) -> bool:
    """Prova com pelo menos uma questão que pede justificativa."""
    return any(exam_question_needs_justify(q) for q in questions)


def question_for_student(q: dict) -> dict:
    """Remove gabarito — visão do aluno."""
    if exam_question_needs_justify(q):
        return {
            "type": "choice_with_justify",
            "question": q["question"],
            "options": q["options"],
        }
    if q.get("type") == "justify" or "options" not in q:
        return {"type": "justify", "question": q["question"]}
    return {
        "type": "choice",
        "question": q["question"],
        "options": q["options"],
    }


def exam_summary(questions: list) -> dict:
    choice = sum(1 for q in questions if q.get("type") == "choice")
    justify = sum(1 for q in questions if q.get("type") == "justify")
    composite = sum(1 for q in questions if q.get("type") == "choice_with_justify")
    return {
        "total": len(questions),
        "choice": choice + composite,
        "justify": justify + composite,
        "composite": composite,
    }
