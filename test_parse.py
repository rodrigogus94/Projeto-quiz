import io
import unittest

from app.pdf_helpers import (
    _normalize_markdown_source,
    parse_exam_from_upload,
    parse_questions_from_upload,
    read_text_from_upload,
)
from pdf_parser import (
    exam_summary,
    merge_exam_questions,
    parse_exam_from_text,
    parse_questions_from_text,
)

SAMPLE_TEXT = """
Pergunta 1: O que é uma variável?
Alternativa A (Vermelho): Um tipo de loop
Alternativa B (Azul): Um espaço para armazenar dados (CORRETA)
Alternativa C (Amarelo): Uma função
Alternativa D (Verde): Um operador

Pergunta 2: Qual estrutura repete código?
Alternativa A (Vermelho): if
Alternativa B (Azul): print
Alternativa C (Amarelo): for (CORRETA)
Alternativa D (Verde): input
"""

MARKDOWN_QUIZ_TEXT = """
### Questão 1
Qual estrutura de repetição é mais indicada quando você **já sabe** exatamente quantas vezes o código deve ser executado?
A) if / else
B) while
C) for
D) switch

**Resposta Correta: C**
**Justificativa:** O loop `for` é projetado especificamente para iterações contáveis.

### Questão 2
O que acontece se a condição de um loop `while` nunca se tornar falsa?
A) O código pula para a próxima linha fora do loop.
B) Ocorre um "Loop Infinito", podendo travar o navegador ou o computador.
C) O JavaScript corrige o erro automaticamente após 100 voltas.
D) O loop é executado apenas uma vez por segurança.

**Resposta Correta: B**
"""

UC2_EXAM_TEXT = """
Questão 1
O que é um algoritmo, segundo os slides?
a) Um software pronto para uso comercial.
b) Uma sequência finita de passos lógicos para resolver um problema.
c) Um tipo de variável em JavaScript.
d) Um framework CSS como o Bootstrap.
Justificativa:
Os slides definem algoritmo como uma sequência finita de passos lógicos e ordenados.

Questão 2
No JavaScript, qual palavra-chave é utilizada para declarar uma constante?
a) let
b) var
c) constant
d) const
Justificativa:
A palavra-chave const é usada para declarar constantes.

GABARITO OFICIAL
Questão 	Resposta Correta 	Nota
1 	B
2 	D
"""

EXAM_TEXT = """
Pergunta 1: Qual é o valor de 2+2?
Alternativa A: 3
Alternativa B: 4 (CORRETA)
Alternativa C: 5
Alternativa D: 6

Pergunta 2: Explique o que é um algoritmo. (JUSTIFICATIVA)
Gabarito: Sequência finita de passos para resolver um problema.

Pergunta 3: Justifique o uso de variáveis em programação.
Resposta esperada: Armazenar dados que podem mudar durante a execução.
"""


class TestParseQuestions(unittest.TestCase):
    def test_extracts_two_questions(self):
        questions = parse_questions_from_text(SAMPLE_TEXT)
        self.assertEqual(len(questions), 2)

    def test_question_text_without_alternatives(self):
        questions = parse_questions_from_text(SAMPLE_TEXT)
        self.assertEqual(questions[0]["question"], "O que é uma variável?")
        self.assertEqual(questions[1]["question"], "Qual estrutura repete código?")

    def test_options_and_correct_letter(self):
        q1 = parse_questions_from_text(SAMPLE_TEXT)[0]
        self.assertEqual(len(q1["options"]), 4)
        self.assertEqual(q1["correct"], "B")
        self.assertNotIn("(CORRETA)", q1["options"][1])


