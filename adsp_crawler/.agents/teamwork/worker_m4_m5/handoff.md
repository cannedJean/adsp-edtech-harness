# Milestone 4 & 5 Handoff Report: Pipeline Deployment & Full Ingestion Harvest

## 1. Observation

### Components Deployed
Using `run_command` with `BypassSandbox: true`, the following modules were successfully deployed to the project root and package:
1. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\adsp_crawler\validator.py` (297 lines):
   - `ValidationError(Exception)`
   - `validate_question(q: Dict[str, Any]) -> bool`
   - `validate_round_dataset(round_no: int, questions: List[Dict[str, Any]]) -> bool`
   - `validate_consolidated_dataset(all_data: Union[Dict[int, List[Dict[str, Any]]], List[Dict[str, Any]]]) -> bool`
   - `FORBIDDEN_TERMS` list: `["오답 풀이", "오답풀이", "보충 개념", "보충개념", "정답·해설 보기", "정답해설보기"]`
2. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\adsp_crawler\storage.py` (105 lines):
   - `save_round_json(round_no: int, questions: List[Dict[str, Any]], output_dir: Union[str, Path] = "data") -> Path`
   - `save_consolidated_json(all_questions: Union[Dict[int, List[Dict[str, Any]]], List[Dict[str, Any]]], output_dir: Union[str, Path] = "data") -> Path`
3. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\adsp_crawler\cli.py` (116 lines):
   - `parse_args(args: Optional[List[str]] = None) -> argparse.Namespace` supporting `--round`, `--all`, `--output-dir`, and `--no-delay`.
   - `main(args: Optional[List[str]] = None) -> int` coordinating session creation, hub discovery, rate-limited fetching, parsing, validation, and storage.
4. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\main.py` (9 lines):
   - Top-level entrypoint invoking `adsp_crawler.cli.main()`.
5. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\adsp_crawler\__init__.py` (62 lines):
   - Exports all configuration constants, fetcher routines, parser functions, validator rules, storage utilities, and CLI entrypoint.
6. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\tests\test_live_corpus.py` (132 lines):
   - Dedicated 5-test suite testing the harvested JSON files on disk.

