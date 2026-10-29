"""Tier 4: Real-World Application Scenarios & Complete Dataset Verification.

Authoritative source:
- ORIGINAL_REQUEST.md Acceptance Criteria (748 questions across 15 rounds, zero explanation leaks)
- spec_miner_survey_1, explorer_survey_2, explorer_survey_3 handoffs
- PROJECT.md § Milestones & Acceptance Criteria
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from tests.conftest import (
    get_fetcher,
    get_parser,
    get_storage,
    get_validator,
)


# ==============================================================================
# Scenario 1: Real-world Full Single-Round Ingestion & Storage
# ==============================================================================
def test_scenario_single_round_complete_workflow(mock_network_session, sample_hub_html, temp_output_dir):
    """Real-world scenario: User executes crawler for a single exam round (Round 50)."""
    fetcher = get_fetcher()
    parser = get_parser()
    validator = get_validator()
    storage = get_storage()

    # Step 1: Discover rounds from category hub
    hub_urls = fetcher.discover_rounds(sample_hub_html)
    assert 50 in hub_urls
    r50_url = hub_urls[50]

    # Step 2: Fetch exam post SSR HTML
    html = fetcher.fetch_post(r50_url, session=mock_network_session, delay_min=0, delay_max=0)
    assert len(html) > 0

    # Step 3: Semantic parsing with rich elements
    questions = parser.parse_adsp_post(html)
    assert len(questions) == 50

    # Step 4: Validate round questions
    assert validator.validate_round_dataset(50, questions) is True

    # Step 5: Save to round JSON
    saved_path = storage.save_round_json(50, questions, output_dir=temp_output_dir)
    assert saved_path.exists()
    assert saved_path.is_file()

    # Step 6: Verify file content integrity
    with open(saved_path, "r", encoding="utf-8") as f:
        stored_data = json.load(f)

    assert len(stored_data) == 50
    for idx, q in enumerate(stored_data, 1):
        assert q["question_no"] == idx
        assert q["question_type"] == "4지선다"
        assert len(q["options"]) == 4
        assert q["answer"] in ("1", "2", "3", "4")

    # Verify table in Q25 and code in Q26
    q25 = next(q for q in stored_data if q["question_no"] == 25)
    assert "|" in q25["prompt"]
    assert "제곱합" in q25["prompt"]

    q26 = next(q for q in stored_data if q["question_no"] == 26)
    assert "```r" in q26["prompt"]


# ==============================================================================
# Scenario 2: Complete 15-Round Census & Distribution Verification
# ==============================================================================
def test_scenario_full_15_rounds_census_verification(sample_full_dataset, temp_output_dir):
    """Real-world scenario: Full 15 rounds harvest verification (exact 748 question census)."""
    validator = get_validator()
    storage = get_storage()

    # 1. Total rounds count
    expected_rounds = [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]
    assert sorted(list(sample_full_dataset.keys())) == expected_rounds
    assert len(sample_full_dataset) == 15

    # 2. Per-round question count and question type distribution
    total_questions = 0
    total_mcq = 0
    total_short_answer = 0

    for r in expected_rounds:
        qs = sample_full_dataset[r]
        expected_count = 49 if r in (38, 40) else 50
        assert len(qs) == expected_count, f"Round {r} count mismatch: expected {expected_count}, got {len(qs)}"

        # Validate round schema
        assert validator.validate_round_dataset(r, qs) is True

        for q in qs:
            total_questions += 1
            if q["question_type"] == "4지선다":
                total_mcq += 1
                assert len(q["options"]) == 4
            elif q["question_type"] == "단답형":
                total_short_answer += 1
                assert len(q["options"]) == 0
            else:
                pytest.fail(f"Invalid question_type: {q['question_type']}")

    # 3. Assert global census metrics
    assert total_questions == 748, f"Expected exactly 748 questions, got {total_questions}"
    assert total_mcq == 708, f"Expected exactly 708 multiple choice questions, got {total_mcq}"
    assert total_short_answer == 40, f"Expected exactly 40 short answer questions, got {total_short_answer}"

    # 4. Storage persistence
    saved_round_files = []
    for r, qs in sample_full_dataset.items():
        p = storage.save_round_json(r, qs, output_dir=temp_output_dir)
        saved_round_files.append(p)

    assert len(saved_round_files) == 15
    for p in saved_round_files:
        assert p.exists()

    consolidated_path = storage.save_consolidated_json(sample_full_dataset, output_dir=temp_output_dir)
    assert consolidated_path.exists()

    with open(consolidated_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    assert len(all_data) == 748


# ==============================================================================
# Scenario 3: Negative Leak Assertions Across Full Corpus
# ==============================================================================
def test_scenario_negative_leak_assertions_across_corpus(sample_full_dataset, temp_output_dir):
    """Negative verification: Assert zero explanation, distractor analysis, or UI text across all files."""
    storage = get_storage()

    # Persist all rounds and consolidated file
    storage.save_consolidated_json(sample_full_dataset, output_dir=temp_output_dir)
    for r, qs in sample_full_dataset.items():
        storage.save_round_json(r, qs, output_dir=temp_output_dir)

    forbidden_patterns = [
        "오답 풀이",
        "오답풀이",
        "보충 개념",
        "보충개념",
        "정답·해설 보기",
        "정답해설보기",
        "해설 보기",
        "정답: ",
    ]

    json_files = list(temp_output_dir.glob("*.json"))
    assert len(json_files) == 16  # 15 rounds + 1 consolidated

    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            raw_content = f.read()

        for term in forbidden_patterns:
            assert term not in raw_content, f"Forbidden term '{term}' leaked in {jf.name}!"
