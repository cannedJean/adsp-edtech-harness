# Challenger 1 Empirical Verification & Adversarial Stress Report

**Verdict**: **REQUEST_CHANGES**
**Overall Risk Assessment**: **CRITICAL**

---

## 1. Observation

### Observation 1: Critical Bug in MCQ Numeric Option Prefix Stripping
- **File**: `adsp_crawler/parser.py`, lines 364–380:
```python
        if q_type == "4지선다":
            for li in it.select("ul.mt-4 > li"):
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
                opt_txt = re.sub(r"^[1-4]\s*[\.\)]\s*", "", opt_txt).strip()
                options.append(opt_txt)
```
- In the SSR HTML from `sqldpass.com`, option numbering is in a sibling element `<span class="font-semibold tabular-nums">1<!-- -->.</span>`, while `span.min-w-0` contains strictly the option content itself (e.g. `"1.0"`).
- When `opt_txt` is `"1.0"`, `re.sub(r"^[1-4]\s*[\.\)]\s*", "", opt_txt)` matches `"1."` at the start of the decimal number and strips it, leaving `"0"`.
- When `opt_txt` is `"1.5"`, it strips `"1."`, leaving `"5"`.
- When `opt_txt` is `"2.0"`, it strips `"2."`, leaving `"0"`.
- When `opt_txt` is `"2.22"`, it strips `"2."`, leaving `"22"`.
- When `opt_txt` is `"3.6"`, it strips `"3."`, leaving `"6"`.

### Observation 2: Verified Real Data Corruption in Harvested Datasets
Inspection of the JSON files in `data/` confirms that multiple exam questions in the actual dataset have suffered data corruption:
- `data/adsp_round_46.json` (Question 24):
```json
{
  "question_no": 24,
  "question_type": "4지선다",
  "prompt": "아래 확률변수 X의 기댓값은?\n\nP(X=1) = 0.4\nP(X=2) = 0.3\nP(X=3) = 0.2\nP(X=4) = 0.1",
  "options": [
    "0",
    "5",
    "0",
    "5"
  ],
  "answer": "3"
}
```
*(Raw HTML contains options: 1.0, 1.5, 2.0, 2.5)*
- `data/adsp_round_46.json` (Question 30):
```json
{
  "question_no": 30,
  "options": [
    "5",
    "0",
    "5",
    "5.0"
  ],
  "answer": "1"
}
```
*(Raw HTML contains options: 1.5, 2.0, 2.5, 5.0. Only 5.0 survived because 5 is not in `[1-4]`)*
- `data/adsp_round_37.json` (Question 25):
`"options": ["6", "2", "2", "5.0"]` *(Raw HTML contains: 3.6, 2.2, 3.2, 5.0)*
- `data/adsp_round_47.json` (Question 31):
`"options": ["2", "22", "5", "30"]` *(Raw HTML contains: 2, 2.22, 2.5, 30)*
- `data/adsp_round_35.json` (Question 32):
`"options": ["0.5", "7", "6", "2"]` *(Raw HTML contains: 0.5, 1.7, 6, 2)*

### Observation 3: High Risk Validator Gap on Forbidden Q50 in Rounds 38 & 40
- **File**: `adsp_crawler/validator.py`, lines 154–162:
```python
    seen_nos = set()
    for q in questions:
        validate_question(q)
        q_no = q["question_no"]
        if q_no in seen_nos:
            raise ValidationError(f"Duplicate question_no {q_no} in Round {round_no}.")
        seen_nos.add(q_no)
```
- `validate_round_dataset(round_no, questions)` checks `len(questions) == 49` for Round 38 and 40, but never checks that `50 not in seen_nos` (or `set(seen_nos) == set(range(1, 50))`).
- Empirically verified: Passing a 49-item dataset containing Q1..Q48 and Q50 (missing Q49) to `validate_round_dataset(38, questions)` succeeded without error.

