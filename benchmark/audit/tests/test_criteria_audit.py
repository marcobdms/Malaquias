import json
import tempfile
import unittest
from pathlib import Path

from benchmark.audit.criteria_audit import audit_suite, pairwise_auc, render_markdown


def _result(multiplier, keyword_scores, hybrid_scores):
    ranking = []
    for index, (keyword, hybrid) in enumerate(zip(keyword_scores, hybrid_scores), start=1):
        ranking.append(
            {
                "candidate_id": f"cv-{index}",
                "source_candidate_id": str(index),
                "filename": f"{index}.pdf",
                "expected_relevance": 1 if index <= 2 else 0,
                "position": index,
                "score_components": {
                    "criteria": [
                        {
                            "id": "criterion-1",
                            "label": "Criterio de prueba",
                            "priority": "required",
                            "semantic_score": hybrid,
                            "keyword_score": keyword,
                            "score": hybrid,
                            "status": "confirmed" if hybrid >= 0.55 else "unknown",
                        }
                    ]
                },
            }
        )
    return {"inputs": {"keyword_multiplier": multiplier}, "ranking": ranking}


class CriteriaAuditTests(unittest.TestCase):
    def test_pairwise_auc_counts_ties(self):
        self.assertEqual(pairwise_auc([1.0, 0.5], [0.5, 0.0]), 0.875)

    def test_audit_compares_saturation_and_discrimination(self):
        with tempfile.TemporaryDirectory() as temporary:
            suite = Path(temporary) / "suite"
            case = suite / "case-1"
            case.mkdir(parents=True)
            (case / "local_pipeline_kw_1_result.json").write_text(
                json.dumps(_result(1.0, [0.8, 0.7, 0.2, 0.1], [0.9, 0.8, 0.2, 0.1])),
                encoding="utf-8",
            )
            (case / "local_pipeline_kw_2p5_result.json").write_text(
                json.dumps(_result(2.5, [1.0, 1.0, 1.0, 1.0], [0.7, 0.7, 0.7, 0.7])),
                encoding="utf-8",
            )

            report = audit_suite(suite)

        low = next(row for row in report["criteria"] if row["config"] == "kw1.0")
        high = next(row for row in report["criteria"] if row["config"] == "kw2.5")
        self.assertEqual(low["components"]["hybrid"]["pairwise_auc"], 1.0)
        self.assertEqual(high["keyword_saturation_rate"], 1.0)
        self.assertTrue(high["non_discriminant"])
        self.assertFalse(high["evidence_available"])
        self.assertIn("kw2.5", render_markdown(report))


if __name__ == "__main__":
    unittest.main()

