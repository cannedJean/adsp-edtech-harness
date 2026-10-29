"""Reference contract implementation for ADsP crawler.

Provides genuine fallback implementations matching interface contracts from
PROJECT.md, spec_miner_survey_1, explorer_survey_2, and explorer_survey_3.
Used for progressive testability when crawler modules are in development.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import time
from typing import Any

from bs4 import BeautifulSoup
import requests

# ==============================================================================
# Config Module Interface
# ==============================================================================
HUB_URL = "https://www.sqldpass.com/blog/category/ADsP"
POST_LINK_PATTERN = re.compile(r"^/blog/past-exam/adsp-(\d{4})-(\d+)$")
TARGET_ROUNDS = [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]
ROUND_QUESTION_COUNTS = {r: (49 if r in (38, 40) else 50) for r in TARGET_ROUNDS}
TOTAL_QUESTIONS = 748

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

JITTER_MIN = 1.0
JITTER_MAX = 2.0
TIMEOUT = 15.0


# ==============================================================================
# Fetcher Module Interface
# ==============================================================================
def discover_rounds(hub_html: str) -> dict[int, str]:
    """Parse category hub HTML to find exam round links."""
    soup = BeautifulSoup(hub_html, "html.parser")
    discovered = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        m = POST_LINK_PATTERN.match(href)
        if m:
            r_no = int(m.group(2))
            full_url = f"https://www.sqldpass.com{href}" if href.startswith("/") else href
            discovered[r_no] = full_url
    return discovered


def fetch_hub_html(session: requests.Session | None = None) -> str:
    """Fetch category hub page HTML with polite headers."""
    sess = session or requests.Session()
    resp = sess.get(HUB_URL, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def fetch_post(
    url: str,
    session: requests.Session | None = None,
    delay_min: float = JITTER_MIN,
    delay_max: float = JITTER_MAX,
    max_retries: int = 3,
) -> str:
    """Fetch post HTML with jitter delay and retry logic."""
    if delay_max > 0:
        sleep_time = random.uniform(delay_min, delay_max)
        time.sleep(sleep_time)

    sess = session or requests.Session()
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = sess.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
            else:
                raise last_exc


def fetch_round_post(
    round_no: int,
    hub_urls: dict[int, str] | None = None,
    session: requests.Session | None = None,
) -> str:
    """Convenience helper to fetch post by round number."""
    if hub_urls is None:
        hub_html = fetch_hub_html(session=session)
        hub_urls = discover_rounds(hub_html)

    if round_no not in hub_urls:
        raise ValueError(f"Round {round_no} not found in discovered rounds.")

    return fetch_post(hub_urls[round_no], session=session)


def fetch_all_posts(rounds: list[int] | None = None) -> dict[int, str]:
    """Fetch posts for specified rounds or all target rounds."""
    target = rounds or TARGET_ROUNDS
    sess = requests.Session()
    hub_html = fetch_hub_html(session=sess)
    hub_urls = discover_rounds(hub_html)

    posts = {}
    for r in target:
        if r in hub_urls:
            posts[r] = fetch_post(hub_urls[r], session=sess)
    return posts


# ==============================================================================
# Parser Module Interface
# ==============================================================================
def _table_to_gfm(table_soup: BeautifulSoup) -> str:
    """Convert HTML table to GFM markdown table with padded empty cells."""
    rows = []
    # Collect thead rows
    thead = table_soup.find("thead")
    if thead:
        for tr in thead.find_all("tr"):
            cells = [th.get_text(strip=True) for th in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)

    # Collect tbody rows
    tbody = table_soup.find("tbody") or table_soup
    for tr in tbody.find_all("tr"):
        if thead and tr.find_parent("thead"):
            continue
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    # Normalize column count across all rows
    max_cols = max(len(r) for r in rows)
    padded_rows = [r + [""] * (max_cols - len(r)) for r in rows]

    header = padded_rows[0]
    sep = ["---"] * max_cols
    body = padded_rows[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def parse_adsp_post(html: str) -> list[dict[str, Any]]:
    """Hybrid parser combining Next.js RSC flight stream with DOM parsing."""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.rounded-2xl")

    # 1. Extract Flight Text Chunks & Prompts
    f_matches = re.findall(
        r'self\.__next_f\.push\(\[(\d+),\s*"((?:[^"\\]|\\.)*)"\]\)', html
    )
    combined = "".join(json.loads(f'"{c}"') for _, c in f_matches)

    # Build text chunk lookup table (hex reference resolution)
    text_chunks = {}
    for m in re.finditer(
        r"(?:^|\n)([0-9a-fA-F]+):T[0-9a-fA-F]+,(.*?)(?=(?:\n[0-9a-fA-F]+:|\Z))",
        combined,
        re.DOTALL,
    ):
        text_chunks[f"${m.group(1)}"] = m.group(2)

    # Extract flight prompts
    prompt_pattern = (
        r'\["\$","div",null,\{"className":"mt-3","children":\["\$","\$L[0-9a-zA-Z]+",null,'
        r'\{"content":"(.*?)"(?:,"variant":"pastExam")?\}\]\}\]'
    )
    raw_prompts = re.findall(prompt_pattern, combined, re.DOTALL)

    questions = []
    for idx, it in enumerate(items):
        # 1. Question Number
        num_el = it.select_one("p.tabular-nums")
        q_no_m = re.search(r"\d+", num_el.get_text(strip=True) if num_el else "")
        q_no = int(q_no_m.group()) if q_no_m else idx + 1

        # 2. Question Type
        badge = it.select_one("div.flex.items-center.justify-between span")
        q_type_raw = badge.get_text(strip=True) if badge else ""
        q_type = "단답형" if "단답" in q_type_raw else "4지선다"

        # 3. Prompt (with flight resolution & ```r normalization)
        if idx < len(raw_prompts):
            p_raw = raw_prompts[idx]
            try:
                prompt_val = json.loads(f'"{p_raw}"')
            except Exception:
                prompt_val = p_raw
            if prompt_val.startswith("$") and prompt_val in text_chunks:
                prompt_val = text_chunks[prompt_val]
        else:
            # Fallback to DOM if flight missing or truncated
            p_div = it.select_one("div.mt-3")
            if p_div:
                # Check for table
                tbl = p_div.find("table")
                tbl_gfm = _table_to_gfm(tbl) if tbl else ""
                # Get text without table text duplicates
                for t in p_div.find_all("table"):
                    t.decompose()
                prompt_text = p_div.get_text(separator="\n", strip=True)
                if tbl_gfm:
                    prompt_val = f"{prompt_text}\n\n{tbl_gfm}"
                else:
                    prompt_val = prompt_text
            else:
                prompt_val = ""

        # Normalize code block language tag to ```r
        prompt_val = re.sub(r"```(?:text)?\n", "```r\n", prompt_val)

        # 4. Options
        options = []
        if q_type == "4지선다":
            for li in it.select("ul.mt-4 > li"):
                span = li.select_one("span.min-w-0")
                opt_txt = span.get_text(strip=True) if span else li.get_text(strip=True)
                options.append(opt_txt.strip())

        # 5. Answer Key
        ans_el = it.select_one("details p.text-base.font-semibold.text-success")
        raw_ans = ans_el.get_text(strip=True) if ans_el else ""
        if q_type == "4지선다":
            ans_m = re.search(r"\d+", raw_ans)
            ans = ans_m.group() if ans_m else raw_ans.strip()
        else:
            ans = raw_ans.strip()

        questions.append({
            "question_no": q_no,
            "question_type": q_type,
            "prompt": prompt_val.strip(),
            "options": options,
            "answer": ans,
        })

    return questions


# ==============================================================================
# Validator Module Interface
# ==============================================================================
class ValidationError(Exception):
    """Raised when question schema or census validation fails."""


def validate_question(q: dict[str, Any]) -> bool:
    """Validate a single question dictionary against strict schema."""
    if not isinstance(q, dict):
        raise ValidationError(f"Question must be a dict, got {type(q)}")

    required_keys = {"question_no", "question_type", "prompt", "options", "answer"}
    if set(q.keys()) != required_keys:
        raise ValidationError(f"Question keys mismatch. Expected {required_keys}, got {set(q.keys())}")

    # question_no: int between 1 and 50
    if not isinstance(q["question_no"], int) or not (1 <= q["question_no"] <= 50):
        raise ValidationError(f"Invalid question_no: {q.get('question_no')}")

    # question_type: '4지선다' or '단답형'
    if q["question_type"] not in ("4지선다", "단답형"):
        raise ValidationError(f"Invalid question_type: {q.get('question_type')}")

    # prompt: non-empty string
    if not isinstance(q["prompt"], str) or len(q["prompt"].strip()) == 0:
        raise ValidationError(f"Prompt must be non-empty string for Q{q.get('question_no')}")

    # options: 4 items for 4지선다, [] for 단답형
    if not isinstance(q["options"], list):
        raise ValidationError(f"Options must be a list for Q{q.get('question_no')}")

    if q["question_type"] == "4지선다":
        if len(q["options"]) != 4:
            raise ValidationError(f"4지선다 question must have exactly 4 options, got {len(q['options'])}")
        for opt in q["options"]:
            if not isinstance(opt, str) or len(opt.strip()) == 0:
                raise ValidationError("Each option in 4지선다 must be non-empty string")
    else:  # 단답형
        if len(q["options"]) != 0:
            raise ValidationError(f"단답형 question must have empty options [], got {len(q['options'])}")

    # answer: non-empty string
    if not isinstance(q["answer"], str) or len(q["answer"].strip()) == 0:
        raise ValidationError(f"Answer must be non-empty string for Q{q.get('question_no')}")

    if q["question_type"] == "4지선다" and q["answer"] not in ("1", "2", "3", "4"):
        raise ValidationError(f"4지선다 answer must be '1'~'4', got '{q['answer']}'")

    # Negative exclusion check: ensure no explanation leaks
    forbidden_terms = ["오답 풀이", "오답풀이", "보충 개념", "보충개념", "정답·해설 보기", "정답해설보기"]
    combined_text = q["prompt"] + " " + " ".join(q["options"]) + " " + q["answer"]
    for term in forbidden_terms:
        if term in combined_text:
            raise ValidationError(f"Forbidden explanation term '{term}' leaked in Q{q['question_no']}")

    return True


def validate_round_dataset(round_no: int, questions: list[dict[str, Any]]) -> bool:
    """Validate all questions in a single round."""
    expected_count = ROUND_QUESTION_COUNTS.get(round_no, 50)
    if len(questions) != expected_count:
        raise ValidationError(
            f"Round {round_no} expected {expected_count} questions, got {len(questions)}"
        )

    seen_nos = set()
    for q in questions:
        validate_question(q)
        q_no = q["question_no"]
        if q_no in seen_nos:
            raise ValidationError(f"Duplicate question_no {q_no} in Round {round_no}")
        seen_nos.add(q_no)

    return True


def validate_consolidated_dataset(all_data: dict[int, list[dict[str, Any]]] | list[dict[str, Any]]) -> bool:
    """Validate the consolidated collection across all 15 rounds."""
    if isinstance(all_data, dict):
        total_questions = sum(len(qs) for qs in all_data.values())
        if len(all_data) != len(TARGET_ROUNDS):
            raise ValidationError(f"Expected {len(TARGET_ROUNDS)} rounds, got {len(all_data)}")
        for r_no, qs in all_data.items():
            validate_round_dataset(r_no, qs)
    elif isinstance(all_data, list):
        total_questions = len(all_data)
        for q in all_data:
            validate_question(q)
    else:
        raise ValidationError(f"Invalid all_data type: {type(all_data)}")

    if total_questions != TOTAL_QUESTIONS:
        raise ValidationError(f"Expected total {TOTAL_QUESTIONS} questions, got {total_questions}")

    return True


# ==============================================================================
# Storage Module Interface
# ==============================================================================
def save_round_json(
    round_no: int,
    questions: list[dict[str, Any]],
    output_dir: str | Path = "data",
) -> Path:
    """Persist single round dataset to data/adsp_round_{round}.json."""
    validate_round_dataset(round_no, questions)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target_file = out_dir / f"adsp_round_{round_no}.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    return target_file


def save_consolidated_json(
    all_questions: list[dict[str, Any]] | dict[int, list[dict[str, Any]]],
    output_dir: str | Path = "data",
) -> Path:
    """Persist consolidated dataset to data/adsp_all.json."""
    validate_consolidated_dataset(all_questions)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target_file = out_dir / "adsp_all.json"

    if isinstance(all_questions, dict):
        # Flatten dict into ordered list
        flattened = []
        for r in sorted(all_questions.keys()):
            for q in all_questions[r]:
                q_copy = dict(q)
                q_copy["round"] = r
                flattened.append(q_copy)
        data_to_write = flattened
    else:
        data_to_write = all_questions

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data_to_write, f, ensure_ascii=False, indent=2)
    return target_file


# ==============================================================================
# CLI Module Interface
# ==============================================================================
def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="ADsP Past Exam Crawler & Dataset Pipeline")
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
        help="Directory to save output JSON files (default: data)",
    )
    parsed = parser.parse_args(args)

    # Validate rounds if provided
    if parsed.rounds:
        for r in parsed.rounds:
            if r not in TARGET_ROUNDS:
                parser.error(
                    f"Invalid round {r}. Supported rounds are: {TARGET_ROUNDS}. "
                    f"(Note: Round 43 does not exist as an exam restoration post)"
                )
    return parsed


def main(args: list[str] | None = None) -> int:
    """CLI entrypoint coordinator."""
    parsed = parse_args(args)
    rounds_to_crawl = parsed.rounds or TARGET_ROUNDS
    output_dir = Path(parsed.output_dir)

    all_harvested = {}
    for r in rounds_to_crawl:
        # In mock / test mode or live mode
        html = fetch_round_post(r)
        questions = parse_adsp_post(html)
        validate_round_dataset(r, questions)
        save_round_json(r, questions, output_dir=output_dir)
        all_harvested[r] = questions

    if len(all_harvested) == len(TARGET_ROUNDS):
        save_consolidated_json(all_harvested, output_dir=output_dir)

    return 0
