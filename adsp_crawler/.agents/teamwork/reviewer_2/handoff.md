# Review & Adversarial Verification Report: ADsP Harvested Dataset Pipeline

**Reviewer**: Reviewer 2 (reviewer, critic)  
**Date**: 2026-10-29  
**Target Artifacts**:
- `data/adsp_round_{round}.json` (15 files)
- `data/adsp_all.json` (1 consolidated file)
- `tests/test_runner.py` and `tests/test_live_corpus.py`
- `adsp_crawler/` (`config.py`, `fetcher.py`, `parser.py`, `validator.py`, `storage.py`, `cli.py`)

---

## 1. Observation

### Obs 1.1: Test Suite Execution Results
- Command: `python tests/test_runner.py`
  - Output:
    ```
    Tier 1: Feature Coverage (17 Features)     | 17      | 0       |   1.92s | PASS
    Tier 2: Boundary & Corner Cases            | 8       | 0       |   0.64s | PASS
    Tier 3: Cross-Feature Interactions         | 6       | 0       |   2.97s | PASS
    Tier 4: Real-World Scenarios & Census      | 3       | 0       |   0.45s | PASS
    TOTAL (4 tiers)                            | 34      | 0       |   5.98s | ALL TESTS PASSED
    ```
- Command: `pytest tests/test_live_corpus.py -v`
  - Output:
    ```
    tests/test_live_corpus.py::test_live_corpus_all_files_exist PASSED
    tests/test_live_corpus.py::test_live_corpus_per_round_census PASSED
    tests/test_live_corpus.py::test_live_corpus_consolidated_dataset PASSED
    tests/test_live_corpus.py::test_live_corpus_rich_elements_formatting PASSED
    tests/test_live_corpus.py::test_live_corpus_negative_exclusion_filter PASSED
    ======================== 5 passed, 1 warning in 0.06s =========================
    ```

### Obs 1.2: File Existence and Question Census
- Exactly 16 JSON files exist in `data/`:
  - `data/adsp_all.json`: 748 questions (417,727 bytes)
  - 15 individual round JSON files:
    - Rounds 32, 35, 37, 39, 41, 42, 44, 45, 46, 47, 48, 49, 50: 50 questions each (missing: `set()`)
    - Round 38: 49 questions (numbers 1~49, missing: `{50}`)
    - Round 40: 49 questions (numbers 1~49, missing: `{50}`)
  - Grand total: 13 * 50 + 49 + 49 = 748 questions.
  - Question types: exactly 708 multiple choice (`4지선다`) and 40 short answer (`단답형`).
  - Short answer questions distribution: exactly 10 in Round 32, 10 in Round 35, 10 in Round 37, 10 in Round 38. Rounds 39~50 have 0 short-answer questions.
  - Equivalence: `adsp_all.json` matches the concatenated questions of all 15 round JSON files with 0 item mismatches.

### Obs 1.3: Schema & Content Integrity Checks
- Keys: Every question in `data/adsp_round_*.json` contains exactly `{'question_no', 'question_type', 'prompt', 'options', 'answer'}`. Every question in `data/adsp_all.json` contains those 5 keys plus `'round'`.
- Options: All 40 short answer questions have `options: []`. All 708 multiple choice questions have `len(options) == 4` with non-empty strings.
- Answers: All 708 multiple choice questions have answers strictly in `('1', '2', '3', '4')` (Distribution: '1': 181, '2': 171, '3': 182, '4': 174). All 40 short answer questions have non-empty text answers.
- Markdown Tables: Exactly 57 questions contain GFM markdown tables with `|` and `|---|`. Round 50 Q25 contains the verified ANOVA table.
- R Code Blocks: Exactly 35 questions contain fenced code blocks. All open code fences are normalized to ````r```` and properly closed. Round 50 Q26 contains the verified PCA summary.
- Standard Forbidden Terms: None of `"오답 풀이"`, `"오답풀이"`, `"보충 개념"`, `"보충개념"`, `"정답·해설 보기"`, `"정답해설보기"` appear in any of the 16 JSON files.

