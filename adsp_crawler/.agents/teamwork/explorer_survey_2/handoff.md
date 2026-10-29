# Hub & Post Structure Exploration Handoff Report

**Agent**: Hub & Post Structure Explorer (Survey 2)  
**Date**: 2026-10-29  
**Target Hub**: `https://www.sqldpass.com/blog/category/ADsP`  

---

## 1. Observation

### 1.1 Category Hub Structure & Rendering Mechanism
- **URL**: `https://www.sqldpass.com/blog/category/ADsP`
- **Response Headers**:
  - `Server: cloudflare`
  - `Content-Type: text/html; charset=utf-8`
  - `x-nextjs-cache: HIT`
  - `x-nextjs-prerender: 1`
  - `Cache-Control: s-maxage=1800, stale-while-revalidate=31534200`
- **Payload Size**: ~140 KB ~ 146 KB
- **Rendering Model**: Full Server-Side Rendering (Next.js SSR / Static Generation). The DOM contains all post metadata and links directly without needing client-side JavaScript execution or pagination.
- **Total Posts Listed**: The page header displays `<p class="mt-2 text-base text-text-muted">35개의 글</p>`. All 35 posts in category ADsP are rendered in a single page across 5 layout blocks:
  1. Top Featured Hero Card (1 post: Round 50 기출 복원)
  2. Section `기출 복원` (14 posts: Rounds 49, 42, 41, 40, 39, 38, 37, 35, 32, 48, 47, 46, 45, 44)
  3. Section `과목별 개념` (12 concept posts)
  4. Section `학습 전략` (4 study strategy posts)
  5. Section `시험 후기` (4 exam review posts)
- **Pagination**: There is NO pagination query parameter or subsequent page (e.g. `?page=2`). All 15 past-exam posts are completely present on the primary category hub page.

### 1.2 User-Agent & Network Tolerance Testing
Testing requests against `https://www.sqldpass.com/blog/category/ADsP` with different client configurations:
1. `User-Agent: Python-urllib/3.12` -> `HTTPError: 403 Forbidden` (Verbatim: `urllib.error.HTTPError: HTTP Error 403: Forbidden`)
2. `User-Agent: python-requests/2.34.2` -> `HTTP 200 OK` (0.995s)
3. `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...` -> `HTTP 200 OK` (0.602s)
4. Empty User-Agent -> `HTTP 200 OK` (0.617s)

### 1.3 Post URL Mapping & Live Survey Results
All 15 past exam URLs follow the slug format: `/blog/past-exam/adsp-{year}-{round}`.  
A live network harvest of all 15 post URLs yielded HTTP 200 responses across all targets.

