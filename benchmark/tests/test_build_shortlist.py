from __future__ import annotations

import unittest

from benchmark.review.build_shortlist import build_form, build_shortlist, render_shortlist


def _candidate(anonymous_id: str, reasons: list[str], position: int, overlay=None) -> dict:
    return {
        "anonymous_id": anonymous_id,
        "original_dataset_label": 0,
        "provisional_overlay": overlay,
        "selection_reasons": reasons,
        "control": {
            "position": position,
            "ranking_score": 0.7,
            "eligibility_state": "eligible",
            "required_coverage": 1.0,
            "lexical_evidence": [],
        },
        "challenger": {
            "position": position + 1,
            "ranking_score": 0.6,
            "eligibility_state": "needs_review",
            "required_coverage": 0.5,
            "lexical_evidence": [],
        },
    }


class ShortlistTest(unittest.TestCase):
    def test_prioritises_regressions_and_adds_anonymised_evidence(self) -> None:
        comparison = {
            "source_ablation": {"suite_id": "suite"},
            "comparison": {"control_variant": "a", "challenger_variant": "b"},
            "label_policy": {},
            "cases": [
                {
                    "query_id": "96027",
                    "title": "Fallas",
                    "candidates": [
                        _candidate("C-REG", ["regresion_dirigida"], 11),
                        _candidate("C-FP", ["falso_positivo_original"], 2),
                    ],
                },
                {
                    "query_id": "91821",
                    "title": "Privacidad",
                    "candidates": [
                        _candidate(
                            "C-OVER",
                            ["falso_positivo_original"],
                            1,
                            overlay={"label": 1, "source": "external_ai_review"},
                        )
                    ],
                },
            ],
        }
        evidence = {
            "queries": [
                {
                    "candidates": [
                        {"anonymous_id": "C-REG", "professional_evidence": "FMEA y causa raíz"}
                    ]
                }
            ]
        }
        shortlist = build_shortlist(comparison, [evidence], maximum=2)
        selected = [row for case in shortlist["cases"] for row in case["candidates"]]
        self.assertEqual({row["anonymous_id"] for row in selected}, {"C-REG", "C-OVER"})
        regression = next(row for row in selected if row["anonymous_id"] == "C-REG")
        self.assertEqual(regression["professional_evidence"], "FMEA y causa raíz")
        self.assertIn("**0** — No encaja", render_shortlist(shortlist))
        self.assertIn("unknown", build_form(shortlist)["label_scale"])


if __name__ == "__main__":
    unittest.main()
