"""Live corpus integration tests for ADsP crawled dataset.

Verifies the actual harvested data files in data/:
- 15 round JSON files + 1 consolidated adsp_all.json
- Exact 748 questions census (708 4지선다, 40 단답형)
- Rounds 38 & 40 have 49 questions (Q50 absent)
- Rounds 32, 35, 37, 38 have 10 short-answer questions each with options: []
- Round 50 Q25 contains GFM markdown table
- Round 50 Q26 contains ```r fenced code block
- Complete negative filter: zero occurrences of forbidden explanation terms
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from adsp_crawler.config import EXPECTED_ROUND_COUNTS, EXPECTED_SHORT_ANSWER_COUNTS, TARGET_ROUNDS
from adsp_crawler.validator import FORBIDDEN_TERMS, validate_consolidated_dataset, validate_round_dataset

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def live_data_dir() -> Path:
    if not DATA_DIR.exists():
        pytest.skip(f"Data directory {DATA_DIR} does not exist yet. Run crawler first.")
    return DATA_DIR


def test_live_corpus_all_files_exist(live_data_dir):
    """Verify all 15 individual round JSON files and adsp_all.json exist."""
    for r in TARGET_ROUNDS:
        round_path = live_data_dir / f"adsp_round_{r}.json"
        assert round_path.exists(), f"Round file {round_path.name} is missing!"
        assert round_path.stat().st_size > 0, f"Round file {round_path.name} is empty!"

    all_path = live_data_dir / "adsp_all.json"
    assert all_path.exists(), "adsp_all.json is missing!"
    assert all_path.stat().st_size > 0, "adsp_all.json is empty!"


def test_live_corpus_per_round_census(live_data_dir):
    """Verify question counts, numbers, and types for every round."""
    total_mcq = 0
    total_sa = 0
    total_questions = 0

    for r in TARGET_ROUNDS:
        round_path = live_data_dir / f"adsp_round_{r}.json"
        with open(round_path, "r", encoding="utf-8") as f:
            questions = json.load(f)

        expected_count = EXPECTED_ROUND_COUNTS[r]
        assert len(questions) == expected_count, (
            f"Round {r} expected {expected_count} questions, got {len(questions)}"
        )

        # Validate round schema
        assert validate_round_dataset(r, questions) is True

        r_mcq = sum(1 for q in questions if q["question_type"] == "4지선다")
        r_sa = sum(1 for q in questions if q["question_type"] == "단답형")
        expected_sa = EXPECTED_SHORT_ANSWER_COUNTS.get(r, 0)

        assert r_sa == expected_sa, f"Round {r} expected {expected_sa} 단답형, got {r_sa}"

        for q in questions:
            if q["question_type"] == "단답형":
                assert q["options"] == []
                assert len(q["answer"].strip()) > 0
            elif q["question_type"] == "4지선다":
                assert len(q["options"]) == 4
                assert q["answer"] in ("1", "2", "3", "4")

        total_questions += len(questions)
        total_mcq += r_mcq
        total_sa += r_sa

    assert total_questions == 748
    assert total_mcq == 708
    assert total_sa == 40


def test_live_corpus_consolidated_dataset(live_data_dir):
    """Verify adsp_all.json contains exactly 748 valid questions."""
    all_path = live_data_dir / "adsp_all.json"
    with open(all_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    assert len(all_data) == 748
    assert validate_consolidated_dataset(all_data) is True

    all_mcq = sum(1 for q in all_data if q["question_type"] == "4지선다")
    all_sa = sum(1 for q in all_data if q["question_type"] == "단답형")
    assert all_mcq == 708
    assert all_sa == 40

    # Verify each round attribute
    rounds_represented = set(q.get("round") for q in all_data)
    assert rounds_represented == set(TARGET_ROUNDS)


def test_live_corpus_rich_elements_formatting(live_data_dir):
    """Verify tables in Q25 and R code in Q26 for Round 50."""
    r50_path = live_data_dir / "adsp_round_50.json"
    with open(r50_path, "r", encoding="utf-8") as f:
        r50_data = json.load(f)

    # Q25 has ANOVA table
    q25 = next(q for q in r50_data if q["question_no"] == 25)
    prompt_25 = q25["prompt"]
    assert "|" in prompt_25
    assert "제곱합" in prompt_25
    assert "p-value" in prompt_25

    # Q26 has PCA summary
    q26 = next(q for q in r50_data if q["question_no"] == 26)
    prompt_26 = q26["prompt"]
    assert "```r" in prompt_26
    assert "prcomp" in prompt_26 or "pca" in prompt_26


def test_live_corpus_negative_exclusion_filter(live_data_dir):
    """Verify zero occurrences of explanation leakage in all 16 JSON files."""
    json_files = list(live_data_dir.glob("*.json"))
    assert len(json_files) == 16

    for jf in json_files:
        content = jf.read_text(encoding="utf-8")
        for term in FORBIDDEN_TERMS:
            assert term not in content, f"Forbidden term '{term}' leaked in {jf.name}"
