# DISPATCH: Specification & Requirements Miner (Survey 1)

## Context
You are the Specification & Requirements Miner for the ADsP crawler project.
Your working directory is: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1`
Project root: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler`

## Task
1. Read `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md` thoroughly.
2. Mine and specify every single requirement, acceptance criterion, schema constraint, edge case, and data pipeline rule:
   - Category Hub discovery, 15 rounds (32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50), expected total 748 questions (min 740).
   - Rate limiting (1.0~2.0s random jitter), polite headers, CLI arguments for round selection.
   - Question items (`li.rounded-2xl`), question types: '4지선다' vs '단답형' (rounds 32~39).
   - Table to GFM conversion (`<table>` -> `| ... |`).
   - R code blocks to fenced code blocks (`<pre><code>` -> ````r ... ````).
   - Options extraction (1~4 array for 4-choice, empty array `[]` for short answer).
   - Answer extraction from `<details>` container.
   - Complete exclusion of explanations, "오답 풀이", "보충 개념", button text.
   - Schema validation: `question_no` (int), `question_type` (str), `prompt` (str), `options` (list[str]), `answer` (str).
   - Storage: `data/adsp_round_{round}.json` and `data/adsp_all.json`.
3. Produce a structured specification and feature inventory handoff report in `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\handoff.md`.


## 2026-10-29T00:32:31Z
sender=dc5a58c3-29d7-4d92-a20c-78cea0bdbd32
content=You are the Specification & Requirements Miner for the ADsP crawler project.
Your working directory is: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1
Read C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md and C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\DISPATCH.md before starting work.
Mine and specify every single requirement, acceptance criterion, schema constraint, edge case, and data pipeline rule.
Maintain progress.md in your working directory.
When finished, write your comprehensive analysis to C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\handoff.md and notify me via send_message.
