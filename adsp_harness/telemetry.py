"""
ADsP Event-Sourced Learner State Store & Metacognitive Telemetry Engine
======================================================================
Stores learner attempt trajectories, error notes, and concept mastery models
in an ACID SQLite database accompanied by an append-only JSONL event log.

Features:
1. LearnerStateDB: Dual SQLite + JSONL event-sourced persistence.
2. Root-Cause Error Taxonomy categorization and breakdown.
3. Co-occurrence Error Clustering for cross-concept confusion pattern detection.
4. Top Confused Concepts ranking by RPE (Reward Prediction Error) priority.
5. Phase 1, Phase 2, and Phase 3 Readiness Gates evaluation.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from adsp_harness.psychometrics import (
    ADsPPassSimulator,
    BKT_FSRS_Tracker,
    CalibrationResult,
    ConfidenceLevel,
    FSRSParameters,
    FSRSState,
    IRT3PLEstimator,
    IRTItem,
    IRTResponse,
    MetacogQuadrant,
    MetacognitionEngine,
    SimulationResult,
)


class ErrorTaxonomyType(Enum):
    """EdTech Root-Cause Error Taxonomy for ADsP Certification."""
    CONCEPTUAL_CONFUSION = "CONCEPTUAL_CONFUSION"     # Fundamental concept misunderstanding
    ILLUSION_OF_COMPETENCE = "ILLUSION_OF_COMPETENCE" # Overconfident error / cognitive bias trap
    INVERSION_OF_TERMS = "INVERSION_OF_TERMS"         # Inversion between paired concepts (암묵지↔형식지, D↔I)
    CALCULATION_SLIP = "CALCULATION_SLIP"             # Formula or arithmetic slip (ANOVA F, Lift ratio, PCA)
    MISREAD_NEGATIVE = "MISREAD_NEGATIVE"             # Framing misread (옳지 않은 것 vs 옳은 것)
    KNOWLEDGE_GAP = "KNOWLEDGE_GAP"                   # Low-confidence unknown concept
    NONE = "NONE"                                     # Correct response or unclassified


class ResolvedStatus(Enum):
    """Resolution lifecycle for auto-generated error notes."""
    UNRESOLVED = "UNRESOLVED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


@dataclass
class AttemptRecord:
    """Detailed record of an individual item attempt."""
    attempt_id: str
    learner_id: str
    item_id: str
    round: Optional[int]
    subject: int
    concept_id: str
    selected_option: str
    correct_answer: str
    is_correct: bool
    confidence_rating: int          # 1: 찍음, 2: 헷갈림, 3: 대체로 확신, 4: 완전 확신
    confidence_prob: float          # 0.25, 0.50, 0.75, 0.95
    response_time_ms: int
    metacog_quadrant: str           # MASTERED, LUCKY_GUESS_CONFUSED, ILLUSION_OF_COMPETENCE, KNOWN_UNKNOWN
    error_type: str                 # ErrorTaxonomyType value
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ErrorNoteRecord:
    """Auto-generated structured error note saving learner's manual writing time."""
    note_id: str
    item_id: str
    learner_id: str
    concept_id: str
    why_wrong_summary: str          # 핵심 오답 원인 (1~2줄 요약)
    core_invariant_rule: str        # 시험에 반복 출제되는 불변 규칙/개념
    confused_options_diff: str      # 내가 고른 오답 선지 vs 정답 선지의 결정적 차이
    socratic_dialogue_log: str      # 소크라테스식 문답 및 오개념 해소 기록
    resolved_status: str            # UNRESOLVED, IN_PROGRESS, RESOLVED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None


@dataclass
class ConceptMasteryRecord:
    """Learner's continuous psychometric state per granular concept."""
    concept_id: str
    learner_id: str
    subject: int
    bkt_p_learn: float = 0.25
    irt_theta: float = 0.0
    fsrs_stability: float = 1.0     # Days until 90% retrievability
    fsrs_difficulty: float = 5.0    # 1.0 to 10.0 scale
    last_review_ts: Optional[str] = None
    attempts_count: int = 0
    error_count: int = 0
    high_conf_error_count: int = 0
    lucky_guess_count: int = 0


@dataclass
class ReadinessGateReport:
    """Comprehensive readiness gate evaluation for Phase 1, Phase 2, and Phase 3."""
    learner_id: str
    evaluated_at: str
    current_phase: int
    total_attempts: int
    avg_bkt_mastery: float
    metacog_calibration: CalibrationResult
    simulation_result: SimulationResult
    gate_1_foundation_passed: bool
    gate_1_details: Dict[str, Any]
    gate_2_debiasing_passed: bool
    gate_2_details: Dict[str, Any]
    gate_3_exam_ready_passed: bool
    gate_3_details: Dict[str, Any]
    recommended_action: str


