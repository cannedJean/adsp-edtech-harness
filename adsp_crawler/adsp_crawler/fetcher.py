"""Hub discovery and SSR HTML fetching module for ADsP crawler with polite rate limiting."""

import logging
import random
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .config import (
    BACKOFF_FACTOR,
    BASE_URL,
    DEFAULT_DELAY_MAX,
    DEFAULT_DELAY_MIN,
    DEFAULT_HEADERS,
    DEFAULT_TIMEOUT,
    HUB_URL,
    MAX_RETRIES,
    POST_LINK_REGEX,
    RETRY_STATUS_CODES,
)

logger = logging.getLogger(__name__)


def create_session(headers: Optional[Dict[str, str]] = None) -> requests.Session:
    """Create and configure a requests.Session with default polite headers and connection pooling.

    Args:
        headers: Optional dictionary of additional or override HTTP headers.

    Returns:
        requests.Session: Pre-configured HTTP session.
    """
    session = requests.Session()
    req_headers = dict(DEFAULT_HEADERS)
    if headers:
        req_headers.update(headers)
    session.headers.update(req_headers)

    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=list(RETRY_STATUS_CODES),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def apply_polite_delay(
    delay_min: float = DEFAULT_DELAY_MIN,
    delay_max: float = DEFAULT_DELAY_MAX,
) -> float:
    """Sleep for a random jitter duration between delay_min and delay_max seconds.

    If delay_max <= 0 or delay_min < 0, no sleep is executed (useful for fast testing).

    Args:
        delay_min: Minimum delay in seconds.
        delay_max: Maximum delay in seconds.

    Returns:
        float: Actual sleep duration in seconds.
    """
    if delay_max <= 0.0 or delay_min < 0.0:
        return 0.0

    actual_min = min(delay_min, delay_max)
    actual_max = max(delay_min, delay_max)
    jitter = random.uniform(actual_min, actual_max)
    logger.debug("Applying polite rate-limiting jitter: %.2fs", jitter)
    time.sleep(jitter)
    return jitter


