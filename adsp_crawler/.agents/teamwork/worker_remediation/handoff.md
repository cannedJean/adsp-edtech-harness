# Handoff Report: Remediation of ADsP Crawler & Live Corpus Pipeline

**Agent**: Remediation Worker (implementer, qa)  
**Date**: 2026-10-29  
**Target Project**: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler`  

---

## 1. Observation

### Obs 1.1: Pre-Remediation Test Failures
Running `python -m pytest tests/ -v` prior to remediation produced 3 test failures:
- `tests/test_tier5_adversarial.py::TestEmpiricalChallengerFindings::test_challenger_finding_mcq_decimal_option_prefix_stripping FAILED`:
  `AssertionError: CRITICAL BUG REPRODUCED: Decimal options were corrupted by prefix regex! Expected ['1.0', '1.5', '2.0', '2.5'], but got ['0', '5', '0', '5']`
- `tests/test_tier5_adversarial.py::TestEmpiricalChallengerFindings::test_challenger_finding_round_38_allows_forbidden_q50 FAILED`:
  `Failed: VALIDATOR GAP REPRODUCED: Round 38 validator permitted Q50 to exist!`
- `tests/test_tier5_adversarial.py::TestEmpiricalChallengerFindings::test_challenger_finding_consolidated_list_ignores_round_census FAILED`:
  `Failed: VALIDATOR GAP REPRODUCED: validate_consolidated_dataset accepted homogeneous list without round census!`

### Obs 1.2: Pre-Remediation Leaked AST Payload in Round 37 Q49
Inspection of `data/adsp_round_37.json` (index 48, Question 49) and `data/adsp_all.json` (index 148):
```json
"prompt": "아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라.\n\n4f:[\"$\",\"li\",\"20413\",{\"className\":\"rounded-2xl border border-border bg-surface/40 p-5\",\"children\":[[\"$\",\"div\",null,{\"className\":\"flex items-center justify-between\",\"children\":[[\"$\",\"p\",null,{\"className\":\"text-xs font-semibold tabular-nums text-text-muted\",\"children\":[\"문제 \",49]}],[\"$\",\"span\",null,{\"className\":\"text-[10px] font-medium uppercase tracking-wider text-text-subtle\",\"children\":\"단답형\"}]]}],[\"$\",\"div\",null,{\"className\":\"mt-3\",\"children\":[\"$\",\"$L1f\",null,{\"content\":\"$52\",\"variant\":\"pastExam\"}]}],false,\"$L53\"]}]"
```
In `adsp_crawler/parser.py:200`, `r"(?:^|\n)([0-9a-fA-F]+):T[0-9a-fA-F]+,(.*?)(?=(?:\n[0-9a-fA-F]+:|\Z))"` allowed text chunk 52 to absorb the subsequent component chunk `4f:[...]` because there was no newline before `4f:`.

### Obs 1.3: Code Modifications Executed
1. **`adsp_crawler/parser.py`**:
   - Line 200: Adjusted flight chunk boundary regex to:
     `r"(?:^|\n)([0-9a-fA-F]+):T[0-9a-fA-F]+,(.*?)(?=(?:\n?[0-9a-fA-F]+:\[|\n[0-9a-fA-F]+:|\Z))"`
     ensuring chunk 52 terminates before component chunk `4f:[`.
   - Lines 347-359: Added dual-layer safety check for React AST markers (`'["$"', '{"className"', "rounded-2xl", "tabular-nums"`). If any candidate flight prompt contains these markers, it immediately falls back to `extract_dom_prompt(it)`.
   - Lines 380-384: Fixed option prefix stripping regex:
     `opt_txt = re.sub(r"^[1-4]\s*[\.\)][ \t]+", "", opt_txt).strip()`
     requiring whitespace after the delimiter so decimal options (e.g. `'1.0'`, `'1.5'`, `'2.0'`, `'2.5'`, `'3.6'`, `'3.5'`) are preserved intact.

2. **`adsp_crawler/validator.py`**:
   - Lines 33-38: Added `'["$"', "rounded-2xl", "tabular-nums", '{"className"'` to `FORBIDDEN_TERMS`.
   - Lines 166-177: Hardened `validate_round_dataset()`: for rounds 38 and 40, verified that `seen_nos == set(range(1, 50))` and `50 not in seen_nos`; for all other rounds, verified `seen_nos == set(range(1, 51))`.
   - Lines 230-244: Hardened `validate_consolidated_dataset()`: when receiving a flat list, asserted that each question has a valid `'round'` attribute and that `rounds_seen == set(TARGET_ROUNDS)`.

### Obs 1.4: Post-Remediation Crawler Pipeline Execution
Executed `python main.py --all --output-dir data`.
Result: Exit code 0.
- All 15 rounds harvested, validated, and saved (`adsp_round_{32..50}.json`).
- Consolidated dataset validated and saved to `data/adsp_all.json` (748 questions).

### Obs 1.5: Post-Remediation Verification of Repaired Data
- `data/adsp_round_46.json` Q24 options: `['1.0', '1.5', '2.0', '2.5']` (previously corrupted to `['0', '5', '0', '5']`).
- `data/adsp_round_46.json` Q30 options: `['3.5', '4.0', '4.5', '5.0']` (previously corrupted to `['5', '0', '5', '5.0']`).
- `data/adsp_round_37.json` Q25 options: `['3.6', '2.2', '3.2', '5.0']` (previously corrupted to `['6', '2', '2', '5.0']`).
- `data/adsp_round_37.json` Q49 prompt: `'아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라.'` (clean text, zero React AST code).
- `data/adsp_all.json` Round 37 Q49 prompt: `'아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라.'`.
- AST / framework markers (`['["$"', 'rounded-2xl', 'tabular-nums', '{"className"']`) scan across all 16 JSON files: exactly 0 leaks.

### Obs 1.6: Post-Remediation Test Results
- `python tests/test_runner.py --verbose`: 34 / 34 PASSED (100% across Tiers 1-4).
- `python -m pytest tests/test_live_corpus.py -v`: 5 / 5 PASSED (100%).
- `python -m pytest tests/test_tier5_adversarial.py -v`: 41 / 41 PASSED (100%).
- Full suite `python -m pytest tests/ -v`: 80 / 80 PASSED (100%).

---

## 2. Logic Chain

1. **Step 1 (Parser Option Stripping)**:
   - In `adsp_crawler/parser.py`, the previous regex `re.sub(r"^[1-4]\s*[\.\)]\s*", "", opt_txt)` treated decimal digits followed by a period (e.g. `"1.0"`) as an option number `"1."`, erroneously stripping it to `"0"`.
   - Modifying the regex to require trailing whitespace `[ \t]+` (`re.sub(r"^[1-4]\s*[\.\)][ \t]+", "", opt_txt)`) preserves valid decimal numbers while correctly stripping legitimate option prefixes (e.g. `"1. Option"`).
   - This directly fixed the data corruption in Round 46 Q24, Q30, Round 37 Q25, Round 47 Q31, and Round 35 Q32, and satisfied adversarial regression test `test_challenger_finding_mcq_decimal_option_prefix_stripping`.

2. **Step 2 (Flight Chunk Boundary & AST Fallback)**:
   - In Next.js RSC Flight payloads where an inline SVG does not end with a newline, component chunks (such as `4f:[...]`) can directly abut the previous text chunk without an intervening newline.
   - Adjusting the lookahead in `extract_flight_prompts()` to `(?=(?:\n?[0-9a-fA-F]+:\[|\n[0-9a-fA-F]+:|\Z))` guarantees that chunk 52 stops before `4f:[`.
   - In addition, adding the AST marker check in `parse_adsp_post()` ensures that even if any unforeseen chunk delimiter issue occurs, any candidate prompt containing framework AST markers immediately falls back to `extract_dom_prompt(it)`.
   - Both layers were verified: Round 37 Q49 prompt now contains strictly `"아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라."` with zero leaked AST markers.

3. **Step 3 (Validator Hardening)**:
   - In `adsp_crawler/validator.py`, adding React AST markers to `FORBIDDEN_TERMS` guarantees that any future AST leaks trigger immediate `ValidationError`.
   - Checking `seen_nos == set(range(1, 50))` for Rounds 38 & 40 ensures that Q50 is strictly forbidden and all 49 questions (1..49) are present, satisfying `test_challenger_finding_round_38_allows_forbidden_q50`.
   - In `validate_consolidated_dataset()`, enforcing the presence of the `'round'` field and verifying `rounds_seen == set(TARGET_ROUNDS)` ensures that flat list datasets cannot pass without all 15 rounds represented, satisfying `test_challenger_finding_consolidated_list_ignores_round_census`.

4. **Step 4 (Corpus Re-generation & Verification)**:
   - Re-running the crawler pipeline (`python main.py --all --output-dir data`) regenerated all 15 round JSON files and `adsp_all.json`.
   - Verification confirmed that all mathematical decimal values and question prompts across all 748 questions are pristine.
   - All 80 automated tests (Tiers 1-5 and live corpus) passed without errors.

---

## 3. Caveats

- **No Caveats**: All identified defects from Challenger 1 and Reviewer 2 reports have been completely addressed, verified against live data and automated test suites, and 100% test pass rate achieved.

---

## 4. Conclusion

All remediation tasks have been successfully completed:
1. `adsp_crawler/parser.py`: Option prefix regex corruption fixed; RSC Flight chunk boundary regex adjusted; React AST fallback to `extract_dom_prompt` implemented.
2. `adsp_crawler/validator.py`: React AST markers added to `FORBIDDEN_TERMS`; strict 1..49 census (excluding Q50) enforced for Rounds 38 and 40; all 15 rounds presence verified in consolidated list validation.
3. Live data corpus regenerated: 15 individual round JSON files + 1 consolidated file (`data/adsp_all.json`, 748 questions) are 100% clean and valid.
4. All test suites pass 100% (80/80 passed).

---

## 5. Verification Method

To independently reproduce and verify the fixes:

1. **Verify Preserved Decimal Options in Regenerated Data**:
```powershell
python -c "import json; d = json.load(open('data/adsp_round_46.json', encoding='utf-8')); q24 = next(q for q in d if q['question_no'] == 24); print('Q24:', q24['options']); q30 = next(q for q in d if q['question_no'] == 30); print('Q30:', q30['options'])"
```
Expected output:
- `Q24: ['1.0', '1.5', '2.0', '2.5']`
- `Q30: ['3.5', '4.0', '4.5', '5.0']`

2. **Verify Clean Prompt for Round 37 Q49**:
```powershell
python -c "import json; qs = json.load(open('data/adsp_round_37.json', encoding='utf-8')); print(repr(qs[48]['prompt']))"
```
Expected output:
`'아래의 덴드로그램을 사용하여 100일 때의 군집의 수를 구하여라.'`

3. **Verify Zero AST Marker Leaks Across All JSON Files**:
```powershell
python -c "import json, glob; ast_markers = ['[\"$\"', 'rounded-2xl', 'tabular-nums', '{\"className\"']; leaks = [q['question_no'] for p in glob.glob('data/*.json') for q in json.load(open(p, encoding='utf-8')) if any(m in q['prompt'] for m in ast_markers)]; print('Leaks count:', len(leaks))"
```
Expected output:
`Leaks count: 0`

4. **Run Test Suites**:
```powershell
python tests/test_runner.py --verbose
python -m pytest tests/test_live_corpus.py -v
python -m pytest tests/test_tier5_adversarial.py -v
python -m pytest tests/ -v
```
Expected output:
- `test_runner.py`: 34 passed (ALL TESTS PASSED)
- `test_live_corpus.py`: 5 passed
- `test_tier5_adversarial.py`: 41 passed
- Full suite: 80 passed in ~5s
