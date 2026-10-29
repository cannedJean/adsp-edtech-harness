"""Tier 3: Cross-Feature Interactions & Multi-Module Pipeline Test Suite.

Authoritative source:
- PROJECT.md § Interface Contracts
- DISPATCH.md § Tier 3 Cross-Feature Interactions
Tests integration across fetcher, parser, validator, storage, and CLI modules.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import requests

from tests.conftest import (
    get_cli,
    get_fetcher,
    get_parser,
    get_storage,
    get_validator,
)


# ==============================================================================
# Pipeline 1: Hub Discovery -> Fetch -> Parse -> Schema Validate
# ==============================================================================
def test_pipeline_fetch_parse_validate(mock_network_session, sample_hub_html):
    """Verify integrated pipeline: discover -> fetch -> parse -> schema validation."""
    fetcher = get_fetcher()
    parser = get_parser()
    validator = get_validator()

    # 1. Discover rounds from hub
    rounds = fetcher.discover_rounds(sample_hub_html)
    assert 50 in rounds
    assert 38 in rounds

    # 2. Fetch posts using mock session
    post_50_html = fetcher.fetch_post(rounds[50], session=mock_network_session, delay_min=0, delay_max=0)
    post_38_html = fetcher.fetch_post(rounds[38], session=mock_network_session, delay_min=0, delay_max=0)

    # 3. Parse posts
    q50 = parser.parse_adsp_post(post_50_html)
    q38 = parser.parse_adsp_post(post_38_html)

    # 4. Validate schema and round integrity
    assert validator.validate_round_dataset(50, q50) is True
    assert validator.validate_round_dataset(38, q38) is True

    # Check structural cross-properties
    assert len(q50) == 50
    assert len(q38) == 49


# ==============================================================================
# Pipeline 2: CLI Arguments -> Storage Persistence
# ==============================================================================
def test_pipeline_cli_to_storage_single_round(mock_network_session, temp_output_dir):
    """Verify CLI coordinator running single round crawls and persists round JSON."""
    cli = get_cli()
    fetcher = get_fetcher()
    parser = get_parser()
    storage = get_storage()
    validator = get_validator()

    args = cli.parse_args(["--round", "50", "--output-dir", str(temp_output_dir)])
    assert args.rounds == [50]
    out_dir = Path(args.output_dir)

    # Execute workflow for target round
    post_html = fetcher.fetch_round_post(
        50,
        hub_urls={50: "https://www.sqldpass.com/blog/past-exam/adsp-2026-50"},
        session=mock_network_session,
    )
    questions = parser.parse_adsp_post(post_html)
    assert validator.validate_round_dataset(50, questions) is True

    saved_file = storage.save_round_json(50, questions, output_dir=out_dir)
    assert saved_file.exists()
    assert saved_file == out_dir / "adsp_round_50.json"

    # Verify adsp_all.json is NOT saved during single round run
    assert not (out_dir / "adsp_all.json").exists()


def test_pipeline_cli_to_storage_all_rounds(sample_full_dataset, temp_output_dir):
    """Verify consolidated dataset writing and round file creation for full collection."""
    storage = get_storage()
    validator = get_validator()

    # Validate consolidated collection
    assert validator.validate_consolidated_dataset(sample_full_dataset) is True

    # Save per-round files
    for r, qs in sample_full_dataset.items():
        saved_round = storage.save_round_json(r, qs, output_dir=temp_output_dir)
        assert saved_round.exists()

    # Save consolidated file
    saved_all = storage.save_consolidated_json(sample_full_dataset, output_dir=temp_output_dir)
    assert saved_all.exists()
    assert saved_all.name == "adsp_all.json"

    with open(saved_all, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 748


# ==============================================================================
# Pipeline 3: Rate Limiting & Transient Retry Handling
# ==============================================================================
def test_pipeline_retry_on_transient_server_error():
    """Verify fetcher retries on HTTP 500/503 and succeeds if subsequent attempt succeeds."""
    fetcher = get_fetcher()

    session = MagicMock(spec=requests.Session)
    call_count = 0

    def flaky_mock_get(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock(spec=requests.Response)
        if call_count == 1:
            resp.status_code = 503
            resp.text = "Service Temporarily Unavailable"
            resp.raise_for_status.side_effect = requests.HTTPError("503 Server Error")
        else:
            resp.status_code = 200
            resp.text = "<html><body>Success</body></html>"
            resp.raise_for_status = MagicMock()
        return resp

    session.get.side_effect = flaky_mock_get

    # Fetch should succeed after 1 retry
    html = fetcher.fetch_post(
        "https://www.sqldpass.com/blog/past-exam/adsp-2026-50",
        session=session,
        delay_min=0,
        delay_max=0,
    )
    assert "Success" in html
    assert call_count >= 2


def test_pipeline_retry_exhaustion_raises_error():
    """Verify fetcher raises exception when all retries are exhausted."""
    fetcher = get_fetcher()

    session = MagicMock(spec=requests.Session)
    def persistent_error_get(url, *args, **kwargs):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 500
        resp.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
        return resp

    session.get.side_effect = persistent_error_get

    with pytest.raises(Exception):
        fetcher.fetch_post(
            "https://www.sqldpass.com/blog/past-exam/adsp-2026-50",
            session=session,
            delay_min=0,
            delay_max=0,
            max_retries=2,
        )


# ==============================================================================
# Pipeline 4: Mixed Round Ingestion (Modern MCQs + Legacy Short Answers)
# ==============================================================================
def test_pipeline_mixed_round_ingestion(sample_round_50_html, sample_round_38_html, temp_output_dir):
    """Verify mixed round pipeline correctly processes modern MCQ round and legacy short answer round."""
    parser = get_parser()
    validator = get_validator()
    storage = get_storage()

    q50 = parser.parse_adsp_post(sample_round_50_html)
    q38 = parser.parse_adsp_post(sample_round_38_html)

    # Validate both
    assert validator.validate_round_dataset(50, q50) is True
    assert validator.validate_round_dataset(38, q38) is True

    # Persist both
    f50 = storage.save_round_json(50, q50, output_dir=temp_output_dir)
    f38 = storage.save_round_json(38, q38, output_dir=temp_output_dir)

    assert f50.exists()
    assert f38.exists()

    with open(f50, "r", encoding="utf-8") as f:
        data_50 = json.load(f)
    with open(f38, "r", encoding="utf-8") as f:
        data_38 = json.load(f)

    # 50 has 0 short answer
    assert all(q["question_type"] == "4지선다" for q in data_50)
    # 38 has exactly 10 short answer
    assert sum(1 for q in data_38 if q["question_type"] == "단답형") == 10
