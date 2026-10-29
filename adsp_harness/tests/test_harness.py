"""
Comprehensive Test Suite for ADsP Psychometrics & Telemetry Harness
===================================================================
Verifies mathematical precision, calibration decomposition, Monte Carlo
simulation, and SQLite+JSONL event-sourced storage.
"""

import json
import math
import os
import shutil
import tempfile
import unittest

from adsp_harness.psychometrics import (
    ADsPPassSimulator,
    BKT_FSRS_Tracker,
    BKTParameters,
    ConfidenceLevel,
    FSRSParameters,
    FSRSState,
    IRT3PLEstimator,
    IRTItem,
    IRTResponse,
    MetacogQuadrant,
    MetacognitionEngine,
)
from adsp_harness.telemetry import (
    AttemptRecord,
    ErrorTaxonomyType,
    LearnerStateDB,
    ResolvedStatus,
)


class TestPsychometrics(unittest.TestCase):
    """Rigorous tests for psychometric mathematical formulas."""

    def test_irt_3pl_probability_exact(self):
        """Verify 3PL IRT probability against exact analytical values."""
        item = IRTItem(
            item_id="q1",
            difficulty=0.0,
            discrimination=1.0,
            guessing=0.25,
            subject=1,
        )
        # When theta == b (0.0), z = 1.702 * 1.0 * (0 - 0) = 0.
        # sigmoid(0) = 0.5.
        # P = 0.25 + (1 - 0.25) * 0.5 = 0.25 + 0.375 = 0.625.
        p = IRT3PLEstimator.probability(0.0, item)
        self.assertAlmostEqual(p, 0.625, places=5)

        # When theta -> +inf, P -> 1.0
        p_high = IRT3PLEstimator.probability(10.0, item)
        self.assertGreater(p_high, 0.999)

        # When theta -> -inf, P -> c (0.25)
        p_low = IRT3PLEstimator.probability(-10.0, item)
        self.assertAlmostEqual(p_low, 0.25, places=3)

    def test_irt_fisher_information(self):
        """Verify Fisher Information is non-negative and peaks near item difficulty."""
        item = IRTItem(item_id="q2", difficulty=0.5, discrimination=1.2, guessing=0.25, subject=2)
        info_at_b = IRT3PLEstimator.item_information(0.5, item)
        info_far = IRT3PLEstimator.item_information(4.0, item)

        self.assertGreater(info_at_b, 0.0)
        self.assertGreater(info_at_b, info_far)

    def test_irt_map_and_eap_estimation(self):
        """Test MAP and EAP ability estimators recover high/low learner abilities."""
        items = [
            IRTItem(item_id=f"item_{i}", difficulty=-1.0 + 0.5 * i, discrimination=1.0, guessing=0.25, subject=1)
            for i in range(5)
        ]
        # Strong learner: all correct
        strong_resp = [IRTResponse(item=it, is_correct=True) for it in items]
        theta_map, se_map = IRT3PLEstimator.estimate_theta_map(strong_resp)
        theta_eap, se_eap = IRT3PLEstimator.estimate_theta_eap(strong_resp)

        self.assertGreater(theta_map, 0.5)
        self.assertGreater(theta_eap, 0.5)
        self.assertGreater(se_map, 0.0)
        self.assertGreater(se_eap, 0.0)

        # Weak learner: all incorrect
        weak_resp = [IRTResponse(item=it, is_correct=False) for it in items]
        w_theta_map, _ = IRT3PLEstimator.estimate_theta_map(weak_resp)
        w_theta_eap, _ = IRT3PLEstimator.estimate_theta_eap(weak_resp)

        self.assertLess(w_theta_map, 0.0)
        self.assertLess(w_theta_eap, 0.0)

    def test_adaptive_item_selection(self):
        """Test item selection selects the item with highest Fisher information at theta."""
        it_easy = IRTItem(item_id="easy", difficulty=-2.0, discrimination=1.5, guessing=0.25, subject=1)
        it_hard = IRTItem(item_id="hard", difficulty=2.0, discrimination=1.5, guessing=0.25, subject=1)

        # For low ability learner (theta = -1.8), it_easy should be selected
        selected_low = IRT3PLEstimator.select_next_item(-1.8, [it_easy, it_hard])
        self.assertEqual(selected_low.item_id, "easy")

        # For high ability learner (theta = 1.8), it_hard should be selected
        selected_high = IRT3PLEstimator.select_next_item(1.8, [it_easy, it_hard])
        self.assertEqual(selected_high.item_id, "hard")

    def test_fsrs6_retrievability_exact_at_stability(self):
        """Verify FSRS-6 retrievability formula: R(S, S) = 90% exactly."""
        state = FSRSState(difficulty=5.0, stability=10.0)
        params = FSRSParameters()
        # R(10, 10) = (1 + 19/81 * 1.0)^(-0.5) = (100/81)^(-0.5) = 9/10 = 0.90
        r = state.retrievability(10.0, params)
        self.assertAlmostEqual(r, 0.90, places=5)

    def test_bkt_confidence_modulation_and_hypercorrection(self):
        """Verify BKT confidence-weighted update and Hypercorrection boost."""
        tracker = BKT_FSRS_Tracker()

        # Prior = 0.30
        # Correct with high confidence (0.95) -> large mastery increase
        mastery_high = tracker.update_bkt(0.30, is_correct=True, confidence_prob=0.95)
        # Correct with low confidence (0.25) -> lucky guess, smaller mastery increase
        mastery_lucky = tracker.update_bkt(0.30, is_correct=True, confidence_prob=0.25)

        self.assertGreater(mastery_high, mastery_lucky)

        # Test Hypercorrection boost
        fsrs_state = FSRSState(difficulty=6.0, stability=2.0)
        boosted_state, boosted_bkt = tracker.apply_hypercorrection_boost(
            fsrs_state, bkt_mastery=0.40, socratic_resolved=True
        )
        self.assertGreater(boosted_state.stability, fsrs_state.stability)
        self.assertLess(boosted_state.difficulty, fsrs_state.difficulty)
        self.assertGreater(boosted_bkt, 0.70)

    def test_murphy_brier_decomposition_identity(self):
        """
        Verify Murphy's 3-component decomposition mathematical identity:
          Brier Score == Reliability - Resolution + Uncertainty
        using discrete confidence ratings.
        """
        observations = [
            (0.95, True),
            (0.95, True),
            (0.95, False), # Illusion of competence
            (0.75, True),
            (0.75, False),
            (0.50, True),  # Lucky guess
            (0.50, False),
            (0.25, False),
            (0.25, False),
            (0.25, True),  # Lucky guess
        ]
        calib = MetacognitionEngine.murphy_brier_decomposition(observations)

        # Check identity: REL - RES + UNC == BS
        reconstructed_bs = calib.reliability - calib.resolution + calib.uncertainty
        self.assertAlmostEqual(calib.brier_score, reconstructed_bs, places=2)
        self.assertGreater(calib.brier_score, 0.0)
        self.assertGreater(calib.ece, 0.0)

        # Check 2x2 quadrants
        self.assertEqual(calib.quadrant_counts[MetacogQuadrant.ILLUSION_OF_COMPETENCE.value], 2)
        self.assertEqual(calib.quadrant_counts[MetacogQuadrant.MASTERED.value], 3)
        self.assertEqual(calib.quadrant_counts[MetacogQuadrant.LUCKY_GUESS_CONFUSED.value], 2)
        self.assertEqual(calib.quadrant_counts[MetacogQuadrant.KNOWN_UNKNOWN.value], 3)

    def test_adsp_pass_simulator(self):
        """Verify ADsP Monte Carlo pass simulator and cutoff risk detection."""
        # Case A: Very high ability learner (theta = 2.0 across all subjects)
        sim_high = ADsPPassSimulator.simulate_exam(
            subject_thetas={1: 2.0, 2: 2.0, 3: 2.0},
            num_trials=2000,
            random_seed=42,
        )
        self.assertGreater(sim_high.pass_probability, 0.95)
        self.assertGreater(sim_high.expected_total_score, 80.0)
        self.assertLess(sim_high.overall_cutoff_risk, 0.01)

        # Case B: Learner with severe Subject 1 weakness (theta_1 = -2.5, theta_2 = 1.0, theta_3 = 1.0)
        sim_weak_s1 = ADsPPassSimulator.simulate_exam(
            subject_thetas={1: -2.5, 2: 1.0, 3: 1.0},
            num_trials=2000,
            random_seed=42,
        )
        self.assertEqual(sim_weak_s1.bottleneck_subject, 1)
        self.assertGreater(sim_weak_s1.subject_cutoff_risk[1], 0.20)
        self.assertLess(sim_weak_s1.pass_probability, sim_high.pass_probability)

        # Test pure-Python fallback matches numpy logic
        probs_mock = {
            1: [0.7] * 10,
            2: [0.7] * 10,
            3: [0.7] * 30,
        }
        res_py = ADsPPassSimulator._simulate_pure_python(probs_mock, num_trials=1000)
        self.assertGreater(res_py.pass_probability, 0.70)
        self.assertAlmostEqual(res_py.expected_total_score, 70.0, delta=4.0)