### Observation 4: Medium Risk Consolidated Dataset List Validator Gap
- **File**: `adsp_crawler/validator.py`, lines 209–222:
- When `validate_consolidated_dataset` receives a `list`, it validates total count (748), total MCQ (708), and total SA (40), but never asserts that the `"round"` attribute is attached or that all 15 rounds are represented.
- Empirically verified: Passing a flat list of 748 questions consisting of 708 MCQ and 40 SA from a single round passed validation without error.

### Observation 5: Robust Handling of Edge Cases across Other Modules
- Malformed HTML:
  - Empty or whitespace HTML returns `[]` cleanly without crashing.
  - None input returns `[]` cleanly.
  - Unclosed HTML tags are parsed into DOM without unhandled parser crashes.
  - Corrupted Next.js flight payload gracefully falls back to DOM parsing.
- Schema Integrity:
  - Non-dict objects, missing required keys, unexpected extra keys, invalid `question_no` types (bool, float, string, None), out-of-bound `question_no` (<1 or >50), invalid `question_type`, empty or whitespace-only prompts/answers, and non-string/empty options are strictly caught and rejected with `ValidationError`.
- Empty Options:
  - 4지선다 with 0, 1, 2, 3, 5, or 6 options is rejected.
  - 4지선다 with empty string or whitespace string is rejected.
  - 단답형 with any non-empty options is rejected.
- Negative Exclusion Leaks:
  - All 6 forbidden terms (`"오답 풀이"`, `"오답풀이"`, `"보충 개념"`, `"보충개념"`, `"정답·해설 보기"`, `"정답해설보기"`) in prompt, options, or answer are strictly caught and rejected with `ValidationError`.
  - `<details>` summary and explanation text do not leak into question prompts.
- Unusual Markdown Tables:
  - Tables without `<thead>` properly designate the first `<tr>` as header.
  - Ragged tables with varying column counts are padded with empty cells to match `max_cols`.
  - Empty cells (such as ANOVA residuals and totals) are properly formatted with aligned pipes.
- CLI Argument Validation:
  - Negative rounds, non-existent round 43, out-of-range rounds, non-numeric strings, mixed valid/invalid rounds, and unknown CLI flags are strictly rejected with `SystemExit(2)`.
- Storage Module Safety:
  - Schema/census validation runs before any file writing; failed validations leave disk completely untouched.

---

## 2. Logic Chain

1. **Step 1**: The project specification (`ORIGINAL_REQUEST.md` R2, Acceptance Criteria) mandates extracting multiple choice options (1~4) into a structured string array for 4지선다 questions.
2. **Step 2**: In `adsp_crawler/parser.py:379`, the regex `re.sub(r"^[1-4]\s*[\.\)]\s*", "", opt_txt)` was introduced under the assumption that option text might contain a numeric prefix like `"1. "` or `"1) "`.
3. **Step 3**: However, `span.min-w-0` extracts only the option text body, not the option number (which is in a sibling element). If the option text body is a decimal number between 1.0 and 4.9 (e.g. `"1.0"`, `"1.5"`, `"2.0"`, `"2.5"`, `"3.6"`, `"2.22"`), the regex erroneously interprets the number and its decimal point as a question option prefix and removes it.
4. **Step 4**: Step 3 directly corrupts multiple real questions in the dataset (`adsp_round_46.json` Q24 & Q30, `adsp_round_37.json` Q25, `adsp_round_47.json` Q31, `adsp_round_35.json` Q32), where mathematical values like `1.0, 1.5, 2.0, 2.5` were corrupted into `["0", "5", "0", "5"]`.
5. **Step 5**: Because this data corruption directly violates the core acceptance criteria of dataset fidelity and question integrity, and because validator gaps allow invalid question distributions to slip through unnoticed, the solution cannot be approved in its current state.

---

## 3. Caveats

- **Network Reliability**: Live network timeout handling during multi-round crawling was tested against mock adapters and synthetic transient errors (Tier 3), but not against physical ISP disruptions.
- **GFM Table Pipes**: `html_table_to_gfm` does not currently escape literal pipes `|` appearing inside table cell text (e.g., conditional probability `P(A | B)`). While no existing exam question table currently contains literal pipes in cells, escaping `|` to `\|` in cell strings would improve future resilience.
- **No Implementation Code Modified**: In strict adherence to Challenger constraints, no implementation files in `adsp_crawler/` were modified. Only test files and reports were authored.

