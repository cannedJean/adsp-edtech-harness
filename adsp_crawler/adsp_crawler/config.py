"""Configuration constants and settings for the ADsP past-exam crawler."""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Tuple

# Base domain and Category Hub URL
BASE_URL: str = "https://www.sqldpass.com"
HUB_URL: str = "https://www.sqldpass.com/blog/category/ADsP"

# Regular expression pattern to match and extract exam post URLs:
# e.g. /blog/past-exam/adsp-2022-32 -> year=2022, round=32
POST_LINK_PATTERN: re.Pattern = re.compile(r"^/blog/past-exam/adsp-(\d{4})-(\d+)$")
POST_LINK_REGEX: re.Pattern = re.compile(r"/blog/past-exam/adsp-(\d{4})-(\d+)")

# Complete list of 15 target exam rounds
TARGET_ROUNDS: List[int] = [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]
TOTAL_EXPECTED_ROUNDS: int = 15

# Total expected questions across all 15 rounds:
# Rounds 38 and 40 each have 49 questions (Question 50 omitted on source platform).
# The other 13 rounds each have 50 questions.
# 13 * 50 + 49 + 49 = 650 + 98 = 748 questions.
TOTAL_EXPECTED_QUESTIONS: int = 748

EXPECTED_ROUND_COUNTS: Dict[int, int] = {
    32: 50,
    35: 50,
    37: 50,
    38: 49,
    39: 50,
    40: 49,
    41: 50,
    42: 50,
    44: 50,
    45: 50,
    46: 50,
    47: 50,
    48: 50,
    49: 50,
    50: 50,
}

# Short-answer questions (단답형):
# Rounds 32, 35, 37, 38 have 10 short-answer questions each.
# Rounds 39 and 40~50 have 0 short-answer questions (100% 4-choice multiple choice).
EXPECTED_SHORT_ANSWER_COUNTS: Dict[int, int] = {
    32: 10,
    35: 10,
    37: 10,
    38: 10,
    39: 0,
    40: 0,
    41: 0,
    42: 0,
    44: 0,
    45: 0,
    46: 0,
    47: 0,
    48: 0,
    49: 0,
    50: 0,
}

# Multiple-choice questions (4지선다):
EXPECTED_MC_COUNTS: Dict[int, int] = {
    32: 40,
    35: 40,
    37: 40,
    38: 39,
    39: 50,
    40: 49,
    41: 50,
    42: 50,
    44: 50,
    45: 50,
    46: 50,
    47: 50,
    48: 50,
    49: 50,
    50: 50,
}

# Polite browser-mimicking HTTP headers to avoid Cloudflare bot blocking
DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Polite rate limiting & jitter delay bounds (in seconds)
DEFAULT_DELAY_MIN: float = 1.0
DEFAULT_DELAY_MAX: float = 2.0

# HTTP connection parameters
DEFAULT_TIMEOUT: float = 15.0
MAX_RETRIES: int = 3
BACKOFF_FACTOR: float = 0.5
RETRY_STATUS_CODES: Tuple[int, ...] = (429, 500, 502, 503, 504)


@dataclass
class CrawlerConfig:
    """Configurable settings container for the ADsP crawler."""

    hub_url: str = HUB_URL
    base_url: str = BASE_URL
    target_rounds: List[int] = field(default_factory=lambda: list(TARGET_ROUNDS))
    headers: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HEADERS))
    delay_min: float = DEFAULT_DELAY_MIN
    delay_max: float = DEFAULT_DELAY_MAX
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = MAX_RETRIES
    backoff_factor: float = BACKOFF_FACTOR
    retry_status_codes: Tuple[int, ...] = RETRY_STATUS_CODES
