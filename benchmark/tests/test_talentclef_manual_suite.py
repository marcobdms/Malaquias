import unittest

from benchmark.scripts.create_talentclef_manual_suite import select_case_candidates
from benchmark.scripts.run_talentclef_manual_suite import (
    build_raw_offer_request,
    build_summary,
    render_summary_markdown,
)


class TalentClefManualSuiteTests(unittest.TestCase):
    def test_selection_is_reproducible_unique_and_uses_baseline_order(self):
        positives = [str(value) for value in range(1, 13)]
        frozen = [*positives, "n3", "n1", "n2", "n4"]
        first = select_case_candidates(
            positives, frozen, query_id="75767", seed=17, target_candidates=13
        )
        second = select_case_candidates(
            list(reversed(positives)), frozen, query_id="75767", seed=17, target_candidates=13
        )
        self.assertEqual(first, second)
        selected_positives, selected_negatives, shortfall = first
        self.assertEqual(10, len(selected_positives))
        self.assertEqual(["n3", "n1", "n2"], selected_negatives)
        self.assertEqual(0, shortfall)
        self.assertEqual(13, len(set(selected_positives + selected_negatives)))

    def test_positive_shortfall_is_filled_with_more_hard_negatives(self):
        selected_positives, selected_negatives, shortfall = select_case_candidates(
            [str(value) for value in range(8)],
            [str(value) for value in range(8)] + [f"n{value}" for value in range(20)],
            query_id="86302",
            seed=17,
        )
        self.assertEqual(8, len(selected_positives))
        self.assertEqual(12, len(selected_negatives))
        self.assertEqual(2, shortfall)

    def test_raw_offer_request_keeps_offer_and_removes_criteria(self):
        request = build_raw_offer_request(
            {
                "job_description": "Oferta completa exacta",
                "categoria": "tecnologia",
                "stack": "Python",
                "strictness": "normal",
                "balance": 0.75,
                "criteria": [{"id": "c1", "label": "Python", "priority": "required"}],
            }
        )
        self.assertEqual("Oferta completa exacta", request["job_description"])
        self.assertEqual([], request["criteria"])
        self.assertEqual(0.5, request["balance"])
        self.assertEqual("tecnologia", request["categoria"])

    def test_summary_macro_and_timings_are_aggregated_without_model(self):
        manifest = {
            "suite_id": "test-suite",
            "known_exceptions": [],
            "cases": [
                {
                    "case_id": "case-a",
                    "query_id": "a",
                    "title": "A",
                    "path": "case-a",
                    "positive_count": 10,
                    "hard_negative_count": 10,
                    "positive_shortfall": 0,
                },
                {
                    "case_id": "case-b",
                    "query_id": "b",
                    "title": "B",
                    "path": "case-b",
                    "positive_count": 8,
                    "hard_negative_count": 12,
                    "positive_shortfall": 2,
                },
            ],
        }
        results = [
            {
                "case_id": case_id,
                "timing": {
                    "parse_seconds": parse,
                    "score_seconds": score,
                    "total_local_seconds": parse + score,
                    "valid_candidates": 20,
                },
                "metrics": {
                    "mrr": metric,
                    "precision@5": metric,
                    "precision@10": metric,
                    "recall@10": metric,
                    "ndcg@5": metric,
                    "ndcg@10": metric,
                },
            }
            for case_id, parse, score, metric in (
                ("case-a", 1.0, 2.0, 1.0),
                ("case-b", 3.0, 4.0, 0.5),
            )
        ]
        summary = build_summary(
            manifest,
            [
                {
                    "input_mode": "criteria",
                    "keyword_multiplier": 2.5,
                    "wall_seconds": 11.0,
                    "results": results,
                },
                {
                    "input_mode": "criteria",
                    "keyword_multiplier": 1.0,
                    "wall_seconds": 10.0,
                    "results": results,
                },
                {
                    "input_mode": "raw_offer",
                    "keyword_multiplier": 2.5,
                    "wall_seconds": 9.0,
                    "results": results,
                },
            ],
            model_load_seconds=3.0,
            total_wall_seconds=33.0,
        )
        control = summary["variants"][0]
        self.assertEqual(0.75, control["macro_metrics"]["precision@10"])
        self.assertEqual(4.0, control["timing"]["parse_seconds"]["total"])
        self.assertEqual(6.0, control["timing"]["score_seconds"]["total"])
        self.assertEqual(40, control["timing"]["candidate_count"])
        self.assertEqual(0.0, summary["comparisons"][0]["macro_metric_deltas"]["ndcg@10"])
        self.assertEqual("raw_offer", summary["variants"][2]["input_mode"])
        self.assertEqual(
            "raw_offer-keyword-2.5", summary["comparisons"][1]["experiment_variant_id"]
        )
        markdown = render_summary_markdown(summary)
        self.assertIn("raw_offer-keyword-2.5 vs criteria-keyword-2.5", markdown)
        self.assertIn("case", control["cases"][0]["result_path"])


if __name__ == "__main__":
    unittest.main()
