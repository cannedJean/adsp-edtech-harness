# HANDOFF REPORT: Question DOM & Markdown Exploration

- **Agent**: Question DOM & Markdown Explorer (`explorer_survey_3`)
- **Date**: 2026-10-29T00:55:00Z
- **Working Directory**: `C:\Users\SSAFY\Desktop\ADsP\adsp_crawler\.agents\teamwork\explorer_survey_3`
- **Recipient**: Orchestrator (`dc5a58c3-29d7-4d92-a20c-78cea0bdbd32`)

---

## 1. Observation

### 1.1 Exam Post Structure & Question Items
Empirical inspection of all 15 rounds (`https://www.sqldpass.com/blog/past-exam/adsp-...`) revealed a consistent container structure:
- Outer Question Element: `li.rounded-2xl`
  - Exact HTML class: `li class="rounded-2xl border border-border bg-surface/40 p-5"`
- Question Counts across 15 rounds:
  - Rounds 32, 35, 37, 39, 41, 42, 44, 45, 46, 47, 48, 49, 50: **50 questions** each.
  - Round 38: **49 questions** (Q1~Q49 present, Q50 omitted on source site).
  - Round 40: **49 questions** (49 questions present).
  - **Total across all 15 rounds**: Exactly **748 questions**.

### 1.2 Question Number & Type Badges
Inside each `li.rounded-2xl`, the header block contains:
```html
<div class="flex items-center justify-between">
  <p class="text-xs font-semibold tabular-nums text-text-muted">문제<!-- -->1</p>
  <span class="text-[10px] font-medium uppercase tracking-wider text-text-subtle">4지선다</span>
</div>
```
- **Question Number Selector**: `p.tabular-nums`
  - Text pattern: `문제 1`, `문제 10`.
  - Regex extraction: `int(re.search(r'\d+', text).group())`.
- **Question Type Selector**: `div.flex.items-center.justify-between span`
  - Multiple Choice: `4지선다` (All rounds 40~50, plus 40 questions each in rounds 32, 35, 37, 38).
  - Short Answer: `단답형` (Exactly 10 questions each in rounds 32, 35, 37, 38 = 40 questions total; Round 39 has 50 multiple choice questions on sqldpass).

### 1.3 Critical Finding: SSR `<pre>` Code Block Bailout vs Next.js RSC Flight Stream
In all 15 rounds, when inspecting the SSR HTML DOM for questions containing R code blocks (e.g. Round 50 Q26 PCA summary, Q27 Logistic regression, Q49 Linear regression):
```html
<!-- Actual SSR HTML DOM for Round 50 Question 26 -->
<div class="mt-3">
  <div class="question-md question-md-past-exam">
    <p class="my-2 text-sm leading-relaxed whitespace-pre-line break-words">
      다음은 표준화한 자료에 주성분분석을 수행한 결과 중 PC1부터 PC7까지를 옮긴 것이다. 해석으로 옳지 않은 것은?
    </p>
    <pre><!--$!--><template data-dgst="BAILOUT_TO_CLIENT_SIDE_RENDERING"></template><div class="my-3 h-24 rounded-lg border border-zinc-800 bg-zinc-900/60 animate-pulse"></div><!--/$--></pre>
  </div>
</div>
```
- **The DOM `<pre>` element contains NO code text!** It only contains a Next.js client-side Suspense fallback placeholder (`animate-pulse`).
- Total affected code blocks across all rounds: **35 code blocks in 14 rounds** (all except Round 32).
- **Where the actual code is located**:
  In the Next.js React Server Component (RSC) flight payload inside `<script>self.__next_f.push([1, "..."])</script>`.
  In that payload, the author's original Markdown is completely intact:
  ```json
  ["$","div",null,{"className":"mt-3","children":["$","$L21",null,{"content":"다음은 표준화한 자료에 주성분분석을 수행한 결과 중 PC1부터 PC7까지를 옮긴 것이다. 해석으로 옳지 않은 것은?\n\n```\n> pca <- prcomp(X, scale. = TRUE)\n> summary(pca)\nImportance of components:\n                          PC1    PC2    PC3     PC4     PC5     PC6    PC7\nStandard deviation     2.0494 1.4491 1.0000 0.89443 0.77460 0.67082 0.6000\nProportion of Variance 0.4200 0.2100 0.1000 0.08000 0.06000 0.04500 0.0360\nCumulative Proportion  0.4200 0.6300 0.7300 0.81000 0.87000 0.91500 0.9510\n```\n","variant":"pastExam"}]}]
  ```

