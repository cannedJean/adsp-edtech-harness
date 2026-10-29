import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import requests

import adsp_crawler
from adsp_crawler.config import (
    BASE_URL,
    HUB_URL,
    TARGET_ROUNDS,
    TOTAL_EXPECTED_ROUNDS,
    TOTAL_EXPECTED_QUESTIONS,
    EXPECTED_ROUND_COUNTS,
    EXPECTED_SHORT_ANSWER_COUNTS,
    EXPECTED_MC_COUNTS,
    DEFAULT_HEADERS,
    DEFAULT_DELAY_MIN,
    DEFAULT_DELAY_MAX,
    DEFAULT_TIMEOUT,
    CrawlerConfig,
)
from adsp_crawler.fetcher import (
    create_session,
    apply_polite_delay,
    discover_rounds,
    fetch_hub_html,
    fetch_post,
    fetch_round_post,
    fetch_all_posts,
)


class TestConfig(unittest.TestCase):
    """Test suite for config.py constants and configurations."""

    def test_target_rounds_and_counts(self):
        self.assertEqual(len(TARGET_ROUNDS), 15)
        self.assertEqual(TOTAL_EXPECTED_ROUNDS, 15)
        self.assertEqual(TARGET_ROUNDS, [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50])

    def test_question_census_distribution(self):
        self.assertEqual(TOTAL_EXPECTED_QUESTIONS, 748)
        self.assertEqual(sum(EXPECTED_ROUND_COUNTS.values()), 748)
        self.assertEqual(EXPECTED_ROUND_COUNTS[38], 49)
        self.assertEqual(EXPECTED_ROUND_COUNTS[40], 49)
        for r in TARGET_ROUNDS:
            if r not in (38, 40):
                self.assertEqual(EXPECTED_ROUND_COUNTS[r], 50)

    def test_short_answer_and_mc_counts(self):
        self.assertEqual(sum(EXPECTED_SHORT_ANSWER_COUNTS.values()), 40)
        self.assertEqual(sum(EXPECTED_MC_COUNTS.values()), 708)
        for r in (32, 35, 37, 38):
            self.assertEqual(EXPECTED_SHORT_ANSWER_COUNTS[r], 10)
        for r in (39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50):
            self.assertEqual(EXPECTED_SHORT_ANSWER_COUNTS[r], 0)

    def test_headers_and_rate_limits(self):
        self.assertIn("User-Agent", DEFAULT_HEADERS)
        self.assertIn("Mozilla", DEFAULT_HEADERS["User-Agent"])
        self.assertIn("Chrome", DEFAULT_HEADERS["User-Agent"])
        self.assertIn("Accept", DEFAULT_HEADERS)
        self.assertIn("Accept-Language", DEFAULT_HEADERS)
        self.assertGreaterEqual(DEFAULT_DELAY_MIN, 1.0)
        self.assertLessEqual(DEFAULT_DELAY_MAX, 2.0)
        self.assertEqual(DEFAULT_TIMEOUT, 15.0)

    def test_crawler_config_dataclass(self):
        cfg = CrawlerConfig(delay_min=0.0, delay_max=0.0, timeout=5.0)
        self.assertEqual(cfg.delay_min, 0.0)
        self.assertEqual(cfg.timeout, 5.0)
        self.assertEqual(len(cfg.target_rounds), 15)


class TestFetcherMocked(unittest.TestCase):
    """Test suite for fetcher.py logic using mocks."""

    def test_create_session(self):
        session = create_session(headers={"X-Custom": "test"})
        self.assertEqual(session.headers.get("X-Custom"), "test")
        self.assertIn("Mozilla", session.headers.get("User-Agent", ""))

    def test_apply_polite_delay_disabled_in_fast_mode(self):
        duration = apply_polite_delay(0.0, 0.0)
        self.assertEqual(duration, 0.0)
        duration_neg = apply_polite_delay(-1.0, 0.0)
        self.assertEqual(duration_neg, 0.0)

    @patch("time.sleep")
    @patch("random.uniform", return_value=1.55)
    def test_apply_polite_delay_enabled(self, mock_uniform, mock_sleep):
        duration = apply_polite_delay(1.0, 2.0)
        self.assertEqual(duration, 1.55)
        mock_uniform.assert_called_once_with(1.0, 2.0)
        mock_sleep.assert_called_once_with(1.55)

    def test_discover_rounds_mock_html(self):
        mock_html = """
        <html>
            <body>
                <a href="/blog/past-exam/adsp-2026-50">50회 기출 복원</a>
                <a href="/blog/past-exam/adsp-2022-32">32회 기출 복원</a>
                <a href="/blog/past-exam/adsp-2023-38">38회 기출 복원</a>
                <a href="/blog/category/ADsP">카테고리 홈</a>
                <a href="https://www.sqldpass.com/blog/past-exam/adsp-2024-40">40회 기출 복원 (절대경로)</a>
                <a href="/blog/exam-guide/adsp-43">가이드</a>
            </body>
        </html>
        """
        rounds = discover_rounds(mock_html, base_url="https://www.sqldpass.com")
        self.assertEqual(list(rounds.keys()), [32, 38, 40, 50])
        self.assertEqual(rounds[32], "https://www.sqldpass.com/blog/past-exam/adsp-2022-32")
        self.assertEqual(rounds[50], "https://www.sqldpass.com/blog/past-exam/adsp-2026-50")
        self.assertEqual(rounds[40], "https://www.sqldpass.com/blog/past-exam/adsp-2024-40")

    def test_discover_rounds_empty_html(self):
        self.assertEqual(discover_rounds(""), {})
        self.assertEqual(discover_rounds("<html><body>No links</body></html>"), {})

    def test_fetch_post_success(self):
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html>Post content</html>"
        mock_session.get.return_value = mock_resp

        html = fetch_post("https://www.sqldpass.com/test", session=mock_session, delay_min=0, delay_max=0)
        self.assertEqual(html, "<html>Post content</html>")
        mock_session.get.assert_called_once_with("https://www.sqldpass.com/test", timeout=DEFAULT_TIMEOUT, headers=None)

    @patch("time.sleep")
    def test_fetch_post_retry_on_500(self, mock_sleep):
        mock_session = MagicMock()
        mock_fail = MagicMock()
        mock_fail.status_code = 500

        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.text = "Recovered after retry"

        mock_session.get.side_effect = [mock_fail, mock_ok]

        html = fetch_post("https://www.sqldpass.com/test", session=mock_session, delay_min=0, delay_max=0, retries=3)
        self.assertEqual(html, "Recovered after retry")
        self.assertEqual(mock_session.get.call_count, 2)
        mock_sleep.assert_called_once()

    def test_fetch_round_post_invalid_round(self):
        with self.assertRaises(ValueError):
            fetch_round_post(999, hub_urls={32: "https://..."}, delay_min=0, delay_max=0)

    def test_fetch_all_posts_with_mock(self):
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "content"
        mock_session.get.return_value = mock_resp

        hub_urls = {
            32: "https://www.sqldpass.com/blog/past-exam/adsp-2022-32",
            50: "https://www.sqldpass.com/blog/past-exam/adsp-2026-50",
        }
        res = fetch_all_posts(rounds=[32, 50], hub_urls=hub_urls, session=mock_session, delay_min=0, delay_max=0)
        self.assertEqual(set(res.keys()), {32, 50})
        self.assertEqual(res[32], "content")
        self.assertEqual(res[50], "content")


if __name__ == "__main__":
    unittest.main()
