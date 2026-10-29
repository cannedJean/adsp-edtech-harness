"""ADsP Exam Crawler package."""

from .config import (
    BACKOFF_FACTOR,
    BASE_URL,
    DEFAULT_DELAY_MAX,
    DEFAULT_DELAY_MIN,
    DEFAULT_HEADERS,
    DEFAULT_TIMEOUT,
    EXPECTED_MC_COUNTS,
    EXPECTED_ROUND_COUNTS,
    EXPECTED_SHORT_ANSWER_COUNTS,
    HUB_URL,
    MAX_RETRIES,
    POST_LINK_PATTERN,
    POST_LINK_REGEX,
    RETRY_STATUS_CODES,
    TARGET_ROUNDS,
    TOTAL_EXPECTED_QUESTIONS,
    TOTAL_EXPECTED_ROUNDS,
    CrawlerConfig,
)
from .fetcher import (
    apply_polite_delay,
    create_session,
    discover_rounds,
    fetch_all_posts,
    fetch_hub_html,
    fetch_post,
    fetch_round_post,
)
from .parser import (
    extract_dom_prompt,
    extract_flight_prompts,
    html_table_to_gfm,
    normalize_r_code_blocks,
    parse_adsp_post,
    strip_inline_svgs,
)
from .validator import (
    ValidationError,
    validate_consolidated_dataset,
    validate_question,
    validate_round_dataset,
)
from .storage import (
    save_consolidated_json,
    save_round_json,
)
from .cli import (
    main,
    parse_args,
)

__version__ = "0.1.0"

__all__ = [
    "BASE_URL",
    "HUB_URL",
    "POST_LINK_PATTERN",
    "POST_LINK_REGEX",
    "TARGET_ROUNDS",
    "TOTAL_EXPECTED_ROUNDS",
    "TOTAL_EXPECTED_QUESTIONS",
    "EXPECTED_ROUND_COUNTS",
    "EXPECTED_SHORT_ANSWER_COUNTS",
    "EXPECTED_MC_COUNTS",
    "DEFAULT_HEADERS",
    "DEFAULT_DELAY_MIN",
    "DEFAULT_DELAY_MAX",
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES",
    "BACKOFF_FACTOR",
    "RETRY_STATUS_CODES",
    "CrawlerConfig",
    "create_session",
    "apply_polite_delay",
    "fetch_hub_html",
    "discover_rounds",
    "fetch_post",
    "fetch_round_post",
    "fetch_all_posts",
    "extract_flight_prompts",
    "extract_dom_prompt",
    "html_table_to_gfm",
    "normalize_r_code_blocks",
    "strip_inline_svgs",
    "parse_adsp_post",
    "ValidationError",
    "validate_question",
    "validate_round_dataset",
    "validate_consolidated_dataset",
    "save_round_json",
    "save_consolidated_json",
    "parse_args",
    "main",
]
