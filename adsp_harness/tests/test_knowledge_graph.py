"""Unit tests for ADsP Knowledge Graph, Q-Matrix & Concept Drift."""

import json
from pathlib import Path
import unittest

from adsp_harness.knowledge_graph import (
    ONTOLOGY_DEFINITIONS,
    ONTOLOGY_DICT,
    validate_dag,
    classify_stem_polarity,
    classify_archetype,
    detect_distractor_traps,
    compute_irt_params,
    QMatrixMapper,
    ERAS,
    ALL_ROUNDS
)


class TestKnowledgeGraph(unittest.TestCase):
    def test_ontology_dag_validity(self):
        """Verify ontology has >= 26 nodes and forms a valid DAG."""
        self.assertGreaterEqual(len(ONTOLOGY_DEFINITIONS), 26)
        topo = validate_dag(ONTOLOGY_DEFINITIONS)
        self.assertEqual(len(topo), len(ONTOLOGY_DEFINITIONS))

    def test_ontology_subject_coverage(self):
        """Verify all 3 subjects are covered."""
        subjects = set(c.subject for c in ONTOLOGY_DEFINITIONS)
        self.assertEqual(subjects, {1, 2, 3})

    def test_polarity_classification(self):
        """Verify negative vs positive question stem detection."""
        neg_prompt = "다음 중 빅데이터에 대한 설명으로 옳지 않은 것은?"
        pos_prompt = "다음 중 분산분석에 대한 설명으로 옳은 것은?"
        self.assertEqual(classify_stem_polarity(neg_prompt), "NEGATIVE")
        self.assertEqual(classify_stem_polarity(pos_prompt), "POSITIVE")

    def test_archetype_classification(self):
        """Verify 7 archetypes can be classified correctly."""
        self.assertEqual(classify_archetype("...", "단답형", []), "SHORT_ANSWER")
        self.assertEqual(
            classify_archetype("```r\n> summary(lm(y ~ x))\n```", "4지선다", []),
            "R_CODE_OUTPUT"
        )
        self.assertEqual(
            classify_archetype("| 오분류표 | 예측값 |\n|---|---|\nF1 스코어를 구하시오.", "4지선다", ["0.8", "0.9"]),
            "TABLE_CALC"
        )

    def test_irt_params_boundaries(self):
        """Verify calibrated 3PL IRT parameters conform to standard bounds."""
        irt = compute_irt_params(
            question_type="4지선다",
            archetype="TABLE_CALC",
            stem_polarity="NEGATIVE",
            distractor_traps=["POLARITY_INVERSION", "QUANTIFIER_TRAP"],
            round_no=50,
            subject=3
        )
        self.assertGreaterEqual(irt["a"], 0.8)
        self.assertLessEqual(irt["a"], 1.8)
        self.assertGreaterEqual(irt["b"], -1.5)
        self.assertLessEqual(irt["b"], 2.0)
        self.assertEqual(irt["c"], 0.25)

    def test_q_matrix_file_integrity(self):
        """Verify generated q_matrix_748.json has exactly 748 valid items."""
        q_path = Path("c:/Users/SSAFY/Desktop/ADsP/adsp_harness/data/q_matrix_748.json")
        self.assertTrue(q_path.exists())
        with open(q_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        self.assertEqual(len(items), 748)
        for it in items:
            self.assertIn("item_id", it)
            self.assertIn("round", it)
            self.assertIn("subject", it)
            self.assertIn("concept_ids", it)
            self.assertGreaterEqual(len(it["concept_ids"]), 1)
            self.assertIn(it["primary_concept_id"], ONTOLOGY_DICT)
            self.assertIn(it["stem_polarity"], ["NEGATIVE", "POSITIVE"])
            self.assertIn("irt_params", it)

    def test_concept_drift_report_integrity(self):
        """Verify generated concept_drift_report.json schema and predictions."""
        report_path = Path("c:/Users/SSAFY/Desktop/ADsP/adsp_harness/data/concept_drift_report.json")
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["metadata"]["total_items"], 748)
        self.assertGreaterEqual(len(rep["ontology"]), 26)
        self.assertGreaterEqual(len(rep["emerging_keywords_era3"]), 10)
        self.assertGreaterEqual(len(rep["predicted_ood_topics_round51_plus"]), 5)


if __name__ == "__main__":
    unittest.main()