class TestParseUC2Exam(unittest.TestCase):
    def test_uc2_extracts_composite_questions(self):
        questions = parse_exam_from_text(UC2_EXAM_TEXT)
        self.assertEqual(len(questions), 2)
        summary = exam_summary(questions)
        self.assertEqual(summary["composite"], 2)

    def test_uc2_question_structure(self):
        q = parse_exam_from_text(UC2_EXAM_TEXT)[0]
        self.assertEqual(q["type"], "choice_with_justify")
        self.assertEqual(q["correct"], "B")
        self.assertEqual(len(q["options"]), 4)
        self.assertIn("sequência finita", q["answer_key"].lower())

    def test_uc2_gabarito_from_table(self):
        q2 = parse_exam_from_text(UC2_EXAM_TEXT)[1]
        self.assertEqual(q2["correct"], "D")

    def test_uc2_with_markdown_headers(self):
        text = UC2_EXAM_TEXT.replace("Questão ", "### Questão ")
        questions = parse_exam_from_text(text)
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0]["type"], "choice_with_justify")

    def test_uc2_with_blockquote_preamble(self):
        text = (
            "> Instruções em blockquote\n\n" + UC2_EXAM_TEXT
        )
        questions = parse_exam_from_text(text)
        self.assertEqual(len(questions), 2)

    def test_markdown_with_justify_is_composite(self):
        questions = parse_exam_from_text(MARKDOWN_QUIZ_TEXT)
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0]["type"], "choice_with_justify")
        self.assertIn("for", questions[0]["answer_key"].lower())

    def test_kahoot_markdown_exam_with_justify(self):
        text = """
## Pergunta 1
* **Pergunta:** Questão de teste do sistema?
* **Alternativas:**
  * [X] A) Opção A correta
  * [ ] B) Opção B
  * [ ] C) Opção C
  * [ ] D) Opção D
* **Justificativa:** Texto esperado na correção da justificativa.

## GABARITO OFICIAL
| Pergunta | Resposta |
| 1 | A |
"""
        questions = parse_exam_from_text(text)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["type"], "choice_with_justify")
        self.assertEqual(questions[0]["correct"], "A")
        self.assertIn("justificativa", questions[0]["answer_key"].lower())

    def test_kahoot_exam_format_imports_as_quiz_material(self):
        text = """
## Pergunta 1
* **Pergunta:** Questão de teste do sistema?
* **Alternativas:**
  * [X] A) Opção A correta
  * [ ] B) Opção B
  * [ ] C) Opção C
  * [ ] D) Opção D
* **Justificativa:** Texto esperado na correção da justificativa.

## Pergunta 2
* **Pergunta:** Segunda questão?
* **Alternativas:**
  * [ ] A) Opção A
  * [X] B) Opção B correta
  * [ ] C) Opção C
  * [ ] D) Opção D

## GABARITO OFICIAL
| Pergunta | Resposta |
| 1 | A |
| 2 | B |
"""
        questions = parse_questions_from_text(text)
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0]["correct"], "A")
        self.assertEqual(questions[1]["correct"], "B")

    def test_pergunta_lowercase_options_with_justify(self):
        text = """
Pergunta 1: O que é um algoritmo?
a) Software
b) Sequência de passos
c) Variável
d) Framework
Justificativa:
Sequência finita de passos lógicos.

GABARITO OFICIAL
1  B
"""
        questions = parse_exam_from_text(text)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["type"], "choice_with_justify")

    def test_question_for_student_infers_justify_from_answer_key(self):
        from pdf_parser import question_for_student

        q = {
            "type": "choice",
            "question": "Teste?",
            "options": ["A", "B", "C", "D"],
            "correct": "B",
            "answer_key": "Gabarito da justificativa",
        }
        view = question_for_student(q)
        self.assertEqual(view["type"], "choice_with_justify")

    def test_uc2_empty_does_not_use_markdown_warnings(self):
        text = (
            "Questão 1\n"
            "Só enunciado sem opções\n"
            "GABARITO OFICIAL\n1  B\n"
        )
        warnings = []
        questions = parse_exam_from_text(text, warnings)
        self.assertEqual(questions, [])
        self.assertTrue(any("a-d" in w for w in warnings))
        # Sem questões válidas no UC2, o parser pode tentar o Markdown em seguida.
        self.assertEqual(questions, [])