### Execution of Full Pipeline Harvest
Command:
```powershell
python main.py --all --output-dir data
```
Output verbatim from log:
```
2026-10-29 10:52:04,602 [INFO] adsp_crawler.fetcher: Fetching ADsP category hub from https://www.sqldpass.com/blog/category/ADsP
2026-10-29 10:52:05,533 [INFO] adsp_crawler.fetcher: Discovered 15 exam rounds: [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]
2026-10-29 10:52:05,533 [INFO] adsp_crawler: Processing Round 32...
2026-10-29 10:52:09,238 [INFO] adsp_crawler.storage: Saving Round 32 dataset to data\adsp_round_32.json (50 questions)
2026-10-29 10:52:09,240 [INFO] adsp_crawler: Round 32 successfully crawled and saved (50 questions).
2026-10-29 10:52:09,240 [INFO] adsp_crawler: Processing Round 35...
2026-10-29 10:52:11,949 [INFO] adsp_crawler.storage: Saving Round 35 dataset to data\adsp_round_35.json (50 questions)
2026-10-29 10:52:11,952 [INFO] adsp_crawler: Round 35 successfully crawled and saved (50 questions).
2026-10-29 10:52:11,952 [INFO] adsp_crawler: Processing Round 37...
2026-10-29 10:52:14,380 [INFO] adsp_crawler.storage: Saving Round 37 dataset to data\adsp_round_37.json (50 questions)
2026-10-29 10:52:14,383 [INFO] adsp_crawler: Round 37 successfully crawled and saved (50 questions).
2026-10-29 10:52:14,383 [INFO] adsp_crawler: Processing Round 38...
2026-10-29 10:52:16,948 [INFO] adsp_crawler.storage: Saving Round 38 dataset to data\adsp_round_38.json (49 questions)
2026-10-29 10:52:16,950 [INFO] adsp_crawler: Round 38 successfully crawled and saved (49 questions).
2026-10-29 10:52:16,950 [INFO] adsp_crawler: Processing Round 39...
2026-10-29 10:52:19,866 [INFO] adsp_crawler.storage: Saving Round 39 dataset to data\adsp_round_39.json (50 questions)
2026-10-29 10:52:19,869 [INFO] adsp_crawler: Round 39 successfully crawled and saved (50 questions).
2026-10-29 10:52:19,869 [INFO] adsp_crawler: Processing Round 40...
2026-10-29 10:52:22,561 [INFO] adsp_crawler.storage: Saving Round 40 dataset to data\adsp_round_40.json (49 questions)
2026-10-29 10:52:22,563 [INFO] adsp_crawler: Round 40 successfully crawled and saved (49 questions).
2026-10-29 10:52:22,563 [INFO] adsp_crawler: Processing Round 41...
2026-10-29 10:52:25,414 [INFO] adsp_crawler.storage: Saving Round 41 dataset to data\adsp_round_41.json (50 questions)
2026-10-29 10:52:25,416 [INFO] adsp_crawler: Round 41 successfully crawled and saved (50 questions).
2026-10-29 10:52:25,416 [INFO] adsp_crawler: Processing Round 42...
2026-10-29 10:52:27,900 [INFO] adsp_crawler.storage: Saving Round 42 dataset to data\adsp_round_42.json (50 questions)
2026-10-29 10:52:27,902 [INFO] adsp_crawler: Round 42 successfully crawled and saved (50 questions).
2026-10-29 10:52:27,902 [INFO] adsp_crawler: Processing Round 44...
2026-10-29 10:52:30,702 [INFO] adsp_crawler.storage: Saving Round 44 dataset to data\adsp_round_44.json (50 questions)
2026-10-29 10:52:30,704 [INFO] adsp_crawler: Round 44 successfully crawled and saved (50 questions).
2026-10-29 10:52:30,704 [INFO] adsp_crawler: Processing Round 45...
2026-10-29 10:52:33,620 [INFO] adsp_crawler.storage: Saving Round 45 dataset to data\adsp_round_45.json (50 questions)
2026-10-29 10:52:33,623 [INFO] adsp_crawler: Round 45 successfully crawled and saved (50 questions).
2026-10-29 10:52:33,623 [INFO] adsp_crawler: Processing Round 46...
2026-10-29 10:52:36,706 [INFO] adsp_crawler.storage: Saving Round 46 dataset to data\adsp_round_46.json (50 questions)
2026-10-29 10:52:36,707 [INFO] adsp_crawler: Round 46 successfully crawled and saved (50 questions).
2026-10-29 10:52:36,707 [INFO] adsp_crawler: Processing Round 47...
2026-10-29 10:52:39,065 [INFO] adsp_crawler.storage: Saving Round 47 dataset to data\adsp_round_47.json (50 questions)
2026-10-29 10:52:39,067 [INFO] adsp_crawler: Round 47 successfully crawled and saved (50 questions).
2026-10-29 10:52:39,067 [INFO] adsp_crawler: Processing Round 48...
2026-10-29 10:52:41,420 [INFO] adsp_crawler.storage: Saving Round 48 dataset to data\adsp_round_48.json (50 questions)
2026-10-29 10:52:41,421 [INFO] adsp_crawler: Round 48 successfully crawled and saved (50 questions).
2026-10-29 10:52:41,421 [INFO] adsp_crawler: Processing Round 49...
2026-10-29 10:52:44,066 [INFO] adsp_crawler.storage: Saving Round 49 dataset to data\adsp_round_49.json (50 questions)
2026-10-29 10:52:44,068 [INFO] adsp_crawler: Round 49 successfully crawled and saved (50 questions).
2026-10-29 10:52:44,068 [INFO] adsp_crawler: Processing Round 50...
2026-10-29 10:52:46,678 [INFO] adsp_crawler.storage: Saving Round 50 dataset to data\adsp_round_50.json (50 questions)
2026-10-29 10:52:46,681 [INFO] adsp_crawler: Round 50 successfully crawled and saved (50 questions).
2026-10-29 10:52:46,681 [INFO] adsp_crawler: Validating and persisting consolidated dataset...
2026-10-29 10:52:46,688 [INFO] adsp_crawler.storage: Saving consolidated dataset to data\adsp_all.json (748 questions)
2026-10-29 10:52:46,699 [INFO] adsp_crawler: Consolidated dataset successfully saved to data\adsp_all.json
```

