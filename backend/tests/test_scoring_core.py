import unittest

import numpy as np

from backend.app.scoring_core import (
    aggregate_semantic_score,
    chunk_text,
    keyword_score_any,
    rank_candidate_results,
    required_eligibility,
)


class ScoringCoreTests(unittest.TestCase):
    def test_chunking_keeps_evidence_after_first_128_tokens(self):
        text = " ".join([f"token{i}" for i in range(180)] + ["python"])
        chunks = chunk_text(text, max_tokens=96, overlap=24)
        self.assertGreater(len(chunks), 1)
        self.assertIn("python", chunks[-1])

    def test_equivalences_are_or_alternatives(self):
        score = keyword_score_any(
            "Experiencia diaria conduciendo montacargas",
            ["carretilla elevadora", "montacargas"],
        )
        self.assertEqual(score, 1.0)

    def test_semantic_aggregation_uses_best_chunks(self):
        query = np.array([[1.0, 0.0]], dtype=np.float32)
        candidate = np.array([[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]], dtype=np.float32)
        self.assertGreater(aggregate_semantic_score(query, candidate, top_k=2), 0.9)

    def test_missing_required_criterion_cannot_be_hidden(self):
        state, coverage = required_eligibility([
            {"priority": "required", "score": 0.2},
            {"priority": "preferred", "score": 1.0},
            {"priority": "preferred", "score": 1.0},
        ], threshold=0.55)
        self.assertEqual(state, "needs_review")
        self.assertEqual(coverage, 0.0)

    def test_candidate_order_is_shared_by_api_and_pipeline_runner(self):
        rows = [
            {"candidate_id": "high-score-review", "eligibility_state": "needs_review", "required_coverage": 0.5, "ranking_score": 0.99},
            {"candidate_id": "eligible", "eligibility_state": "eligible", "required_coverage": 1.0, "ranking_score": 0.40},
            {"candidate_id": "better-coverage", "eligibility_state": "needs_review", "required_coverage": 0.8, "ranking_score": 0.20},
        ]
        ranked = rank_candidate_results(rows)
        self.assertEqual(
            [row["candidate_id"] for row in ranked],
            ["eligible", "better-coverage", "high-score-review"],
        )


if __name__ == "__main__":
    unittest.main()