### 1.4 Tables in Questions (e.g. Round 50 Q25 ANOVA Table)
- In the HTML DOM, tables are rendered with standard semantic tags inside `div.mt-3`:
  ```html
  <div aria-label="문항 표" class="my-4 overflow-x-auto overscroll-x-contain" role="region" tabindex="0">
    <table class="w-max min-w-full border-collapse border border-zinc-500 bg-white text-left font-sans text-sm text-zinc-950">
      <thead class="bg-zinc-100 text-zinc-950">
        <tr>
          <th class="min-w-[5.5rem] border border-zinc-500 px-3 py-2 align-middle font-sans font-semibold">요인</th>
          <th class="min-w-[5.5rem] border border-zinc-500 px-3 py-2 align-middle font-sans font-semibold">제곱합</th>
          ...
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="min-w-[5.5rem] border border-zinc-500 px-3 py-2 align-middle font-sans text-zinc-950">회귀</td>
          <td class="min-w-[5.5rem] border border-zinc-500 px-3 py-2 align-middle font-sans text-zinc-950">100</td>
          ...
        </tr>
      </tbody>
    </table>
  </div>
  ```
- In the RSC Flight Stream, the table is **already formatted as clean GitHub Flavored Markdown (GFM)**:
  ```markdown
  다음은 단순선형회귀분석 결과로 얻은 분산분석표이다. 빈칸 ( )을 채워 해석한 내용으로 옳지 않은 것은?

  | 요인 | 제곱합 | 자유도 | 평균제곱 | F | p-value |
  |---|---:|---:|---:|---:|---:|
  | 회귀 | 100 | 1 | ( ) | ( ) | 3.41e-05 |
  | 잔차 | ( ) | 10 | ( ) |  |  |
  | 합계 | 120 | 11 |  |  |  |
  ```

### 1.5 Options Array Structure
- Multiple Choice (`4지선다`):
  ```html
  <ul class="mt-4 space-y-1.5">
    <li class="flex items-start gap-2 rounded-md border border-border bg-bg px-3 py-2 text-sm">
      <span class="font-semibold tabular-nums">1<!-- -->.</span>
      <span class="min-w-0 flex-1">
        <div class="question-md question-md-past-exam mcq-option">
          <p class="my-2 text-sm leading-relaxed whitespace-pre-line break-words">D(Data): 가공되기 전의 객관적 사실로...</p>
        </div>
      </span>
    </li>
    ... (total 4 items)
  </ul>
  ```
  - Selector for option text: `it.select('ul.mt-4 > li')`, then for each `li`, `span.min-w-0` contains the option text without number prefix.
  - Across all 708 multiple-choice questions, option count is **strictly 4** (0 exceptions).
- Short Answer (`단답형`, 40 questions in rounds 32, 35, 37, 38):
  - No `ul` exists. Option array is strictly `[]` (empty list).

### 1.6 Answer Key & Complete Isolation of Explanations
Inside each `li.rounded-2xl`, the answer container is an HTML `<details>` element:
```html
<details class="mt-4 group">
  <summary class="cursor-pointer select-none rounded-md ...">
    정답·해설 보기
    <span class="ml-2 text-xs ...">▾</span>
  </summary>
  <div class="mt-3 space-y-3 rounded-md border border-border bg-bg p-4 text-sm">
    <!-- Block 1: Answer Key -->
    <div>
      <p class="text-xs font-semibold text-text-muted">정답</p> <!-- or "모범답안" for 단답형 -->
      <p class="mt-1 text-base font-semibold text-success">2<!-- -->번</p> <!-- or "SCM", "데이터베이스" -->
    </div>
    <!-- Block 2: Explanation & Distractor Analysis (MUST EXCLUDE) -->
    <div>
      <p class="text-xs font-semibold text-text-muted">해설</p>
      <div class="mt-1 leading-relaxed">
        <div class="question-md question-md-past-exam">
          <p>정답: 2. ...</p>
          <p><strong class="font-semibold text-foreground">오답 풀이</strong></p>
          <ul class="my-2 ml-5 list-disc space-y-1 text-sm">...</ul>
          <p><strong class="font-semibold text-foreground">보충 개념</strong>...</p>
        </div>
      </div>
    </div>
  </div>
</details>
```
- **Answer Key Selector**: `details p.text-base.font-semibold.text-success`
  - For `4지선다`: contains `2번` -> clean with `re.search(r'\d+', text).group()` -> `"2"`.
  - For `단답형`: contains `SCM` or `데이터베이스` -> clean with `text.strip()` -> `"SCM"`.
  - Tested on 748 questions: **100% extracted, 0 missing**.