class TestParseExam(unittest.TestCase):
    def test_mixed_exam_types(self):
        questions = parse_exam_from_text(EXAM_TEXT)
        self.assertEqual(len(questions), 3)
        summary = exam_summary(questions)
        self.assertEqual(summary["choice"], 1)
        self.assertEqual(summary["justify"], 2)

    def test_choice_exam_question(self):
        q = parse_exam_from_text(EXAM_TEXT)[0]
        self.assertEqual(q["type"], "choice")
        self.assertEqual(q["correct"], "B")

    def test_justify_with_gabarito(self):
        q = parse_exam_from_text(EXAM_TEXT)[1]
        self.assertEqual(q["type"], "justify")
        self.assertIn("Sequência finita", q["answer_key"])

    def test_justify_with_resposta_esperada(self):
        q = parse_exam_from_text(EXAM_TEXT)[2]
        self.assertEqual(q["type"], "justify")
        self.assertIn("Armazenar dados", q["answer_key"])


class TestParseMarkdownQuiz(unittest.TestCase):
    def test_extracts_markdown_questions(self):
        questions = parse_questions_from_text(MARKDOWN_QUIZ_TEXT)
        self.assertEqual(len(questions), 2)

    def test_markdown_strips_bold_and_finds_correct(self):
        q1 = parse_questions_from_text(MARKDOWN_QUIZ_TEXT)[0]
        self.assertIn("já sabe", q1["question"])
        self.assertNotIn("**", q1["question"])
        self.assertEqual(q1["correct"], "C")
        self.assertEqual(len(q1["options"]), 4)

    def test_markdown_exam_import(self):
        questions = parse_exam_from_text(MARKDOWN_QUIZ_TEXT)
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0]["type"], "choice_with_justify")


class TestMarkdownUpload(unittest.TestCase):
    def test_normalize_strips_code_fence(self):
        wrapped = "```\nPergunta 1: Teste?\n```"
        self.assertEqual(_normalize_markdown_source(wrapped), "Pergunta 1: Teste?")

    def test_parse_questions_from_md_upload(self):
        content = SAMPLE_TEXT.strip().encode("utf-8")
        uploaded = io.BytesIO(content)
        uploaded.name = "quiz.md"
        questions = parse_questions_from_upload(uploaded, show_warnings=False)
        self.assertEqual(len(questions), 2)

    def test_parse_exam_from_md_upload(self):
        content = EXAM_TEXT.strip().encode("utf-8")
        uploaded = io.BytesIO(content)
        uploaded.name = "prova.md"
        questions = parse_exam_from_upload(uploaded, show_warnings=False)
        self.assertEqual(len(questions), 3)

    def test_read_md_with_bom(self):
        content = "\ufeffPergunta 1: ok".encode("utf-8-sig")
        uploaded = io.BytesIO(content)
        uploaded.name = "notas.md"
        self.assertIn("Pergunta 1", read_text_from_upload(uploaded))


class TestMergeExamQuestions(unittest.TestCase):
    def test_merge_restores_answer_key_from_backup(self):
        current = [
            {
                "type": "choice",
                "question": "Q1",
                "options": ["a", "b", "c", "d"],
                "correct": "B",
            }
        ]
        backup = [
            {
                "type": "choice_with_justify",
                "question": "Q1",
                "options": ["a", "b", "c", "d"],
                "correct": "B",
                "answer_key": "Texto gabarito justificativa",
            }
        ]
        merged = merge_exam_questions(current, backup)
        self.assertEqual(merged[0]["type"], "choice_with_justify")
        self.assertEqual(merged[0]["answer_key"], "Texto gabarito justificativa")


if __name__ == "__main__":
    unittest.main()
