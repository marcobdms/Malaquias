import tempfile
import unittest
from pathlib import Path

from benchmark.experiments.ablation_runner import (
    VARIANT_SPECS,
    criterion_saturation,
    eligibility_rates,
    evaluate_case_ranking,
    score_variant,
)
from backend.app.job_criteria import build_scoring_criteria, parse_job_criteria


class AblationRunnerTests(unittest.TestCase):
    def test_variant_matrix_is_exactly_two_criteria_by_three_lexical_modes(self):
        identities = {
            (row["criteria"], row["lexical"], row["multiplier"])
            for row in VARIANT_SPECS
        }
        self.assertEqual(6, len(VARIANT_SPECS))
        self.assertEqual(
            {
                ("v1", "v1", 2.5), ("v1", "v1", 1.0), ("v1", "v2", None),
                ("v2", "v1", 2.5), ("v2", "v1", 1.0), ("v2", "v2", None),
            },
            identities,
        )

    def test_lexical_v2_uses_cached_semantics_and_separates_fmea_from_bi(self):
        criteria = parse_job_criteria(
            '[{"id":"failure","label":"Análisis de fallas y determinación de causa raíz",'
            '"priority":"required","equivalences":["failure analysis","RCA"]}]'
        )
        scoring = build_scoring_criteria(criteria)
        scores = score_variant(
            [
                "Analista BI: análisis de requisitos y documentación funcional.",
                "Ingeniero de calidad responsable de FMEA en producto.",
            ],
            scoring,
            [[0.2], [0.2]],
            lexical="v2",
            keyword_multiplier=None,
            balance=0.5,
            strictness="normal",
            required_threshold=0.55,
        )

        self.assertEqual("needs_review", scores[0]["eligibility_state"])
        self.assertEqual("eligible", scores[1]["eligibility_state"])
        self.assertLess(scores[0]["ranking_score"], scores[1]["ranking_score"])
        self.assertEqual(
            "fmea",
            scores[1]["criteria_scores"][0]["lexical_evidence"][
                "matched_alternative"
            ],
        )

    def test_saturation_and_false_eligible_are_reported_without_model(self):
        ranking = [
            {
                "source_candidate_id": "neg",
                "filename": "neg.pdf",
                "position": 1,
                "expected_relevance": 0,
                "ranking_score": 0.8,
                "eligibility_state": "eligible",
                "score_components": {"criteria": [
                    {"id": "c1", "label": "C1", "keyword_score": 1.0},
                    {"id": "c2", "label": "C2", "keyword_score": 0.2},
                ]},
            },
            {
                "source_candidate_id": "pos",
                "filename": "pos.pdf",
                "position": 2,
                "expected_relevance": 1,
                "ranking_score": 0.7,
                "eligibility_state": "eligible",
                "score_components": {"criteria": [
                    {"id": "c1", "label": "C1", "keyword_score": 1.0},
                    {"id": "c2", "label": "C2", "keyword_score": 0.5},
                ]},
            },
            {
                "source_candidate_id": "bad-pdf",
                "filename": "bad.pdf",
                "position": 3,
                "expected_relevance": 0,
                "ranking_score": 0.0,
                "eligibility_state": "extraction_failed",
                "score_components": None,
            },
        ]
        saturation = criterion_saturation(ranking)
        metrics, false_eligible = evaluate_case_ranking(ranking, "q", None)

        self.assertEqual(0.5, saturation["mean_rate"])
        self.assertEqual(1, saturation["criteria_saturated_gte_80pct"])
        self.assertEqual(1, false_eligible["original"]["count"])
        self.assertIn("precision@5", metrics["original"])
        eligible = eligibility_rates(ranking)
        self.assertEqual(1.0, eligible["positive_eligible_rate"])
        self.assertEqual(0.5, eligible["negative_eligible_rate"])

    def test_bad_semantic_matrix_is_rejected_before_any_model_use(self):
        with self.assertRaises(ValueError):
            score_variant(
                ["cv"], [], [[0.1]], lexical="v2", keyword_multiplier=None,
                balance=0.5, strictness="normal", required_threshold=0.55,
            )


if __name__ == "__main__":
    unittest.main()
