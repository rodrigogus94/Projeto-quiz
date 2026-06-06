import unittest

from auto_grade import (
    CLASSIFICATIONS,
    classify_choice,
    classify_justify,
    grade_justify_answer,
    summarize_answers,
)


class TestAutoGrade(unittest.TestCase):
    def test_choice_correct_is_a(self):
        self.assertEqual(classify_choice("B", "B"), "A")

    def test_choice_wrong_is_na(self):
        self.assertEqual(classify_choice("A", "B"), "NA")

    def test_justify_empty_is_na(self):
        self.assertEqual(classify_justify("", "gabarito qualquer"), "NA")

    def test_justify_high_overlap_is_a(self):
        key = "Sequência finita de passos para resolver um problema"
        ans = "É uma sequência finita de passos ordenados para resolver um problema"
        self.assertEqual(classify_justify(ans, key), "A")

    def test_justify_partial_is_pa(self):
        key = "Armazenar dados que podem mudar durante a execução do programa"
        ans = "Serve para guardar dados no programa"
        self.assertEqual(classify_justify(ans, key), "PA")

    def test_summarize_counts(self):
        answers = [
            {"classification": "A", "points": 1.0},
            {"classification": "PA", "points": 0.5},
            {"classification": "NA", "points": 0.0},
        ]
        s = summarize_answers(answers)
        self.assertEqual(s["counts"]["A"], 1)
        self.assertEqual(s["counts"]["PA"], 1)
        self.assertEqual(s["total_points"], 1.5)


if __name__ == "__main__":
    unittest.main()
