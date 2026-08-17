import unittest

from benchmark.scripts.create_ecyl_holdout_pools import (
    PRIORITY_REVIEW_IDS,
    select_stratified_pool,
    stable_job_seed,
    validate_pool_payload,
)


class EcylHoldoutPoolTests(unittest.TestCase):
    def test_selection_is_reproducible_mixed_and_unique(self):
        ranking = [
            {
                "candidate_id": f"candidate-{index:03d}",
                "score": 1.0 - index / 1000,
                "semantic_score": 0.8,
                "keyword_score": 0.6,
            }
            for index in range(100)
        ]
        first = select_stratified_pool(ranking, job_id="ecyl-test", seed=17)
        second = select_stratified_pool(ranking, job_id="ecyl-test", seed=17)
        self.assertEqual(first, second)
        self.assertEqual(20, len(first))
        self.assertEqual(20, len({row["candidate_id"] for row in first}))
        self.assertEqual(list(range(1, 9)), [row["baseline_rank"] for row in first[:8]])
        self.assertTrue(all(9 <= row["baseline_rank"] <= 60 for row in first[8:14]))
        self.assertTrue(all(row["baseline_rank"] >= 61 for row in first[14:]))

    def test_stable_seed_does_not_depend_on_python_hash_randomization(self):
        self.assertEqual(stable_job_seed(10, "ecyl-test"), stable_job_seed(10, "ecyl-test"))
        self.assertNotEqual(stable_job_seed(10, "ecyl-test"), stable_job_seed(10, "ecyl-other"))

    def test_payload_rejects_labels_and_accepts_exact_unjudged_shape(self):
        groups = ["baseline_top"] * 8 + ["baseline_adjacent"] * 6 + ["seeded_random_tail"] * 6
        pools = []
        priority_ids = set(PRIORITY_REVIEW_IDS)
        all_ids = list(PRIORITY_REVIEW_IDS) + [f"ecyl-extra-{index}" for index in range(6)]
        for job_id in all_ids:
            pools.append(
                {
                    "job_id": job_id,
                    "priority_review": job_id in priority_ids,
                    "candidates": [
                        {
                            "candidate_id": f"{job_id}-candidate-{index}",
                            "relevance": "unknown",
                            "selection_group": group,
                        }
                        for index, group in enumerate(groups)
                    ],
                }
            )
        payload = {"benchmark_status": "incoming_unjudged", "pools": pools}
        validate_pool_payload(payload)
        payload["pools"][0]["candidates"][0]["relevance"] = 1
        with self.assertRaisesRegex(ValueError, "no puede contener etiquetas"):
            validate_pool_payload(payload)

    def test_payload_rejects_display_name_metadata(self):
        groups = ["baseline_top"] * 8 + ["baseline_adjacent"] * 6 + ["seeded_random_tail"] * 6
        pools = []
        for job_id in list(PRIORITY_REVIEW_IDS) + [f"ecyl-extra-{index}" for index in range(6)]:
            pools.append(
                {
                    "job_id": job_id,
                    "priority_review": job_id in PRIORITY_REVIEW_IDS,
                    "candidates": [
                        {
                            "candidate_id": f"{job_id}-candidate-{index}",
                            "relevance": "unknown",
                            "selection_group": group,
                        }
                        for index, group in enumerate(groups)
                    ],
                }
            )
        payload = {"benchmark_status": "incoming_unjudged", "pools": pools}
        payload["pools"][0]["candidates"][0]["display_name"] = "Nombre innecesario"
        with self.assertRaisesRegex(ValueError, "no deben duplicar nombres"):
            validate_pool_payload(payload)


if __name__ == "__main__":
    unittest.main()
