# Specification & Requirements Miner Survey Handoff Report

## 1. Observation

### Target Source Verification
- **Category Hub Endpoint**: `https://www.sqldpass.com/blog/category/ADsP`
  - Fetched via `read_url_content` and verified with Python `urllib.request`.
  - Discovered 15 past-exam links matching regex `/blog/past-exam/adsp-\d{4}-(\d+)`:
    - Featured link: `/blog/past-exam/adsp-2026-50`
    - Grid links (14 items): Round 49 (`adsp-2026-49`), Round 42 (`adsp-2024-42`), Round 41 (`adsp-2024-41`), Round 40 (`adsp-2024-40`), Round 39 (`adsp-2023-39`), Round 38 (`adsp-2023-38`), Round 37 (`adsp-2023-37`), Round 35 (`adsp-2022-35`), Round 32 (`adsp-2022-32`), Round 48 (`adsp-2026-48`), Round 47 (`adsp-2025-47`), Round 46 (`adsp-2025-46`), Round 45 (`adsp-2025-45`), Round 44 (`adsp-2025-44`).
    - Note: Round 43 does NOT exist as a past-exam post (`adsp-43-preparation` is a guide post under general concepts).
- **Comprehensive Question Count Census**:
  - Script execution: `survey_all_rounds.py` queried all 15 round pages.
  - Round counts:
    - Round 50: 50 questions (50 '4지선다')
    - Round 49: 50 questions (50 '4지선다')
    - Round 48: 50 questions (50 '4지선다')
    - Round 47: 50 questions (50 '4지선다')
    - Round 46: 50 questions (50 '4지선다')
    - Round 45: 50 questions (50 '4지선다')
    - Round 44: 50 questions (50 '4지선다')
    - Round 42: 50 questions (50 '4지선다')
    - Round 41: 50 questions (50 '4지선다')
    - Round 40: 49 questions (49 '4지선다', missing Q50)
    - Round 39: 50 questions (50 '4지선다')
    - Round 38: 49 questions (39 '4지선다', 10 '단답형', missing Q50)
    - Round 37: 50 questions (40 '4지선다', 10 '단답형')
    - Round 35: 50 questions (40 '4지선다', 10 '단답형')
    - Round 32: 50 questions (40 '4지선다', 10 '단답형')
  - **Grand Total Questions**: Exactly 748 questions (708 '4지선다', 40 '단답형').
- **Missing Questions Verification**:
  - Script execution `check_missing_nos.py` confirmed:
    - Round 40 has questions 1 through 49 (missing {50}).
    - Round 38 has questions 1 through 49 (missing {50}).
- **Tag & Content Deep Scan (`deep_scan_all_questions.py`)**:
  - Total questions with tables: 45 questions across 15 rounds (e.g., Round 50 Q25 ANOVA table, Q29, Q41).
  - Total questions with `<pre>` tags: 35 questions across 15 rounds (e.g., Round 50 Q26 PCA, Q27 glm, Q49 lm).
  - Total questions with `<img>`: 0 questions (all visual diagrams use inline `<svg>`).
  - Empty prompts: 0 questions.
  - Unexpected option counts: 0 questions (all 708 multiple choice questions have exactly 4 options; all 40 short answer questions have 0 options).
  - Missing answers: 0 questions (all 748 questions have answers present in `<details>`).
