import unittest

from pdf_parser import exam_summary, parse_exam_from_text, parse_questions_from_text

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


if __name__ == "__main__":
    unittest.main()
