from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from benchmark.review.compare_ablation import build_comparison, build_review_form, render_markdown


def _candidate(candidate_id: str, position: int, label: int, score: float, lexical: bool = False) -> dict:
    evidence = None
    if lexical:
        evidence = {
            "reason": "exact_phrase",
            "match_source": "criterion",
            "matched_alternative": "causa raíz",
            "matched_terms": ["causa", "raíz"],
            "matched_specific_terms": ["causa", "raíz"],
            "matched_anchors": ["raíz"],
            "exact": True,
        }
    return {
        "candidate_id": candidate_id,
        "source_candidate_id": candidate_id,
        "position": position,
        "expected_relevance": label,
        "ranking_score": score,
        "match_score": score * 100,
        "eligibility_state": "eligible" if position <= 10 else "needs_review",
        "required_coverage": 1.0 if position <= 10 else 0.5,
        "score_components": {
            "criteria": [
                {
                    "id": "criterion-1",
                    "label": "Causa raíz",
                    "priority": "required",
                    "status": "confirmed" if position <= 10 else "unknown",
                    "semantic_score": 0.4,
                    "keyword_score": 1.0 if position <= 10 else 0.2,
                    "lexical_evidence": evidence,
                }
            ]
        },
    }


class CompareAblationTest(unittest.TestCase):
    def test_selects_changes_errors_and_keeps_overlay_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "cases" / "case-1").mkdir(parents=True)
            (root / "summary.json").write_text(
                json.dumps(
                    {
                        "suite_id": "suite",
                        "generated_at": "corrected",
                        "variants": [
                            {
                                "variant_id": "control",
                                "macro_metrics_by_view": {"original": {"precision@5": 0.5}},
                                "cpu_gate_vs_control": {"passes": True},
                            },
                            {
                                "variant_id": "challenger",
                                "cpu_gate_vs_control": {
                                    "passes": False,
                                    "relative_change": 0.2,
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            control_ranking = [
                _candidate("neg", 1, 0, 0.9),
                _candidate("pos", 11, 1, 0.5),
            ]
            challenger_ranking = [
                _candidate("pos", 1, 1, 0.8, lexical=True),
                _candidate("neg", 11, 0, 0.4, lexical=True),
            ]
            for variant, ranking in (("control", control_ranking), ("challenger", challenger_ranking)):
                (root / "cases" / "case-1" / f"{variant}.json").write_text(
                    json.dumps(
                        {
                            "case_id": "case-1",
                            "query_id": "q1",
                            "title": "Oferta",
                            "ranking": ranking,
                            "metrics_by_view": {"original": {"precision@10": 0.5}},
                        }
                    ),
                    encoding="utf-8",
                )
            overlay = {
                "judgments": [
                    {
                        "query_id": "q1",
                        "candidate_id": "neg",
                        "label": 2,
                        "status": "provisional",
                        "source": "external_ai_review",
                        "confidence": "low",
                        "reason": "hipótesis",
                    }
                ]
            }

            package = build_comparison(root, "control", "challenger", overlay=overlay)

        self.assertEqual(package["totals"]["enters"], 1)
        self.assertEqual(package["totals"]["leaves"], 1)
        self.assertEqual(package["comparison"]["promotion_status"], "no_go")
        self.assertIn("umbral experimental 0.55", package["eligibility_note"])
        rows = {row["selection_reasons"][0]: row for row in package["cases"][0]["candidates"]}
        negative = next(row for row in package["cases"][0]["candidates"] if row["original_dataset_label"] == 0)
        self.assertEqual(negative["original_dataset_label"], 0)
        self.assertEqual(negative["provisional_overlay"]["label"], 2)
        serialised = json.dumps(package)
        self.assertNotIn('"candidate_id": "neg"', serialised)
        self.assertNotIn('"source_candidate_id": "neg"', serialised)
        self.assertIsNone(negative["control"]["lexical_evidence"][0]["lexical"])
        positive = next(row for row in package["cases"][0]["candidates"] if row["original_dataset_label"] == 1)
        self.assertEqual(
            positive["challenger"]["lexical_evidence"][0]["lexical"]["matched_alternative"],
            "causa raíz",
        )
        form = build_review_form(package)
        self.assertIn("unknown", form["label_scale"])
        markdown = render_markdown(package)
        self.assertIn("no un negativo humano confirmado", markdown)
        self.assertIn("no se propone para producción", markdown)
        self.assertIn("## Resumen macro original", markdown)


if __name__ == "__main__":
    unittest.main()
