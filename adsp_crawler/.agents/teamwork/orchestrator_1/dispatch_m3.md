# DISPATCH: Semantic Parser & Markdown Converter Worker (Milestone 3)

## Context
You are the Worker implementing Milestone 3: Semantic Parser & Markdown Converter Module.
Working directory: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m3`
Project root: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler`

## Exclusive File Ownership
You exclusively own and may write to:
- `adsp_crawler/parser.py`
DO NOT touch files in `tests/` or modify other modules.

## Required Inputs to Read
1. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\PROJECT.md`
3. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_3\handoff.md` (DOM selectors & production parser reference)
4. `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\handoff.md` (schema requirements & edge cases)

## Task Description
Implement `adsp_crawler/parser.py`:
1. `parse_adsp_post(html: str) -> list[dict]`:
   - Extracts all question items from HTML.
   - `question_no` (int): from `p.tabular-nums` (e.g. "문제 1" -> 1).
   - `question_type` (str): '4지선다' vs '단답형' (inspect badge `span` or options presence).
   - `prompt` (str):
     - Uses Next.js RSC flight payload resolution (`self.__next_f.push`) with `re.DOTALL` and hex reference chunk resolution (`$51`, `$5c`, etc.) so R code blocks and GFM tables are 100% preserved.
     - Fallback to DOM if flight payload is not present.
     - Normalizes code fence language tags to ```` ```r ````.
     - Strips inline SVGs if present so prompt text remains clean.
   - `options` (list[str]):
     - For '4지선다': strictly 4 options from `ul.mt-4 > li span.min-w-0` (or `.mcq-option`).
     - For '단답형': strictly empty list `[]`.
   - `answer` (str):
     - Extracted from `details p.text-base.font-semibold.text-success`.
     - For '4지선다': strip `"번"` (e.g. `"2번"` -> `"2"`).
     - For '단답형': clean model answer string (e.g. `"IoT"`, `"0.4"`, `"SCM"`).
   - Complete exclusion of explanations:
     - Zero occurrence of "오답 풀이", "보충 개념", or "정답·해설 보기".
2. Helper functions:
   - `extract_flight_prompts(html: str) -> list[str]`: Flight stream extraction with reference chunk dictionary.
   - `html_table_to_gfm(table_soup) -> str`: Fallback HTML table converter to GFM pipes `| ... |`.
3. Verification:
   - Run verification against sample HTMLs (Round 50, Round 38, Round 40).
   - Run existing E2E tests: `python -m pytest tests/test_tier1_feature_coverage.py -k "parser or question or table or code or option or answer"`
   - Document commands and test output in your handoff report.
   - Write handoff to `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m3\handoff.md`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
