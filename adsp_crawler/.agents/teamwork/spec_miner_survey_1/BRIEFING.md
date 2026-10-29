# BRIEFING — 2026-10-29T00:45:00Z

## Mission
Mine and specify every single requirement, acceptance criterion, schema constraint, edge case, and data pipeline rule for the ADsP past exam crawler.

## 🔒 My Identity
- Archetype: specification_miner
- Roles: Specification & Requirements Miner
- Working directory: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1
- Original parent: dc5a58c3-29d7-4d92-a20c-78cea0bdbd32
- Milestone: survey

## 🔒 Key Constraints
- Mine and specify every single requirement, acceptance criterion, schema constraint, edge case, and data pipeline rule
- Read-only on implementation: do NOT implement crawler or models; specify thoroughly
- Write only to own directory: C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1
- Provide exhaustive, unambiguous rules, schemas, and edge case inventories

## Current Parent
- Conversation ID: dc5a58c3-29d7-4d92-a20c-78cea0bdbd32
- Updated: 2026-10-29T00:32:31Z

## Task Summary
- **What to build**: Full specification and feature inventory for ADsP past exam crawler (15 rounds, 748 questions)
- **Success criteria**: Exhaustive feature inventory, edge cases, schema constraints, conversion rules (tables, R code, options, answer extraction, negative exclusions), CLI requirements, pipeline validation rules
- **Interface contracts**: ORIGINAL_REQUEST.md, handoff.md
- **Code layout**: data/ for outputs, src/ or similar for implementation (per PROJECT.md)

## Key Decisions Made
- Prioritize probing actual site responses and HTML structures alongside explicit requirements in ORIGINAL_REQUEST.md.
- Verified total question count is exactly 748 (Rounds 38 and 40 have 49 questions; remaining 13 rounds have 50).
- Discovered Next.js RSC payload (`self.__next_f.push`) carries raw markdown code blocks for questions where SSR HTML `<pre>` tags bail out to client-side rendering.
- Identified option leaking edge case: naive `ul > li` selector catches `오답 풀이` items inside `<details>`.
- Identified 40 short answer questions exclusively in rounds 32, 35, 37, 38 with schema rule `options: []`.

## Artifact Index
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\DISPATCH.md — Dispatch instructions
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\progress.md — Progress and heartbeat tracking
- C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\spec_miner_survey_1\handoff.md — Final specification report
