## 2026-10-29T01:34:20Z
You are the Worker implementing Milestone 4: Validator, Storage & CLI Module for the ADsP crawler project.
Your working directory is: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m4
Project root: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler

Read these files before starting work:
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\PROJECT.md
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\handoff.md
- Existing modules: adsp_crawler/config.py, adsp_crawler/fetcher.py, adsp_crawler/parser.py

Exclusive file ownership:
- adsp_crawler/validator.py
- adsp_crawler/storage.py
- adsp_crawler/cli.py
- main.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. `adsp_crawler/validator.py`:
   - `validate_question(q: dict) -> bool`:
     - Checks strictly: `question_no` (int >= 1), `question_type` ('4지선다' or '단답형'), `prompt` (non-empty str), `options` (list[str]), `answer` (non-empty str).
     - Options check: exactly 4 items for 4지선다, strictly [] for 단답형.
     - Negative exclusion check: raises ValidationError if '오답 풀이', '보충 개념', or '정답·해설 보기' appears in prompt or options.
   - `validate_round_dataset(round_no: int, questions: list[dict]) -> bool`: validates round question count (49 for 38 and 40, 50 for all other 13 rounds), validates each question.
   - `validate_consolidated_dataset(all_data: dict[int, list[dict]] | list[dict]) -> bool`: validates total 748 questions (min 740), 708 MCQ, 40 short answer, all 15 rounds present.
2. `adsp_crawler/storage.py`:
   - `save_round_json(round_no: int, questions: list[dict], output_dir: str | Path = "data") -> Path`: writes `data/adsp_round_{round_no}.json` with UTF-8, indent=2, ensure_ascii=False.
   - `save_consolidated_json(all_questions: list[dict] | dict[int, list[dict]], output_dir: str | Path = "data") -> Path`: writes `data/adsp_all.json`.
3. `adsp_crawler/cli.py` & `main.py`:
   - CLI flags: `--round` (int, single or multiple), `--all` (default), `--output-dir` (default `data/`), `--no-delay` (disables jitter for fast testing).
   - Coordinates: discover hub -> fetch posts -> parse -> validate -> store.
   - Top-level `main.py` entrypoint.
4. Run verification:
   - Run tests: `python -m pytest tests/`
   - Run CLI: `python main.py --round 50 --output-dir test_data --no-delay`
   - Clean up test_data afterwards.

Write your handoff report to C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\worker_m4\handoff.md and notify me via send_message when done.
