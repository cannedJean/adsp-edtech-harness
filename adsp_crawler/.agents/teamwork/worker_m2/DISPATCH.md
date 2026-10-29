# DISPATCH: Ingestion & Fetcher Worker (Milestone 2)

## Context
You are the Worker implementing Milestone 2: Ingestion & Fetcher Module.
Working directory: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m2`
Project root: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler`

## Exclusive File Ownership
You exclusively own and may write to:
- `adsp_crawler/__init__.py`
- `adsp_crawler/config.py`
- `adsp_crawler/fetcher.py`
DO NOT touch any files in `tests/` or write other files.

## Required Inputs to Read
1. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\PROJECT.md`
3. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_2\handoff.md`

## Task Description
Implement `adsp_crawler/config.py` and `adsp_crawler/fetcher.py`:
1. `config.py`:
   - Hub URL: `https://www.sqldpass.com/blog/category/ADsP`
   - Target 15 rounds: `[32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]`
   - Question counts mapping: 38 -> 49, 40 -> 49, all other 13 rounds -> 50. Total = 748.
   - Polite HTTP headers: realistic Chrome User-Agent, Accept, Accept-Language.
   - Jitter delay configuration: 1.0~2.0s random delay bounds (allow setting to 0 in test mode).
   - Timeout: 15.0s.
2. `fetcher.py`:
   - `fetch_hub_html(session: requests.Session = None) -> str`: fetch category hub with headers and error handling.
   - `discover_rounds(hub_html: str) -> dict[int, str]`: extract round numbers and full post URLs matching `/blog/past-exam/adsp-\d{4}-(\d+)`.
   - `fetch_post(url: str, session: requests.Session = None, delay_min: float = 1.0, delay_max: float = 2.0) -> str`: fetch exam post HTML with polite jitter delay and retry logic.
   - `fetch_round_post(round_no: int, hub_urls: dict[int, str] = None, session: requests.Session = None) -> str`: convenience helper to fetch by round number.
3. Verification:
   - Run tests / self-check verifying `discover_rounds` and `fetch_hub_html` live or against saved HTML.
   - Document verification commands and output in your handoff report.
   - Write handoff report to `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m2\handoff.md`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-10-29T00:58:04Z
You are the Worker implementing Milestone 2: Ingestion & Fetcher Module for the ADsP crawler project.
Your working directory is: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m2
Project root: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler

Read these files before starting work:
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\PROJECT.md
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m2\DISPATCH.md
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_2\handoff.md

Exclusive file ownership:
- adsp_crawler/__init__.py
- adsp_crawler/config.py
- adsp_crawler/fetcher.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement config.py and fetcher.py genuine functionality: hub discovery, rate limiter jitter (1.0~2.0s), polite headers, URL mapping for all 15 rounds. Run tests/self-verification and document the output in your handoff report at C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m2\handoff.md. Notify me via send_message when complete.