- **DOM & SSR Rendering Quirk (Next.js App Router Client Bailout)**:
  - In SSR HTML, `<pre>` tags render as:
    `<pre><!--$!--><template data-dgst="BAILOUT_TO_CLIENT_SIDE_RENDERING"></template><div class="my-3 h-24 rounded-lg border border-zinc-800 bg-zinc-900/60 animate-pulse"></div><!--/$--></pre>`
  - The actual prompt text and code snippet reside in the same SSR HTML inside `<script>` chunks calling `self.__next_f.push([1, "..."])`:
    Example in Round 50 Q26:
    `{"content":"다음은 표준화한 자료에 주성분분석을 수행한 결과 중 PC1부터 PC7까지를 옮긴 것이다. 해석으로 옳지 않은 것은?\n\n```\n> pca <- prcomp(X, scale. = TRUE)\n> summary(pca)\nImportance of components:\n                          PC1    PC2    PC3     PC4     PC5     PC6    PC7\nStandard deviation     2.0494 1.4491 1.0000 0.89443 0.77460 0.67082 0.6000\nProportion of Variance 0.4200 0.2100 0.1000 0.08000 0.06000 0.04500 0.0360\nCumulative Proportion  0.4200 0.6300 0.7300 0.81000 0.87000 0.91500 0.9510\n```"}`
- **Option Leaking Quirk**:
  - In `li.rounded-2xl`, `<details>` contains `오답 풀이` items inside `ul.list-disc > li`. A naive selector `q.select('ul > li')` returns 8 items instead of 4.
- **Answer Suffix Quirk**:
  - For 4지선다, `p.text-base.font-semibold.text-success` holds `"2<!-- -->번"`.
  - For 단답형, `p.text-base.font-semibold.text-success` holds model answers like `"IoT"`, `"SCM"`, `"0.4"`, `"1.2"`, `"57.5%"`.
- **Sandbox Network Behavior**:
  - Python scripts running under standard Windows sandbox without socket permissions fail with `WinError 10013`. Commands requiring outbound network must run with `BypassSandbox: true`.

---

## 2. Logic Chain

1. **Category Discovery**:
   - `ORIGINAL_REQUEST.md` R1 specifies discovering 15 rounds from `https://www.sqldpass.com/blog/category/ADsP`.
   - Probing the category hub confirmed that exactly 15 exam restoration articles are linked directly on the page, covering rounds 32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50.
   - Therefore, the discovery pipeline can either parse the category hub HTML for `/blog/past-exam/adsp-\d{4}-(\d+)` or use an explicit round map verified against the hub.

2. **Question Count Integrity & Acceptance Criteria**:
   - Target acceptance criterion specifies: "Total questions harvested across all rounds is at least 740 (expected 748 questions)."
   - Our census revealed 13 rounds with 50 questions (650) + Round 38 with 49 questions + Round 40 with 49 questions = exactly 748 questions.
   - The validation pipeline must assert `len(questions) == 748` for the full collection (with 50 for all rounds except 49 for R38 and R40).

3. **Question Type Segregation**:
   - Pre-2024 rounds (32, 35, 37, 38) have 10 short-answer questions each.
   - Round 39 has 50 multiple-choice questions (all '4지선다').
   - Post-2024 rounds (40~50) have 100% multiple-choice questions ('4지선다').
   - In short-answer questions, options must strictly be `[]`.
   - In multiple-choice questions, options must strictly be a list of 4 non-empty strings.

