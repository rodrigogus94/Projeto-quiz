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
    r"^(?:[*\-●○•]\s*)?([A-Da-d])\)\s*(.*)$", re.IGNORECASE
)
UC2_JUSTIFICATIVA_LINE = re.compile(r"^Justificativa\s*:\s*(.*)$", re.IGNORECASE)
UC2_GABARITO_SECTION = re.compile(r"GABARITO(?:\s+OFICIAL)?", re.IGNORECASE)
UC2_GABARITO_ROW = re.compile(
    r"(?:^|\n)\s*(\d{1,2})\s+([A-Da-d])\b"
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


def _parse_markdown_exam_questions(full_text: str, warnings: list | None = None) -> list:
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
            questions.append(
                {
                    "type": "choice",
                    "question": parsed["question"],
                    "options": parsed["options"],
                    "correct": parsed["correct"],
                }
            )
        else:
            _warn(
                warnings,
                f"Questão {num} ignorada: enunciado, 4 opções (A-D) ou Resposta Correta incompletos.",
            )

    return questions


def _parse_kahoot_question_block(block: str) -> dict | None:
    question_parts: list[str] = []
    options: list[list[str]] = []
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
            else:
                # "Alternativas:" apenas abre a lista; "Tempo limite" e
                # "Justificativa" são ignorados (incluindo linhas de continuação).
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

    return {"question": question_text, "options": opts, "correct": correct}


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
            justify_parts.append(line)

    opts = [o for o in options if o is not None]
    question = _clean_text(" ".join(question_lines))
    if len(options) != 4 or any(o is None or not o for o in options) or not question:
        return None
    if not correct_letter or correct_letter.upper() not in "ABCD":
        return None

    return {
        "type": "choice_with_justify",
        "question": question,
        "options": [options[0], options[1], options[2], options[3]],
        "correct": correct_letter.upper(),
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
    # Formato UC2 (Atividade avaliativa) tem prioridade quando detectado.
    if UC2_QUESTAO_HEADER.search(full_text) or "Justificativa:" in full_text:
        uc2 = _parse_uc2_exam_questions(full_text, warnings)
        if uc2 or UC2_QUESTAO_HEADER.search(full_text):
            # Não cair no parser Markdown (evita mensagens enganosas de "Resposta Correta").
            return uc2

    matches = list(PERGUNTA_HEADER.finditer(full_text))
    if not matches:
        kahoot = _parse_kahoot_questions(full_text, warnings)
        if kahoot:
            return [{"type": "choice", **q} for q in kahoot]
        md = _parse_markdown_exam_questions(full_text, warnings)
        if md:
            return md
        return _parse_uc2_exam_questions(full_text, warnings)

    questions = []

    for i, match in enumerate(matches):
        num = match.group(1)
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[match.start() : block_end]
        header_end = match.end() - match.start()

        parsed = None
        if _is_justify_block(block, header_end):
            parsed = _parse_justify_block(block, header_end)
        else:
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

    return questions


def parse_questions_from_text(full_text: str, warnings: list | None = None) -> list:
    """Parser de quiz — múltipla escolha (formato PDF ou Markdown)."""
    matches = list(PERGUNTA_HEADER.finditer(full_text))
    if not matches:
        kahoot = _parse_kahoot_questions(full_text, warnings)
        if kahoot:
            return kahoot
        return _parse_markdown_quiz_questions(full_text, warnings)

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

    return questions


def question_for_student(q: dict) -> dict:
    """Remove gabarito — visão do aluno."""
    if q.get("type") == "choice_with_justify":
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