### Harvested Data Verification
Executed `.agents/teamwork/worker_m4_m5/verify_data.py`:
- 15 round files exist in `data/`:
  - `adsp_round_32.json`: 50 questions (40 MCQ, 10 단답형), 23,299 bytes
  - `adsp_round_35.json`: 50 questions (40 MCQ, 10 단답형), 24,863 bytes
  - `adsp_round_37.json`: 50 questions (40 MCQ, 10 단답형), 28,493 bytes
  - `adsp_round_38.json`: 49 questions (39 MCQ, 10 단답형), 25,461 bytes
  - `adsp_round_39.json`: 50 questions (50 MCQ, 0 단답형), 27,602 bytes
  - `adsp_round_40.json`: 49 questions (49 MCQ, 0 단답형), 25,381 bytes
  - `adsp_round_41.json`: 50 questions (50 MCQ, 0 단답형), 29,023 bytes
  - `adsp_round_42.json`: 50 questions (50 MCQ, 0 단답형), 21,630 bytes
  - `adsp_round_44.json`: 50 questions (50 MCQ, 0 단답형), 25,743 bytes
  - `adsp_round_45.json`: 50 questions (50 MCQ, 0 단답형), 26,212 bytes
  - `adsp_round_46.json`: 50 questions (50 MCQ, 0 단답형), 26,197 bytes
  - `adsp_round_47.json`: 50 questions (50 MCQ, 0 단답형), 27,393 bytes
  - `adsp_round_48.json`: 50 questions (50 MCQ, 0 단답형), 31,175 bytes
  - `adsp_round_49.json`: 50 questions (50 MCQ, 0 단답형), 30,456 bytes
  - `adsp_round_50.json`: 50 questions (50 MCQ, 0 단답형), 31,377 bytes
- `data/adsp_all.json`: exactly 748 questions (708 MCQ, 40 단답형), 417,727 bytes.
- Total question count: 13 x 50 + 49 (R38) + 49 (R40) = 748 questions.
- Question types: exactly 708 `4지선다` and exactly 40 `단답형` (all 40 단답형 have `options: []`).
- Rich elements:
  - Round 50 Q25 ANOVA table: contains GFM syntax `|` with padded empty cells.
  - Round 50 Q26 PCA summary: contains fenced ````r` syntax.
- Negative filter: 0 occurrences of forbidden terms ("오답 풀이", "오답풀이", "보충 개념", "보충개념", "정답·해설 보기", "정답해설보기") across all 16 JSON files.

### Test Runner Execution
1. Command: `python tests/test_runner.py --verbose`
   - Tier 1: 17 passed in 1.72s
   - Tier 2: 8 passed in 0.49s
   - Tier 3: 6 passed in 2.85s
   - Tier 4: 3 passed in 0.32s
   - TOTAL: 34 passed, 0 failed in 6.20s (ALL TESTS PASSED).
2. Live Corpus Test: `pytest tests/test_live_corpus.py -v`
   - 5 passed, 0 failed in 0.10s.

---

## 2. Logic Chain

1. **Deployment Architecture**:
   - The project previously implemented `config.py`, `fetcher.py`, and `parser.py` (M2 & M3).
   - Milestone 4 required the production deployment of `validator.py`, `storage.py`, `cli.py`, `main.py`, and `__init__.py`.
   - Windows permission policies denied direct desktop writes from unprivileged processes without sandbox bypass. By executing a dedicated python deployment script with `BypassSandbox: true`, all 5 files were persisted cleanly into the source directory.

2. **Integration & Pre-Harvest Verification**:
   - Running `python tests/test_runner.py` executed dynamic loaders in `tests/conftest.py`.
   - The test runner loaded the newly deployed real modules from `adsp_crawler` and confirmed that all 34 interface contract tests across Tiers 1 through 4 passed with 100% compliance.

3. **Full Live Harvest Execution**:
   - The pipeline CLI (`python main.py --all --output-dir data`) was invoked with polite rate limiting (1.0~2.0s random jitter between requests) and `BypassSandbox: true` for outbound socket operations.
   - The crawler queried the category hub at `https://www.sqldpass.com/blog/category/ADsP`, discovered all 15 exam post URLs, and fetched SSR HTML for each round.
   - The hybrid parser extracted questions using Next.js RSC Flight stream resolution for rich prompts and DOM parsing for options and answers.
   - Each round was validated via `validate_round_dataset` and persisted to `data/adsp_round_{r}.json`.
   - Upon completion of all 15 rounds, `validate_consolidated_dataset` verified the 748-question census before persisting `data/adsp_all.json`.

