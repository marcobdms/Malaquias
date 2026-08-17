import unittest

from benchmark.experiments.lexical_v2 import score_lexical_criterion


FAILURE_CRITERION = {
    "id": "96027-failure-root-cause",
    "label": "Análisis de fallas y determinación de causa raíz",
    "equivalences": ["failure analysis", "root cause analysis", "RCA"],
}


class LexicalV2Tests(unittest.TestCase):
    def test_business_analysis_and_documentation_do_not_confirm_failure_engineering(self):
        result = score_lexical_criterion(
            FAILURE_CRITERION,
            "Analista de negocio y BI. Análisis de requisitos, datos y documentación funcional.",
        )

        self.assertLessEqual(result["score"], 0.12)
        self.assertFalse(result["exact"])
        self.assertEqual("generic_overlap", result["reason"])
        self.assertNotIn("falla", result["matched_anchors"])

    def test_fmea_and_spanish_expansion_are_full_domain_aliases(self):
        for cv_text in (
            "Ingeniero de calidad con aplicación de FMEA en producto industrial.",
            "Responsable del análisis de modo de falla y efectos en nuevos diseños.",
        ):
            with self.subTest(cv_text=cv_text):
                result = score_lexical_criterion(FAILURE_CRITERION, cv_text)
                self.assertEqual(1.0, result["score"])
                self.assertTrue(result["exact"])
                self.assertEqual("domain_alias", result["match_source"])

    def test_fmea_domain_alias_does_not_leak_into_adjacent_criteria(self):
        criteria = [
            FAILURE_CRITERION,
            {
                "label": "Diseño y ejecución de planes de prueba",
                "equivalences": ["test planning", "validación de causa raíz"],
            },
            {
                "label": "Interpretación de datos e informes técnicos",
                "equivalences": ["análisis de resultados", "technical reporting"],
            },
            {
                "label": "Implantación de acciones correctivas",
                "equivalences": ["corrective actions", "prevención de recurrencias"],
            },
            {
                "label": "Documentación y trazabilidad de análisis",
                "equivalences": ["registro de investigaciones", "documentación de calidad"],
            },
        ]
        results = [
            score_lexical_criterion(
                criterion,
                "FMEA",
            )
            for criterion in criteria
        ]

        self.assertEqual(1.0, results[0]["score"])
        self.assertEqual("domain_alias", results[0]["match_source"])
        for result in results[1:]:
            self.assertEqual(0.0, result["score"])
            self.assertNotEqual("domain_alias", result["match_source"])

    def test_equivalences_are_or_and_missing_aliases_do_not_penalize(self):
        criterion = {
            "label": "Programación con Python",
            "equivalences": ["Python 3", "Java"],
        }
        result = score_lexical_criterion(criterion, "Desarrollador backend Java.")

        self.assertEqual(1.0, result["score"])
        self.assertEqual("Java", result["matched_alternative"])
        self.assertEqual(3, result["alternatives_evaluated"])

    def test_isolated_generic_mention_cannot_saturate_a_criterion(self):
        result = score_lexical_criterion(
            {
                "label": "Documentación y trazabilidad de análisis",
                "equivalences": ["documentación de calidad", "registro de investigaciones"],
            },
            "Curso introductorio con una mención a documentación.",
        )

        self.assertGreater(result["score"], 0.0)
        self.assertLessEqual(result["score"], 0.12)
        self.assertFalse(result["exact"])

    def test_basic_negation_suppresses_an_exact_phrase(self):
        result = score_lexical_criterion(
            FAILURE_CRITERION,
            "Perfil de BI sin experiencia demostrable en análisis de fallas ni causa raíz.",
        )

        self.assertLess(result["score"], 0.5)
        self.assertFalse(result["exact"])
        self.assertTrue(result["negated_evidence"])

    def test_explicit_anchor_enables_interpretable_partial_evidence(self):
        result = score_lexical_criterion(
            {
                "label": "Administración de bases de datos PostgreSQL",
                "equivalences": ["database administration"],
                "anchor_terms": ["PostgreSQL"],
            },
            "Migraciones y optimización avanzada en PostgreSQL.",
        )

        self.assertGreater(result["score"], 0.5)
        self.assertLess(result["score"], 1.0)
        self.assertEqual(["postgresql"], result["matched_anchors"])
        self.assertEqual("exact_anchor_phrase", result["reason"])
        self.assertEqual("explicit_anchor", result["match_source"])

    def test_multiword_anchor_is_not_flattened_into_independent_tokens(self):
        result = score_lexical_criterion(
            {
                "label": "Gestión regional multisitio de instalaciones",
                "equivalences": ["multi-site facility management"],
                "anchor_terms": ["varias sedes"],
            },
            "Responsable de una sede y de documentación administrativa.",
        )

        self.assertLess(result["score"], 0.55)
        self.assertNotEqual("explicit_anchor", result["match_source"])

    def test_broad_single_word_anchor_remains_weak(self):
        result = score_lexical_criterion(
            {
                "label": "Seguridad y cumplimiento normativo de instalaciones",
                "equivalences": ["facility compliance"],
                "anchor_terms": ["edificios"],
            },
            "Mantenimiento general de edificios.",
        )

        self.assertLessEqual(result["score"], 0.12)


if __name__ == "__main__":
    unittest.main()
