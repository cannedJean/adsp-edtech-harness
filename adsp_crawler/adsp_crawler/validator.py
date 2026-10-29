"""Schema, census, and content integrity validator module for ADsP exam questions.

Provides strict validation for:
- Individual question schema (question_no, question_type, prompt, options, answer)
- Negative exclusion assertions (ensuring zero explanation/leakage in prompt/options/answer)
- Single exam round question count census (49 for R38/R40, 50 for all other 13 rounds)
- Consolidated dataset census across all 15 rounds (748 total: 708 MCQ, 40 short answer)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

from .config import (
    EXPECTED_MC_COUNTS,
    EXPECTED_ROUND_COUNTS,
    EXPECTED_SHORT_ANSWER_COUNTS,
    TARGET_ROUNDS,
    TOTAL_EXPECTED_QUESTIONS,
    TOTAL_EXPECTED_ROUNDS,
)

logger = logging.getLogger(__name__)

# Explanation terms and raw framework AST markers that must never leak into extracted question fields
FORBIDDEN_TERMS: List[str] = [
    "오답 풀이",
    "오답풀이",
    "보충 개념",
    "보충개념",
    "정답·해설 보기",
    "정답해설보기",
    '["$"',
    "rounded-2xl",
    "tabular-nums",
    '{"className"',
]


class ValidationError(Exception):
    """Raised when question schema, content, or census validation fails."""


def validate_question(q: Dict[str, Any]) -> bool:
    """Validate a single question dictionary against strict schema and negative constraints.

    Args:
        q: Question dictionary to validate.

    Returns:
        bool: True if question passes all schema and integrity checks.

    Raises:
        ValidationError: If schema, types, counts, or content constraints are violated.
    """
    if not isinstance(q, dict):
        raise ValidationError(f"Question must be a dict, got {type(q).__name__}")

    required_keys = {"question_no", "question_type", "prompt", "options", "answer"}
    keys = set(q.keys())
    # Allow optional 'round' field in consolidated dataset
    if keys != required_keys and keys != (required_keys | {"round"}):
        raise ValidationError(
            f"Question keys mismatch. Expected {required_keys}, got {keys}"
        )

    if "round" in q:
        r = q["round"]
        if not isinstance(r, int) or isinstance(r, bool) or r not in TARGET_ROUNDS:
            raise ValidationError(f"Invalid round key in question: {r}")

    # 1. question_no: int between 1 and 50
    q_no = q["question_no"]
    if not isinstance(q_no, int) or isinstance(q_no, bool) or not (1 <= q_no <= 50):
        raise ValidationError(f"Invalid question_no: {q_no}. Must be integer between 1 and 50.")

    # 2. question_type: '4지선다' or '단답형'
    q_type = q["question_type"]
    if q_type not in ("4지선다", "단답형"):
        raise ValidationError(f"Invalid question_type: '{q_type}'. Must be '4지선다' or '단답형'.")

    # 3. prompt: non-empty string
    prompt = q["prompt"]
    if not isinstance(prompt, str) or len(prompt.strip()) == 0:
        raise ValidationError(f"Prompt must be a non-empty string for Q{q_no}.")

    # 4. options: list[str]
    options = q["options"]
    if not isinstance(options, list):
        raise ValidationError(f"Options must be a list for Q{q_no}, got {type(options).__name__}.")

    if q_type == "4지선다":
        if len(options) != 4:
            raise ValidationError(
                f"4지선다 question must have exactly 4 options, got {len(options)} for Q{q_no}."
            )
        for idx, opt in enumerate(options, 1):
            if not isinstance(opt, str) or len(opt.strip()) == 0:
                raise ValidationError(
                    f"Option {idx} for 4지선다 Q{q_no} must be a non-empty string."
                )
    else:  # 단답형
        if len(options) != 0:
            raise ValidationError(
                f"단답형 question must have empty options [], got {len(options)} options for Q{q_no}."
            )

    # 5. answer: non-empty string
    answer = q["answer"]
    if not isinstance(answer, str) or len(answer.strip()) == 0:
        raise ValidationError(f"Answer must be a non-empty string for Q{q_no}.")

    if q_type == "4지선다":
        if answer not in ("1", "2", "3", "4"):
            raise ValidationError(
                f"4지선다 answer must be '1', '2', '3', or '4', got '{answer}' for Q{q_no}."
            )

    # 6. Negative exclusion check: ensure no explanation leaks
    all_text = prompt + " " + " ".join(options) + " " + answer
    for term in FORBIDDEN_TERMS:
        if term in all_text:
            raise ValidationError(
                f"Forbidden explanation term '{term}' leaked in Q{q_no}."
            )

    return True


def validate_round_dataset(round_no: int, questions: List[Dict[str, Any]]) -> bool:
    """Validate all question items within a single exam round.

    Args:
        round_no: The exam round number (e.g. 50).
        questions: List of parsed question dictionaries for this round.

    Returns:
        bool: True if all questions and the round census are valid.

    Raises:
        ValidationError: If question count mismatch, duplicate question_no, or schema failure occurs.
    """
    if not isinstance(questions, list):
        raise ValidationError(
            f"Round {round_no} questions must be a list, got {type(questions).__name__}."
        )

    expected_count = EXPECTED_ROUND_COUNTS.get(round_no)
    if expected_count is None:
        raise ValidationError(f"Unknown exam round: {round_no}. Expected one of {TARGET_ROUNDS}.")

    if len(questions) != expected_count:
        raise ValidationError(
            f"Round {round_no} expected {expected_count} questions, got {len(questions)}."
        )

    seen_nos = set()
    for q in questions:
        validate_question(q)
        q_no = q["question_no"]
        if q_no in seen_nos:
            raise ValidationError(f"Duplicate question_no {q_no} in Round {round_no}.")
        seen_nos.add(q_no)

    if round_no in (38, 40):
        expected_nos = set(range(1, 50))
        if 50 in seen_nos or seen_nos != expected_nos:
            raise ValidationError(
                f"Round {round_no} question numbers must be strictly 1..49 without Q50. Got {sorted(seen_nos)}."
            )
    else:
        expected_nos = set(range(1, 51))
        if seen_nos != expected_nos:
            raise ValidationError(
                f"Round {round_no} question numbers must be strictly 1..50. Got {sorted(seen_nos)}."
            )

    return True


def validate_consolidated_dataset(
    all_data: Union[Dict[int, List[Dict[str, Any]]], List[Dict[str, Any]]]
) -> bool:
    """Validate the consolidated dataset across all exam rounds.

    Asserts:
    - All 15 expected rounds are represented.
    - Grand total of 748 questions (minimum 740).
    - Exactly 708 multiple choice ('4지선다') questions.
    - Exactly 40 short answer ('단답형') questions.
    - Every individual question passes schema validation.

    Args:
        all_data: Either a dictionary mapping round_no -> list of questions,
                  or a flat list of all questions.

    Returns:
        bool: True if consolidated dataset is valid.

    Raises:
        ValidationError: If census counts, round presence, or question schemas fail.
    """
    if isinstance(all_data, dict):
        if len(all_data) != TOTAL_EXPECTED_ROUNDS:
            raise ValidationError(
                f"Expected {TOTAL_EXPECTED_ROUNDS} rounds, got {len(all_data)}."
            )
        missing_rounds = set(TARGET_ROUNDS) - set(all_data.keys())
        if missing_rounds:
            raise ValidationError(f"Missing required exam rounds: {sorted(missing_rounds)}.")

        total_questions = 0
        total_mcq = 0
        total_sa = 0

        for r_no, qs in all_data.items():
            validate_round_dataset(r_no, qs)
            total_questions += len(qs)
            for q in qs:
                if q["question_type"] == "4지선다":
                    total_mcq += 1
                elif q["question_type"] == "단답형":
                    total_sa += 1

    elif isinstance(all_data, list):
        total_questions = len(all_data)
        total_mcq = 0
        total_sa = 0
        rounds_seen = set()
        for q in all_data:
            validate_question(q)
            if "round" not in q:
                raise ValidationError(
                    "Each question in a consolidated dataset list must contain a 'round' field."
                )
            r = q["round"]
            if not isinstance(r, int) or isinstance(r, bool) or r not in TARGET_ROUNDS:
                raise ValidationError(f"Invalid round key in question: {r}")
            rounds_seen.add(r)
            if q["question_type"] == "4지선다":
                total_mcq += 1
            elif q["question_type"] == "단답형":
                total_sa += 1

        missing_rounds = set(TARGET_ROUNDS) - rounds_seen
        if missing_rounds:
            raise ValidationError(
                f"Consolidated dataset list is missing rounds: {sorted(missing_rounds)}."
            )
    else:
        raise ValidationError(
            f"Invalid all_data type: {type(all_data).__name__}. Expected dict or list."
        )

    if total_questions != TOTAL_EXPECTED_QUESTIONS or total_questions < 740:
        raise ValidationError(
            f"Expected total {TOTAL_EXPECTED_QUESTIONS} questions (min 740), got {total_questions}."
        )

    if total_mcq != 708:
        raise ValidationError(
            f"Expected exactly 708 '4지선다' questions across dataset, got {total_mcq}."
        )

    if total_sa != 40:
        raise ValidationError(
            f"Expected exactly 40 '단답형' questions across dataset, got {total_sa}."
        )

    return True