| Round | Year | Exam Title (from `<h1>`) | Relative Path | Full Post URL | Size (Bytes) | Questions Harvested | 4지선다 (MC) | 단답형 (Short) | Missing Q No |
|:---:|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **32** | 2022 | 2022년 ADsP 32회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2022-32` | `https://www.sqldpass.com/blog/past-exam/adsp-2022-32` | 551,614 | 50 | 40 | 10 | None |
| **35** | 2022 | 2022년 ADsP 35회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2022-35` | `https://www.sqldpass.com/blog/past-exam/adsp-2022-35` | 572,573 | 50 | 40 | 10 | None |
| **37** | 2023 | 2023년 ADsP 37회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2023-37` | `https://www.sqldpass.com/blog/past-exam/adsp-2023-37` | 566,234 | 50 | 40 | 10 | None |
| **38** | 2023 | 2023년 ADsP 38회 문제·정답·해설 전문 49문항 | `/blog/past-exam/adsp-2023-38` | `https://www.sqldpass.com/blog/past-exam/adsp-2023-38` | 570,732 | **49** | 39 | 10 | **Q50** |
| **39** | 2023 | 2023년 ADsP 39회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2023-39` | `https://www.sqldpass.com/blog/past-exam/adsp-2023-39` | 601,499 | 50 | 50 | 0 | None |
| **40** | 2024 | 2024년 ADsP 40회 문제·정답·해설 전문 49문항 | `/blog/past-exam/adsp-2024-40` | `https://www.sqldpass.com/blog/past-exam/adsp-2024-40` | 582,623 | **49** | 49 | 0 | **Q50** |
| **41** | 2024 | 2024년 ADsP 41회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2024-41` | `https://www.sqldpass.com/blog/past-exam/adsp-2024-41` | 630,961 | 50 | 50 | 0 | None |
| **42** | 2024 | 2024년 ADsP 42회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2024-42` | `https://www.sqldpass.com/blog/past-exam/adsp-2024-42` | 590,236 | 50 | 50 | 0 | None |
| **44** | 2025 | 2025년 ADsP 44회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2025-44` | `https://www.sqldpass.com/blog/past-exam/adsp-2025-44` | 559,746 | 50 | 50 | 0 | None |
| **45** | 2025 | 2025년 ADsP 45회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2025-45` | `https://www.sqldpass.com/blog/past-exam/adsp-2025-45` | 559,935 | 50 | 50 | 0 | None |
| **46** | 2025 | 2025년 ADsP 46회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2025-46` | `https://www.sqldpass.com/blog/past-exam/adsp-2025-46` | 580,765 | 50 | 50 | 0 | None |
| **47** | 2025 | 2025년 ADsP 47회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2025-47` | `https://www.sqldpass.com/blog/past-exam/adsp-2025-47` | 596,965 | 50 | 50 | 0 | None |
| **48** | 2026 | 2026년 ADsP 48회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2026-48` | `https://www.sqldpass.com/blog/past-exam/adsp-2026-48` | 595,090 | 50 | 50 | 0 | None |
| **49** | 2026 | 2026년 ADsP 49회 문제·정답·해설 전문 50문항 | `/blog/past-exam/adsp-2026-49` | `https://www.sqldpass.com/blog/past-exam/adsp-2026-49` | 614,860 | 50 | 50 | 0 | None |
| **50** | 2026 | 2026년 ADsP 50회 기출 복원 | `/blog/past-exam/adsp-2026-50` | `https://www.sqldpass.com/blog/past-exam/adsp-2026-50` | 632,899 | 50 | 50 | 0 | None |
| **Total** | - | - | - | - | **~8.8 MB** | **748** | **708** | **40** | **2 Qs** |

### 1.4 Post DOM Internal Structure
Each question item is encapsulated in `<li class="... rounded-2xl ...">` with standard child elements:
1. **Header**: `<div class="flex items-center justify-between">`
   - Question Number: `<p class="text-xs font-semibold tabular-nums text-text-muted">문제 <!-- -->{N}</p>`
   - Question Type Badge: `<span class="text-[10px] font-medium uppercase tracking-wider text-text-subtle">4지선다</span>` or `단답형`
2. **Prompt Body**: `<div class="mt-3"><div class="question-md question-md-past-exam">...`
   - Contains prompt `<p>`, HTML `<table>`, and code `<pre><code>`.
3. **Options Container** (Present ONLY for `4지선다`): `<ul class="mt-4 space-y-1.5">`
   - Child items: `<li class="flex items-start gap-2 rounded-md border border-border bg-bg px-3 py-2 text-sm">`
   - Option number: `<span class="font-semibold tabular-nums">{1..4}<!-- -->.</span>`
   - Option text: `<span class="min-w-0 flex-1"><div class="question-md question-md-past-exam mcq-option">...`
4. **Answer/Explanation Container**: `<details class="mt-4 group">`
   - Summary button: `<summary>...정답·해설 보기...</summary>`
   - Inner content contains answer key and explanation.

---

## 2. Logic Chain

1. **Step 1 (Discovery Integrity)**:
   - Observation: Category hub HTML has exactly 15 `<a>` tags matching regex `^/blog/past-exam/adsp-(\d{4})-(\d+)$`.
   - Inference: The crawler can discover all rounds dynamically from a single request to `https://www.sqldpass.com/blog/category/ADsP` without maintaining hardcoded URLs or handling pagination.
2. **Step 2 (Question Count Reconciliation)**:
   - Observation: 13 rounds contain exactly 50 `li.rounded-2xl` questions. Round 38 has 49 items, and Round 40 has 49 items.
   - Observation: Titles on sqldpass.com explicitly state `2023년 ADsP 38회 문제·정답·해설 전문 49문항` and `2024년 ADsP 40회 문제·정답·해설 전문 49문항`.
   - Observation: Inspecting the question number list for both Round 38 and Round 40 revealed questions 1 through 49 sequentially, with Question 50 omitted on the source platform.
   - Inference: $13 \times 50 + 2 \times 49 = 650 + 98 = 748$ questions total. This aligns with the acceptance criterion of 748 total questions.
