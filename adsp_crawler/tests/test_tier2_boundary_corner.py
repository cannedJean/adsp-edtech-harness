"""Tier 2: Boundary, Corner Case, and Adversarial Verification Test Suite.

Authoritative source:
- ORIGINAL_REQUEST.md Acceptance Criteria & Edge Cases
- PROJECT.md § Edge Cases (Rounds 38/40 missing Q50, GFM empty cells, R code bailout, diverse short answers)
- spec_miner_survey_1 & explorer_survey_3 handoffs
"""

from __future__ import annotations

import re
import pytest

from tests.conftest import (
    get_cli,
    get_config,
    get_fetcher,
    get_parser,
    get_validator,
)
from tests.fixtures.mock_data import _generate_question_html


# ==============================================================================
# 1. Empty Options for 단답형 (Short Answer)
# ==============================================================================
def test_boundary_short_answer_empty_options(sample_round_38_html):
    """Verify all 단답형 questions strictly have options: [], never None or non-empty."""
    parser = get_parser()
    validator = get_validator()

    questions = parser.parse_adsp_post(sample_round_38_html)
    sa_questions = [q for q in questions if q["question_type"] == "단답형"]
    assert len(sa_questions) == 10

    for q in sa_questions:
        assert isinstance(q["options"], list)
        assert len(q["options"]) == 0
        assert q["options"] == []
        assert validator.validate_question(q) is True

    # Adversarial: 단답형 with non-empty options must fail validation
    corrupted_sa = dict(sa_questions[0], options=["불법 옵션"])
    with pytest.raises(validator.ValidationError) as exc_info:
        validator.validate_question(corrupted_sa)
    assert "단답형" in str(exc_info.value) or "options" in str(exc_info.value)


# ==============================================================================
# 2. Missing Q50 in Rounds 38 & 40 (49 Questions Census)
# ==============================================================================
def test_boundary_missing_q50_rounds_38_and_40(sample_round_38_html, sample_round_40_html):
    """Verify Rounds 38 and 40 have exactly 49 questions (1~49), Q50 absent."""
    parser = get_parser()
    validator = get_validator()

    for html, round_no in [(sample_round_38_html, 38), (sample_round_40_html, 40)]:
        questions = parser.parse_adsp_post(html)
        assert len(questions) == 49
        q_nos = [q["question_no"] for q in questions]
        assert q_nos == list(range(1, 50))
        assert 50 not in q_nos

        # Round validator must succeed for 49 questions in R38/R40
        assert validator.validate_round_dataset(round_no, questions) is True

    # Adversarial: 49 questions in any round other than 38 or 40 must fail validation
    q50_html_corrupted = questions  # 49 items
    with pytest.raises(validator.ValidationError) as exc_info:
        validator.validate_round_dataset(50, q50_html_corrupted)
    assert "50" in str(exc_info.value) or "expected 50" in str(exc_info.value).lower()


# ==============================================================================
# 3. GFM Table Conversion with Empty Cells (ANOVA Table)
# ==============================================================================
def test_boundary_gfm_table_empty_cells():
    """Verify HTML table with empty cells (ANOVA residuals/total) converts with padded cells."""
    parser = get_parser()

    # Question with empty cells in table rows
    html_with_sparse_table = f"""
    <ul>
      {_generate_question_html(
          q_no=25,
          q_type="4지선다",
          prompt_text="분산분석표의 빈칸을 채우시오.",
          has_table=True,
          answer_raw="3<!-- -->번"
      )}
    </ul>
    """
    questions = parser.parse_adsp_post(html_with_sparse_table)
    assert len(questions) == 1
    prompt = questions[0]["prompt"]

    # Table lines must exist
    table_lines = [line for line in prompt.split("\n") if line.strip().startswith("|")]
    assert len(table_lines) >= 3, "Table must have header, separator, and at least one data row"

    # Header column count
    header_cols = [c.strip() for c in table_lines[0].split("|")[1:-1]]
    num_cols = len(header_cols)
    assert num_cols == 6, f"Expected 6 columns, got {num_cols}"

    # Verify each data row has matching column count (empty cells padded)
    for line in table_lines[2:]:
        row_cols = [c.strip() for c in line.split("|")[1:-1]]
        assert len(row_cols) == num_cols, f"Row column count mismatch: {line}"


# ==============================================================================
# 4. R Code Block Resolution from Next.js RSC Flight Stream
# ==============================================================================
def test_boundary_r_code_block_flight_resolution(sample_round_50_html):
    """Verify code is recovered from flight stream when DOM pre tag has BAILOUT placeholder."""
    parser = get_parser()

    # In SSR DOM, pre only contains BAILOUT_TO_CLIENT_SIDE_RENDERING
    assert "BAILOUT_TO_CLIENT_SIDE_RENDERING" in sample_round_50_html

    questions = parser.parse_adsp_post(sample_round_50_html)
    q26 = next(q for q in questions if q["question_no"] == 26)

    # Must contain code block with ```r
    assert "```r" in q26["prompt"]
    assert "prcomp" in q26["prompt"]
    assert "Standard deviation" in q26["prompt"]
    assert "BAILOUT_TO_CLIENT_SIDE_RENDERING" not in q26["prompt"]


