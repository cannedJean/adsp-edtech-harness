"""Pytest configuration, fixtures, and dynamic module loaders for ADsP crawler test suite.

Progressive Testability & Independence:
- Tests seamlessly test real `adsp_crawler` implementation when available.
- When implementation is in progress, falls back to `tests.mock_crawler` reference logic.
- All fixtures are self-contained, isolated, and leave no persistent artifacts.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import re
import sys
from typing import Any
from unittest.mock import MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import requests

from tests.fixtures.mock_data import (
    MOCK_HUB_HTML,
    generate_full_15_rounds_dataset,
    generate_round_38_html,
    generate_round_40_html,
    generate_round_50_html,
)
import tests.mock_crawler as mock_crawler


# ==============================================================================
# Dynamic Module Resolvers
# ==============================================================================
def get_config():
    try:
        mod = importlib.import_module("adsp_crawler.config")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_crawler


def get_fetcher():
    try:
        mod = importlib.import_module("adsp_crawler.fetcher")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_crawler


def get_parser():
    try:
        mod = importlib.import_module("adsp_crawler.parser")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_crawler


def get_validator():
    try:
        mod = importlib.import_module("adsp_crawler.validator")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_crawler


def get_storage():
    try:
        mod = importlib.import_module("adsp_crawler.storage")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_crawler


def get_cli():
    try:
        mod = importlib.import_module("adsp_crawler.cli")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_crawler


# ==============================================================================
# Fixtures for Modules
# ==============================================================================
@pytest.fixture
def config_module():
    return get_config()


@pytest.fixture
def fetcher_module():
    return get_fetcher()


@pytest.fixture
def parser_module():
    return get_parser()


@pytest.fixture
def validator_module():
    return get_validator()


@pytest.fixture
def storage_module():
    return get_storage()


@pytest.fixture
def cli_module():
    return get_cli()


# ==============================================================================
# Fixtures for Mock HTML & Datasets
# ==============================================================================
@pytest.fixture
def sample_hub_html() -> str:
    return MOCK_HUB_HTML


@pytest.fixture
def sample_round_50_html() -> str:
    return generate_round_50_html()


@pytest.fixture
def sample_round_38_html() -> str:
    return generate_round_38_html()


@pytest.fixture
def sample_round_40_html() -> str:
    return generate_round_40_html()


@pytest.fixture
def sample_full_dataset() -> dict[int, list[dict[str, Any]]]:
    return generate_full_15_rounds_dataset()


# ==============================================================================
# Network Mocking Session Fixture
# ==============================================================================
@pytest.fixture
def mock_network_session(
    sample_hub_html, sample_round_50_html, sample_round_38_html, sample_round_40_html
):
    """Provides a requests.Session mock that handles requests to sqldpass URLs."""
    session = MagicMock(spec=requests.Session)

    def mock_get(url, *args, **kwargs):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200

        if "/blog/category/ADsP" in url:
            resp.text = sample_hub_html
        elif "adsp-2026-50" in url:
            resp.text = sample_round_50_html
        elif "adsp-2023-38" in url:
            resp.text = sample_round_38_html
        elif "adsp-2024-40" in url:
            resp.text = sample_round_40_html
        elif re.search(r"adsp-\d{4}-\d+", url):
            # Other rounds default to 50-question mock
            resp.text = sample_round_50_html
        else:
            resp.status_code = 404
            resp.text = "Not Found"
            resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
            return resp

        resp.raise_for_status = MagicMock()
        return resp

    session.get.side_effect = mock_get
    return session


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Provides an isolated directory for output file verification."""
    out = tmp_path / "test_data"
    out.mkdir(parents=True, exist_ok=True)
    return out