- **Explanation Exclusion**:
  - Explanations reside entirely inside `details div.leading-relaxed` and `summary`.
  - By strictly extracting `answer` from `details p.text-base.font-semibold.text-success` and extracting `prompt` from the prompt container, explanation text ("오답 풀이", "보충 개념", "정답·해설 보기") is **100% excluded**.
  - Verification across all 748 questions confirmed **0 leaks**.

### 1.7 Next.js RSC Reference Chunk Resolution
In questions with complex diagrams (e.g. SVG scatter plots in Round 50 Q34, Scree plot in Round 47 Q46, Carseats boxplot + summary in Round 41 Q34):
- In the flight stream, `content` is a reference such as `"$51"`, `"$53"`, `"$5c"`.
- The corresponding text chunk is defined in the flight stream as:
  `<hex_id>:T<hex_length>,<content>` (e.g. `51:T3474,...`, `5c:T775,...`).
- Resolving this dictionary allows 100% extraction of all prompts without losing code or text.

---

## 2. Logic Chain

1. **Observation 1.1 & 1.2**: Every question on sqldpass is bounded by `li.rounded-2xl` with a header `p.tabular-nums` and a badge `span`.
   - **Inference**: Question items can be cleanly enumerated with `soup.select('li.rounded-2xl')` and typed with simple badge string checking.
2. **Observation 1.3**: Next.js SSR Suspense replaces `<pre>` code blocks with `<template data-dgst="BAILOUT_TO_CLIENT_SIDE_RENDERING">` in the HTML DOM for 35 questions across 14 rounds.
   - **Inference**: A purely DOM-based crawler will extract empty code blocks and fail acceptance criterion 37 ("Questions containing R outputs contain fenced code block syntax").
3. **Observation 1.3 & 1.4**: The Next.js RSC flight payload inside `<script>self.__next_f.push(...)</script>` stores the exact author Markdown before rendering, containing complete R code snippets and pristine GFM tables (`| ... |`).
   - **Inference**: Extracting prompts from the RSC flight stream is vastly superior to converting HTML back to Markdown, as it gives 100% fidelity to the original markdown source without loss.
4. **Observation 1.7**: Some prompts in the flight stream contain reference keys (e.g. `"$51"`).
   - **Inference**: Building a chunk lookup table matching `(?:^|\n)([0-9a-fA-F]+):T[0-9a-fA-F]+,(.*?)(?=(?:\n[0-9a-fA-F]+:|\Z))` resolves 100% of references.
5. **Observation 1.5 & 1.6**: Options and answer keys are cleanly exposed in the DOM (`ul.mt-4 > li span.min-w-0` and `details p.text-base.font-semibold.text-success`) and are strictly separated from explanations.
   - **Inference**: A hybrid architecture—extracting metadata, options, and answer keys from DOM while extracting prompts from the flight stream—provides optimal robustness, zero explanation leaks, and 100% schema compliance.

---

## 3. Caveats

1. **Inline SVG Diagrams**: Some prompts (e.g. Round 50 Q34, Round 47 Q46) contain embedded SVG diagrams (`<svg>...</svg>`). These can either be kept as raw SVG in the markdown prompt or stripped via regex `re.sub(r'<svg[\s\S]*?</svg>', '', prompt).strip()`. The prompt question text itself is fully preserved regardless.
2. **Language Tag for Code Blocks**: In sqldpass's raw markdown, some code blocks use unadorned triple backticks (```` ``` ````) or ```` ```text ````. To satisfy acceptance criterion 37, the crawler should normalize these to ```` ```r ````:
   `prompt = re.sub(r'```(?:text)?\n', '```r\n', prompt)`.
3. **Round 38 and Round 40 Question Counts**: Round 38 has 49 questions (Q50 is absent on sqldpass), and Round 40 has 49 questions. Total questions harvested is 748, which comfortably exceeds the minimum acceptance requirement of 740.

---

## 4. Conclusion & Recommended Parsers

### Final Schema Mapping
For every question $i \in [1, N]$:
```json
{
  "question_no": int,        // 1 to 50
  "question_type": str,      // "4지선다" or "단답형"
  "prompt": str,             // GFM table & ```r code block preserved
  "options": list[str],      // 4 strings for 4지선다, [] for 단답형
  "answer": str              // e.g. "2" for 4지선다, "SCM" for 단답형
}
```

### Complete Production-Ready Extraction Implementation

```python
import re
import json
from bs4 import BeautifulSoup