---

## 4. Conclusion & Required Changes

**Verdict**: **REQUEST_CHANGES**

### Required Remediation Items:

1. **Fix Parser Option Prefix Stripping (`adsp_crawler/parser.py:379`) [CRITICAL]**:
   - The regex `re.sub(r"^[1-4]\s*[\.\)]\s*", "", opt_txt)` must NOT strip decimal numbers.
   - Specifically, when `span.min-w-0` is found, the prefix is already absent and no stripping should be performed. Alternatively, use a negative lookahead to ensure digits do not follow the punctuation (e.g., `r"^[1-4]\s*[\.\)](?!\d)\s*"`), or only strip if followed by whitespace/non-digit.
   - Re-crawl or re-parse all 15 rounds so that affected questions (`adsp_round_46.json` Q24, Q30; `adsp_round_37.json` Q25; `adsp_round_47.json` Q31; `adsp_round_35.json` Q32) contain accurate decimal numbers in their options arrays.

2. **Harden Round Census Validator (`adsp_crawler/validator.py:154-162`) [HIGH]**:
   - In `validate_round_dataset`, for rounds 38 and 40, explicitly assert that `50 not in seen_nos` (or verify that `seen_nos == set(range(1, 50))`).
   - For all other rounds, verify that `seen_nos == set(range(1, 51))`.

3. **Harden Consolidated List Validator (`adsp_crawler/validator.py:209-222`) [MEDIUM]**:
   - When `validate_consolidated_dataset` receives a flat list, verify that every item has a valid `round` attribute (`TARGET_ROUNDS`) and that all 15 rounds are represented.

---

## 5. Verification Method

To independently reproduce all findings and verify the defects:

1. **Run Full Test Suite**:
```powershell
python -m pytest tests/ -v
```
**Expected Result**: 77 PASSED, 3 FAILED (`test_challenger_finding_mcq_decimal_option_prefix_stripping`, `test_challenger_finding_round_38_allows_forbidden_q50`, `test_challenger_finding_consolidated_list_ignores_round_census`).

2. **Verify Decimal Option Bug in Parser**:
```powershell
python -m pytest tests/test_tier5_adversarial.py -k "test_challenger_finding_mcq_decimal_option_prefix_stripping" -v
```
**Observed Failure**:
`AssertionError: CRITICAL BUG REPRODUCED: Decimal options were corrupted by prefix regex! Expected ['1.0', '1.5', '2.0', '2.5'], but got ['0', '5', '0', '5']`

3. **Verify Existing Corrupted Data in Saved Dataset**:
```powershell
python -c "import json; d = json.load(open('data/adsp_round_46.json', encoding='utf-8')); q24 = next(q for q in d if q['question_no'] == 24); print('Q24 options:', q24['options'])"
```
**Observed Output**:
`Q24 options: ['0', '5', '0', '5']` (Should be: `['1.0', '1.5', '2.0', '2.5']`)

```powershell
python -c "import json; d = json.load(open('data/adsp_round_46.json', encoding='utf-8')); q30 = next(q for q in d if q['question_no'] == 30); print('Q30 options:', q30['options'])"
```
**Observed Output**:
`Q30 options: ['5', '0', '5', '5.0']` (Should be: `['1.5', '2.0', '2.5', '5.0']`)

4. **Verify Round 38 Validator Gap**:
```powershell
python -m pytest tests/test_tier5_adversarial.py -k "test_challenger_finding_round_38_allows_forbidden_q50" -v
```
**Observed Failure**:
`Failed: VALIDATOR GAP REPRODUCED: Round 38 validator permitted Q50 to exist!`

5. **Verify Consolidated Dataset List Gap**:
```powershell
python -m pytest tests/test_tier5_adversarial.py -k "test_challenger_finding_consolidated_list_ignores_round_census" -v
```
**Observed Failure**:
`Failed: VALIDATOR GAP REPRODUCED: validate_consolidated_dataset accepted homogeneous list without round census!`
