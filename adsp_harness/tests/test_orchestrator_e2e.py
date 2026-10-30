"""
End-to-End Integration Tests for the ADsP Top-Down Multi-Agent Learning Harness
(`QuotaAwareModelRouter`, `ADsPMultiAgentSpecialists`, `ADsPHarnessOrchestrator`, `cli`).
"""

from __future__ import annotations

from pathlib import Path

from adsp_harness.orchestrator import ADsPHarnessOrchestrator
from adsp_harness.quota_router import QuotaAwareModelRouter, AGENT_ROLE_ROUTING_POLICY


class TestMultiAgentHarnessE2E:
    def test_quota_router_and_role_assignments(self):
        router = QuotaAwareModelRouter()
        summary = router.get_routing_summary()
        assert "quotas" in summary
        assert "role_assignments" in summary
        for role in AGENT_ROLE_ROUTING_POLICY:
            assert role in summary["role_assignments"]
            assigned = summary["role_assignments"][role]
            assert assigned["remaining_quota_pct"] > 0.0
            assert assigned["assigned_model_id"] != ""

    def test_phase1_phase2_phase3_full_loop(self, tmp_path: Path):
        db_file = tmp_path / "test_learner.db"
        orch = ADsPHarnessOrchestrator(
            learner_id="test_edtech_user",
            db_path=str(db_file),
            live_cli=False,
        )
        assert len(orch.questions) == 748

        # Phase 1: Fetch Round 50 questions and submit all 4 metacognitive quadrants
        r50_qs = orch.get_phase1_questions(round_no=50, limit=4)
        assert len(r50_qs) == 4

        # 1) Q1: MASTERED (Correct + Conf 4)
        q0 = r50_qs[0]
        res0 = orch.submit_phase1_attempt(q0["item_id"], q0["answer"], confidence_rating=4)
        assert res0["attempt"]["metacog_quadrant"] == "MASTERED"
        assert res0["needs_intervention"] is False
        assert res0["auto_error_note"] is None

        # 2) Q2: LUCKY_GUESS_CONFUSED (Correct + Conf 2)
        q1 = r50_qs[1]
        res1 = orch.submit_phase1_attempt(
            q1["item_id"],
            q1["answer"],
            confidence_rating=2,
            learner_socratic_reply="불변 원리로 오답 선지를 소거했습니다.",
        )
        assert res1["attempt"]["metacog_quadrant"] == "LUCKY_GUESS_CONFUSED"
        assert res1["needs_intervention"] is True
        assert res1["auto_error_note"] is not None
        assert res1["socratic_turn_1"]["turn"] == 1
        assert res1["socratic_turn_2"]["turn"] == 2

        # 3) Q3: ILLUSION_OF_COMPETENCE (Wrong + Conf 4)
        q2 = r50_qs[2]
        wrong_opt = "1" if str(q2["answer"]) != "1" else "2"
        res2 = orch.submit_phase1_attempt(
            q2["item_id"],
            wrong_opt,
            confidence_rating=4,
            learner_socratic_reply="부정형 발문을 놓쳤습니다.",
        )
        assert res2["attempt"]["metacog_quadrant"] == "ILLUSION_OF_COMPETENCE"
        assert res2["needs_intervention"] is True
        assert res2["auto_error_note"] is not None

        # 4) Q4: KNOWN_UNKNOWN (Wrong + Conf 1)
        q3 = r50_qs[3]
        wrong_opt3 = "1" if str(q3["answer"]) != "1" else "2"
        res3 = orch.submit_phase1_attempt(q3["item_id"], wrong_opt3, confidence_rating=1)
        assert res3["attempt"]["metacog_quadrant"] == "KNOWN_UNKNOWN"
        assert res3["needs_intervention"] is True

        # Phase 2: Global Weakness & Metacognitive Calibration Report
        p2_report = orch.run_phase2_global_analysis()
        assert "metacognitive_profile" in p2_report
        assert "weakness_analysis" in p2_report
        assert "pass_simulation" in p2_report
        assert p2_report["weakness_analysis"]["total_attempts"] == 4

        # Phase 3: OOD Novel Question Generation & SIT Vaccine
        p3_session = orch.run_phase3_ood_vaccine_session(count=5)
        assert len(p3_session["ood_vaccine_items"]) == 5
        for item in p3_session["ood_vaccine_items"]:
            assert item["psychometric_audit"]["single_unambiguous_answer"] is True
            assert len(item["options"]) == 4
            assert "sit_cognitive_vaccine_protocol" in item

        # Verify Socratic resolution & Personalized Master Study Note generation (Q2, Q3, Q4 all persisted)
        resolved = orch.resolve_item_socratic_note(
            item_id=q3["item_id"],
            learner_misconception="데이터베이스 중복 저장이 통합성이라고 오해함",
            corrected_explanation="통합된 데이터(Integrated Data)는 중복을 최소화하는 것이 원칙임",
        )
        assert resolved["resolved_status"] == "RESOLVED"
        assert "중복을 최소화" in resolved["socratic_dialogue_log"]

        note_path = tmp_path / "MY_MASTER_STUDY_NOTE.md"
        note_res = orch.generate_personalized_study_note(output_path=str(note_path))
        assert note_res["total_notes"] == 3  # Q2 + Q3 + Q4 (Q1 MASTERED excluded)
        assert note_res["q3_illusion_count"] == 1
        assert note_res["q4_unknown_count"] == 1
        assert note_res["q2_confused_count"] == 1
        assert note_path.exists()
        content = note_path.read_text(encoding="utf-8")
        assert "최우선 과교정 노트" in content
        assert "중복을 최소화" in content