def parse_adsp_post(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('li.rounded-2xl')
    
    # 1. Extract Flight Text Chunks & Prompts
    f_matches = re.findall(r'self\.__next_f\.push\(\[(\d+),\s*"((?:[^"\\]|\\.)*)"\]\)', html)
    combined = ''.join(json.loads(f'"{c}"') for _, c in f_matches)
    
    # Build text chunk reference dictionary (hex-safe)
    text_chunks = {}
    for m in re.finditer(r'(?:^|\n)([0-9a-fA-F]+):T[0-9a-fA-F]+,(.*?)(?=(?:\n[0-9a-fA-F]+:|\Z))', combined, re.DOTALL):
        text_chunks[f"${m.group(1)}"] = m.group(2)
        
    # Extract flight prompts
    prompt_pattern = r'\["\$","div",null,\{"className":"mt-3","children":\["\$","\$L[0-9a-zA-Z]+",null,\{"content":"(.*?)"(?:,"variant":"pastExam")?\}\]\}\]'
    raw_prompts = re.findall(prompt_pattern, combined)
    
    questions = []
    for idx, it in enumerate(items):
        # 1. Question Number
        num_el = it.select_one('p.tabular-nums')
        q_no_m = re.search(r'\d+', num_el.get_text(strip=True) if num_el else '')
        q_no = int(q_no_m.group()) if q_no_m else idx + 1
        
        # 2. Question Type
        badge = it.select_one('div.flex.items-center.justify-between span')
        q_type_raw = badge.get_text(strip=True) if badge else ""
        q_type = "단답형" if "단답" in q_type_raw else "4지선다"
        
        # 3. Prompt (with flight resolution & ```r normalization)
        if idx < len(raw_prompts):
            p_raw = raw_prompts[idx]
            try:
                prompt_val = json.loads(f'"{p_raw}"')
            except Exception:
                prompt_val = p_raw
            if prompt_val.startswith('$') and prompt_val in text_chunks:
                prompt_val = text_chunks[prompt_val]
        else:
            # Fallback to DOM if flight missing
            p_div = it.select_one('div.mt-3')
            prompt_val = p_div.get_text(strip=True) if p_div else ""
            
        # Ensure ```r code fence
        prompt_val = re.sub(r'```(?:text)?\n', '```r\n', prompt_val)
        
        # 4. Options
        options = []
        if q_type == "4지선다":
            for li in it.select('ul.mt-4 > li'):
                span = li.select_one('span.min-w-0')
                opt_txt = span.get_text(strip=True) if span else li.get_text(strip=True)
                options.append(opt_txt.strip())
                
        # 5. Answer Key
        ans_el = it.select_one('details p.text-base.font-semibold.text-success')
        raw_ans = ans_el.get_text(strip=True) if ans_el else ""
        if q_type == "4지선다":
            ans_m = re.search(r'\d+', raw_ans)
            ans = ans_m.group() if ans_m else raw_ans.strip()
        else:
            ans = raw_ans.strip()
            
        questions.append({
            "question_no": q_no,
            "question_type": q_type,
            "prompt": prompt_val.strip(),
            "options": options,
            "answer": ans
        })
        
    return questions
```

---

## 5. Verification Method

### Test Scripts Available in Scratch Directory
The following verification scripts have been executed and verified in `C:\Users\SSAFY\.gemini\antigravity\scratch`:

1. **Verify Flight Prompt Resolution across All 15 Rounds**:
   `python C:\Users\SSAFY\.gemini\antigravity\scratch\verify_flight_resolution.py`
   - Verified: 748 prompts harvested, 100% matched, 0 unresolved references.
2. **Verify Answer Key Extraction across Rounds**:
   `python C:\Users\SSAFY\.gemini\antigravity\scratch\verify_answers.py`
   - Verified: 100% answer extraction without a single missing value.
3. **Verify Options Count across All Rounds**:
   `python C:\Users\SSAFY\.gemini\antigravity\scratch\verify_options.py`
   - Verified: Exactly 4 options for 4지선다, exactly 0 options for 단답형.
4. **Verify Zero Explanation Text Leaks**:
   `python C:\Users\SSAFY\.gemini\antigravity\scratch\verify_no_explanation_leaks.py`
   - Verified: 748 questions checked, 0 occurrences of "오답 풀이", "보충 개념", or "정답·해설 보기".

### Invalidation Conditions
- If sqldpass changes their Next.js build module IDs or switches to client-side-only rendering without RSC stream.
- If class names on `li.rounded-2xl` or `p.text-base.font-semibold.text-success` are altered.