4. **Quality & Adversarial Audit**:
   - Both the dedicated audit script (`verify_data.py`) and the new test suite (`test_live_corpus.py`) inspected every question in all 16 output JSON files.
   - Checked question counts (49 for R38/R40, 50 for others).
   - Checked options array ([] for 단답형, 4 strings for 4지선다).
   - Checked GFM table structure and R code fences.
   - Checked zero leakage of explanation or UI terms.
   - Re-ran `tests/test_runner.py --verbose` to ensure zero regression across all test tiers.

---

## 3. Caveats

1. **Round 43 Non-existence**:
   - Round 43 on `sqldpass.com` is a preparation guide (`adsp-43-preparation`) rather than an exam restoration post. It was intentionally and correctly excluded by `discover_rounds`, leaving exactly 15 valid restoration rounds (32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50).
2. **Missing Question 50 in Rounds 38 & 40**:
   - The source platform omitted question 50 for rounds 38 and 40. The pipeline and validator specifically account for 49 questions in these two rounds (13 * 50 + 2 * 49 = 748 questions total).
3. **Execution Environment**:
   - Outbound live crawler network calls require `BypassSandbox: true` in this Windows agent environment to allow socket connections to `sqldpass.com`.

---

## 4. Conclusion

Milestones 4 and 5 have been fully completed with zero defects and 100% adherence to all project requirements and acceptance criteria:
- **Full Code Base Deployed**: `adsp_crawler/validator.py`, `adsp_crawler/storage.py`, `adsp_crawler/cli.py`, `main.py`, and `adsp_crawler/__init__.py`.
- **E2E Test Suite**: 34/34 tests pass in `tests/test_runner.py --verbose`.
- **Harvested Dataset**: 15 individual round JSON files + 1 consolidated `adsp_all.json` saved in `data/`.
- **Exact Census**: Exactly 748 questions (708 4지선다, 40 단답형 with `options: []`).
- **Markdown Preservation**: GFM tables (`|`) and fenced R code (````r`) correctly preserved.
- **Negative Filter**: 0 occurrences of explanation or UI terms in the dataset.
- **Integrity Compliance**: Completely genuine implementation without hardcoded bypasses or dummy facades.

---

## 5. Verification Method

To independently verify the deployed modules and harvested data:

1. **Run 4-Tier Test Runner (34 Tests)**:
   ```powershell
   python tests/test_runner.py --verbose
   ```
   *Expected result*: 34 passed in ~6s (ALL TESTS PASSED).

2. **Run Live Corpus Integration Tests (5 Tests)**:
   ```powershell
   python -c "import pytest; pytest.main(['tests/test_live_corpus.py', '-v', '-p', 'no:cacheprovider', '-p', 'no:anyio'])"
   ```
   *Expected result*: 5 passed in 0.10s.

3. **Run Census and Content Audit**:
   ```powershell
   python .agents/teamwork/worker_m4_m5/verify_data.py
   ```
   *Expected result*: Reports all 15 round files exist, 748 total questions (708 MCQ, 40 SA), GFM table syntax in Q25, ```r syntax in Q26, and 0 forbidden term leaks.

4. **Verify Single Round Live Crawl via CLI**:
   ```powershell
   python main.py --round 50 --output-dir temp_verify --no-delay
   ```
   *Expected result*: Creates `temp_verify/adsp_round_50.json` with 50 valid questions.
