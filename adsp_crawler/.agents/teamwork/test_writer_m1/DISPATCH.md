# DISPATCH: E2E Test Suite Writer (Milestone 1)

## Context
You are the Test Writer for the E2E Testing Track of the ADsP Crawler project.
Working directory: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\test_writer_m1`
Project root: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler`

## Required Inputs to Read
1. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md` (authoritative user requirements)
2. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\PROJECT.md` (architecture, feature inventory, code layout)
3. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\handoff.md` (spec and schema findings)
4. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_2\handoff.md` (round and hub census)
5. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_3\handoff.md` (DOM and markdown findings)

## Task & Scope
Implement the full opaque-box, requirement-driven E2E test suite in `tests/`:
1. **Test Infrastructure**:
   - `tests/conftest.py`: Fixtures, mock SSR HTML payloads (e.g. sample Round 50, Round 38 short answer, table Q25, R code Q26), network mocking helpers.
   - `tests/test_runner.py`: Standalone CLI runner capable of running all tiers and reporting summary metrics.
   - Create `TEST_INFRA.md` in `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\TEST_INFRA.md` (and a copy or link in `.agents/teamwork/TEST_INFRA.md`).
2. **4-Tier Test Suite**:
   - `tests/test_tier1_feature_coverage.py`: Tier 1 Feature Coverage (tests for all 17 features: hub discovery, rate limiter, headers, CLI args, output dir, question items, question numbers, question types, GFM tables, ```r code fences, options array, answer key, explanation exclusion, schema validator, census validator, per-round storage, consolidated storage).
   - `tests/test_tier2_boundary_corner.py`: Tier 2 Boundary & Corner Cases (empty options for 단답형, missing Q50 in rounds 38/40, tables with empty cells, R code blocks in RSC flight stream, diverse short answer formats, answer suffix stripping, invalid CLI args).
   - `tests/test_tier3_cross_feature.py`: Tier 3 Cross-Feature Interactions (fetching + parsing + schema validation pipeline; CLI execution + storage persistence; rate limiting + retry under network errors).
   - `tests/test_tier4_scenarios.py`: Tier 4 Real-World Application Scenarios (full single-round crawl & store; full 15-round census verification; negative test for explanation leaks across all output files).
3. **Publish `TEST_READY.md`**:
   - Once all test files are written and verified with pytest (using mock data where live crawler implementation is pending), create `TEST_READY.md` at `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\TEST_READY.md` (and `.agents/teamwork/TEST_READY.md`).
4. **Handoff**:
   - Write comprehensive report to `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\test_writer_m1\handoff.md`.


## 2026-10-29T00:58:04Z
You are the Test Writer for the E2E Testing Track (Milestone 1) of the ADsP crawler project.
Your working directory is: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\test_writer_m1
Project root: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler

Read these files before starting work:
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\PROJECT.md
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\test_writer_m1\DISPATCH.md
- Survey reports in C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\handoff.md, explorer_survey_2\handoff.md, explorer_survey_3\handoff.md

Implement the comprehensive 4-tier opaque-box E2E test suite in `tests/` per the project methodology:
1. `tests/conftest.py`, fixtures, mock HTML samples
2. `tests/test_tier1_feature_coverage.py` (all 17 features covered)
3. `tests/test_tier2_boundary_corner.py` (empty options for 단답형, R38/R40 missing Q50, GFM tables with empty cells, R code blocks in flight stream, answer suffix stripping)
4. `tests/test_tier3_cross_feature.py` (pairwise combinations)
5. `tests/test_tier4_scenarios.py` (real-world workflows, full 15 rounds dataset verification, negative leak assertions)
6. `tests/test_runner.py`
7. Create TEST_INFRA.md and TEST_READY.md when tests are ready.

Run pytest to verify the test suite executes cleanly.
Write your handoff report to C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\test_writer_m1\handoff.md and notify me via send_message when done.
