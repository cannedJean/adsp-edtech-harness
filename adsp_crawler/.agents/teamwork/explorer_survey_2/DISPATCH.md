# DISPATCH: Hub & Post Structure Explorer (Survey 2)

## Context
You are the Hub & Post Structure Explorer for the ADsP crawler project.
Your working directory is: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_2`
Project root: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler`

## Task
1. Read `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md`.
2. Investigate the live category hub at `https://www.sqldpass.com/blog/category/ADsP`:
   - Inspect the network response / SSR HTML of `https://www.sqldpass.com/blog/category/ADsP`.
   - Check how posts are listed (is it static HTML SSR, paginated, or API-driven?).
   - Map out all 15 rounds: 32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50. Find the exact post URLs or slugs for each round.
   - Check response headers, User-Agent behavior, rate limiting tolerances, and whether requests via `requests` or `httpx` or python standard library work reliably.
3. Produce a structured handoff report in `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_2\handoff.md` with:
   - Category URL structure and post link extraction selectors/regex
   - Table of all 15 round titles and direct post URLs
   - Network / HTTP fetch recommendations (User-Agent, headers, timeouts, jitter)


## 2026-10-29T00:32:31Z
Received dispatch message:
"You are the Hub & Post Structure Explorer for the ADsP crawler project.
Your working directory is: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_2
Read C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\ORIGINAL_REQUEST.md and C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_2\DISPATCH.md before starting work.
Investigate https://www.sqldpass.com/blog/category/ADsP and discover all 15 rounds (32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50). Inspect SSR HTML, pagination, headers, network behavior.
Maintain progress.md in your working directory.
When finished, write your findings and direct post URL mapping to C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_2\handoff.md and notify me via send_message."