def fetch_hub_html(
    session: Optional[requests.Session] = None,
    hub_url: str = HUB_URL,
    timeout: float = DEFAULT_TIMEOUT,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """Fetch the HTML content of the ADsP category hub page.

    Args:
        session: requests.Session instance to use. If None, a new session is created.
        hub_url: URL of the category hub page (defaults to config.HUB_URL).
        timeout: Network timeout in seconds.
        headers: Optional additional request headers.

    Returns:
        str: Raw HTML body of the hub page.

    Raises:
        requests.RequestException: If the HTTP request fails or returns a non-200 status.
    """
    # Accommodate positional string argument if caller called fetch_hub_html(url_string)
    if isinstance(session, str):
        hub_url = session
        session = None

    sess = session if session is not None else create_session()
    logger.info("Fetching ADsP category hub from %s", hub_url)
    resp = sess.get(hub_url, timeout=timeout, headers=headers)
    resp.raise_for_status()
    return resp.text


def discover_rounds(hub_html: str, base_url: str = BASE_URL) -> Dict[int, str]:
    """Parse category hub HTML to dynamically discover all ADsP exam post URLs.

    Args:
        hub_html: HTML content of the category hub page.
        base_url: Base URL to prepend to relative paths.

    Returns:
        Dict[int, str]: Mapping of round number (int) -> absolute post URL (str),
            ordered by ascending round number.
    """
    if not hub_html:
        return {}

    soup = BeautifulSoup(hub_html, "html.parser")
    discovered: Dict[int, str] = {}

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        match = POST_LINK_REGEX.search(href)
        if match:
            round_no = int(match.group(2))
            full_url = urljoin(base_url, href)
            # Retain or overwrite with canonical full URL
            discovered[round_no] = full_url

    # Return sorted by round number
    sorted_rounds = dict(sorted(discovered.items(), key=lambda item: item[0]))
    logger.info("Discovered %d exam rounds: %s", len(sorted_rounds), list(sorted_rounds.keys()))
    return sorted_rounds


def fetch_post(
    url: str,
    session: Optional[requests.Session] = None,
    delay_min: float = DEFAULT_DELAY_MIN,
    delay_max: float = DEFAULT_DELAY_MAX,
    retries: int = MAX_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """Fetch an individual exam post SSR HTML with polite rate limiting and retry handling.

    Args:
        url: Full URL of the exam post.
        session: Reusable requests.Session. If None, a new session is created.
        delay_min: Minimum jitter delay before request in seconds.
        delay_max: Maximum jitter delay before request in seconds.
        retries: Number of retry attempts on transient failures.
        timeout: Request timeout in seconds.
        headers: Optional override/additional headers.

    Returns:
        str: Raw HTML body of the exam post.

    Raises:
        requests.RequestException: If the post could not be fetched after all retries.
    """
    apply_polite_delay(delay_min, delay_max)

    sess = session if session is not None else create_session()
    last_exception: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            logger.debug("Fetching post (attempt %d/%d): %s", attempt, retries, url)
            resp = sess.get(url, timeout=timeout, headers=headers)

            if resp.status_code in RETRY_STATUS_CODES and attempt < retries:
                backoff = BACKOFF_FACTOR * (2 ** (attempt - 1))
                logger.warning(
                    "HTTP %d received for %s. Retrying in %.2fs (attempt %d/%d)...",
                    resp.status_code,
                    url,
                    backoff,
                    attempt,
                    retries,
                )
                time.sleep(backoff)
                continue

            resp.raise_for_status()
            return resp.text

        except (requests.RequestException, Exception) as exc:
            last_exception = exc
            if attempt < retries:
                backoff = BACKOFF_FACTOR * (2 ** (attempt - 1))
                logger.warning(
                    "Error fetching %s: %s. Retrying in %.2fs (attempt %d/%d)...",
                    url,
                    exc,
                    backoff,
                    attempt,
                    retries,
                )
                time.sleep(backoff)
            else:
                logger.error("Failed to fetch %s after %d attempts: %s", url, retries, exc)
                raise last_exception from exc

    if last_exception:
        raise last_exception
    raise RuntimeError(f"Unexpected termination fetching {url}")


def fetch_round_post(
    round_no: int,
    hub_urls: Optional[Dict[int, str]] = None,
    session: Optional[requests.Session] = None,
    delay_min: float = DEFAULT_DELAY_MIN,
    delay_max: float = DEFAULT_DELAY_MAX,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Fetch the HTML of a specific exam round post.

    If hub_urls is not provided, the category hub is queried to discover the URL mapping.

    Args:
        round_no: The round number (e.g. 50).
        hub_urls: Optional pre-discovered mapping of round numbers to URLs.
        session: Optional reusable session.
        delay_min: Minimum jitter delay before request in seconds.
        delay_max: Maximum jitter delay before request in seconds.
        timeout: Request timeout in seconds.

    Returns:
        str: Raw HTML body of the round post.

    Raises:
        ValueError: If round_no is not found in discovered hub posts.
        requests.RequestException: If fetching fails.
    """
    sess = session if session is not None else create_session()

    if hub_urls is None:
        hub_html = fetch_hub_html(session=sess, timeout=timeout)
        hub_urls = discover_rounds(hub_html)

    if round_no not in hub_urls:
        available = sorted(hub_urls.keys())
        raise ValueError(f"Round {round_no} not found in discovered hub posts. Available rounds: {available}")

    url = hub_urls[round_no]
    return fetch_post(
        url=url,
        session=sess,
        delay_min=delay_min,
        delay_max=delay_max,
        timeout=timeout,
    )


def fetch_all_posts(
    rounds: Optional[List[int]] = None,
    hub_urls: Optional[Dict[int, str]] = None,
    session: Optional[requests.Session] = None,
    delay_min: float = DEFAULT_DELAY_MIN,
    delay_max: float = DEFAULT_DELAY_MAX,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[int, str]:
    """Fetch HTML content for all specified rounds (or all discovered rounds).

    Args:
        rounds: Specific round numbers to fetch. If None, all discovered rounds are fetched.
        hub_urls: Optional pre-discovered round URL mapping.
        session: Optional reusable requests.Session.
        delay_min: Minimum jitter delay between consecutive post requests.
        delay_max: Maximum jitter delay between consecutive post requests.
        timeout: Request timeout in seconds.

    Returns:
        Dict[int, str]: Mapping of round number -> post HTML content.
    """
    sess = session if session is not None else create_session()

    if hub_urls is None:
        hub_html = fetch_hub_html(session=sess, timeout=timeout)
        hub_urls = discover_rounds(hub_html)

    target_rounds = rounds if rounds is not None else sorted(hub_urls.keys())
    results: Dict[int, str] = {}

    for round_no in target_rounds:
        if round_no not in hub_urls:
            raise ValueError(f"Target round {round_no} is not present in discovered hub URLs.")
        url = hub_urls[round_no]
        logger.info("Fetching exam post for Round %d: %s", round_no, url)
        results[round_no] = fetch_post(
            url=url,
            session=sess,
            delay_min=delay_min,
            delay_max=delay_max,
            timeout=timeout,
        )

    return results
