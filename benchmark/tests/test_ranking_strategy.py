import unittest

from benchmark.experiments.ranking_strategy import (
    rank_with_strategy,
    required_score_summary,
    strategy_orders_across_thresholds,
)


def candidate(candidate_id, ranking_score, required_scores):
    return {
        "source_candidate_id": candidate_id,
        "expected_relevance": 1,
        "ranking_score": ranking_score,
        "eligibility_state": "needs_review",
        "required_coverage": 0.0,
        "score_components": {"criteria": [
            {"id": f"r{i}", "priority": "required", "score": score, "status": "unknown"}
            for i, score in enumerate(required_scores)
        ]},
    }


class RankingStrategyTests(unittest.TestCase):
    def test_required_summary(self):
        result = required_score_summary(candidate("a", 0.7, [0.2, 0.8]))
        self.assertEqual(2, result["count"])
        self.assertEqual(0.2, result["minimum"])
        self.assertEqual(0.5, result["mean"])

    def test_each_continuous_strategy_uses_its_declared_key(self):
        rows = [
            candidate("high-global", 0.9, [0.6, 0.3]),
            candidate("balanced", 0.7, [0.45, 0.45]),
            candidate("high-mean", 0.6, [0.4, 0.8]),
        ]
        self.assertEqual(
            "high-global",
            rank_with_strategy(rows, "B_ranking_score")[0]["source_candidate_id"],
        )
        self.assertEqual(
            "balanced",
            rank_with_strategy(rows, "C_min_mean_score")[0]["source_candidate_id"],
        )
        self.assertEqual(
            "high-mean",
            rank_with_strategy(rows, "D_mean_score")[0]["source_candidate_id"],
        )

    def test_b_c_d_are_threshold_invariant_but_canonical_can_change(self):
        rows = [
            candidate("partial", 0.9, [0.50, 0.30]),
            candidate("complete", 0.7, [0.45, 0.45]),
        ]
        canonical = strategy_orders_across_thresholds(
            rows, "A_canonical", thresholds=(0.40, 0.55)
        )
        self.assertNotEqual(canonical[0.40], canonical[0.55])
        for strategy in (
            "B_ranking_score", "C_min_mean_score", "D_mean_score"
        ):
            orders = strategy_orders_across_thresholds(
                rows, strategy, thresholds=(0.35, 0.45, 0.55)
            )
            self.assertEqual(1, len({tuple(order) for order in orders.values()}))

    def test_unknown_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            rank_with_strategy([], "E")


if __name__ == "__main__":
    unittest.main()