### Obs 1.4: Critical Defect Discovered in Round 37 Question 49
- Location: `data/adsp_round_37.json` (index 48, Question 49) and `data/adsp_all.json` (index 148).
- Verbatim prompt value:
  ```json
  "아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라.\n\n4f:[\"$\",\"li\",\"20413\",{\"className\":\"rounded-2xl border border-border bg-surface/40 p-5\",\"children\":[[\"$\",\"div\",null,{\"className\":\"flex items-center justify-between\",\"children\":[[\"$\",\"p\",null,{\"className\":\"text-xs font-semibold tabular-nums text-text-muted\",\"children\":[\"문제 \",49]}],[\"$\",\"span\",null,{\"className\":\"text-[10px] font-medium uppercase tracking-wider text-text-subtle\",\"children\":\"단답형\"}]]}],[\"$\",\"div\",null,{\"className\":\"mt-3\",\"children\":[\"$\",\"$L1f\",null,{\"content\":\"$52\",\"variant\":\"pastExam\"}]}],false,\"$L53\"]}]"
  ```
- Code inspection of `adsp_crawler/parser.py` lines 198-208:
  ```python
  text_chunks: Dict[str, str] = {}
  for m in re.finditer(
      r"(?:^|\n)([0-9a-fA-F]+):T[0-9a-fA-F]+,(.*?)(?=(?:\n[0-9a-fA-F]+:|\Z))",
      flight_text,
      re.DOTALL,
  ):
      ref_id = m.group(1)
      content = m.group(2)
      text_chunks[f"${ref_id}"] = content
  ```
- Live payload inspection of Round 37 SSR HTML:
  In the raw Next.js flight payload of Round 37, chunk `52:Tbaf,...` contained the prompt text and an inline `<svg>` tree diagram ending with `</svg>`. Immediately following `</svg>` was component chunk `4f:["$","li","20413",...` WITHOUT a preceding newline `\n`.
  Because the lookahead in `parser.py` was `(?=(?:\n[0-9a-fA-F]+:|\Z))`, it did not match `4f:` (as there was no newline before `4f:`), and instead matched until `\n50:`.
  Consequently, chunk 52's text absorbed the React Flight AST node of `li.rounded-2xl` for Q49.
  When `strip_inline_svgs` subsequently stripped `<svg>...</svg>`, the trailing React Flight AST string `4f:[...]` was left attached to Question 49's prompt.
- DOM Fallback Comparison:
  Calling `extract_dom_prompt(it)` directly on the DOM element for Round 37 Question 49 yields the completely clean, uncorrupted prompt:
  `"아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라."`

---

## 2. Logic Chain

1. **Acceptance Criteria Verification**:
   - ORIGINAL_REQUEST.md R2 & Acceptance Criteria explicitly demand clean semantic parsing where prompts are pristine Markdown, free of UI artifacts and internal leaks:
     *"Semantic Parsing & Rich Element Markdown Conversion"*
     *"Every question strictly adheres to the schema: question_no (int), question_type (str), prompt (str), options (list of str), answer (str)."*
     *"No question prompt or options array contains explanation text such as '오답 풀이', '보충 개념', or the '정답·해설 보기' button text."*
2. **Impact of Observation 1.4**:
   - In `data/adsp_round_37.json` and `data/adsp_all.json`, Question 49's prompt contains 285 characters of raw Next.js RSC Flight AST syntax:
     `4f:["$","li","20413",{"className":"rounded-2xl border border-border bg-surface/40 p-5",...`
   - It contains internal DOM class names (`tabular-nums`, `rounded-2xl`), Next.js flight references (`$L1f`, `$52`, `$53`), and React array AST structures (`["$", "div", ...]`).
   - This corrupts question prompt text and leaks web framework implementation internals into the harvested dataset.
3. **Integrity Assessment**:
   - We verified that the crawler is a genuine implementation: `fetcher.py` performs real HTTP requests to `sqldpass.com`, `parser.py` processes live Next.js RSC flight streams and DOM structures, and `storage.py` outputs real parsed data. There are no hardcoded fake answers or facade implementations.
   - However, the validation suite (`validator.py` and `tests/test_live_corpus.py`) had a coverage gap: it only checked for 6 specific Korean explanation terms (`"오답 풀이"`, etc.), missing checks for raw Flight AST markers (`["$"`, `rounded-2xl`, `tabular-nums`, `className`).
   - Because the test suite passed despite prompt corruption in Round 37 Question 49, the work cannot be approved without remediation.
4. **Conclusion Support**:
   - Because the prompt of Round 37 Question 49 is demonstrably corrupted in both the per-round file and the consolidated file, the dataset fails acceptance criteria.
   - Therefore, the verdict MUST be **REQUEST_CHANGES**.

---

## 3. Caveats

