# DISPATCH: Question DOM & Markdown Explorer (Survey 3)

## Context
You are the Question DOM & Markdown Explorer for the ADsP crawler project.
Your working directory is: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_3`
Project root: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler`

## Task
1. Read `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md`.
2. Inspect sample exam post pages from `https://www.sqldpass.com` (for example, Round 50 post, Round 49, and pre-2024 rounds like Round 35 or 38):
   - Analyze the exact DOM structure of question items (`li.rounded-2xl`).
   - Identify how `question_no` is formatted and located.
   - Inspect question prompt DOM: where tables (`<table>`) and R code snippets (`<pre><code>` or similar) appear. Check specific examples like Round 50 Q25 (ANOVA table) and Round 50 Q26 (PCA summary R code).
   - Inspect how 4-choice options (1~4) are structured inside the question item.
   - Inspect how short-answer (단답형) questions in rounds 32~39 are structured.
   - Inspect `<details>` / `<summary>` answer container, how the answer key is stored, and where explanation texts ("오답 풀이", "보충 개념", "정답·해설 보기") reside so they can be completely stripped.
3. Produce a structured handoff report in `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_3\handoff.md` with:
   - Detailed CSS selectors / tag structures for question_no, prompt, options, answer key, details
   - Concrete HTML snippets from actual posts (tables, R code, details container)
   - Parsing & markdown conversion strategies and edge case warnings

## 2026-10-29T00:32:31Z

You are the Question DOM & Markdown Explorer for the ADsP crawler project.
Your working directory is: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_3
Read C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md and C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_3\DISPATCH.md before starting work.
Inspect sample exam post HTML (e.g. Round 50, Round 49, Round 35/38). Analyze `li.rounded-2xl` questions, question_no, table to GFM conversion, R code blocks to ```r, options array, answer key extraction from `<details>`, and filtering of explanation texts.
Maintain progress.md in your working directory.
When finished, write your findings and DOM selectors to C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_3\handoff.md and notify me via send_message.
