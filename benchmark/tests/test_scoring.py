import unittest

import numpy as np

from benchmark.scoring import apply_strictness, keyword_score, rank_pool


class ScoringTests(unittest.TestCase):
    def test_keyword_score_is_bounded(self):
        self.assertEqual(keyword_score("python sql react", "python sql", 2.5), 1.0)

    def test_strictness_validation(self):
        self.assertEqual(apply_strictness(0.6, "normal"), 0.5)
        with self.assertRaises(ValueError):
            apply_strictness(0.5, "desconocido")

    def test_ranking_is_deterministic_on_ties(self):
        rows = rank_pool(
            "python", ["b", "a"], ["python", "python"],
            np.array([1.0, 0.0]), np.array([[1.0, 0.0], [1.0, 0.0]]),
            balance=0.5, strictness="flexible", keyword_multiplier=2.5,
        )
        self.assertEqual([row["candidate_id"] for row in rows], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