class LearnerStateDB:
    """
    SQLite + JSONL event-sourced state store for the ADsP Learning Harness.
    Guarantees ACID transactions locally with append-only JSONL audit logs.
    """

    def __init__(
        self,
        db_path: Union[str, Path] = "learner_state.db",
        jsonl_path: Optional[Union[str, Path]] = None,
    ):
        self.db_path = str(db_path)
        if jsonl_path is None:
            base_dir = os.path.dirname(self.db_path) or "."
            self.jsonl_path = os.path.join(base_dir, "events.jsonl")
        else:
            self.jsonl_path = str(jsonl_path)

        # Initialize trackers
        self.tracker = BKT_FSRS_Tracker()
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Create database tables and indices if not already present."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Attempts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    learner_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    round INTEGER,
                    subject INTEGER NOT NULL,
                    concept_id TEXT,
                    selected_option TEXT,
                    correct_answer TEXT,
                    is_correct INTEGER NOT NULL,
                    confidence_rating INTEGER NOT NULL,
                    confidence_prob REAL NOT NULL,
                    response_time_ms INTEGER NOT NULL,
                    metacog_quadrant TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_learner ON attempts(learner_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_learner_subj ON attempts(learner_id, subject)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_concept ON attempts(concept_id)")

            # 2. Error Notes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_notes (
                    note_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    learner_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    why_wrong_summary TEXT NOT NULL,
                    core_invariant_rule TEXT NOT NULL,
                    confused_options_diff TEXT NOT NULL,
                    socratic_dialogue_log TEXT NOT NULL,
                    resolved_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_learner ON error_notes(learner_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_status ON error_notes(learner_id, resolved_status)")

            # 3. Concept Mastery table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS concept_mastery (
                    concept_id TEXT NOT NULL,
                    learner_id TEXT NOT NULL,
                    subject INTEGER NOT NULL,
                    bkt_p_learn REAL NOT NULL,
                    irt_theta REAL NOT NULL,
                    fsrs_stability REAL NOT NULL,
                    fsrs_difficulty REAL NOT NULL,
                    last_review_ts TEXT,
                    attempts_count INTEGER NOT NULL,
                    error_count INTEGER NOT NULL,
                    high_conf_error_count INTEGER NOT NULL,
                    lucky_guess_count INTEGER NOT NULL,
                    PRIMARY KEY (concept_id, learner_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mastery_learner ON concept_mastery(learner_id)")
            conn.commit()

    def _append_event(self, event_type: str, learner_id: str, payload: Dict[str, Any]) -> None:
        """Append an immutable event record to the JSONL log."""
        os.makedirs(os.path.dirname(os.path.abspath(self.jsonl_path)), exist_ok=True)
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "learner_id": learner_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # ==========================================================================
    # Recording Attempts & Updating Mastery
    # ==========================================================================

    def record_attempt(
        self,
        learner_id: str,
        item_id: str,
        subject: int,
        concept_id: str,
        selected_option: str,
        correct_answer: str,
        is_correct: bool,
        confidence_rating: int,
        response_time_ms: int = 15000,
        round_no: Optional[int] = None,
        error_type: Optional[Union[str, ErrorTaxonomyType]] = None,
        auto_generate_note: bool = True,
        note_why_wrong: str = "",
        note_invariant_rule: str = "",
        note_confused_diff: str = "",
        note_socratic_log: str = "",
        note_resolved: bool = False,
    ) -> AttemptRecord:
        """
        Record a learner's question attempt, update continuous psychometric mastery
        (BKT + FSRS-6), classify metacognitive quadrant, log JSONL event, and
        optionally generate an initial structured error note.
        """
        confidence_prob = MetacognitionEngine.get_confidence_prob(confidence_rating)
        metacog_quad = MetacognitionEngine.classify_quadrant(is_correct, confidence_prob).value

        # Infer error type if not provided
        if error_type is None:
            if is_correct:
                err_type_str = ErrorTaxonomyType.NONE.value
            else:
                if metacog_quad == MetacogQuadrant.ILLUSION_OF_COMPETENCE.value:
                    err_type_str = ErrorTaxonomyType.ILLUSION_OF_COMPETENCE.value
                else:
                    err_type_str = ErrorTaxonomyType.CONCEPTUAL_CONFUSION.value
        else:
            err_type_str = error_type.value if isinstance(error_type, ErrorTaxonomyType) else str(error_type)

        attempt_id = f"att_{uuid.uuid4().hex[:12]}"
        now_ts = datetime.now(timezone.utc).isoformat()

        record = AttemptRecord(
            attempt_id=attempt_id,
            learner_id=learner_id,
            item_id=item_id,
            round=round_no,
            subject=subject,
            concept_id=concept_id,
            selected_option=selected_option,
            correct_answer=correct_answer,
            is_correct=is_correct,
            confidence_rating=confidence_rating,
            confidence_prob=confidence_prob,
            response_time_ms=response_time_ms,
            metacog_quadrant=metacog_quad,
            error_type=err_type_str,
            timestamp=now_ts,
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Insert Attempt
            cursor.execute(
                """
                INSERT INTO attempts (
                    attempt_id, learner_id, item_id, round, subject, concept_id,
                    selected_option, correct_answer, is_correct, confidence_rating,
                    confidence_prob, response_time_ms, metacog_quadrant, error_type, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.attempt_id,
                    record.learner_id,
                    record.item_id,
                    record.round,
                    record.subject,
                    record.concept_id,
                    record.selected_option,
                    record.correct_answer,
                    1 if record.is_correct else 0,
                    record.confidence_rating,
                    record.confidence_prob,
                    record.response_time_ms,
                    record.metacog_quadrant,
                    record.error_type,
                    record.timestamp,
                ),
            )

            # 2. Retrieve or initialize Concept Mastery
            cursor.execute(
                "SELECT * FROM concept_mastery WHERE concept_id = ? AND learner_id = ?",
                (concept_id, learner_id),
            )
            row = cursor.fetchone()
            if row is None:
                current_p_learn = 0.25
                current_theta = 0.0
                state = FSRSState(difficulty=5.0, stability=1.0)
                attempts_count = 0
                error_count = 0
                high_conf_error_count = 0
                lucky_guess_count = 0
                last_ts = None
            else:
                current_p_learn = float(row["bkt_p_learn"])
                current_theta = float(row["irt_theta"])
                state = FSRSState(
                    difficulty=float(row["fsrs_difficulty"]),
                    stability=float(row["fsrs_stability"]),
                )
                attempts_count = int(row["attempts_count"])
                error_count = int(row["error_count"])
                high_conf_error_count = int(row["high_conf_error_count"])
                lucky_guess_count = int(row["lucky_guess_count"])
                last_ts = row["last_review_ts"]

            # Compute elapsed days for FSRS
            if last_ts:
                try:
                    last_dt = datetime.fromisoformat(last_ts)
                    now_dt = datetime.fromisoformat(now_ts)
                    elapsed_days = max(0.01, (now_dt - last_dt).total_seconds() / 86400.0)
                except Exception:
                    elapsed_days = 1.0
            else:
                elapsed_days = 1.0

            # Update BKT
            new_p_learn = self.tracker.update_bkt(current_p_learn, is_correct, confidence_prob)

            # Update FSRS
            fsrs_rating = confidence_rating if is_correct else 1
            new_fsrs_state = self.tracker.update_fsrs(state, elapsed_days, is_correct, rating=fsrs_rating)

            # Update stats
            attempts_count += 1
            if not is_correct:
                error_count += 1
                if metacog_quad == MetacogQuadrant.ILLUSION_OF_COMPETENCE.value:
                    high_conf_error_count += 1
            else:
                if metacog_quad == MetacogQuadrant.LUCKY_GUESS_CONFUSED.value:
                    lucky_guess_count += 1

            # Update IRT theta increment approximation
            theta_delta = 0.15 if is_correct else -0.15
            new_theta = max(-4.0, min(4.0, current_theta + theta_delta))

            cursor.execute(
                """
                INSERT INTO concept_mastery (
                    concept_id, learner_id, subject, bkt_p_learn, irt_theta,
                    fsrs_stability, fsrs_difficulty, last_review_ts, attempts_count,
                    error_count, high_conf_error_count, lucky_guess_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(concept_id, learner_id) DO UPDATE SET
                    bkt_p_learn = excluded.bkt_p_learn,
                    irt_theta = excluded.irt_theta,
                    fsrs_stability = excluded.fsrs_stability,
                    fsrs_difficulty = excluded.fsrs_difficulty,
                    last_review_ts = excluded.last_review_ts,
                    attempts_count = excluded.attempts_count,
                    error_count = excluded.error_count,
                    high_conf_error_count = excluded.high_conf_error_count,
                    lucky_guess_count = excluded.lucky_guess_count
                """,
                (
                    concept_id,
                    learner_id,
                    subject,
                    new_p_learn,
                    new_theta,
                    new_fsrs_state.stability,
                    new_fsrs_state.difficulty,
                    now_ts,
                    attempts_count,
                    error_count,
                    high_conf_error_count,
                    lucky_guess_count,
                ),
            )

            # 3. Auto-generate or update Error/Confusion Note if incorrect or lucky guess (Q2/Q3/Q4)
            should_save_note = auto_generate_note and (
                (not is_correct)
                or (metacog_quad == MetacogQuadrant.LUCKY_GUESS_CONFUSED.value)
                or bool(note_why_wrong)
            )
            if should_save_note:
                cursor.execute(
                    "SELECT note_id, socratic_dialogue_log, resolved_status FROM error_notes WHERE item_id = ? AND learner_id = ? ORDER BY created_at DESC LIMIT 1",
                    (item_id, learner_id),
                )
                existing_note = cursor.fetchone()
                resolved_val = (
                    ResolvedStatus.RESOLVED.value
                    if (note_resolved or bool(note_socratic_log))
                    else (existing_note["resolved_status"] if existing_note else ResolvedStatus.UNRESOLVED.value)
                )
                resolved_ts = now_ts if resolved_val == ResolvedStatus.RESOLVED.value else None
                why_val = note_why_wrong or (
                    f"[찍어서 맞힌 혼동 문항 (Q2)] 정답({correct_answer}번)을 맞혔으나 확신도가 낮아 변별 기준 점검 필요"
                    if is_correct
                    else f"선택지 {selected_option}번 선택 오답 (정답: {correct_answer}번)"
                )
                inv_val = note_invariant_rule or f"개념 [{concept_id}] 기본 정의 및 핵심 불변식 복습 요망"
                diff_val = note_confused_diff or f"선택지 {selected_option}번 vs {correct_answer}번 개념적 전도 차이 분석"
                soc_val = note_socratic_log or (existing_note["socratic_dialogue_log"] if existing_note else "")

                if existing_note:
                    cursor.execute(
                        """
                        UPDATE error_notes SET
                            concept_id = ?,
                            why_wrong_summary = ?,
                            core_invariant_rule = ?,
                            confused_options_diff = ?,
                            socratic_dialogue_log = ?,
                            resolved_status = ?,
                            resolved_at = COALESCE(?, resolved_at)
                        WHERE note_id = ?
                        """,
                        (
                            concept_id,
                            why_val,
                            inv_val,
                            diff_val,
                            soc_val,
                            resolved_val,
                            resolved_ts,
                            existing_note["note_id"],
                        ),
                    )
                else:
                    note_id = f"note_{uuid.uuid4().hex[:12]}"
                    cursor.execute(
                        """
                        INSERT INTO error_notes (
                            note_id, item_id, learner_id, concept_id, why_wrong_summary,
                            core_invariant_rule, confused_options_diff, socratic_dialogue_log,
                            resolved_status, created_at, resolved_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            note_id,
                            item_id,
                            learner_id,
                            concept_id,
                            why_val,
                            inv_val,
                            diff_val,
                            soc_val,
                            resolved_val,
                            now_ts,
                            resolved_ts,
                        ),
                    )

            conn.commit()

        # Emit audit event to JSONL
        self._append_event("ATTEMPT_RECORDED", learner_id, asdict(record))

        return record

    def upsert_or_resolve_note_by_item(
        self,
        learner_id: str,
        item_id: str,
        concept_id: str,
        why_wrong_summary: Optional[str] = None,
        core_invariant_rule: Optional[str] = None,
        confused_options_diff: Optional[str] = None,
        socratic_dialogue_log: str = "",
        apply_hypercorrection: bool = True,
    ) -> Dict[str, Any]:
        """
        Create or update an error/confusion note by `item_id`, recording the learner's
        initial misconception and the Socratic corrected explanation, and marking it RESOLVED.
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM error_notes WHERE item_id = ? AND learner_id = ? ORDER BY created_at DESC LIMIT 1",
                (item_id, learner_id),
            )
            existing = cursor.fetchone()
            if existing:
                note_id = existing["note_id"]
                cid = concept_id or existing["concept_id"]
                why_val = why_wrong_summary or existing["why_wrong_summary"]
                inv_val = core_invariant_rule or existing["core_invariant_rule"]
                diff_val = confused_options_diff or existing["confused_options_diff"]
                soc_val = socratic_dialogue_log or existing["socratic_dialogue_log"]
                cursor.execute(
                    """
                    UPDATE error_notes SET
                        concept_id = ?,
                        why_wrong_summary = ?,
                        core_invariant_rule = ?,
                        confused_options_diff = ?,
                        socratic_dialogue_log = ?,
                        resolved_status = ?,
                        resolved_at = ?
                    WHERE note_id = ?
                    """,
                    (
                        cid,
                        why_val,
                        inv_val,
                        diff_val,
                        soc_val,
                        ResolvedStatus.RESOLVED.value,
                        now_ts,
                        note_id,
                    ),
                )
            else:
                note_id = f"note_{uuid.uuid4().hex[:12]}"
                cid = concept_id
                why_val = why_wrong_summary or f"[{item_id}] 오답 및 혼동 개념 점검"
                inv_val = core_invariant_rule or f"개념 [{cid}] 핵심 불변 원리"
                diff_val = confused_options_diff or f"[{item_id}] 선지 변별 포인트"
                soc_val = socratic_dialogue_log
                cursor.execute(
                    """
                    INSERT INTO error_notes (
                        note_id, item_id, learner_id, concept_id, why_wrong_summary,
                        core_invariant_rule, confused_options_diff, socratic_dialogue_log,
                        resolved_status, created_at, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        note_id,
                        item_id,
                        learner_id,
                        cid,
                        why_val,
                        inv_val,
                        diff_val,
                        soc_val,
                        ResolvedStatus.RESOLVED.value,
                        now_ts,
                        now_ts,
                    ),
                )
            conn.commit()

        if apply_hypercorrection:
            self.resolve_error_note(
                note_id=note_id,
                learner_id=learner_id,
                socratic_dialogue_log=soc_val,
                apply_hypercorrection=True,
            )

        return {
            "note_id": note_id,
            "item_id": item_id,
            "learner_id": learner_id,
            "concept_id": cid,
            "why_wrong_summary": why_val,
            "core_invariant_rule": inv_val,
            "confused_options_diff": diff_val,
            "socratic_dialogue_log": soc_val,
            "resolved_status": ResolvedStatus.RESOLVED.value,
            "resolved_at": now_ts,
        }

    def get_all_study_notes(self, learner_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all recorded error and confusion notes joined with the latest attempt metadata
        for personalized master study note generation.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    n.note_id,
                    n.item_id,
                    n.learner_id,
                    n.concept_id,
                    n.why_wrong_summary,
                    n.core_invariant_rule,
                    n.confused_options_diff,
                    n.socratic_dialogue_log,
                    n.resolved_status,
                    n.created_at,
                    n.resolved_at,
                    a.round,
                    a.subject,
                    a.selected_option,
                    a.correct_answer,
                    a.is_correct,
                    a.confidence_rating,
                    a.confidence_prob,
                    a.metacog_quadrant,
                    a.error_type
                FROM error_notes n
                LEFT JOIN (
                    SELECT a1.*
                    FROM attempts a1
                    INNER JOIN (
                        SELECT item_id, learner_id, MAX(timestamp) AS max_ts
                        FROM attempts
                        GROUP BY item_id, learner_id
                    ) a2 ON a1.item_id = a2.item_id AND a1.learner_id = a2.learner_id AND a1.timestamp = a2.max_ts
                ) a ON n.item_id = a.item_id AND n.learner_id = a.learner_id
                WHERE n.learner_id = ?
                ORDER BY n.item_id ASC
                """,
                (learner_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_all_concept_mastery(self, learner_id: str) -> List[ConceptMasteryRecord]:
        """Retrieve all ConceptMasteryRecord rows for a learner."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM concept_mastery WHERE learner_id = ? ORDER BY bkt_p_learn ASC",
                (learner_id,),
            )
            return [ConceptMasteryRecord(**dict(row)) for row in cursor.fetchall()]

    def resolve_error_note(
        self,
        note_id: str,
        learner_id: str,
        socratic_dialogue_log: str = "",
        apply_hypercorrection: bool = True,
    ) -> bool:
        """
        Resolve an error note following successful Socratic debiasing.
        If apply_hypercorrection is True, grants the Hypercorrection Boost
        (massive stability multiplier and BKT mastery boost) to the concept.
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM error_notes WHERE note_id = ? AND learner_id = ?",
                (note_id, learner_id),
            )
            note = cursor.fetchone()
            if not note:
                return False

            concept_id = note["concept_id"]

            cursor.execute(
                """
                UPDATE error_notes SET
                    resolved_status = ?,
                    socratic_dialogue_log = ?,
                    resolved_at = ?
                WHERE note_id = ? AND learner_id = ?
                """,
                (
                    ResolvedStatus.RESOLVED.value,
                    socratic_dialogue_log or note["socratic_dialogue_log"],
                    now_ts,
                    note_id,
                    learner_id,
                ),
            )

            # Apply Hypercorrection boost to concept mastery if requested
            if apply_hypercorrection:
                cursor.execute(
                    "SELECT * FROM concept_mastery WHERE concept_id = ? AND learner_id = ?",
                    (concept_id, learner_id),
                )
                m_row = cursor.fetchone()
                if m_row:
                    state = FSRSState(
                        difficulty=float(m_row["fsrs_difficulty"]),
                        stability=float(m_row["fsrs_stability"]),
                    )
                    bkt_m = float(m_row["bkt_p_learn"])
                    boosted_state, boosted_bkt = self.tracker.apply_hypercorrection_boost(
                        state, bkt_m, socratic_resolved=True
                    )
                    cursor.execute(
                        """
                        UPDATE concept_mastery SET
                            bkt_p_learn = ?,
                            fsrs_stability = ?,
                            fsrs_difficulty = ?,
                            last_review_ts = ?
                        WHERE concept_id = ? AND learner_id = ?
                        """,
                        (
                            boosted_bkt,
                            boosted_state.stability,
                            boosted_state.difficulty,
                            now_ts,
                            concept_id,
                            learner_id,
                        ),
                    )

            conn.commit()

        self._append_event(
            "ERROR_NOTE_RESOLVED",
            learner_id,
            {
                "note_id": note_id,
                "concept_id": concept_id,
                "hypercorrection_applied": apply_hypercorrection,
                "resolved_at": now_ts,
            },
        )
        return True

    # ==========================================================================
    # Analytics 1: Root-Cause Error Taxonomy Breakdown
    # ==========================================================================

    def get_error_taxonomy_breakdown(self, learner_id: str) -> Dict[str, Any]:
        """
        Aggregate and categorize learner's errors according to the Root-Cause Taxonomy:
        CONCEPTUAL_CONFUSION, ILLUSION_OF_COMPETENCE, INVERSION_OF_TERMS,
        CALCULATION_SLIP, MISREAD_NEGATIVE, KNOWLEDGE_GAP.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT error_type, metacog_quadrant, COUNT(*) as count
                FROM attempts
                WHERE learner_id = ? AND is_correct = 0
                GROUP BY error_type, metacog_quadrant
                """,
                (learner_id,),
            )
            rows = cursor.fetchall()

        total_errors = sum(r["count"] for r in rows)
        counts_by_type: Dict[str, int] = {}
        high_conf_by_type: Dict[str, int] = {}

        for r in rows:
            et = r["error_type"]
            cnt = r["count"]
            quad = r["metacog_quadrant"]

            counts_by_type[et] = counts_by_type.get(et, 0) + cnt
            if quad == MetacogQuadrant.ILLUSION_OF_COMPETENCE.value:
                high_conf_by_type[et] = high_conf_by_type.get(et, 0) + cnt

        breakdown = []
        for et, cnt in sorted(counts_by_type.items(), key=lambda x: x[1], reverse=True):
            pct = round((cnt / total_errors) * 100.0, 1) if total_errors > 0 else 0.0
            hi_cnt = high_conf_by_type.get(et, 0)
            hi_pct = round((hi_cnt / cnt) * 100.0, 1) if cnt > 0 else 0.0
            breakdown.append({
                "error_type": et,
                "error_count": cnt,
                "percentage_of_total_errors": pct,
                "high_confidence_count": hi_cnt,
                "high_confidence_ratio": hi_pct,
            })

        dominant_type = breakdown[0]["error_type"] if breakdown else "NONE"

        return {
            "learner_id": learner_id,
            "total_errors": total_errors,
            "dominant_error_type": dominant_type,
            "taxonomy_breakdown": breakdown,
        }

    # ==========================================================================
    # Analytics 2: Co-occurrence Error Clusters
    # ==========================================================================

    def get_cooccurrence_error_clusters(
        self,
        learner_id: str,
        min_cooccurrence: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Detect concepts that frequently co-occur as errors in the same exam session
        or study round, highlighting cross-concept confusion clusters.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT round, concept_id
                FROM attempts
                WHERE learner_id = ? AND is_correct = 0 AND round IS NOT NULL AND concept_id != ''
                ORDER BY round, timestamp
                """,
                (learner_id,),
            )
            rows = cursor.fetchall()

        # Group error concepts by round
        round_errors: Dict[int, Set[str]] = {}
        for r in rows:
            rnd = r["round"]
            c_id = r["concept_id"]
            if rnd not in round_errors:
                round_errors[rnd] = set()
            round_errors[rnd].add(c_id)

        # Count pair co-occurrences
        pair_counts: Dict[Tuple[str, str], int] = {}
        concept_counts: Dict[str, int] = {}

        for rnd, concepts in round_errors.items():
            c_list = sorted(list(concepts))
            for c in c_list:
                concept_counts[c] = concept_counts.get(c, 0) + 1
            for i in range(len(c_list)):
                for j in range(i + 1, len(c_list)):
                    pair = (c_list[i], c_list[j])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

        clusters = []
        for (c1, c2), count in sorted(pair_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= min_cooccurrence:
                # Jaccard similarity: intersection / union
                c1_cnt = concept_counts.get(c1, 1)
                c2_cnt = concept_counts.get(c2, 1)
                union = c1_cnt + c2_cnt - count
                jaccard = round(count / union, 3) if union > 0 else 0.0
                clusters.append({
                    "concept_pair": [c1, c2],
                    "cooccurrence_rounds": count,
                    "jaccard_similarity": jaccard,
                    "risk_assessment": "HIGH_CONFUSION_CLUSTER" if jaccard >= 0.50 else "MODERATE_CLUSTER",
                })

        return clusters

    # ==========================================================================
    # Analytics 3: Top Confused Concepts
    # ==========================================================================

    def get_top_confused_concepts(
        self,
        learner_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Rank concepts needing urgent intervention using the Priority Index:
          Priority = 4 * HighConfErrors + 2 * LuckyGuesses + Errors + 6 * (1 - BKT_Mastery)
        High-confidence errors (Illusion of Competence) receive top priority.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT cm.*, 
                       (SELECT COUNT(*) FROM error_notes en 
                        WHERE en.concept_id = cm.concept_id 
                          AND en.learner_id = cm.learner_id 
                          AND en.resolved_status != 'RESOLVED') as unresolved_notes
                FROM concept_mastery cm
                WHERE cm.learner_id = ?
                """,
                (learner_id,),
            )
            rows = cursor.fetchall()

        results = []
        for r in rows:
            c_id = r["concept_id"]
            subj = r["subject"]
            bkt = float(r["bkt_p_learn"])
            stab = float(r["fsrs_stability"])
            diff = float(r["fsrs_difficulty"])
            att_cnt = int(r["attempts_count"])
            err_cnt = int(r["error_count"])
            hi_cnt = int(r["high_conf_error_count"])
            lucky_cnt = int(r["lucky_guess_count"])
            unres_notes = int(r["unresolved_notes"])

            # Compute current retrievability assuming 1 day elapsed
            fsrs_state = FSRSState(difficulty=diff, stability=stab)
            retrievability = round(fsrs_state.retrievability(1.0), 3)

            # Cognitive Priority Index
            priority_score = round(
                4.0 * hi_cnt + 2.0 * lucky_cnt + 1.0 * err_cnt + 6.0 * (1.0 - bkt),
                2
            )

            results.append({
                "concept_id": c_id,
                "subject": subj,
                "priority_score": priority_score,
                "bkt_mastery": round(bkt, 3),
                "fsrs_stability_days": round(stab, 2),
                "fsrs_retrievability": retrievability,
                "attempts": att_cnt,
                "errors": err_cnt,
                "high_confidence_errors": hi_cnt,
                "lucky_guesses": lucky_cnt,
                "unresolved_notes": unres_notes,
                "action_recommendation": (
                    "URGENT_SOCRATIC_DEBIASING" if hi_cnt > 0 and unres_notes > 0
                    else "SCAFFOLDING_FOUNDATION" if bkt < 0.40
                    else "SPACED_RETRIEVAL_PRACTICE"
                ),
            })

        results.sort(key=lambda x: x["priority_score"], reverse=True)
        return results[:limit]

    # ==========================================================================
    # Analytics 4: Phase 1, Phase 2, Phase 3 Readiness Gates
    # ==========================================================================

    def evaluate_readiness_gates(self, learner_id: str) -> ReadinessGateReport:
        """
        Assess learner eligibility across Phase 1, Phase 2, and Phase 3 readiness gates:
        - Phase 1 Gate (Foundation):
          - Minimum 50 item attempts
          - Subject coverage (Sub1 >= 10, Sub2 >= 10, Sub3 >= 30)
          - Average BKT mastery >= 0.55
        - Phase 2 Gate (Deep Debiasing & Metacognitive Calibration):
          - Phase 1 passed
          - High-confidence error resolution rate >= 85%
          - Murphy Brier Reliability (REL) <= 0.08
          - All subject cutoff risks < 10%
          - Average BKT mastery >= 0.70
        - Phase 3 Gate (Final Sprint & High Probability Pass):
          - Phase 2 passed
          - Monte Carlo Pass Probability >= 85%
          - Overall cutoff risk < 5% (each subject cutoff risk < 5%)
          - Expected total score >= 70 points
          - Global IRT theta >= 0.50
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Fetch all attempts
            cursor.execute(
                "SELECT * FROM attempts WHERE learner_id = ? ORDER BY timestamp",
                (learner_id,),
            )
            att_rows = cursor.fetchall()

            # Fetch concept mastery
            cursor.execute(
                "SELECT * FROM concept_mastery WHERE learner_id = ?",
                (learner_id,),
            )
            mastery_rows = cursor.fetchall()

            # Fetch error notes resolution stats
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_notes,
                    SUM(CASE WHEN resolved_status = 'RESOLVED' THEN 1 ELSE 0 END) as resolved_notes
                FROM error_notes
                WHERE learner_id = ?
                """,
                (learner_id,),
            )
            notes_stat = cursor.fetchone()

        total_attempts = len(att_rows)
        now_str = datetime.now(timezone.utc).isoformat()

        # Metacognitive calibration via Murphy Brier decomposition
        obs = [(float(r["confidence_prob"]), bool(r["is_correct"])) for r in att_rows]
        calib = MetacognitionEngine.murphy_brier_decomposition(obs)

        # Subject coverage
        sub_attempts = {1: 0, 2: 0, 3: 0}
        for r in att_rows:
            s = int(r["subject"])
            if s in sub_attempts:
                sub_attempts[s] += 1

        # Average BKT mastery
        if mastery_rows:
            avg_bkt = sum(float(r["bkt_p_learn"]) for r in mastery_rows) / len(mastery_rows)
        else:
            avg_bkt = 0.25

        # IRT Subject Ability Estimates
        irt_responses = []
        for r in att_rows:
            item = IRTItem(
                item_id=r["item_id"],
                subject=int(r["subject"]),
                difficulty=0.0,
                discrimination=1.0,
                guessing=0.25,
            )
            irt_responses.append(
                IRTResponse(item=item, is_correct=bool(r["is_correct"]))
            )

        subj_thetas_dict = IRT3PLEstimator.estimate_subject_thetas(irt_responses, method="map")
        thetas_for_sim = {s: subj_thetas_dict.get(s, (0.0, 1.0))[0] for s in (1, 2, 3)}
        global_theta, _ = IRT3PLEstimator.estimate_theta_map(irt_responses)

        # Monte Carlo Exam Simulation
        sim_result = ADsPPassSimulator.simulate_exam(thetas_for_sim, num_trials=5000)

        # Error note resolution
        total_notes = notes_stat["total_notes"] if notes_stat else 0
        resolved_notes = notes_stat["resolved_notes"] if notes_stat and notes_stat["resolved_notes"] else 0
        resolution_rate = (resolved_notes / total_notes) if total_notes > 0 else 1.0

        # High-confidence error resolution
        high_conf_errors = calib.quadrant_counts.get(MetacogQuadrant.ILLUSION_OF_COMPETENCE.value, 0)

        # Gate 1 Evaluation
        gate_1_sub_ok = (sub_attempts[1] >= 10 and sub_attempts[2] >= 10 and sub_attempts[3] >= 30)
        gate_1_passed = (total_attempts >= 50 and gate_1_sub_ok and avg_bkt >= 0.55)
        gate_1_details = {
            "passed": gate_1_passed,
            "total_attempts": f"{total_attempts} / 50",
            "subject_attempts": f"Sub1: {sub_attempts[1]}/10, Sub2: {sub_attempts[2]}/10, Sub3: {sub_attempts[3]}/30",
            "avg_bkt_mastery": f"{round(avg_bkt, 3)} / 0.55",
        }

        # Gate 2 Evaluation
        cutoff_max = max(sim_result.subject_cutoff_risk.values()) if sim_result.subject_cutoff_risk else 1.0
        gate_2_passed = (
            gate_1_passed
            and resolution_rate >= 0.85
            and calib.reliability <= 0.08
            and cutoff_max < 0.10
            and avg_bkt >= 0.70
        )
        gate_2_details = {
            "passed": gate_2_passed,
            "error_note_resolution_rate": f"{round(resolution_rate * 100, 1)}% / 85.0%",
            "brier_reliability_calibration": f"{calib.reliability} / <= 0.08",
            "max_subject_cutoff_risk": f"{round(cutoff_max * 100, 1)}% / < 10.0%",
            "avg_bkt_mastery": f"{round(avg_bkt, 3)} / 0.70",
        }

        # Gate 3 Evaluation
        sub_cutoff_safe = all(risk < 0.05 for risk in sim_result.subject_cutoff_risk.values())
        gate_3_passed = (
            gate_2_passed
            and sim_result.pass_probability >= 0.85
            and sub_cutoff_safe
            and sim_result.expected_total_score >= 70.0
            and global_theta >= 0.50
        )
        gate_3_details = {
            "passed": gate_3_passed,
            "monte_carlo_pass_probability": f"{round(sim_result.pass_probability * 100, 1)}% / >= 85.0%",
            "all_subject_cutoffs_under_5pct": sub_cutoff_safe,
            "expected_total_score": f"{sim_result.expected_total_score} / >= 70.0 pts",
            "global_irt_theta": f"{global_theta} / >= 0.50",
        }

        # Determine current phase
        if gate_3_passed:
            current_phase = 3
            recommendation = (
                "축하합니다! Phase 3 합격 관문을 통과했습니다. 모의고사 실전 시간 관리 및 최신 기출(50회) "
                "유지 보수 학습을 진행하십시오."
            )
        elif gate_2_passed:
            current_phase = 3
            recommendation = (
                f"Phase 2를 통과하여 Phase 3 최종 실전 단계에 진입했습니다. 병목 과목인 제{sim_result.bottleneck_subject}과목의 "
                f"과락 위험도({round(sim_result.subject_cutoff_risk[sim_result.bottleneck_subject]*100, 1)}%)를 5% 미만으로 낮추기 위한 "
                "집중 기출 모의고사를 추천합니다."
            )
        elif gate_1_passed:
            current_phase = 2
            recommendation = (
                f"Phase 1 기초 관문을 통과했습니다. Phase 2 진입을 위해 과신 오답(Illusion of Competence: {high_conf_errors}건) "
                "오답 노트를 소크라테스식 문답으로 해소하고, 메타인지 캘리브레이션 오차(REL)를 낮추십시오."
            )
        else:
            current_phase = 1
            recommendation = (
                "Phase 1 기초 역량 형성 단계입니다. 3개 전 과목(특히 과락 방지) 기초 문항을 고르게 학습하고, "
                "찍어서 맞힌 문제(Lucky Guess)의 개념을 정립하십시오."
            )

        return ReadinessGateReport(
            learner_id=learner_id,
            evaluated_at=now_str,
            current_phase=current_phase,
            total_attempts=total_attempts,
            avg_bkt_mastery=round(avg_bkt, 4),
            metacog_calibration=calib,
            simulation_result=sim_result,
            gate_1_foundation_passed=gate_1_passed,
            gate_1_details=gate_1_details,
            gate_2_debiasing_passed=gate_2_passed,
            gate_2_details=gate_2_details,
            gate_3_exam_ready_passed=gate_3_passed,
            gate_3_details=gate_3_details,
            recommended_action=recommendation,
        )
