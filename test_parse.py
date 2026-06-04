import unittest

from main import parse_questions_from_text

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

    def test_invalid_block_adds_warning(self):
        warnings = []
        text = """
Pergunta 1: Só enunciado sem alternativas completas
Alternativa A (Vermelho): uma
"""
        questions = parse_questions_from_text(text, warnings=warnings)
        self.assertEqual(questions, [])
        self.assertTrue(any("Pergunta 1" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
