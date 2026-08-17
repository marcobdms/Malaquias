import unittest

from benchmark.experiments.threshold_grid import rethreshold_ranking


def candidate(candidate_id, relevance, ranking_score, required_scores):
    return {
        "source_candidate_id": candidate_id,
        "filename": f"{candidate_id}.pdf",
        "expected_relevance": relevance,
        "ranking_score": ranking_score,
        "eligibility_state": "needs_review",
        "required_coverage": 0.0,
        "score_components": {
            "criteria": [
                {
                    "id": f"r{index}", "priority": "required", "score": score,
                    "status": "unknown",
                }
                for index, score in enumerate(required_scores)
            ]
        },
    }


class ThresholdGridTests(unittest.TestCase):
    def test_lower_threshold_recomputes_status_coverage_and_canonical_order(self):
        ranking = [
            candidate("partial", 1, 0.9, [0.50, 0.30]),
            candidate("complete", 1, 0.7, [0.45, 0.45]),
        ]

        high = rethreshold_ranking(ranking, 0.55)
        low = rethreshold_ranking(ranking, 0.45)

        self.assertTrue(all(row["eligibility_state"] == "needs_review" for row in high))
        self.assertEqual("complete", low[0]["source_candidate_id"])
        self.assertEqual("eligible", low[0]["eligibility_state"])
        self.assertEqual(1.0, low[0]["required_coverage"])
        self.assertEqual("confirmed", low[0]["score_components"]["criteria"][0]["status"])
        self.assertEqual("unknown", low[1]["score_components"]["criteria"][1]["status"])

    def test_extraction_failure_stays_outside_eligibility(self):
        ranking = [{
            "source_candidate_id": "bad", "expected_relevance": 0,
            "ranking_score": 0.0, "eligibility_state": "extraction_failed",
            "required_coverage": None, "score_components": None,
        }]
        result = rethreshold_ranking(ranking, 0.35)
        self.assertEqual("extraction_failed", result[0]["eligibility_state"])
        self.assertIsNone(result[0]["required_coverage"])

    def test_invalid_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            rethreshold_ranking([], 1.1)


if __name__ == "__main__":
    unittest.main()