1. **Source Site Census Anomalies**:
   - On `sqldpass.com`, Question 50 is legitimately absent from the source platform for both Round 38 and Round 40. This was independently confirmed by inspecting the live HTML of those rounds. The expected count of 748 (13 x 50 + 49 + 49) is accurate.
   - On `sqldpass.com`, Round 39 has 50 questions that are 100% 4-choice multiple choice (badges marked `4지선다`), with 0 short-answer questions. This was confirmed by querying the live badges on `sqldpass.com`.
2. **Scope of Prompt Defect**:
   - Exhaustive scanning across all 748 questions confirmed that this regex bleeding issue occurred in exactly **one** question: Round 37 Question 49. All other 747 questions across all 15 rounds are free of Flight AST leaks, HTML tags, or unclosed code blocks.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

The crawler architecture, census accuracy (748 questions across 15 rounds), GFM table conversions, and R code block fencing are of high quality. However, the harvested dataset contains a critical defect:
- In `data/adsp_round_37.json` and `data/adsp_all.json`, Question 49's prompt is corrupted by leaked Next.js RSC Flight AST code (`4f:["$","li","20413",{"className":"rounded-2xl border border-border...`).
- The regex in `adsp_crawler/parser.py` (`extract_flight_prompts`) must be hardened to prevent chunk bleeding when text chunks end without a newline before the next chunk.
- `adsp_crawler/validator.py` and `tests/test_live_corpus.py` must be enhanced to assert that prompts do not contain Flight/AST syntax.
- Round 37 and `adsp_all.json` must be re-harvested and regenerated cleanly.

---

## 5. Verification Method

To independently verify the defect and validate the subsequent fix:

1. **Inspect Corrupted Prompt in Existing Data**:
   ```powershell
   python -c "import json; qs = json.load(open('data/adsp_round_37.json', encoding='utf-8')); print(repr(qs[48]['prompt']))"
   ```
   *Expected Current Output*: Shows `4f:["$","li","20413",{"className":"rounded-2xl border border-border...`.
   *Target Fixed Output*: Must be strictly:
   `"아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라."`

2. **Run Full Corpus AST / Class Leak Search**:
   ```powershell
   python -c "import json, glob; [print(f, q['question_no'], t) for f in glob.glob('data/*.json') for q in json.load(open(f, encoding='utf-8')) for t in ['[\"$\"', 'rounded-2xl', 'tabular-nums', 'className'] if t in q.get('prompt', '')]"
   ```
   *Target Fixed Output*: Exactly 0 matches.

3. **Verify DOM Fallback Output for Round 37 Q49**:
   ```powershell
   python -c "from adsp_crawler.fetcher import fetch_round_post; from adsp_crawler.parser import extract_dom_prompt; from bs4 import BeautifulSoup; soup = BeautifulSoup(fetch_round_post(37, delay_min=0, delay_max=0), 'html.parser'); print([extract_dom_prompt(it) for it in soup.select('li.rounded-2xl') if '49' in (it.select_one('p.tabular-nums') or {}).get_text('')][0])"
   ```
   *Output*: Clean prompt `"아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라."`.

4. **Run Complete Test Suite**:
   ```powershell
   python tests/test_runner.py
   pytest tests/test_live_corpus.py -v
   ```
   *Target Fixed Output*: All test tiers pass 100%.

---

## Quality Review Summary

**Verdict**: REQUEST_CHANGES

### Findings

#### [Critical] Finding 1: Prompt Corruption in Round 37 Question 49
- **What**: The prompt of Question 49 in Round 37 contains raw Next.js React Server Component (RSC) Flight AST payload code and CSS classes:
  `4f:["$","li","20413",{"className":"rounded-2xl border border-border bg-surface/40 p-5",...}`
- **Where**: `data/adsp_round_37.json` (Question 49) and `data/adsp_all.json` (Question 49 of Round 37).
- **Why**: Violates Acceptance Criteria R2 (Semantic Parsing) and R3 (Content Integrity). Leaks internal web framework AST nodes and DOM styling into question dataset.
- **Suggestion**:
  1. In `adsp_crawler/parser.py`: In `parse_adsp_post()`, check if `candidate` prompt contains flight AST markers (e.g. `["$"` or `className` or `border-border` or `tabular-nums`). If detected, discard `candidate` and fall back to `extract_dom_prompt(it)`, which extracts the pristine prompt `"아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라."`.
  2. In `adsp_crawler/parser.py`: In `extract_flight_prompts()`, adjust the chunk regex or strip trailing `\n?[0-9a-fA-F]+:\[.*$` so that adjacent component chunks are never absorbed into text chunks.
  3. Re-run crawler to regenerate `data/adsp_round_37.json` and `data/adsp_all.json`.

