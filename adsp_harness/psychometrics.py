"""
ADsP Psychometric Modeling & Adaptive Assessment Engine
======================================================
Core Mathematical Framework for the ADsP Multi-Agent Learning Harness.

Components:
1. IRT3PLEstimator: 3-Parameter Logistic Item Response Theory model for ability
   estimation (MAP, EAP, Newton-Raphson), Fisher Information, and adaptive selection.
2. BKT_FSRS_Tracker: Hybrid Bayesian Knowledge Tracing + Free Spaced Repetition (FSRS-6)
   scheduler with Hypercorrection boost for high-confidence error recovery.
3. MetacognitionEngine: Retrospective Confidence Judgment calibration, 2x2 quadrant
   classification, and Murphy's 3-Component Brier Score decomposition.
4. ADsPPassSimulator: Bayesian Monte Carlo simulation for ADsP exam passing probability
   and subject-specific cutoff (과락) risk analysis.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple, Union

# Attempt numpy import for vectorized acceleration; pure Python fallback guaranteed
try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False
    np = None


# ==============================================================================
# 1. 3-Parameter Logistic Item Response Theory (3PL IRT)
# ==============================================================================

@dataclass
class IRTItem:
    """Psychometric representation of an ADsP exam question."""
    item_id: str
    difficulty: float = 0.0      # b_j: item difficulty, standard normal scale [-3, +3]
    discrimination: float = 1.0  # a_j: item discrimination slope, typically [0.5, 2.5]
    guessing: float = 0.25       # c_j: pseudo-guessing parameter (0.25 for 4-choice, 0.0 for short-answer)
    subject: int = 1             # 1: 데이터 이해, 2: 데이터 분석 기획, 3: 데이터 분석
    concept_id: str = ""         # Associated granular concept identifier

    def __post_init__(self):
        if self.discrimination <= 0.0:
            raise ValueError(f"Discrimination a_j must be positive, got {self.discrimination}")
        if not (0.0 <= self.guessing < 1.0):
            raise ValueError(f"Guessing c_j must be in [0, 1), got {self.guessing}")
        if self.subject not in (1, 2, 3):
            raise ValueError(f"Subject must be 1, 2, or 3, got {self.subject}")


@dataclass
class IRTResponse:
    """Individual learner response to an IRT item."""
    item: IRTItem
    is_correct: bool
    confidence_prob: float = 0.5  # Subjective confidence in [0.25, 1.0]


class IRT3PLEstimator:
    """
    3-Parameter Logistic Item Response Theory Estimator.

    Probability formula:
      P(Y_ij = 1 | theta_i, a_j, b_j, c_j) = c_j + (1 - c_j) / (1 + exp(-D * a_j * (theta_i - b_j)))
      where D = 1.702 (logistic-to-normal ogive scaling constant).
    """

    D: float = 1.702  # Scaling constant

    @classmethod
    def probability(cls, theta: float, item: IRTItem) -> float:
        """
        Compute the probability of a correct response under 3PL IRT.
        P_j(theta) = c_j + (1 - c_j) * sigmoid(D * a_j * (theta - b_j))
        """
        z = cls.D * item.discrimination * (theta - item.difficulty)
        # Numerical stability clamp
        z = max(-35.0, min(35.0, z))
        p_star = 1.0 / (1.0 + math.exp(-z))
        return item.guessing + (1.0 - item.guessing) * p_star

    @classmethod
    def probability_derivative(cls, theta: float, item: IRTItem) -> float:
        """
        First derivative dP_j(theta)/dtheta.
        dP/dtheta = D * a_j * (1 - c_j) * P*(theta) * (1 - P*(theta))
        """
        z = cls.D * item.discrimination * (theta - item.difficulty)
        z = max(-35.0, min(35.0, z))
        p_star = 1.0 / (1.0 + math.exp(-z))
        return cls.D * item.discrimination * (1.0 - item.guessing) * p_star * (1.0 - p_star)

    @classmethod
    def item_information(cls, theta: float, item: IRTItem) -> float:
        """
        Fisher Information for a single item:
          I_j(theta) = (dP_j/dtheta)^2 / (P_j * (1 - P_j))
                     = (D * a_j)^2 * (1 - P_j) / P_j * ((P_j - c_j) / (1 - c_j))^2
        """
        p = cls.probability(theta, item)
        p = max(1e-9, min(1.0 - 1e-9, p))
        c = item.guessing
        factor = (p - c) / (1.0 - c) if c < 1.0 else 0.0
        return (cls.D * item.discrimination) ** 2 * ((1.0 - p) / p) * (factor ** 2)

    @classmethod
    def test_information(cls, theta: float, items: Sequence[IRTItem]) -> float:
        """Sum of Fisher Information across a set of items: I(theta) = sum I_j(theta)."""
        return sum(cls.item_information(theta, it) for it in items)

    @classmethod
    def standard_error(cls, theta: float, items: Sequence[IRTItem], prior_var: float = 1.0) -> float:
        """
        Standard Error of ability estimation:
          SE(theta) = 1 / sqrt(sum(I_j(theta)) + 1 / prior_var)
        """
        info = cls.test_information(theta, items)
        prior_info = 1.0 / prior_var if prior_var > 0 else 0.0
        total_info = info + prior_info
        return 1.0 / math.sqrt(max(1e-6, total_info))

    @classmethod
    def estimate_theta_map(
        cls,
        responses: Sequence[IRTResponse],
        prior_mean: float = 0.0,
        prior_var: float = 1.0,
        max_iter: int = 50,
        tol: float = 1e-4,
    ) -> Tuple[float, float]:
        """
        Estimate learner ability theta via Maximum A Posteriori (MAP) using Newton-Raphson.

        Returns:
            (estimated_theta, standard_error)
        """
        if not responses:
            return prior_mean, math.sqrt(prior_var)

        theta = prior_mean
        prior_precision = 1.0 / prior_var

        for _ in range(max_iter):
            score = 0.0
            info = 0.0

            for resp in responses:
                item = resp.item
                y = 1.0 if resp.is_correct else 0.0
                p = cls.probability(theta, item)
                p = max(1e-9, min(1.0 - 1e-9, p))
                dp = cls.probability_derivative(theta, item)

                # First derivative of log-likelihood: sum (y - P) / (P * (1 - P)) * dP/dtheta
                score += (y - p) / (p * (1.0 - p)) * dp
                # Expected Fisher information
                info += cls.item_information(theta, item)

            # MAP includes prior contribution
            grad = score - prior_precision * (theta - prior_mean)
            hessian = -(info + prior_precision)

            if abs(hessian) < 1e-9:
                break

            delta = -grad / hessian
            # Step damping to avoid wild oscillations
            delta = max(-1.0, min(1.0, delta))
            theta += delta
            # Constrain theta to reasonable psychometric range [-4.0, +4.0]
            theta = max(-4.0, min(4.0, theta))

            if abs(delta) < tol:
                break

        items = [r.item for r in responses]
        se = cls.standard_error(theta, items, prior_var=prior_var)
        return round(theta, 4), round(se, 4)

    @classmethod
    def estimate_theta_eap(
        cls,
        responses: Sequence[IRTResponse],
        prior_mean: float = 0.0,
        prior_var: float = 1.0,
        num_quad: int = 81,
        range_min: float = -4.0,
        range_max: float = 4.0,
    ) -> Tuple[float, float]:
        """
        Estimate learner ability theta via Expected A Posteriori (EAP) numerical quadrature.
        Guaranteed to converge even with all-correct or all-incorrect responses.

        Returns:
            (eap_theta, standard_error)
        """
        if not responses:
            return prior_mean, math.sqrt(prior_var)

        # Quadrature grid
        step = (range_max - range_min) / (num_quad - 1)
        grid = [range_min + i * step for i in range(num_quad)]
        prior_sd = math.sqrt(prior_var)

        log_posteriors = []
        for x in grid:
            # Normal prior log density
            log_prior = -0.5 * ((x - prior_mean) / prior_sd) ** 2
            # Log likelihood
            log_lik = 0.0
            for r in responses:
                p = cls.probability(x, r.item)
                p = max(1e-9, min(1.0 - 1e-9, p))
                log_lik += math.log(p) if r.is_correct else math.log(1.0 - p)
            log_posteriors.append(log_prior + log_lik)

        # Softmax for normalized posterior probabilities
        max_lp = max(log_posteriors)
        unnorm_weights = [math.exp(lp - max_lp) for lp in log_posteriors]
        total_w = sum(unnorm_weights)
        weights = [w / total_w for w in unnorm_weights]

        eap_theta = sum(x * w for x, w in zip(grid, weights))
        var = sum(((x - eap_theta) ** 2) * w for x, w in zip(grid, weights))
        se = math.sqrt(max(1e-6, var))

        return round(eap_theta, 4), round(se, 4)

    @classmethod
    def estimate_subject_thetas(
        cls,
        responses: Sequence[IRTResponse],
        method: str = "map",
    ) -> Dict[int, Tuple[float, float]]:
        """
        Estimate learner ability per subject: theta_1 (Sub1), theta_2 (Sub2), theta_3 (Sub3).
        Returns dict: {subject_id: (theta, se)}.
        """
        res: Dict[int, Tuple[float, float]] = {}
        for s in (1, 2, 3):
            sub_resp = [r for r in responses if r.item.subject == s]
            if method.lower() == "eap":
                res[s] = cls.estimate_theta_eap(sub_resp)
            else:
                res[s] = cls.estimate_theta_map(sub_resp)
        return res

    @classmethod
    def select_next_item(
        cls,
        current_theta: float,
        candidate_items: Sequence[IRTItem],
        excluded_ids: Optional[Sequence[str]] = None,
        target_subject: Optional[int] = None,
        target_concept: Optional[str] = None,
    ) -> Optional[IRTItem]:
        """
        Select the next best item for adaptive testing by maximizing Fisher Information
        at current_theta, filtered by subject, target concept, or excluded IDs.
        """
        excluded = set(excluded_ids or [])
        pool = [
            it for it in candidate_items
            if it.item_id not in excluded
            and (target_subject is None or it.subject == target_subject)
            and (target_concept is None or it.concept_id == target_concept)
        ]
        if not pool:
            return None

        # Return item that yields maximum Fisher information at theta
        return max(pool, key=lambda it: cls.item_information(current_theta, it))


# ==============================================================================
# 2. Bayesian Knowledge Tracing + FSRS-6 Memory Scheduler
# ==============================================================================

@dataclass
class BKTParameters:
    """Standard Bayesian Knowledge Tracing hyperparameters."""
    p_init: float = 0.25   # P(L_0): initial mastery probability
    p_transit: float = 0.15 # P(T): probability of transitioning from unlearned to learned
    p_slip: float = 0.10   # P(S): probability of slip (knows but answers wrong)
    p_guess: float = 0.25  # P(G): probability of guess (4-choice item)


@dataclass
class FSRSParameters:
    """FSRS-6 (Free Spaced Repetition Scheduler v6) parameters."""
    decay: float = -0.5             # Power law memory decay
    factor: float = 19.0 / 81.0     # 0.2345679 -> retrievability = 90% when t == S
    request_retention: float = 0.90 # Target retention probability
    # Weights for stability and difficulty transitions
    w_recall_base: float = 0.40
    w_recall_diff: float = 0.20
    w_recall_ret: float = 0.80
    w_forget_mult: float = 0.35
    w_diff_mean_rev: float = 0.10
    hypercorrection_mult: float = 1.75 # Multiplier for correcting high-confidence errors


@dataclass
class FSRSState:
    """FSRS memory state for an item or concept."""
    difficulty: float = 5.0     # D in [1.0, 10.0]
    stability: float = 1.0      # S in days (days until retrievability drops to 90%)
    last_review_days: float = 0.0 # Days elapsed at last review
    reps: int = 0
    lapses: int = 0
    consecutive_correct: int = 0

    def retrievability(self, elapsed_days: float, params: Optional[FSRSParameters] = None) -> float:
        """
        Compute memory retrievability R(t, S) = (1 + FACTOR * (t / S))^DECAY.
        """
        p = params or FSRSParameters()
        t = max(0.0, elapsed_days)
        s = max(0.01, self.stability)
        r = (1.0 + p.factor * (t / s)) ** p.decay
        return max(0.0, min(1.0, r))


class BKT_FSRS_Tracker:
    """
    Hybrid Bayesian Knowledge Tracing + FSRS-6 Memory Tracker.
    Integrates confidence calibration into BKT observation updates and applies
    psychometric Hypercorrection boosts for Socratic dialogue remediation.
    """

    def __init__(
        self,
        bkt_params: Optional[BKTParameters] = None,
        fsrs_params: Optional[FSRSParameters] = None,
    ):
        self.bkt = bkt_params or BKTParameters()
        self.fsrs = fsrs_params or FSRSParameters()

    def update_bkt(
        self,
        current_p_mastery: float,
        is_correct: bool,
        confidence_prob: float = 0.5,
    ) -> float:
        """
        Perform a Bayesian Knowledge Tracing posterior update given observation and confidence.

        Adjusts effective slip/guess rates:
        - Correct with high confidence (>= 0.75): lower guess probability (unlikely a lucky guess).
        - Correct with low confidence (<= 0.50): higher guess probability (likely lucky guess).
        - Incorrect with high confidence (>= 0.75): lower slip probability (indicates deep misconception, not random slip).
        """
        p_l = max(0.001, min(0.999, current_p_mastery))
        p_t = self.bkt.p_transit
        p_s = self.bkt.p_slip
        p_g = self.bkt.p_guess

        # Modulate effective parameters using confidence level
        if is_correct:
            if confidence_prob >= 0.75:
                # Highly confident correct response -> genuine knowledge
                eff_g = max(0.05, p_g * (1.0 - confidence_prob + 0.1))
                eff_s = p_s
            elif confidence_prob <= 0.50:
                # Low confidence correct response -> likely lucky guess
                eff_g = min(0.75, p_g + (0.50 - confidence_prob) * 0.8)
                eff_s = p_s
            else:
                eff_g = p_g
                eff_s = p_s

            numerator = p_l * (1.0 - eff_s)
            denominator = numerator + (1.0 - p_l) * eff_g
            p_obs = numerator / max(1e-9, denominator)
        else:
            if confidence_prob >= 0.75:
                # High confidence incorrect response -> Illusion of competence / entrenched misconception
                eff_s = max(0.01, p_s * 0.2)  # Not a random slip!
                eff_g = p_g
            else:
                eff_s = p_s
                eff_g = p_g

            numerator = p_l * eff_s
            denominator = numerator + (1.0 - p_l) * (1.0 - eff_g)
            p_obs = numerator / max(1e-9, denominator)

        # Transition model: P(L_{t+1}) = P(L_t | obs) + (1 - P(L_t | obs)) * P(T)
        p_next = p_obs + (1.0 - p_obs) * p_t
        return round(max(0.001, min(0.999, p_next)), 4)

    def update_fsrs(
        self,
        state: FSRSState,
        elapsed_days: float,
        is_correct: bool,
        rating: int = 3,  # 1: Again, 2: Hard, 3: Good, 4: Easy
    ) -> FSRSState:
        """
        Update FSRS-6 memory state after a review.
        """
        d = state.difficulty
        s = state.stability
        r = state.retrievability(elapsed_days, self.fsrs)
        reps = state.reps + 1
        lapses = state.lapses
        consec = state.consecutive_correct

        # 1. Update Difficulty with mean-reversion
        delta_d = -0.6 * (rating - 3)
        d_raw = d + delta_d
        d_new = (1.0 - self.fsrs.w_diff_mean_rev) * d_raw + self.fsrs.w_diff_mean_rev * 5.0
        d_new = max(1.0, min(10.0, d_new))

        # 2. Update Stability
        if is_correct:
            consec += 1
            # Recall stability growth
            diff_factor = 11.0 - d_new
            ret_factor = math.exp(self.fsrs.w_recall_ret * (1.0 - r)) - 1.0
            stab_growth = 1.0 + math.exp(self.fsrs.w_recall_base) * diff_factor * (s ** (-self.fsrs.w_recall_diff)) * max(0.0, ret_factor)
            # Ensure stability at least grows by at least 10% on successful recall
            s_new = max(s * 1.10, s * stab_growth)
        else:
            consec = 0
            lapses += 1
            # Forget stability drop: drops proportional to difficulty and past stability
            s_new = max(0.1, min(s * 0.40, self.fsrs.w_forget_mult * (d_new ** -0.3) * (s ** 0.2)))

        return FSRSState(
            difficulty=round(d_new, 3),
            stability=round(s_new, 3),
            last_review_days=elapsed_days,
            reps=reps,
            lapses=lapses,
            consecutive_correct=consec,
        )

    def apply_hypercorrection_boost(
        self,
        state: FSRSState,
        bkt_mastery: float,
        socratic_resolved: bool = True,
    ) -> Tuple[FSRSState, float]:
        """
        Hypercorrection effect (Butterfield & Metcalfe, 2001; Metcalfe, 2017):
        When a high-confidence error (Illusion of Competence) is resolved through
        Socratic de-biasing, the resulting Reward Prediction Error (RPE) produces
        hyper-consolidation in memory stability and posterior mastery.
        """
        if not socratic_resolved:
            return state, bkt_mastery

        # Stability boost: restoring from lapsed state with RPE hypercorrection multiplier
        # Memory consolidation from active Socratic dialogue resets and expands stability
        base_stability = max(1.5, state.stability)
        new_stability = base_stability * self.fsrs.hypercorrection_mult
        # Difficulty reduction reflecting resolved misconception
        new_difficulty = max(1.0, state.difficulty - 1.5)
        # Substantial jump in BKT posterior mastery
        new_bkt = min(0.98, bkt_mastery + 0.35)

        boosted_state = FSRSState(
            difficulty=round(new_difficulty, 3),
            stability=round(new_stability, 3),
            last_review_days=0.0,
            reps=state.reps + 1,
            lapses=state.lapses,
            consecutive_correct=state.consecutive_correct + 1,
        )
        return boosted_state, round(new_bkt, 4)


# ==============================================================================
# 3. Metacognitive Calibration & Murphy Brier Decomposition
# ==============================================================================

class ConfidenceLevel(Enum):
    """Retrospective Confidence Judgment (RCJ) discrete levels."""
    GUESS = 1          # "찍음 / 모름" (p = 0.25)
    CONFUSED = 2       # "헷갈림 (2개 중 고민)" (p = 0.50)
    CONFIDENT = 3      # "대체로 확신" (p = 0.75)
    CERTAIN = 4        # "완전 확신" (p = 0.95)

    @classmethod
    def to_probability(cls, level: Union[int, ConfidenceLevel]) -> float:
        mapping = {1: 0.25, 2: 0.50, 3: 0.75, 4: 0.95}
        val = level.value if isinstance(level, ConfidenceLevel) else level
        return mapping.get(val, 0.50)

    @classmethod
    def from_probability(cls, p: float) -> ConfidenceLevel:
        if p < 0.375:
            return cls.GUESS
        elif p < 0.625:
            return cls.CONFUSED
        elif p < 0.85:
            return cls.CONFIDENT
        else:
            return cls.CERTAIN


class MetacogQuadrant(Enum):
    """2x2 Metacognitive Quadrants combining Accuracy and Subjective Confidence."""
    MASTERED = "MASTERED"
    LUCKY_GUESS_CONFUSED = "LUCKY_GUESS_CONFUSED"
    ILLUSION_OF_COMPETENCE = "ILLUSION_OF_COMPETENCE"
    KNOWN_UNKNOWN = "KNOWN_UNKNOWN"


@dataclass
class CalibrationResult:
    """Statistical decomposition of metacognitive calibration."""
    sample_size: int
    brier_score: float
    reliability: float       # REL: Calibration error (lower is better, ideally 0)
    resolution: float        # RES: Discrimination power (higher is better)
    uncertainty: float       # UNC: Inherent outcome variance y_bar * (1 - y_bar)
    ece: float               # Expected Calibration Error across bins
    overconfidence_index: float # mean(p) - mean(y), > 0: overconfident, < 0: underconfident
    quadrant_counts: Dict[str, int] = field(default_factory=dict)
    quadrant_proportions: Dict[str, float] = field(default_factory=dict)


class MetacognitionEngine:
    """
    Evaluator of learner metacognitive calibration, illusion of competence detection,
    and Murphy's 3-Component Brier Score decomposition.
    """

    CONFIDENCE_PROB_MAP = {
        1: 0.25,
        2: 0.50,
        3: 0.75,
        4: 0.95,
    }

    @classmethod
    def get_confidence_prob(cls, rating: Union[int, ConfidenceLevel]) -> float:
        if isinstance(rating, ConfidenceLevel):
            return ConfidenceLevel.to_probability(rating)
        return cls.CONFIDENCE_PROB_MAP.get(rating, 0.50)

    @classmethod
    def classify_quadrant(cls, is_correct: bool, confidence_prob: float) -> MetacogQuadrant:
        """
        Classify response into the 2x2 Metacognitive Quadrants:
        - MASTERED: Correct + High Confidence (p >= 0.70)
        - LUCKY_GUESS_CONFUSED: Correct + Low Confidence (p < 0.70) -> Phase 1 follow-up required!
        - ILLUSION_OF_COMPETENCE: Incorrect + High Confidence (p >= 0.70) -> Socratic RPE de-biasing target!
        - KNOWN_UNKNOWN: Incorrect + Low Confidence (p < 0.70) -> Scaffolding required
        """
        high_conf = confidence_prob >= 0.70
        if is_correct:
            return MetacogQuadrant.MASTERED if high_conf else MetacogQuadrant.LUCKY_GUESS_CONFUSED
        else:
            return MetacogQuadrant.ILLUSION_OF_COMPETENCE if high_conf else MetacogQuadrant.KNOWN_UNKNOWN

    @classmethod
    def murphy_brier_decomposition(
        cls,
        observations: Sequence[Tuple[float, bool]],
        num_bins: int = 4,
    ) -> CalibrationResult:
        """
        Compute Murphy's (1973) 3-Component Brier Score decomposition:
          BS = REL - RES + UNC
        where:
          - REL (Reliability): sum_k (n_k / N) * (f_k - y_bar_k)^2  [Calibration error]
          - RES (Resolution):  sum_k (n_k / N) * (y_bar_k - y_bar)^2 [Discrimination]
          - UNC (Uncertainty): y_bar * (1 - y_bar)                  [Outcome entropy]
        and ECE (Expected Calibration Error) and Overconfidence Index.
        """
        n = len(observations)
        if n == 0:
            return CalibrationResult(
                sample_size=0,
                brier_score=0.0,
                reliability=0.0,
                resolution=0.0,
                uncertainty=0.0,
                ece=0.0,
                overconfidence_index=0.0,
                quadrant_counts={},
                quadrant_proportions={},
            )

        y_vals = [1.0 if obs[1] else 0.0 for obs in observations]
        p_vals = [obs[0] for obs in observations]

        y_bar = sum(y_vals) / n
        p_bar = sum(p_vals) / n
        brier_score = sum((p - y) ** 2 for p, y in zip(p_vals, y_vals)) / n
        uncertainty = y_bar * (1.0 - y_bar)

        # Discretize into M confidence bins (default 4 matching discrete confidence ratings)
        # Defined bin intervals: [0.0, 0.375), [0.375, 0.625), [0.625, 0.85), [0.85, 1.0]
        bins_data: Dict[int, List[Tuple[float, float]]] = {i: [] for i in range(num_bins)}

        for p, y in zip(p_vals, y_vals):
            if p < 0.375:
                bins_data[0].append((p, y))
            elif p < 0.625:
                bins_data[1].append((p, y))
            elif p < 0.85:
                bins_data[2].append((p, y))
            else:
                bins_data[3].append((p, y))

        rel = 0.0
        res = 0.0
        ece = 0.0

        for b_idx, items in bins_data.items():
            n_k = len(items)
            if n_k == 0:
                continue
            f_k = sum(p for p, _ in items) / n_k
            y_bar_k = sum(y for _, y in items) / n_k
            weight = n_k / n

            rel += weight * ((f_k - y_bar_k) ** 2)
            res += weight * ((y_bar_k - y_bar) ** 2)
            ece += weight * abs(f_k - y_bar_k)

        overconfidence = p_bar - y_bar

        # Metacognitive quadrant classification counts
        quad_counts: Dict[str, int] = {q.value: 0 for q in MetacogQuadrant}
        for p, y_bool in observations:
            q = cls.classify_quadrant(y_bool, p)
            quad_counts[q.value] += 1

        quad_props = {k: round(v / n, 4) for k, v in quad_counts.items()}

        return CalibrationResult(
            sample_size=n,
            brier_score=round(brier_score, 4),
            reliability=round(rel, 4),
            resolution=round(res, 4),
            uncertainty=round(uncertainty, 4),
            ece=round(ece, 4),
            overconfidence_index=round(overconfidence, 4),
            quadrant_counts=quad_counts,
            quadrant_proportions=quad_props,
        )


# ==============================================================================
# 4. ADsP Bayesian Monte Carlo Pass & Cutoff Risk Simulator
# ==============================================================================

@dataclass
class SimulationResult:
    """Comprehensive output of the ADsP exam Monte Carlo risk simulator."""
    trials_count: int
    pass_probability: float
    expected_total_score: float
    subject_expected_scores: Dict[int, float]
    subject_cutoff_risk: Dict[int, float]  # Probability of failing subject cutoff (< 40%)
    overall_cutoff_risk: float             # Probability of failing any cutoff
    bottleneck_subject: int                # Subject with highest cutoff risk or score deficit
    score_percentiles: Dict[int, float]    # 5th, 25th, 50th, 75th, 95th percentiles


class ADsPPassSimulator:
    """
    ADsP Exam Structure & Bayesian Monte Carlo Pass/Cutoff Simulator.

    Exact ADsP Exam Specifications:
    - Total Items: 50 items (2 points each, max 100 points)
      - Subject 1 (데이터 이해): 10 items (20 pts) -> Cutoff: < 4 items (< 8 pts, 40%)
      - Subject 2 (데이터 분석 기획): 10 items (20 pts) -> Cutoff: < 4 items (< 8 pts, 40%)
      - Subject 3 (데이터 분석): 30 items (60 pts) -> Cutoff: < 12 items (< 24 pts, 40%)
    - Passing Criteria:
      - Total Score >= 60 points (at least 30 items correct)
      - Subject 1 Score >= 8 points (>= 4 correct)
      - Subject 2 Score >= 8 points (>= 4 correct)
      - Subject 3 Score >= 24 points (>= 12 correct)
    """

    TOTAL_ITEMS = 50
    POINTS_PER_ITEM = 2
    SUBJECT_COUNTS = {1: 10, 2: 10, 3: 30}
    SUBJECT_CUTOFF_ITEMS = {1: 4, 2: 4, 3: 12}
    PASSING_SCORE = 60

    @classmethod
    def generate_representative_exam_items(cls) -> List[IRTItem]:
        """
        Generate a standardized 50-item ADsP exam blueprint with representative difficulty
        and discrimination parameters derived from historical past exams.
        """
        items: List[IRTItem] = []
        # Subject 1: 10 items (Introductory to intermediate)
        for i in range(1, 11):
            items.append(
                IRTItem(
                    item_id=f"S1_{i:02d}",
                    difficulty=-0.5 + 0.1 * i,  # Range [-0.4, 0.5]
                    discrimination=1.0 + 0.05 * (i % 4),
                    guessing=0.25,
                    subject=1,
                    concept_id=f"concept_s1_{i}",
                )
            )
        # Subject 2: 10 items (Methodologies, Governance)
        for i in range(1, 11):
            items.append(
                IRTItem(
                    item_id=f"S2_{i:02d}",
                    difficulty=-0.3 + 0.12 * i, # Range [-0.18, 0.9]
                    discrimination=1.1 + 0.04 * (i % 4),
                    guessing=0.25,
                    subject=2,
                    concept_id=f"concept_s2_{i}",
                )
            )
        # Subject 3: 30 items (R code, statistics, models, machine learning)
        for i in range(1, 31):
            items.append(
                IRTItem(
                    item_id=f"S3_{i:02d}",
                    difficulty=-0.6 + 0.08 * i, # Range [-0.52, 1.8]
                    discrimination=1.2 + 0.03 * (i % 5),
                    guessing=0.25,
                    subject=3,
                    concept_id=f"concept_s3_{i}",
                )
            )
        return items

    @classmethod
    def simulate_exam(
        cls,
        subject_thetas: Dict[int, float],
        exam_items: Optional[Sequence[IRTItem]] = None,
        num_trials: int = 5000,
        random_seed: Optional[int] = None,
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation over `num_trials` exam administrations given learner's
        per-subject ability estimates (theta_1, theta_2, theta_3).
        """
        if random_seed is not None:
            random.seed(random_seed)
            if _NUMPY_AVAILABLE:
                np.random.seed(random_seed)

        items = list(exam_items) if exam_items is not None else cls.generate_representative_exam_items()

        # Compute item success probabilities using 3PL IRT
        # Group probabilities by subject
        probs_by_subject: Dict[int, List[float]] = {1: [], 2: [], 3: []}
        for it in items:
            theta = subject_thetas.get(it.subject, 0.0)
            p = IRT3PLEstimator.probability(theta, it)
            probs_by_subject[it.subject].append(p)

        # Execute simulation: fast vectorized numpy if available, pure Python fallback
        if _NUMPY_AVAILABLE:
            return cls._simulate_numpy(probs_by_subject, num_trials)
        else:
            return cls._simulate_pure_python(probs_by_subject, num_trials)

    @classmethod
    def _simulate_numpy(
        cls,
        probs_by_subject: Dict[int, List[float]],
        num_trials: int,
    ) -> SimulationResult:
        """Fast vectorized Monte Carlo using numpy."""
        # Correct counts arrays per subject
        s1_probs = np.array(probs_by_subject[1])
        s2_probs = np.array(probs_by_subject[2])
        s3_probs = np.array(probs_by_subject[3])

        # Random matrix shape (num_trials, num_items)
        s1_draws = (np.random.rand(num_trials, len(s1_probs)) < s1_probs).sum(axis=1)
        s2_draws = (np.random.rand(num_trials, len(s2_probs)) < s2_probs).sum(axis=1)
        s3_draws = (np.random.rand(num_trials, len(s3_probs)) < s3_probs).sum(axis=1)

        total_correct = s1_draws + s2_draws + s3_draws
        total_scores = total_correct * cls.POINTS_PER_ITEM

        # Cutoff checks: correct < cutoff threshold
        s1_cutoff = s1_draws < cls.SUBJECT_CUTOFF_ITEMS[1]
        s2_cutoff = s2_draws < cls.SUBJECT_CUTOFF_ITEMS[2]
        s3_cutoff = s3_draws < cls.SUBJECT_CUTOFF_ITEMS[3]
        any_cutoff = s1_cutoff | s2_cutoff | s3_cutoff

        # Passing condition: score >= 60 and no cutoff
        passed = (total_scores >= cls.PASSING_SCORE) & (~any_cutoff)
        pass_prob = float(passed.mean())

        # Subject scores and cutoff risks
        sub_expected_scores = {
            1: round(float((s1_draws * cls.POINTS_PER_ITEM).mean()), 2),
            2: round(float((s2_draws * cls.POINTS_PER_ITEM).mean()), 2),
            3: round(float((s3_draws * cls.POINTS_PER_ITEM).mean()), 2),
        }
        sub_cutoff_risks = {
            1: round(float(s1_cutoff.mean()), 4),
            2: round(float(s2_cutoff.mean()), 4),
            3: round(float(s3_cutoff.mean()), 4),
        }

        # Identify bottleneck subject: highest cutoff risk or lowest score percentage
        bottleneck = max(sub_cutoff_risks.items(), key=lambda x: x[1])[0]

        percentiles = {
            5: round(float(np.percentile(total_scores, 5)), 1),
            25: round(float(np.percentile(total_scores, 25)), 1),
            50: round(float(np.percentile(total_scores, 50)), 1),
            75: round(float(np.percentile(total_scores, 75)), 1),
            95: round(float(np.percentile(total_scores, 95)), 1),
        }

        return SimulationResult(
            trials_count=num_trials,
            pass_probability=round(pass_prob, 4),
            expected_total_score=round(float(total_scores.mean()), 2),
            subject_expected_scores=sub_expected_scores,
            subject_cutoff_risk=sub_cutoff_risks,
            overall_cutoff_risk=round(float(any_cutoff.mean()), 4),
            bottleneck_subject=bottleneck,
            score_percentiles=percentiles,
        )

    @classmethod
    def _simulate_pure_python(
        cls,
        probs_by_subject: Dict[int, List[float]],
        num_trials: int,
    ) -> SimulationResult:
        """Zero-dependency pure Python Monte Carlo fallback."""
        s1_probs = probs_by_subject[1]
        s2_probs = probs_by_subject[2]
        s3_probs = probs_by_subject[3]

        pass_count = 0
        s1_cutoff_count = 0
        s2_cutoff_count = 0
        s3_cutoff_count = 0
        any_cutoff_count = 0

        s1_score_sum = 0
        s2_score_sum = 0
        s3_score_sum = 0
        all_total_scores = []

        rand = random.random

        for _ in range(num_trials):
            # Subject 1
            s1_c = sum(1 for p in s1_probs if rand() < p)
            # Subject 2
            s2_c = sum(1 for p in s2_probs if rand() < p)
            # Subject 3
            s3_c = sum(1 for p in s3_probs if rand() < p)

            s1_score = s1_c * cls.POINTS_PER_ITEM
            s2_score = s2_c * cls.POINTS_PER_ITEM
            s3_score = s3_c * cls.POINTS_PER_ITEM
            tot_score = s1_score + s2_score + s3_score

            s1_score_sum += s1_score
            s2_score_sum += s2_score
            s3_score_sum += s3_score
            all_total_scores.append(tot_score)

            is_s1_cut = s1_c < cls.SUBJECT_CUTOFF_ITEMS[1]
            is_s2_cut = s2_c < cls.SUBJECT_CUTOFF_ITEMS[2]
            is_s3_cut = s3_c < cls.SUBJECT_CUTOFF_ITEMS[3]
            is_any_cut = is_s1_cut or is_s2_cut or is_s3_cut

            if is_s1_cut:
                s1_cutoff_count += 1
            if is_s2_cut:
                s2_cutoff_count += 1
            if is_s3_cut:
                s3_cutoff_count += 1
            if is_any_cut:
                any_cutoff_count += 1

            if tot_score >= cls.PASSING_SCORE and not is_any_cut:
                pass_count += 1

        all_total_scores.sort()
        n = num_trials

        def get_pct(pct: float) -> float:
            idx = int(n * (pct / 100.0))
            idx = min(idx, n - 1)
            return float(all_total_scores[idx])

        sub_cutoff_risks = {
            1: round(s1_cutoff_count / n, 4),
            2: round(s2_cutoff_count / n, 4),
            3: round(s3_cutoff_count / n, 4),
        }
        bottleneck = max(sub_cutoff_risks.items(), key=lambda x: x[1])[0]

        return SimulationResult(
            trials_count=num_trials,
            pass_probability=round(pass_count / n, 4),
            expected_total_score=round(sum(all_total_scores) / n, 2),
            subject_expected_scores={
                1: round(s1_score_sum / n, 2),
                2: round(s2_score_sum / n, 2),
                3: round(s3_score_sum / n, 2),
            },
            subject_cutoff_risk=sub_cutoff_risks,
            overall_cutoff_risk=round(any_cutoff_count / n, 4),
            bottleneck_subject=bottleneck,
            score_percentiles={
                5: get_pct(5),
                25: get_pct(25),
                50: get_pct(50),
                75: get_pct(75),
                95: get_pct(95),
            },
        )