4. **DOM Extraction Strategy & Next.js RSC Handling**:
   - If parsing purely static SSR HTML DOM:
     - `<table>` elements are fully rendered in the DOM and easily transformed to GFM via AST table walker.
     - `<pre>` code blocks are empty placeholders in the DOM (`BAILOUT_TO_CLIENT_SIDE_RENDERING`).
     - However, the raw markdown prompt including code blocks ````\n...```` is present in the RSC payload (`self.__next_f.push`).
     - Therefore, the extractor must either:
       1. Extract question prompts from the RSC payload `self.__next_f.push` (which preserves code blocks natively), OR
       2. Parse the SSR DOM and patch empty `<pre>` tags using the matching RSC text, OR
       3. Run a lightweight headless browser (Playwright) that triggers Next.js client hydration so `<pre><code>` is fully populated.
     - In all cases, code blocks must be tagged with ```r as specified in R2.

5. **Exclusion of Contamination Elements**:
   - Explanation text (`해설`, `오답 풀이`, `보충 개념`, `정답·해설 보기`, `키워드`) resides entirely within `<details>` or specific sub-elements.
   - Keeping question prompts restricted to `div.mt-3` and options restricted to `ul.mt-4 > li` completely prevents explanation contamination.

---

## 3. Caveats

1. **Round 43**: Round 43 was never published as an exam restoration post by 문어CBT (only a general concept article `adsp-43-preparation` exists). This is intentional and expected.
2. **Missing Q50 in Rounds 38 & 40**: Rounds 38 and 40 only have 49 restored questions on the source platform. This matches the 748 total requirement.
3. **Inline SVG Diagrams**: A few questions contain `<svg>` tags for flowcharts/curves. In markdown conversion, these should either be omitted or summarized as text if text is present, without corrupting the prompt text.
4. **Network Jitter and Polite Headers**: The server enforces Cloudflare / Next.js edge caching. A jitter of 1.0~2.0s with standard browser User-Agent avoids 429 Too Many Requests and IP throttling.

---

## 4. Conclusion

All requirements, edge cases, and schema constraints have been probed against the live authoritative source (`sqldpass.com`). The pipeline specification is complete, deterministic, and ready for immediate architectural structuring and dual-track implementation.

Key target numbers:
- **Rounds**: 15 (32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50)
- **Total Questions**: 748 (708 '4지선다', 40 '단답형')
- **Per-round Files**: `data/adsp_round_{round}.json` (15 files)
- **Consolidated File**: `data/adsp_all.json` (1 file)

---

## 5. Verification Method

To verify the observations independently:
1. **Network Survey Verification**:
   ```bash
   python -c "import urllib.request, re; req = urllib.request.Request('https://www.sqldpass.com/blog/category/ADsP', headers={'User-Agent': 'Mozilla/5.0'}); html = urllib.request.urlopen(req).read().decode('utf-8'); links = re.findall(r'/blog/past-exam/adsp-\d{4}-(\d+)', html); print('Discovered rounds:', sorted([int(x) for x in set(links)])); assert len(set(links)) == 15"
   ```
2. **Question Count Verification**:
   Run `C:\Users\SSAFY\.gemini\antigravity\scratch\survey_all_rounds.py` (with network bypass) and check that total equals 748.
3. **Missing Q50 Verification**:
   Run `C:\Users\SSAFY\.gemini\antigravity\scratch\check_missing_nos.py` and observe `missing={50}` for rounds 38 and 40.
4. **Table & Code Inspection**:
   Run `C:\Users\SSAFY\.gemini\antigravity\scratch\test_table_convert.py` to verify GFM table output for Round 50 Q25.

---

# Comprehensive Specification & Feature Inventory

## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Ingestion | Hub Discovery | Automatically fetch `https://www.sqldpass.com/blog/category/ADsP` and index all 15 exam restoration post URLs | Hub URL | Dict mapping round number (int) -> post URL (str) | HTTPError / NetworkError: retry with jitter, fail if not 200 | ORIGINAL_REQUEST R1, Live Hub probe |
| 2 | Ingestion | Rate Limiter | Apply 1.0~2.0s randomized delay between outgoing requests to prevent rate limiting | Jitter bounds (min_s=1.0, max_s=2.0) | None (sleep elapsed time) | Timeout / Negative jitter: clamp to valid range | ORIGINAL_REQUEST R1 |
| 3 | Ingestion | Polite Headers | Attach realistic browser User-Agent and standard Accept headers to all requests | Request object | Request with headers attached | Missing header warning | ORIGINAL_REQUEST R1 |
| 4 | CLI | CLI Round Selector | Support specifying single round (`--round 50`) or multiple rounds (`--round 32 35 50` or `--rounds 32,50`) or crawling all rounds by default | CLI argv | List of target round numbers | Invalid round number: exit with error code and usage help | ORIGINAL_REQUEST R1 |
| 5 | CLI | Custom Output Directory | Allow user to override destination directory (`--output-dir`) defaulting to `data/` | CLI argv (`--output-dir PATH`) | Path object | Invalid path / permission error: exit with error | ORIGINAL_REQUEST R3 |
| 6 | Parsing | Question Extractor | Extract each question block from `li.rounded-2xl` elements | HTML Document / DOM | List of question item elements | 0 questions found: Raise extraction error | ORIGINAL_REQUEST R2, Live DOM probe |
| 7 | Parsing | Question Number Parser | Extract integer question number from `p.text-xs.font-semibold` | Element text (e.g. "문제 1") | Integer (`question_no`: int) | No digits found: Raise ValueError | ORIGINAL_REQUEST R2, Schema validation |
| 8 | Parsing | Question Type Classifier | Detect whether question is '4지선다' or '단답형' via `span.text-[10px]` or options presence | Element text | String ('4지선다' or '단답형') | Unknown type: Default based on options count or raise error | ORIGINAL_REQUEST R2, Live DOM probe |
| 9 | Parsing | GFM Table Converter | Convert HTML `<table>` elements in question prompt into valid GitHub Flavored Markdown tables with pipes `|` | `<table>` HTML node | Markdown table string (`| Col 1 | Col 2 |\n| --- | --- |\n...`) | Malformed table: fallback to text or pad missing cells | ORIGINAL_REQUEST R2, Round 50 Q25 probe |
| 10 | Parsing | R Code Block Converter | Convert R code snippets (RSC payload or `<pre><code>`) into fenced code blocks with language tag (````r ... ````) | Code block node / RSC markdown snippet | Fenced code block (````r\n... \n````) | Empty code: omit block or output comment | ORIGINAL_REQUEST R2, Round 50 Q26 probe |
| 11 | Parsing | Options Extractor | Extract exactly 4 multiple choice options from `ul.mt-4 > li` into a string array | `ul.mt-4` node | `list[str]` of 4 items for 4지선다, `[]` for 단답형 | Length != 4 for 4지선다: ValidationError | ORIGINAL_REQUEST R2, Schema validation |
| 12 | Parsing | Answer Key Extractor | Extract answer key from `<details>` container, stripping `"번"` for 4지선다 and preserving text for 단답형 | `<details>` element | Clean answer string (e.g. `"3"`, `"IoT"`) | Answer element missing: ValidationError | ORIGINAL_REQUEST R2, Live DOM probe |
| 13 | Parsing | Negative Exclusion Filter | Exclude all explanation paragraphs, "오답 풀이", "보충 개념", button text ("정답·해설 보기"), and keywords | Question node & Details node | Sanitized prompt and options | Leak detected: Trigger schema/content validation failure | ORIGINAL_REQUEST R2, Acceptance Criteria |
| 14 | Validation | Schema Integrity Validator | Validate every question record against strict schema (`question_no`: int, `question_type`: str, `prompt`: str, `options`: list[str], `answer`: str) | Question dict | Boolean / Validated Question | Raise ValidationError with specific violation details | ORIGINAL_REQUEST R3, Acceptance Criteria |
| 15 | Validation | Total Count Validator | Assert total questions harvested across all 15 rounds is >= 740 (expected 748) | List of all questions | Boolean / Assert | Fail with count discrepancy report | ORIGINAL_REQUEST Acceptance Criteria |
| 16 | Storage | Per-Round JSON Storage | Persist each round's questions to `data/adsp_round_{round}.json` with UTF-8 encoding and indented JSON | Round number, Questions list | JSON file on disk | IO/Permission error: Raise OSError | ORIGINAL_REQUEST R3 |
| 17 | Storage | Consolidated JSON Storage | Persist all 748 harvested questions to `data/adsp_all.json` | All rounds data | Consolidated JSON file on disk | IO/Permission error: Raise OSError | ORIGINAL_REQUEST R3 |