# ==============================================================================
# 5. Diverse Short Answer Formats Preservation
# ==============================================================================
def test_boundary_diverse_short_answer_formats():
    """Verify various 단답형 answer formats (acronyms, Korean phrases, decimals, %, formulas)."""
    validator = get_validator()

    test_answers = [
        ("IoT", "English Acronym"),
        ("SCM", "English Acronym"),
        ("하향식 접근 방법", "Korean Multi-word Phrase"),
        ("데이터베이스", "Korean Single-word"),
        ("0.4", "Decimal Number"),
        ("1.2", "Decimal Number"),
        ("57.5%", "Percentage String"),
        ("1/5", "Fraction Expression"),
        ("a / (a+b)", "Mathematical Formula"),
        ("ROC 곡선", "Alphanumeric Phrase"),
    ]

    for ans, desc in test_answers:
        q = {
            "question_no": 41,
            "question_type": "단답형",
            "prompt": f"{desc}를 요구하는 단답형 문항 지문입니다.",
            "options": [],
            "answer": ans,
        }
        assert validator.validate_question(q) is True, f"Failed for {desc}: '{ans}'"


# ==============================================================================
# 6. Answer Suffix Stripping vs Preservation
# ==============================================================================
def test_boundary_answer_suffix_stripping():
    """Verify '번' is stripped for 4지선다, but preserved if part of short answer."""
    parser = get_parser()

    # 4지선다 with various suffix representations
    for raw_ans, expected in [
        ("2<!-- -->번", "2"),
        ("3번", "3"),
        (" 4 번 ", "4"),
        ("1", "1"),
    ]:
        html = f"<ul>{_generate_question_html(1, '4지선다', '문제', answer_raw=raw_ans)}</ul>"
        q = parser.parse_adsp_post(html)[0]
        assert q["answer"] == expected

    # 단답형 answers containing numbers or Korean words must NOT strip
    for sa_ans in ["2차원", "3단계", "100%", "4번 타자"]:
        html = f"<ul>{_generate_question_html(41, '단답형', '문제', options=[], answer_raw=sa_ans)}</ul>"
        q = parser.parse_adsp_post(html)[0]
        assert q["answer"] == sa_ans


# ==============================================================================
# 7. Invalid CLI Arguments
# ==============================================================================
def test_boundary_invalid_cli_arguments():
    """Verify CLI rejects invalid rounds, negative values, and non-existent Round 43."""
    cli = get_cli()

    # Round 43 (concept guide, not exam post)
    with pytest.raises(SystemExit):
        cli.parse_args(["--round", "43"])

    # Negative round number
    with pytest.raises(SystemExit):
        cli.parse_args(["--round", "-1"])

    # Non-existent round 99
    with pytest.raises(SystemExit):
        cli.parse_args(["--round", "99"])

    # Non-numeric round
    with pytest.raises(SystemExit):
        cli.parse_args(["--round", "not_a_number"])


# ==============================================================================
# 8. Adversarial Schema and Content Violations
# ==============================================================================
def test_boundary_adversarial_validation_failures():
    """Verify validator strictly catches duplicate numbers, empty prompts, and forbidden leaks."""
    validator = get_validator()

    base_q = {
        "question_no": 1,
        "question_type": "4지선다",
        "prompt": "정상적인 지문",
        "options": ["1", "2", "3", "4"],
        "answer": "1",
    }

    # 1. Empty prompt
    with pytest.raises(validator.ValidationError):
        validator.validate_question(dict(base_q, prompt=""))

    # 2. Whitespace-only prompt
    with pytest.raises(validator.ValidationError):
        validator.validate_question(dict(base_q, prompt="   \n\t  "))

    # 3. 4지선다 answer outside '1'~'4'
    with pytest.raises(validator.ValidationError):
        validator.validate_question(dict(base_q, answer="5"))

    with pytest.raises(validator.ValidationError):
        validator.validate_question(dict(base_q, answer="A"))

    # 4. Leaked explanation text in prompt
    with pytest.raises(validator.ValidationError) as exc:
        validator.validate_question(dict(base_q, prompt="문제입니다. 오답 풀이: 틀린 내용"))
    assert "오답 풀이" in str(exc.value)

    # 5. Leaked explanation text in options
    with pytest.raises(validator.ValidationError) as exc:
        validator.validate_question(dict(base_q, options=["A", "보충 개념 정리", "C", "D"]))
    assert "보충 개념" in str(exc.value)

    # 6. Duplicate question numbers in round
    questions_with_duplicate = [
        dict(base_q, question_no=1),
        dict(base_q, question_no=1),  # Duplicate
    ]
    with pytest.raises(validator.ValidationError):
        validator.validate_round_dataset(50, questions_with_duplicate)
