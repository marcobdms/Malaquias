import math
import unittest

from benchmark.metrics import evaluate_ranking, ndcg_at_k, precision_at_k, recall_at_k


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.ranking = ["bad", "best", "good", "other"]
        self.relevance = {"bad": 0, "best": 2, "good": 1, "other": 0}

    def test_precision_and_recall(self):
        self.assertEqual(precision_at_k(self.ranking, self.relevance, 2), 0.5)
        self.assertEqual(recall_at_k(self.ranking, self.relevance, 2), 0.5)

    def test_mrr_and_ndcg(self):
        metrics = evaluate_ranking(self.ranking, self.relevance, [2])
        self.assertEqual(metrics["mrr"], 0.5)
        self.assertGreater(ndcg_at_k(self.ranking, self.relevance, 3), 0.0)
        self.assertLess(ndcg_at_k(self.ranking, self.relevance, 3), 1.0)

    def test_unknown_is_not_penalized(self):
        relevance = {"unknown": "unknown", "yes": 1}
        self.assertEqual(precision_at_k(["unknown", "yes"], relevance, 1), 1.0)
        self.assertEqual(recall_at_k(["unknown", "yes"], relevance, 1), 1.0)

    def test_perfect_ndcg(self):
        self.assertTrue(math.isclose(ndcg_at_k(["best", "good"], self.relevance, 2), 1.0))


if __name__ == "__main__":
    unittest.main()