class TestTelemetryDB(unittest.TestCase):
    """Tests for SQLite + JSONL event-sourced LearnerStateDB."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_learner.db")
        self.jsonl_path = os.path.join(self.test_dir, "test_events.jsonl")
        self.db = LearnerStateDB(db_path=self.db_path, jsonl_path=self.jsonl_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_record_attempt_and_jsonl_event(self):
        """Test recording an attempt writes to SQLite and appends JSONL event."""
        learner_id = "user_001"
        rec = self.db.record_attempt(
            learner_id=learner_id,
            item_id="q_50_01",
            subject=1,
            concept_id="dikw_pyramid",
            selected_option="2",
            correct_answer="2",
            is_correct=True,
            confidence_rating=4, # Certain (0.95)
            round_no=50,
        )

        self.assertEqual(rec.metacog_quadrant, MetacogQuadrant.MASTERED.value)
        self.assertEqual(rec.confidence_prob, 0.95)

        # Verify JSONL log contains the event
        self.assertTrue(os.path.exists(self.jsonl_path))
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        event_obj = json.loads(lines[0])
        self.assertEqual(event_obj["event_type"], "ATTEMPT_RECORDED")
        self.assertEqual(event_obj["learner_id"], learner_id)
        self.assertEqual(event_obj["payload"]["concept_id"], "dikw_pyramid")

    def test_error_note_generation_and_resolution(self):
        """Test auto-generation of error notes and Socratic resolution with Hypercorrection."""
        learner_id = "user_002"
        # High confidence error -> Illusion of Competence
        rec = self.db.record_attempt(
            learner_id=learner_id,
            item_id="q_50_03",
            subject=1,
            concept_id="tacit_explicit_knowledge",
            selected_option="4",
            correct_answer="4",
            is_correct=False,
            confidence_rating=4, # High confidence error
            round_no=50,
            error_type=ErrorTaxonomyType.INVERSION_OF_TERMS,
            note_why_wrong="암묵지를 '겉으로 드러난 유형의 지식'으로 오인",
            note_invariant_rule="암묵지: 경험 체화/공유 어려움, 형식지: 문서화/체계화/공유 용이",
            note_confused_diff="암묵지와 형식지의 정의를 정반대로 전도함",
        )
        self.assertEqual(rec.metacog_quadrant, MetacogQuadrant.ILLUSION_OF_COMPETENCE.value)

        # Check error note in DB
        with self.db._get_connection() as conn:
            notes = conn.execute(
                "SELECT * FROM error_notes WHERE learner_id = ?", (learner_id,)
            ).fetchall()
        self.assertEqual(len(notes), 1)
        note_id = notes[0]["note_id"]
        self.assertEqual(notes[0]["resolved_status"], ResolvedStatus.UNRESOLVED.value)

        # Resolve via Socratic dialogue
        resolved = self.db.resolve_error_note(
            note_id=note_id,
            learner_id=learner_id,
            socratic_dialogue_log="Q: 매뉴얼로 공유 가능한 지식은? A: 형식지. 오개념 교정 완료.",
            apply_hypercorrection=True,
        )
        self.assertTrue(resolved)

        # Check concept mastery received Hypercorrection boost
        with self.db._get_connection() as conn:
            m = conn.execute(
                "SELECT * FROM concept_mastery WHERE concept_id = ? AND learner_id = ?",
                ("tacit_explicit_knowledge", learner_id),
            ).fetchone()
        self.assertGreater(float(m["bkt_p_learn"]), 0.50)
        self.assertGreater(float(m["fsrs_stability"]), 1.5)

    def test_analytics_error_taxonomy_and_clusters(self):
        """Test error taxonomy aggregation and co-occurrence clusters."""
        learner_id = "user_003"
        # Round 48: 2 errors
        self.db.record_attempt(learner_id, "q_48_01", 1, "concept_dikw", "1", "2", False, 4, round_no=48, error_type=ErrorTaxonomyType.INVERSION_OF_TERMS)
        self.db.record_attempt(learner_id, "q_48_02", 1, "concept_tacit", "3", "4", False, 3, round_no=48, error_type=ErrorTaxonomyType.INVERSION_OF_TERMS)
        # Round 49: same 2 errors co-occurring
        self.db.record_attempt(learner_id, "q_49_01", 1, "concept_dikw", "1", "2", False, 4, round_no=49, error_type=ErrorTaxonomyType.INVERSION_OF_TERMS)
        self.db.record_attempt(learner_id, "q_49_02", 1, "concept_tacit", "3", "4", False, 4, round_no=49, error_type=ErrorTaxonomyType.INVERSION_OF_TERMS)
        # Round 50: calculation slip
        self.db.record_attempt(learner_id, "q_50_25", 3, "concept_anova_f", "2", "3", False, 2, round_no=50, error_type=ErrorTaxonomyType.CALCULATION_SLIP)

        # 1. Taxonomy Breakdown
        tax = self.db.get_error_taxonomy_breakdown(learner_id)
        self.assertEqual(tax["total_errors"], 5)
        self.assertEqual(tax["dominant_error_type"], ErrorTaxonomyType.INVERSION_OF_TERMS.value)

        # 2. Co-occurrence clusters
        clusters = self.db.get_cooccurrence_error_clusters(learner_id, min_cooccurrence=2)
        self.assertTrue(len(clusters) >= 1)
        pair = sorted(clusters[0]["concept_pair"])
        self.assertEqual(pair, ["concept_dikw", "concept_tacit"])
        self.assertEqual(clusters[0]["cooccurrence_rounds"], 2)

        # 3. Top confused concepts
        top_concepts = self.db.get_top_confused_concepts(learner_id, limit=5)
        self.assertGreater(len(top_concepts), 0)
        self.assertIn("concept_dikw", [c["concept_id"] for c in top_concepts])

    def test_readiness_gates_evaluation(self):
        """Test evaluation of Phase 1, Phase 2, and Phase 3 readiness gates."""
        learner_id = "user_004"

        # Initially, 0 attempts -> Gate 1 should fail
        report_init = self.db.evaluate_readiness_gates(learner_id)
        self.assertFalse(report_init.gate_1_foundation_passed)
        self.assertFalse(report_init.gate_2_debiasing_passed)
        self.assertFalse(report_init.gate_3_exam_ready_passed)
        self.assertEqual(report_init.current_phase, 1)

        # Simulate 55 successful attempts covering all 3 subjects
        for i in range(12): # Sub 1
            self.db.record_attempt(learner_id, f"s1_{i}", 1, f"c_s1_{i}", "1", "1", True, 4)
        for i in range(12): # Sub 2
            self.db.record_attempt(learner_id, f"s2_{i}", 2, f"c_s2_{i}", "2", "2", True, 4)
        for i in range(35): # Sub 3
            self.db.record_attempt(learner_id, f"s3_{i}", 3, f"c_s3_{i}", "3", "3", True, 4)

        report_advanced = self.db.evaluate_readiness_gates(learner_id)
        self.assertTrue(report_advanced.gate_1_foundation_passed)
        self.assertTrue(report_advanced.gate_2_debiasing_passed)
        self.assertTrue(report_advanced.gate_3_exam_ready_passed)
        self.assertEqual(report_advanced.current_phase, 3)
        self.assertGreater(report_advanced.simulation_result.pass_probability, 0.85)


if __name__ == "__main__":
    unittest.main()
