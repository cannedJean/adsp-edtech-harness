"""Command Line Interface (CLI) and crawler pipeline coordinator for ADsP."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from .config import DEFAULT_DELAY_MAX, DEFAULT_DELAY_MIN, TARGET_ROUNDS
from .fetcher import create_session, discover_rounds, fetch_hub_html, fetch_round_post
from .parser import parse_adsp_post
from .storage import save_consolidated_json, save_round_json
from .validator import validate_consolidated_dataset, validate_round_dataset

logger = logging.getLogger("adsp_crawler")


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ADsP Past Exam Crawler & Dataset Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--round",
        type=int,
        nargs="+",
        dest="rounds",
        help="Specific round(s) to crawl (e.g. --round 50 or --round 38 40 50)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Crawl all 15 rounds (default if --round not specified)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Directory to save output JSON files",
    )
    parser.add_argument(
        "--no-delay",
        action="store_true",
        default=False,
        help="Disable polite jitter delays for fast testing",
    )
    parsed = parser.parse_args(args)

    if parsed.rounds:
        for r in parsed.rounds:
            if r not in TARGET_ROUNDS:
                parser.error(
                    f"Invalid round {r}. Supported rounds are: {TARGET_ROUNDS}. "
                    f"(Note: Round 43 does not exist as an exam restoration post)"
                )
    return parsed


def main(args: Optional[List[str]] = None) -> int:
    """Coordinate the ADsP exam crawl: discovery -> fetch -> parse -> validate -> store."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parsed = parse_args(args)
    rounds_to_crawl = parsed.rounds if parsed.rounds is not None else TARGET_ROUNDS
    output_dir = Path(parsed.output_dir)

    delay_min = 0.0 if parsed.no_delay else DEFAULT_DELAY_MIN
    delay_max = 0.0 if parsed.no_delay else DEFAULT_DELAY_MAX

    session = create_session()
    hub_html = fetch_hub_html(session=session)
    hub_urls = discover_rounds(hub_html)

    all_harvested: Dict[int, List[Dict[str, Any]]] = {}

    for r in rounds_to_crawl:
        logger.info("Processing Round %d...", r)
        html = fetch_round_post(
            r,
            hub_urls=hub_urls,
            session=session,
            delay_min=delay_min,
            delay_max=delay_max,
        )
        questions = parse_adsp_post(html)
        validate_round_dataset(r, questions)
        save_round_json(r, questions, output_dir=output_dir)
        all_harvested[r] = questions
        logger.info("Round %d successfully crawled and saved (%d questions).", r, len(questions))

    # If all 15 rounds were crawled, validate and persist consolidated dataset
    if set(all_harvested.keys()) == set(TARGET_ROUNDS):
        logger.info("Validating and persisting consolidated dataset...")
        validate_consolidated_dataset(all_harvested)
        save_consolidated_json(all_harvested, output_dir=output_dir)
        logger.info("Consolidated dataset successfully saved to %s", output_dir / "adsp_all.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
