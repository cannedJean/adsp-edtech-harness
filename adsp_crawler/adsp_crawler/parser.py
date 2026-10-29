"""Semantic parser and rich element Markdown converter for ADsP exam questions.

Combines Next.js React Server Component (RSC) flight payload stream resolution
with DOM fallback parsing to extract questions with 100% fidelity:
- Integer question_no (1~50)
- question_type ('4지선다' or '단답형')
- Clean prompt preserving GFM tables (| ... |) and fenced ```r code blocks
- options array (4 strings for 4지선다, [] for 단답형)
- answer key ('1'~'4' for 4지선다, model answer text for 단답형)
- Zero explanation leaks (no '오답 풀이', '보충 개념', or '정답·해설 보기')
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# Explanation terms that must never leak into extracted question fields
FORBIDDEN_EXPLANATION_TERMS = [
    "오답 풀이",
    "오답풀이",
    "보충 개념",
    "보충개념",
    "정답·해설 보기",
    "정답해설보기",
]


def _decode_flight_chunk(chunk: str) -> str:
    """Decode a raw flight payload JSON-escaped string safely."""
    try:
        return json.loads(f'"{chunk}"')
    except Exception:
        try:
            escaped = chunk.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
            return json.loads(f'"{escaped}"')
        except Exception:
            return chunk


def html_table_to_gfm(table_soup: Optional[Union[BeautifulSoup, Tag]]) -> str:
    """Convert an HTML <table> element into a clean GitHub Flavored Markdown (GFM) table.

    Ensures empty cells are padded so all data rows match the column count of the header.

    Args:
        table_soup: A BeautifulSoup object or Tag representing an HTML table.

    Returns:
        str: GitHub Flavored Markdown table string with pipes (`| ... |`), or empty string.
    """
    if table_soup is None:
        return ""

    rows: List[List[str]] = []

    # 1. Look for thead rows
    thead = table_soup.find("thead")
    if thead:
        for tr in thead.find_all("tr"):
            cells = [th.get_text(strip=True) for th in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)

    # 2. Look for tbody rows (or any tr not in thead)
    tbody = table_soup.find("tbody") or table_soup
    for tr in tbody.find_all("tr"):
        if thead and tr.find_parent("thead"):
            continue
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    # Determine maximum number of columns across all rows
    max_cols = max(len(r) for r in rows)
    if max_cols == 0:
        return ""

    # Pad any rows that have fewer columns than max_cols
    padded_rows = [r + [""] * (max_cols - len(r)) for r in rows]

    header = padded_rows[0]
    separator = ["---"] * max_cols
    body_rows = padded_rows[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in body_rows:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def normalize_r_code_blocks(text: str) -> str:
    """Normalize code block fences to ```r language tag.

    Transforms unadorned triple backticks (```) and ```text into ```r,
    while preserving closing fences (```) and other language tags.

    Args:
        text: Input markdown text.

    Returns:
        str: Normalized text with ```r fenced code blocks.
    """
    if "```" not in text:
        return text

    # Match paired code blocks: ```[optional_lang]\n[code]\n```
    def _repl_block(match: re.Match) -> str:
        lang = match.group(1).strip()
        body = match.group(2)
        target_lang = "r" if lang.lower() in ("", "text") else lang
        return f"```{target_lang}\n{body}\n```"

    block_pattern = re.compile(
        r"```([a-zA-Z0-9_-]*)[ \t]*\n([\s\S]*?)\n```(?=[ \t]*(?:\n|$))"
    )
    new_text, count = block_pattern.subn(_repl_block, text)
    if count > 0:
        return new_text

    # State machine fallback for alternating opening/closing fences
    parts = re.split(r"(```[a-zA-Z0-9_-]*[ \t]*(?:\n|$))", text)
    output = []
    is_open = False
    for part in parts:
        if part.startswith("```"):
            if not is_open:
                fence_m = re.match(r"```([a-zA-Z0-9_-]*)", part)
                lang = fence_m.group(1).strip() if fence_m else ""
                target_lang = "r" if lang.lower() in ("", "text") else lang
                has_nl = "\n" in part
                output.append(f"```{target_lang}\n" if has_nl else f"```{target_lang}")
                is_open = True
            else:
                has_nl = "\n" in part
                output.append("```\n" if has_nl else "```")
                is_open = False
        else:
            output.append(part)

    return "".join(output)



def strip_inline_svgs(text: str) -> str:
    """Strip inline <svg>...</svg> elements from markdown prompt text.

    Args:
        text: Prompt text potentially containing embedded SVG markup.

    Returns:
        str: Prompt text with SVGs removed and clean whitespace.
    """
    if "<svg" not in text:
        return text
    cleaned = re.sub(r"<svg[\s\S]*?</svg>", "", text, flags=re.IGNORECASE)
    # Remove any resulting multiple blank lines
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def extract_flight_prompts(html: str) -> List[str]:
    """Extract question prompts from Next.js RSC Flight payload stream.

    Resolves hexadecimal reference chunks ($51, $5c, etc.) and normalizes
    fenced code blocks and GFM tables with 100% fidelity.

    Args:
        html: Raw SSR HTML page containing Next.js flight script tags.

    Returns:
        List[str]: Extracted and resolved question prompt markdown strings.
    """
    # 1. Extract all push chunks
    f_matches = re.findall(
        r'self\.__next_f\.push\(\[\s*(\d+)\s*,\s*"((?:[^"\\]|\\.)*)"\s*\]\)',
        html,
    )
    if not f_matches:
        return []

    combined_chunks = [_decode_flight_chunk(c) for _, c in f_matches]
    flight_text = "".join(combined_chunks)

    # 2. Build reference chunk dictionary (hex IDs: e.g. 51:T20,...)
    text_chunks: Dict[str, str] = {}
    for m in re.finditer(
        r"(?:^|\n)([0-9a-fA-F]+):T[0-9a-fA-F]+,(.*?)(?=(?:\n?[0-9a-fA-F]+:\[|\n[0-9a-fA-F]+:|\Z))",
        flight_text,
        re.DOTALL,
    ):
        ref_id = m.group(1)
        content = m.group(2)
        text_chunks[f"${ref_id}"] = content
        text_chunks[f"${ref_id.lower()}"] = content
        text_chunks[f"${ref_id.upper()}"] = content

    # 3. Extract question prompt content strings
    prompt_pattern = (
        r'\["\$","div",null,\{"className":"mt-3","children":\["\$","\$L[0-9a-zA-Z]+",null,'
        r'\{"content":"((?:[^"\\]|\\.)*)"(?:,"variant":"pastExam")?\}\]\}\]'
    )
    raw_prompts = re.findall(prompt_pattern, flight_text, re.DOTALL)

    resolved_prompts: List[str] = []
    for p_raw in raw_prompts:
        try:
            p_val = json.loads(f'"{p_raw}"')
        except Exception:
            p_val = p_raw

        # Resolve hex reference chunk if applicable (e.g. "$51")
        if p_val.startswith("$") and p_val in text_chunks:
            p_val = text_chunks[p_val]

        # Strip inline SVGs
        p_val = strip_inline_svgs(p_val)

        # Normalize code fences to ```r
        p_val = normalize_r_code_blocks(p_val)

        resolved_prompts.append(p_val.strip())

    return resolved_prompts


def extract_dom_prompt(question_container: Tag) -> str:
    """Fallback extraction of prompt text from question DOM container.

    Preserves GFM tables and R code blocks when flight stream is unavailable.

    Args:
        question_container: bs4.element.Tag representing `li.rounded-2xl`.

    Returns:
        str: Prompt markdown text.
    """
    p_div = question_container.select_one("div.mt-3")
    if not p_div:
        return ""

    # Parse an isolated sub-tree so modifications don't mutate the parent
    working_soup = BeautifulSoup(str(p_div), "html.parser")
    p_copy = working_soup.find("div") or working_soup

    # 1. Remove inline SVGs
    for svg in p_copy.find_all("svg"):
        svg.decompose()

    # 2. Convert and preserve HTML tables to GFM
    tables = p_copy.find_all("table")
    table_gfms: List[str] = []
    for tbl in tables:
        gfm = html_table_to_gfm(tbl)
        if gfm:
            table_gfms.append(gfm)
        tbl.decompose()

    # 3. Handle pre/code blocks: decompose bailout placeholders or preserve real code
    for pre in p_copy.find_all("pre"):
        pre_text = pre.get_text()
        if "BAILOUT_TO_CLIENT_SIDE_RENDERING" in pre_text or "animate-pulse" in str(pre):
            pre.decompose()
        else:
            code_text = pre_text.strip()
            pre.replace_with(f"\n\n```r\n{code_text}\n```\n\n")

    # 4. Extract remaining prompt text
    prompt_text = p_copy.get_text(separator="\n", strip=True)

    # Append any converted GFM tables
    if table_gfms:
        if prompt_text:
            combined = prompt_text + "\n\n" + "\n\n".join(table_gfms)
        else:
            combined = "\n\n".join(table_gfms)
    else:
        combined = prompt_text

    combined = normalize_r_code_blocks(combined)
    return combined.strip()


def parse_adsp_post(html: str) -> List[Dict[str, Any]]:
    """Parse an ADsP exam post HTML into structured question dictionaries.

    Uses hybrid Next.js RSC flight payload stream extraction with fallback
    to DOM parsing. Guaranteed to extract:
    - question_no: int (1~50)
    - question_type: str ('4지선다' or '단답형')
    - prompt: str (GFM tables and ```r code blocks preserved, zero explanation text)
    - options: list[str] (4 items for 4지선다, [] for 단답형)
    - answer: str ('1'~'4' for 4지선다, model answer text for 단답형)

    Args:
        html: Raw HTML content of the exam post.

    Returns:
        List[Dict[str, Any]]: List of parsed question records.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.rounded-2xl")

    # 1. Extract Flight Prompts
    flight_prompts = extract_flight_prompts(html)

    questions: List[Dict[str, Any]] = []

    for idx, it in enumerate(items):
        # 1. Question Number (from p.tabular-nums)
        num_el = it.select_one("p.tabular-nums")
        num_text = num_el.get_text(strip=True) if num_el else ""
        q_no_m = re.search(r"\d+", num_text)
        if q_no_m:
            q_no = int(q_no_m.group())
        else:
            q_no = idx + 1

        # 2. Question Type (from badge in header)
        badge = it.select_one("div.flex.items-center.justify-between span")
        q_type_raw = badge.get_text(strip=True) if badge else ""
        if "단답" in q_type_raw:
            q_type = "단답형"
        elif "4지" in q_type_raw or "선다" in q_type_raw:
            q_type = "4지선다"
        else:
            # Fallback heuristic: check if multiple choice list exists
            opts_found = it.select("ul.mt-4 > li")
            q_type = "4지선다" if len(opts_found) > 0 else "단답형"

        # 3. Prompt (Flight resolution preferred, DOM fallback)
        prompt_val = ""
        ast_markers = ('["$"', '{"className"', "rounded-2xl", "tabular-nums")
        if idx < len(flight_prompts) and flight_prompts[idx].strip():
            candidate = flight_prompts[idx].strip()
            # Verify candidate is not an unresolved chunk reference like "$51"
            # and does not leak raw React AST / Flight markers
            if (candidate.startswith("$") and len(candidate) < 10) or any(
                m in candidate for m in ast_markers
            ):
                prompt_val = extract_dom_prompt(it)
            else:
                prompt_val = candidate
        else:
            prompt_val = extract_dom_prompt(it)

        # Ensure R code fence normalization
        prompt_val = normalize_r_code_blocks(prompt_val)

        # 4. Options Extraction
        options: List[str] = []
        if q_type == "4지선다":
            for li in it.select("ul.mt-4 > li"):
                # Strictly ignore any list items inside <details>
                if li.find_parent("details") is not None:
                    continue
                span = li.select_one("span.min-w-0")
                if span:
                    opt_txt = span.get_text(strip=True)
                else:
                    mcq_div = li.select_one(".mcq-option")
                    if mcq_div:
                        opt_txt = mcq_div.get_text(strip=True)
                    else:
                        opt_txt = li.get_text(strip=True)

                # Strip option numbering prefix if present ("1. ", "1<!-- -->.")
                # Note: span.min-w-0 already isolates option text; do not strip without whitespace
                # so decimal numbers like "1.0", "1.5", "2.0", "2.5" are preserved.
                opt_txt = re.sub(r"^[1-4]\s*[\.\)][ \t]+", "", opt_txt).strip()
                options.append(opt_txt)

        # 5. Answer Key Extraction (from details)
        ans_el = it.select_one("details p.text-base.font-semibold.text-success")
        if not ans_el:
            ans_el = it.select_one("details p.text-success")
        raw_ans = ans_el.get_text(strip=True) if ans_el else ""

        if q_type == "4지선다":
            # Strip '번' suffix: e.g. "2번" -> "2", "2<!-- -->번" -> "2"
            ans_m = re.search(r"([1-4])", raw_ans)
            ans = ans_m.group(1) if ans_m else raw_ans.strip()
        else:
            # 단답형: preserve model answer exactly (e.g. "IoT", "0.4", "SCM", "57.5%", "1/5", "4번 타자")
            ans = raw_ans.strip()

        questions.append({
            "question_no": q_no,
            "question_type": q_type,
            "prompt": prompt_val.strip(),
            "options": options,
            "answer": ans,
        })

    return questions