---

## Edge Cases
| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | R Code Block Extraction | Round 50 Question 26 (PCA summary) in SSR HTML | SSR HTML renders `<pre><template data-dgst="BAILOUT_TO_CLIENT_SIDE_RENDERING">...<div class="animate-pulse"></div></pre>`. The raw code is contained in the RSC payload (`self.__next_f.push`). Parser must read RSC payload or hydrate DOM to extract code. |
| 2 | Options Selector Leaking | Any 4지선다 question when using broad `q.select('ul > li')` selector | Matches both the 4 choices in `ul.mt-4` AND the 4 bullet points in `오답 풀이` inside `<details>`. Selector must strictly be `ul.mt-4 > li` or exclude `<details>`. |
| 3 | Question Count Discrepancy | Rounds 38 and 40 on live site | Question 50 is missing on sqldpass.com for both Round 38 and Round 40 (only 49 questions exist). Total across 15 rounds is 748, not 750. Total count validator must allow 748 (>= 740). |
| 4 | Answer Text Suffix | 4지선다 questions (e.g. Round 50 Q1) | `<p class="text-success">` displays `2<!-- -->번`. Stripping `"번"` yields `"2"`, matching the required `"3"` format. |
| 5 | Diverse Short Answer Formats | 단답형 questions in Rounds 32~38 | Model answers contain acronyms (`IoT`, `SCM`), phrases (`하향식 접근 방법`), decimals (`0.4`, `1.2`), percentages (`57.5%`), and fractions (`1/5`, `a / (a+b)`). Answer field must preserve exact string. |
| 6 | GFM Table Empty Cells | Round 50 Question 25 ANOVA table | Residual and Total rows have empty cells. Markdown table generator must pad empty cells with spaces (`| |`) to avoid breaking table layout. |
| 7 | Inline SVG in Prompts | Questions containing diagrams (e.g. ROC curve, neural net) | Prompts contain inline `<svg>` elements with nested `<circle>`, `<path>`, `<text>`. Parser must preserve surrounding text and handle SVG elements without crashing. |
| 8 | Multiple Choice Option Label Prefix | HTML markup for options (`span.tabular-nums` "1." + `mcq-option`) | Option numbering (`1.`) is separate from option content (`.mcq-option`). Parser can extract pure text from `.mcq-option` to keep options clean. |
| 9 | Windows Sandbox Socket Blocks | Outbound socket connections in sandbox | Standard Python `urllib` fails with `WinError 10013` inside sandbox. Network commands must run outside sandbox (`BypassSandbox: true`). |
| 10 | Round 43 Omission | Round selection / hub indexing | Round 43 does not exist as an exam restoration post. CLI must reject `--round 43` with a friendly error informing the user that Round 43 was not published. |