#### [Major] Finding 2: Incomplete Negative Validation in Validator & Live Corpus Test
- **What**: `validate_question()` in `adsp_crawler/validator.py` and `test_live_corpus_negative_exclusion_filter()` in `tests/test_live_corpus.py` only checked for 6 explanation strings (`FORBIDDEN_TERMS = ["오답 풀이", "오답풀이", "보충 개념", "보충개념", "정답·해설 보기", "정답해설보기"]`).
- **Where**: `adsp_crawler/validator.py:27-35`, `tests/test_live_corpus.py:126-134`.
- **Why**: Allowed the corrupted prompt in Round 37 Question 49 to pass validation without raising `ValidationError`, leading to a false sense of security.
- **Suggestion**: Add Flight AST indicators (`["$"`, `rounded-2xl`, `tabular-nums`, `{"className"`) to `FORBIDDEN_TERMS` in `validator.py` and test assertions in `test_live_corpus.py`.

#### [Minor] Finding 3: `test_live_corpus.py` Omitted from Standalone `test_runner.py`
- **What**: `tests/test_runner.py` only executes Tiers 1 through 4 (which operate against mock fixtures). It does not invoke `test_live_corpus.py` (which validates the live harvested files in `data/`).
- **Where**: `tests/test_runner.py:24-29`.
- **Why**: Running `python tests/test_runner.py` reported 100% PASS without actually testing the data files in `data/`.
- **Suggestion**: Add a `--live` flag or include `test_live_corpus.py` as a validation tier in `test_runner.py`.

---

## Verified Claims

- Total question count == 748 (13 rounds x 50 + R38 x 49 + R40 x 49) → verified via python script → PASS
- 15 individual JSON files and 1 consolidated adsp_all.json exist in data/ → verified via `Path.glob` → PASS
- Multiple-choice questions have exactly 4 options and answer in 1~4 → verified across 708 questions → PASS
- Short-answer questions have options: [] and model answer in answer field → verified across 40 questions → PASS
- Table questions preserve GFM Markdown tables (| ... |) (e.g. Round 50 Q25 ANOVA table) → verified across 57 table questions → PASS
- R code questions preserve fenced ```r code blocks (e.g. Round 50 Q26 PCA summary) → verified across 35 code block questions → PASS
- Zero explanation leaks ("오답 풀이", "보충 개념", "정답·해설 보기") → verified across all 16 JSON files → PASS
- Next.js RSC Flight AST prompt hygiene → verified across 748 questions → **FAIL** (Round 37 Question 49 contains leaked React Flight AST payload)

---

## Coverage Gaps

- Flight payload delimiter robustness: Text chunks immediately followed by component chunks without newlines were not tested in Tier 1~4 unit tests.
  - Risk Level: Medium
  - Recommendation: Add unit test in `tests/test_tier2_boundary_corner.py` for chunks ending without newlines and containing inline SVGs.

---

## Adversarial Challenge Report

### Challenge Summary
**Overall Risk Assessment**: MEDIUM-HIGH (Data corruption present in live harvest; core pipeline architecture is sound).

### Challenge 1: Text Chunk Bleeding Over Adjacent Component Chunks
- **Assumption Challenged**: Assumed Next.js flight stream text chunks (`id:Tlen,...`) are always separated from subsequent chunks by a newline `\n`.
- **Attack Scenario**: When a post contains an inline SVG without a trailing newline, the subsequent component chunk `4f:[...]` directly abuts the closing `</svg>` tag (`</svg>4f:["$","li",...`).
- **Blast Radius**: Regex fails lookahead boundary, causing component definitions, styling classes, and AST nodes to bleed into question prompts.
- **Mitigation**: Parse chunk hex byte length directly or enforce lookahead on `\n?[0-9a-fA-F]+:\[` and add fallback to DOM parsing whenever prompt text contains `["$"`.

### Challenge 2: Test Suite Self-Certification via Synthetic Mocks
- **Assumption Challenged**: Assumed `test_runner.py` passing 34/34 proves the harvested data in `data/` is valid.
- **Attack Scenario**: Tiers 1-4 execute against synthetic mock HTML fixtures in `tests/fixtures/mock_data.py`. `data/*.json` can be corrupted while `test_runner.py` continues to report 100% PASS.
- **Blast Radius**: Developers may ship broken or corrupted crawled data believing tests have passed.
- **Mitigation**: Wire `test_live_corpus.py` directly into `test_runner.py` and expand negative filter assertions to include framework tokens.