3. **Step 3 (Short Answer Distribution)**:
   - Observation: Rounds 32, 35, 37, 38 each have 10 `단답형` questions (questions 41~50 for 32/35/37, questions 41~49 for 38).
   - Observation: Round 39 and all rounds from 40 through 50 have 0 `단답형` questions (100% `4지선다` with 4 options).
   - Inference: The parser must dynamically inspect the badge or presence of `<ul class="mt-4 space-y-1.5">` to set `question_type: "단답형"` and `options: []` for those specific questions.
4. **Step 4 (Network & Bot Protection Strategy)**:
   - Observation: Standard Python `urllib` without custom headers triggered HTTP 403 Forbidden by Cloudflare.
   - Observation: Requests with a standard Chrome `User-Agent` returned HTTP 200 OK with fast response times (< 1.5s per page).
   - Inference: The crawler must configure a browser-mimicking `User-Agent` and include a random polite jitter (1.0~2.0s) between post downloads.

---

## 3. Caveats

- **No Question 50 in Rounds 38 & 40**: The source website `sqldpass.com` does not have Question 50 published for these two rounds. The crawler schema validator must allow 49 questions for rounds 38 and 40 while requiring 50 questions for all other rounds.
- **Cloudflare Edge Rules**: Direct rapid scraping without delay might trigger Cloudflare rate limiting or CAPTCHA challenges. A 1.0~2.0s jitter delay is necessary.
- **Round 43**: Notice that round 43 does not exist in the past-exam list (the sequence jumps from 42 to 44). The category hub lists an article titled "ADsP 43회 수험 가이드", but there is no 43회 기출 복원 post on sqldpass.com.

---

## 4. Conclusion

1. **Ingestion Entry Point**:
   ```python
   HUB_URL = "https://www.sqldpass.com/blog/category/ADsP"
   POST_LINK_PATTERN = re.compile(r"^/blog/past-exam/adsp-(\d{4})-(\d+)$")
   ```
   Extraction method:
   ```python
   def discover_exam_posts(html_text: str) -> dict[int, str]:
       soup = BeautifulSoup(html_text, "html.parser")
       discovered = {}
       for a in soup.find_all("a", href=POST_LINK_PATTERN):
           m = POST_LINK_PATTERN.match(a["href"])
           round_no = int(m.group(2))
           discovered[round_no] = f"https://www.sqldpass.com{a['href']}"
       return discovered
   ```
2. **HTTP Client Configuration**:
   - Client: `requests.Session()`
   - Headers:
     ```python
     DEFAULT_HEADERS = {
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
     }
     ```
   - Request Timeout: `timeout=15.0`
   - Jitter Delay: `time.sleep(random.uniform(1.0, 2.0))`
3. **Data Completeness Guarantee**:
   - Total expected rounds: 15
   - Total expected questions: 748 (Rounds 38 and 40 have 49; all others have 50)
   - Total short-answer questions: 40 (10 in Round 32, 10 in Round 35, 10 in Round 37, 10 in Round 38)
   - Total multiple-choice questions: 708

---

## 5. Verification Method

To independently verify all findings and validate the mapping against the live website:

1. Run the hub discovery verification test:
   ```powershell
   python -c "
   import requests, re
   res = requests.get('https://www.sqldpass.com/blog/category/ADsP', headers={'User-Agent': 'Mozilla/5.0'})
   links = re.findall(r'/blog/past-exam/adsp-\d{4}-(\d+)', res.text)
   rounds = sorted(list(set(int(r) for r in links)))
   print('Discovered rounds:', rounds)
   assert rounds == [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]
   print('Verification Passed: 15/15 rounds matched!')
   "
   ```
2. Inspect the saved survey payload at `C:\Users\SSAFY\.gemini\antigravity\scratch\all_rounds_survey.json` to review individual round statuses, sizes, and question distributions.
3. Invalidation condition: If `sqldpass.com` updates Round 38 or 40 to include Question 50, the total question count will increase from 748 to 749 or 750.
