"""
Top-Down Multi-Agent Learning Harness Orchestrator (`ADsPHarnessOrchestrator`).

Coordinates the 3-Phase Top-Down Learning Loop across the 748 ADsP past questions,
the Event-Sourced SQLite/JSONL Telemetry Store, the 3PL IRT / BKT / FSRS-6 / Brier /
Monte Carlo Psychometric Engine, and the Quota-Aware Multi-Model Agents
(Gemini 3.8 Flash, Claude Sonnet 5.5, Claude Opus 5.5, Gemini 4 Argon, GPT-OSS 120B).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .agents import ADsPMultiAgentSpecialists, AutoErrorNote
from .psychometrics import (
    ADsPPassSimulator,
    IRT3PLEstimator,
    IRTItem,
    IRTResponse,
    MetacogQuadrant,
    MetacognitionEngine,
)
from .quota_router import QuotaAwareModelRouter
from .telemetry import LearnerStateDB


class ADsPHarnessOrchestrator:
    """
    Central orchestrator for the ADsP Top-Down Adaptive Learning Harness:
    - Phase 1: Top-Down Past Exam Solving -> Auto Error Note (Flash) -> 2-Turn Socratic Q&A (Sonnet) -> Confused/Wrong Re-testing
    - Phase 2: Data-Driven Global Weakness Analysis (Opus) & Metacognitive Calibration (Sonnet/Argon) + Monte Carlo Pass/Cutoff Simulation
    - Phase 3: Longitudinal Concept Drift Extrapolation & Out-of-Distribution (OOD) Cognitive Vaccine Loop (Opus + Argon)
    """

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        learner_id: str = "default_learner",
        db_path: Optional[str] = None,
        live_cli: bool = False,
    ):
        self.workspace_root = Path(workspace_root or Path(__file__).resolve().parent.parent)
        self.learner_id = learner_id
        self.data_dir = self.workspace_root / "adsp_harness" / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        default_db = self.data_dir / "learner_state.db"
        default_jsonl = self.data_dir / "learner_events.jsonl"
        self.db = LearnerStateDB(
            db_path=db_path or str(default_db),
            jsonl_path=str(default_jsonl) if db_path is None else str(Path(db_path).with_suffix(".jsonl")),
        )
        self.router = QuotaAwareModelRouter()
        self.specialists = ADsPMultiAgentSpecialists(router=self.router, live_cli=live_cli)

        self.questions: List[Dict[str, Any]] = self._load_corpus()
        self.items_by_id: Dict[str, Dict[str, Any]] = {q["item_id"]: q for q in self.questions}

    def _load_corpus(self) -> List[Dict[str, Any]]:
        """Load the enriched 748-question Q-Matrix if available, or enrich on the fly from adsp_all.json."""
        q_matrix_path = self.data_dir / "q_matrix_748.json"
        if q_matrix_path.exists():
            with open(q_matrix_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "items" in data:
                    return data["items"]
                if isinstance(data, list):
                    return data

        raw_path = self.workspace_root / "adsp_crawler" / "data" / "adsp_all.json"
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f)

        enriched = []
        for q in raw_items:
            r = int(q["round"])
            qno = int(q["question_no"])
            subj = 1 if qno <= 10 else (2 if qno <= 20 else 3)
            item_id = f"R{r}-Q{qno:02d}"
            prompt = q["prompt"]
            neg = any(
                kw in prompt
                for kw in ("옳지 않은", "적절하지 않은", "아닌 것은", "거리가 먼", "틀린", "부적절한", "잘못된")
            )
            if q["question_type"] == "단답형":
                arch = "SHORT_ANSWER"
            elif "```" in prompt:
                arch = "R_CODE_OUTPUT"
            elif "|" in prompt and "---" in prompt:
                arch = "TABLE_CALC"
            else:
                arch = "CONCEPTUAL_4C"

            cid = f"C0{subj}_CORE"
            text = (prompt + " " + " ".join(q.get("options", []))).lower()
            if "회귀" in text or "vif" in text or "결정계수" in text:
                cid = "C14_REGRESSION_OLS_VIF"
            elif "라쏘" in text or "릿지" in text or "전진" in text or "후진" in text or "단계" in text:
                cid = "C15_VARIABLE_SELECTION_PENALTY"
            elif "로지스틱" in text or "오즈" in text:
                cid = "C16_LOGISTIC_REGRESSION"
            elif "주성분" in text or "pca" in text or "요인분석" in text:
                cid = "C17_PCA_DIMENSION_REDUCTION"
            elif "시계열" in text or "정상성" in text or "arima" in text:
                cid = "C18_TIME_SERIES_ARIMA"
            elif "의사결정나무" in text or "불순도" in text or "지니" in text or "가지치기" in text:
                cid = "C19_DECISION_TREE"
            elif "앙상블" in text or "배깅" in text or "부스팅" in text or "랜덤포레스트" in text:
                cid = "C20_ENSEMBLE_BAGGING_BOOSTING"
            elif "신경망" in text or "활성화" in text or "은닉층" in text or "퍼셉트론" in text:
                cid = "C21_ANN_DEEP_LEARNING"
            elif "혼동행렬" in text or "정밀도" in text or "재현율" in text or "roc" in text or "불균형" in text or "smote" in text:
                cid = "C23_MODEL_EVAL_IMBALANCED"
            elif "군집" in text or "k-평균" in text or "계층적" in text or "som" in text:
                cid = "C24_CLUSTERING_SOM_GMM"
            elif "지지도" in text or "신뢰도" in text or "향상도" in text or "연관" in text:
                cid = "C25_ASSOCIATION_APRIORI"
            elif "귀무가설" in text or "유의수준" in text or "p-value" in text or "1종" in text:
                cid = "C11_HYPOTHESIS_TESTING"
            elif "왜도" in text or "첨도" in text or "사분위수" in text or "이상값" in text or "이상치" in text or "esd" in text:
                cid = "C09_DESC_STATS_OUTLIER"
            elif "마스터플랜" in text or "우선순위" in text or "시급성" in text or "거버넌스" in text or "isp" in text:
                cid = "C07_MASTERPLAN_GOVERNANCE"
            elif "crisp" in text or "kdd" in text or "방법론" in text:
                cid = "C06_METHODOLOGY_KDD_CRISP"
            elif "하향식" in text or "상향식" in text or "프로토타이핑" in text:
                cid = "C05_PLAN_TOPDOWN_BOTTOMUP"
            elif "개인정보" in text or "비식별" in text or "위기" in text or "책임" in text:
                cid = "C03_BIGDATA_VALUE_PRIVACY"
            elif "웨어하우스" in text or "레이크" in text or "마트" in text or "dbms" in text or "sql" in text:
                cid = "C02_DB_DW_LAKE"
            elif subj == 1:
                cid = "C01_DATA_DIKW"

            q_copy = dict(q)
            q_copy.update(
                {
                    "item_id": item_id,
                    "subject": subj,
                    "concept_ids": [cid],
                    "primary_concept_id": cid,
                    "stem_polarity": "NEGATIVE" if neg else "POSITIVE",
                    "archetype": arch,
                    "irt_params": {
                        "a": 1.35 if arch in ("R_CODE_OUTPUT", "TABLE_CALC") else 1.10,
                        "b": 0.65 if neg or arch in ("R_CODE_OUTPUT", "TABLE_CALC") else -0.10,
                        "c": 0.25 if q["question_type"] == "4지선다" else 0.0,
                    },
                }
            )
            enriched.append(q_copy)
        return enriched

    # =========================================================================
    # Phase 1: Top-Down Exam Solving, Auto Error Note & Socratic Q&A Loop
    # =========================================================================
    def get_phase1_questions(
        self,
        round_no: Optional[int] = 50,
        subject: Optional[int] = None,
        limit: int = 10,
        prioritize_weak_or_confused: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve questions for Phase 1 top-down solving.
        Defaults to starting from the latest exam round (Round 50 -> 49 -> ...),
        or adaptive remediation of wrong/confused concepts when `prioritize_weak_or_confused=True`.
        """
        pool = self.questions
        if round_no is not None and not prioritize_weak_or_confused:
            pool = [q for q in pool if int(q["round"]) == int(round_no)]
        if subject is not None:
            pool = [q for q in pool if int(q["subject"]) == int(subject)]

        if prioritize_weak_or_confused:
            top_confused = self.db.get_top_confused_concepts(self.learner_id, limit=5)
            weak_cids = {c["concept_id"] for c in top_confused}
            if weak_cids:
                weak_pool = [
                    q
                    for q in pool
                    if (q.get("primary_concept_id") in weak_cids)
                    or any(c in weak_cids for c in q.get("concept_ids", []))
                ]
                if weak_pool:
                    pool = weak_pool

        return pool[:limit]

    def submit_phase1_attempt(
        self,
        item_id: str,
        selected_option: str,
        confidence_rating: int,
        response_time_ms: int = 18000,
        learner_socratic_reply: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a single question attempt in Phase 1:
        1. Grade correctness & compute 2x2 Metacognitive Quadrant (`MASTERED`, `LUCKY_GUESS_CONFUSED`, `ILLUSION_OF_COMPETENCE`, `KNOWN_UNKNOWN`).
        2. If `MASTERED` (Q1): Skip error note & Socratic dialogue -> save 100% of review time.
        3. If `Q2` (Lucky Guess / Confused), `Q3` (High-Confidence Error), or `Q4` (Known Unknown):
           - Invoke `AutoErrorNoteAgent` (Flash) to synthesize a 1-line invariant + option contrast note (saving ~4 mins of manual note-taking).
           - Invoke `SocraticTutorAgent` (Sonnet) to conduct a 2-turn Socratic Q&A that triggers Dopaminergic RPE & Hypercorrection.
        """
        if item_id not in self.items_by_id:
            raise KeyError(f"Unknown item_id: {item_id}")
        q = self.items_by_id[item_id]
        ans = str(q["answer"]).strip()
        sel = str(selected_option).strip()
        is_correct = (sel.lower() == ans.lower())

        conf_prob = MetacognitionEngine.get_confidence_prob(confidence_rating)
        quadrant = MetacognitionEngine.classify_quadrant(is_correct, conf_prob).value
        cids = q.get("concept_ids") or [q.get("primary_concept_id", f"C0{q['subject']}_CORE")]
        primary_cid = cids[0]

        needs_intervention = quadrant in (
            MetacogQuadrant.LUCKY_GUESS_CONFUSED.value,
            MetacogQuadrant.ILLUSION_OF_COMPETENCE.value,
            MetacogQuadrant.KNOWN_UNKNOWN.value,
        )

        auto_note: Optional[AutoErrorNote] = None
        socratic_turn1: Optional[Dict[str, Any]] = None
        socratic_turn2: Optional[Dict[str, Any]] = None

        if needs_intervention:
            auto_note = self.specialists.generate_auto_error_note(q, sel, quadrant)
            socratic_turn1 = self.specialists.generate_socratic_turn(q, sel, quadrant, learner_reply=None)
            if learner_socratic_reply:
                socratic_turn2 = self.specialists.generate_socratic_turn(
                    q, sel, quadrant, learner_reply=learner_socratic_reply
                )

        # Map our 5-class ADsP error taxonomy to Telemetry's ErrorTaxonomyType
        err_tax_map = {
            "POLARITY_TRAP": "MISREAD_NEGATIVE",
            "QUANTIFIER_TRAP": "ILLUSION_OF_COMPETENCE",
            "CONCEPT_SWAP": "INVERSION_OF_TERMS",
            "TABLE_CALC_ERROR": "CALCULATION_SLIP",
            "R_OUTPUT_MISREAD": "CONCEPTUAL_CONFUSION",
            "NONE_CORRECT": "NONE",
        }
        mapped_err = err_tax_map.get(auto_note.error_taxonomy if auto_note else "NONE_CORRECT", "CONCEPTUAL_CONFUSION")

        attempt_rec = self.db.record_attempt(
            learner_id=self.learner_id,
            item_id=item_id,
            subject=int(q["subject"]),
            concept_id=primary_cid,
            selected_option=sel,
            correct_answer=ans,
            is_correct=is_correct,
            confidence_rating=confidence_rating,
            response_time_ms=response_time_ms,
            round_no=int(q["round"]),
            error_type=mapped_err if not is_correct else "NONE",
            auto_generate_note=(not is_correct),
            note_why_wrong=auto_note.why_wrong_diagnosis if auto_note else "",
            note_invariant_rule=auto_note.core_invariant_rule if auto_note else "",
            note_confused_diff=auto_note.confused_options_contrast if auto_note else "",
        )

        return {
            "attempt": asdict(attempt_rec),
            "question_summary": {
                "item_id": item_id,
                "round": q["round"],
                "question_no": q["question_no"],
                "subject": q["subject"],
                "concept_id": primary_cid,
                "stem_polarity": q.get("stem_polarity", "POSITIVE"),
                "archetype": q.get("archetype", "CONCEPTUAL_4C"),
            },
            "needs_intervention": needs_intervention,
            "auto_error_note": asdict(auto_note) if auto_note else None,
            "socratic_turn_1": socratic_turn1,
            "socratic_turn_2": socratic_turn2,
        }

    # =========================================================================
    # Phase 2: Global Weakness Diagnosis & Metacognitive Calibration Loop
    # =========================================================================
    def run_phase2_global_analysis(self) -> Dict[str, Any]:
        """
        Execute Phase 2 after solving past exam rounds:
        1. Extract Root-Cause Error Taxonomy Breakdown & Co-occurrence Error Clusters.
        2. Rank Top Confused Concepts (combining Q3 high-confidence errors & Q2 lucky guesses).
        3. Compute Murphy's 3-Component Brier Score Decomposition & ECE.
        4. Run 5,000-trial Bayesian Monte Carlo ADsP Pass & 40% Subject Cutoff Risk Simulation.
        5. Synthesize Opus Root-Cause Diagnosis + Sonnet Metacognitive Calibration Report.
        """
        tax_breakdown = self.db.get_error_taxonomy_breakdown(self.learner_id)
        co_clusters = self.db.get_cooccurrence_error_clusters(self.learner_id, min_cooccurrence=1)
        top_confused = self.db.get_top_confused_concepts(self.learner_id, limit=8)
        gates = self.db.evaluate_readiness_gates(self.learner_id)

        brier_dict = asdict(gates.metacog_calibration)
        sim_dict = asdict(gates.simulation_result)

        analytics_summary = {
            "total_attempts": gates.total_attempts,
            "avg_bkt_mastery": gates.avg_bkt_mastery,
            "error_taxonomy": tax_breakdown,
            "cooccurrence_clusters": co_clusters[:5],
            "top_confused_concepts": top_confused,
            "readiness_gates": {
                "current_phase": gates.current_phase,
                "gate_1_passed": gates.gate_1_foundation_passed,
                "gate_2_passed": gates.gate_2_debiasing_passed,
                "gate_3_passed": gates.gate_3_exam_ready_passed,
                "recommended_action": gates.recommended_action,
            },
        }

        report = self.specialists.synthesize_phase2_diagnostic_report(
            analytics_summary=analytics_summary,
            brier_metrics=brier_dict,
            pass_sim=sim_dict,
        )
        return report

    # =========================================================================
    # Phase 3: Longitudinal Trend Extrapolation & OOD Cognitive Vaccine Loop
    # =========================================================================
    def run_phase3_ood_vaccine_session(self, count: int = 5) -> Dict[str, Any]:
        """
        Execute Phase 3:
        1. Load longitudinal Concept Drift signals from Rounds 46–50 (`concept_drift_report.json`).
        2. Intersect with learner's top confused/weak concepts from Phase 2.
        3. Invoke Tri-Agent Pipeline (Opus Generator -> Argon/GPT-OSS Critic -> SIT Cognitive Vaccine)
           to deliver unseen Out-of-Distribution (OOD) exam items that eliminate exam-day cognitive dissonance.
        """
        drift_path = self.data_dir / "concept_drift_report.json"
        drift_summary = {}
        if drift_path.exists():
            with open(drift_path, "r", encoding="utf-8") as f:
                drift_summary = json.load(f)

        top_confused = self.db.get_top_confused_concepts(self.learner_id, limit=5)
        weak_cids = [c["concept_id"] for c in top_confused]

        ood_items = self.specialists.generate_and_verify_ood_vaccine_items(
            weak_concepts=weak_cids,
            count=count,
        )

        return {
            "phase": "Phase 3: Out-of-Distribution (OOD) Trend Extrapolation & Cognitive Vaccine",
            "learner_weak_concepts_targeted": weak_cids,
            "recent_round_46_50_drift_highlights": drift_summary.get(
                "emerging_keywords_46_50",
                ["SMOTE", "Elastic Net", "ESD", "GMM", "SECI", "MLP/Hyperbolic Tangent", "ANOVA Table Reconstruction"],
            ),
            "ood_vaccine_items": ood_items,
        }