---

## Detailed Data Contract Specification

### Question Item JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ADsPQuestion",
  "type": "object",
  "required": ["question_no", "question_type", "prompt", "options", "answer"],
  "additionalProperties": false,
  "properties": {
    "question_no": {
      "type": "integer",
      "minimum": 1,
      "maximum": 50,
      "description": "Question number within the exam round"
    },
    "question_type": {
      "type": "string",
      "enum": ["4지선다", "단답형"],
      "description": "Type of question: multiple-choice (4 choices) or short-answer"
    },
    "prompt": {
      "type": "string",
      "minLength": 1,
      "description": "Question prompt text, including GFM tables (| ... |) and fenced R code (```r ... ```)"
    },
    "options": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "description": "List of 4 option strings for '4지선다', or empty list [] for '단답형'"
    },
    "answer": {
      "type": "string",
      "minLength": 1,
      "description": "Answer key: '1'~'4' for 4지선다, model answer text for 단답형"
    }
  }
}
```

### Storage Files
1. **Per-Round Files**: `data/adsp_round_{round}.json`
   - Array of questions: `[ { "question_no": 1, ... }, ... ]`
   - Total 15 files: rounds 32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50.
2. **Consolidated File**: `data/adsp_all.json`
   - Consolidated collection of all 748 questions across all 15 rounds.
