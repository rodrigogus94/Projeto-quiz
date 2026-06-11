import unittest

from pdf_export import build_exam_lines, build_exam_pdf_bytes, export_filename


class TestPdfExport(unittest.TestCase):
    EXAM = {
        "title": "Prova 1",
        "questions": [
            {
                "type": "choice",
                "question": "2+2?",
                "options": ["3", "4", "5", "6"],
                "correct": "B",
            },
            {
                "type": "justify",
                "question": "Explique algoritmos.",
                "answer_key": "Passos ordenados",
            },
        ],
    }
    SUB = {
        "student_name": "João Santos",
        "submitted_at": "2026-06-04T10:00:00",
        "answers": [
            {"type": "choice", "selected": "B", "classification": "A"},
            {"type": "justify", "text": "Sequência de passos", "classification": "PA"},
        ],
        "summary": {
            "counts": {"A": 1, "PA": 1, "NA": 0},
            "total_points": 1.5,
            "max_points": 2,
        },
    }

    def test_lines_include_student_and_answers(self):
        text = "\n".join(build_exam_lines(self.EXAM, self.SUB, include_correction=True))
        self.assertIn("João Santos", text)
        self.assertIn("RESPOSTA DO ALUNO", text)
        self.assertIn("Sequência de passos", text)

    def test_lines_hide_correction_until_released(self):
        text = "\n".join(build_exam_lines(self.EXAM, self.SUB))
        self.assertNotIn("Classificação:", text)

    def test_pdf_bytes_generated(self):
        data = build_exam_pdf_bytes(self.EXAM, self.SUB, include_correction=True)
        self.assertTrue(data.startswith(b"%PDF"))

    def test_filename(self):
        self.assertIn("Joao_Santos", export_filename(self.EXAM, self.SUB))


if __name__ == "__main__":
    unittest.main()
