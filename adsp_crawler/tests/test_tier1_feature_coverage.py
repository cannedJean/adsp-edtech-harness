"""Tier 1: Comprehensive Feature Coverage Test Suite.

Authoritative source: PROJECT.md § Feature Inventory (Features 1 through 17).
Every feature is rigorously verified with dedicated opaque-box test cases.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
import pytest

from tests.conftest import (
    get_cli,
    get_config,
    get_fetcher,
    get_parser,
    get_storage,
    get_validator,
)


# ==============================================================================
# Feature 1: Hub Discovery
# ==============================================================================
def test_f01_hub_discovery(sample_hub_html):
    """F1: Automatically discover and index all 15 exam post URLs from hub HTML."""
    fetcher = get_fetcher()
    rounds = fetcher.discover_rounds(sample_hub_html)

    expected_rounds = [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]
    assert sorted(list(rounds.keys())) == expected_rounds
    assert len(rounds) == 15

    # Check URL integrity
    for r_no, url in rounds.items():
        assert isinstance(url, str)
        assert f"adsp-" in url
        assert str(r_no) in url
        assert url.startswith("https://www.sqldpass.com/blog/past-exam/")

    # Non-exam guide post (e.g. 43 preparation) must be excluded
    assert 43 not in rounds
    for url in rounds.values():
        assert "adsp-43-preparation" not in url


# ==============================================================================
# Feature 2: Rate Limiter
# ==============================================================================
def test_f02_rate_limiter(mock_network_session):
    """F2: Polite jitter delay between requests."""
    fetcher = get_fetcher()
    config = get_config()

    jitter_min = getattr(config, "JITTER_MIN", getattr(config, "DEFAULT_DELAY_MIN", 1.0))
    jitter_max = getattr(config, "JITTER_MAX", getattr(config, "DEFAULT_DELAY_MAX", 2.0))
    assert jitter_min >= 0
    assert jitter_max >= jitter_min

    # Test delay enforcement with small test bounds
    start_time = time.perf_counter()
    fetcher.fetch_post(
        "https://www.sqldpass.com/blog/past-exam/adsp-2026-50",
        session=mock_network_session,
        delay_min=0.05,
        delay_max=0.10,
    )
    elapsed = time.perf_counter() - start_time
    assert elapsed >= 0.045, f"Delay too short: elapsed {elapsed}s"


# ==============================================================================
# Feature 3: Polite Headers
# ==============================================================================
def test_f03_polite_headers():
    """F3: Realistic browser User-Agent and Accept headers attached to requests."""
    config = get_config()
    headers = config.DEFAULT_HEADERS

    assert "User-Agent" in headers
    assert "Accept" in headers
    # Ensure User-Agent is not standard Python-urllib (which gets 403 on Cloudflare)
    assert "Python-urllib" not in headers["User-Agent"]
    assert "Mozilla" in headers["User-Agent"] or "Chrome" in headers["User-Agent"]


# ==============================================================================
# Feature 4: CLI Round Selector
# ==============================================================================
def test_f04_cli_round_selector():
    """F4: Support specifying single round, multiple rounds, or all rounds by default."""
    cli = get_cli()

    # Single round
    args_single = cli.parse_args(["--round", "50"])
    assert args_single.rounds == [50]

    # Multiple rounds
    args_multi = cli.parse_args(["--round", "38", "40", "50"])
    assert args_multi.rounds == [38, 40, 50]

    # All rounds by default
    args_all = cli.parse_args([])
    assert args_all.rounds is None

    # Invalid round rejected
    with pytest.raises(SystemExit):
        cli.parse_args(["--round", "43"])


# ==============================================================================
# Feature 5: Custom Output Directory
# ==============================================================================
def test_f05_custom_output_dir():
    """F5: Allow overriding output destination directory via --output-dir."""
    cli = get_cli()

    # Default output dir
    args_default = cli.parse_args([])
    assert args_default.output_dir == "data"

    # Custom output dir
    args_custom = cli.parse_args(["--output-dir", "custom_exams_dir"])
    assert args_custom.output_dir == "custom_exams_dir"


# ==============================================================================
# Feature 6: Question Item Extraction
# ==============================================================================
def test_f06_question_item_extraction(sample_round_50_html, sample_round_38_html):
    """F6: Extract all li.rounded-2xl question containers."""
    parser = get_parser()

    # Round 50 must have exactly 50 question items
    q50 = parser.parse_adsp_post(sample_round_50_html)
    assert len(q50) == 50

    # Round 38 must have exactly 49 question items
    q38 = parser.parse_adsp_post(sample_round_38_html)
    assert len(q38) == 49


# ==============================================================================
# Feature 7: Question Number Parser
# ==============================================================================
def test_f07_question_number_parser(sample_round_50_html, sample_round_38_html):
    """F7: Extract integer question_no from p.tabular-nums."""
    parser = get_parser()

    q50 = parser.parse_adsp_post(sample_round_50_html)
    nos_50 = [q["question_no"] for q in q50]
    assert nos_50 == list(range(1, 51))
    assert all(isinstance(n, int) for n in nos_50)

    q38 = parser.parse_adsp_post(sample_round_38_html)
    nos_38 = [q["question_no"] for q in q38]
    assert nos_38 == list(range(1, 50))
    assert 50 not in nos_38


# ==============================================================================
# Feature 8: Question Type Classifier
# ==============================================================================
def test_f08_question_type_classifier(sample_round_50_html, sample_round_38_html):
    """F8: Accurately classify questions as '4지선다' or '단답형'."""
    parser = get_parser()

    # Round 50 is 100% 4지선다
    q50 = parser.parse_adsp_post(sample_round_50_html)
    for q in q50:
        assert q["question_type"] == "4지선다"

    # Round 38 has 39 MCQs and 10 short answers
    q38 = parser.parse_adsp_post(sample_round_38_html)
    mc_count = sum(1 for q in q38 if q["question_type"] == "4지선다")
    sa_count = sum(1 for q in q38 if q["question_type"] == "단답형")
    assert mc_count == 39
    assert sa_count == 10

    # Questions 40~49 in Round 38 are 단답형
    for q in q38[39:]:
        assert q["question_type"] == "단답형"


# ==============================================================================
# Feature 9: GFM Table Preservation
# ==============================================================================
def test_f09_gfm_table_preservation(sample_round_50_html):
    """F9: Preserve/convert HTML tables into clean GFM tables (| ... |)."""
    parser = get_parser()
    q50 = parser.parse_adsp_post(sample_round_50_html)

    # Q25 has ANOVA table
    q25 = next(q for q in q50 if q["question_no"] == 25)
    prompt = q25["prompt"]

    assert "|" in prompt
    assert "| 요인 |" in prompt or "| 요인 " in prompt
    assert "|---|---" in prompt or "| --- |" in prompt
    assert "제곱합" in prompt
    assert "p-value" in prompt


# ==============================================================================
# Feature 10: R Code Block Converter
# ==============================================================================
def test_f10_r_code_block_converter(sample_round_50_html):
    """F10: Convert R code snippets into fenced code blocks (```r ... ```)."""
    parser = get_parser()
    q50 = parser.parse_adsp_post(sample_round_50_html)

    # Q26 has PCA summary R output
    q26 = next(q for q in q50 if q["question_no"] == 26)
    prompt = q26["prompt"]

    assert "```r" in prompt
    assert "prcomp" in prompt or "pca" in prompt
    assert "PC1" in prompt


# ==============================================================================
# Feature 11: Options Extractor
# ==============================================================================
def test_f11_options_extractor(sample_round_50_html, sample_round_38_html):
    """F11: Extract 4 options for 4지선다, strictly empty [] for 단답형."""
    parser = get_parser()

    # 4지선다 in Round 50
    q50 = parser.parse_adsp_post(sample_round_50_html)
    for q in q50:
        assert isinstance(q["options"], list)
        assert len(q["options"]) == 4
        assert all(isinstance(opt, str) and len(opt.strip()) > 0 for opt in q["options"])

    # 단답형 in Round 38
    q38 = parser.parse_adsp_post(sample_round_38_html)
    for q in q38:
        if q["question_type"] == "단답형":
            assert q["options"] == []


# ==============================================================================
# Feature 12: Answer Key Extractor
# ==============================================================================
def test_f12_answer_key_extractor(sample_round_50_html, sample_round_38_html):
    """F12: Extract answer from details, strip '번' for 4지선다, keep text for 단답형."""
    parser = get_parser()

    # 4지선다: '2<!-- -->번' -> '2'
    q50 = parser.parse_adsp_post(sample_round_50_html)
    for q in q50:
        assert q["answer"] in ("1", "2", "3", "4")

    # 단답형 in Round 38
    q38 = parser.parse_adsp_post(sample_round_38_html)
    q40 = next(q for q in q38 if q["question_no"] == 40)
    assert q40["answer"] == "IoT"

    q41 = next(q for q in q38 if q["question_no"] == 41)
    assert q41["answer"] == "SCM"


# ==============================================================================
# Feature 13: Negative Exclusion Filter
# ==============================================================================
def test_f13_negative_exclusion_filter(sample_round_50_html, sample_round_38_html):
    """F13: Strictly exclude all explanation text ('오답 풀이', '보충 개념', button text)."""
    parser = get_parser()
    forbidden = ["오답 풀이", "오답풀이", "보충 개념", "보충개념", "정답·해설 보기", "정답해설보기"]

    for html in (sample_round_50_html, sample_round_38_html):
        questions = parser.parse_adsp_post(html)
        for q in questions:
            for term in forbidden:
                assert term not in q["prompt"], f"Term '{term}' found in prompt of Q{q['question_no']}"
                for opt in q["options"]:
                    assert term not in opt, f"Term '{term}' found in option of Q{q['question_no']}"
                assert term not in q["answer"], f"Term '{term}' found in answer of Q{q['question_no']}"


# ==============================================================================
# Feature 14: Schema Integrity Validator
# ==============================================================================
def test_f14_schema_integrity_validator():
    """F14: Validate question dict against strict schema."""
    validator = get_validator()

    valid_q = {
        "question_no": 1,
        "question_type": "4지선다",
        "prompt": "문항 지문",
        "options": ["A", "B", "C", "D"],
        "answer": "2",
    }
    assert validator.validate_question(valid_q) is True

    # Missing field
    with pytest.raises(validator.ValidationError):
        invalid_missing = dict(valid_q)
        del invalid_missing["answer"]
        validator.validate_question(invalid_missing)

    # Invalid question_no (0 or >50)
    with pytest.raises(validator.ValidationError):
        invalid_no = dict(valid_q, question_no=51)
        validator.validate_question(invalid_no)

    # 4지선다 with wrong option count
    with pytest.raises(validator.ValidationError):
        invalid_opts = dict(valid_q, options=["A", "B", "C"])
        validator.validate_question(invalid_opts)


# ==============================================================================
# Feature 15: Total Count Validator
# ==============================================================================
def test_f15_total_count_validator(sample_full_dataset):
    """F15: Total count validator asserts full census 748 questions."""
    validator = get_validator()

    # Full collection must validate
    assert validator.validate_consolidated_dataset(sample_full_dataset) is True

    # Missing one question must fail
    corrupted_data = {r: list(qs) for r, qs in sample_full_dataset.items()}
    corrupted_data[50] = corrupted_data[50][:-1]  # 49 instead of 50
    with pytest.raises(validator.ValidationError):
        validator.validate_consolidated_dataset(corrupted_data)


# ==============================================================================
# Feature 16: Per-Round Storage
# ==============================================================================
def test_f16_per_round_storage(sample_full_dataset, temp_output_dir):
    """F16: Persist single round dataset to data/adsp_round_{round}.json."""
    storage = get_storage()
    r50_data = sample_full_dataset[50]

    saved_path = storage.save_round_json(50, r50_data, output_dir=temp_output_dir)
    assert saved_path.exists()
    assert saved_path.name == "adsp_round_50.json"

    # Verify UTF-8 JSON content
    with open(saved_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 50
    assert loaded[0]["question_no"] == 1


# ==============================================================================
# Feature 17: Consolidated Storage
# ==============================================================================
def test_f17_consolidated_storage(sample_full_dataset, temp_output_dir):
    """F17: Persist all 748 questions to data/adsp_all.json."""
    storage = get_storage()

    saved_path = storage.save_consolidated_json(sample_full_dataset, output_dir=temp_output_dir)
    assert saved_path.exists()
    assert saved_path.name == "adsp_all.json"

    with open(saved_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 748
