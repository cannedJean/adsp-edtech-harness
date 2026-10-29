"""Mock HTML, flight payloads, and datasets for ADsP crawler E2E test suite.

Authoritative source:
- ORIGINAL_REQUEST.md
- PROJECT.md
- Survey handoffs (spec_miner_survey_1, explorer_survey_2, explorer_survey_3)
"""

import json
import re

MOCK_HUB_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>ADsP 기출문제 및 수험자료 | 문어CBT</title>
</head>
<body class="bg-background text-foreground">
  <header>
    <h1>ADsP 기출문제</h1>
    <p class="mt-2 text-base text-text-muted">35개의 글</p>
  </header>
  <main>
    <!-- Top Featured Hero Card (Round 50) -->
    <section class="featured">
      <a href="/blog/past-exam/adsp-2026-50" class="hero-link">
        <h2>2026년 ADsP 50회 기출 복원</h2>
      </a>
    </section>

    <!-- Grid: 14 other exam rounds -->
    <section class="past-exams">
      <a href="/blog/past-exam/adsp-2026-49">2026년 ADsP 49회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2026-48">2026년 ADsP 48회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2025-47">2025년 ADsP 47회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2025-46">2025년 ADsP 46회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2025-45">2025년 ADsP 45회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2025-44">2025년 ADsP 44회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2024-42">2024년 ADsP 42회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2024-41">2024년 ADsP 41회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2024-40">2024년 ADsP 40회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2023-39">2023년 ADsP 39회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2023-38">2023년 ADsP 38회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2023-37">2023년 ADsP 37회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2022-35">2022년 ADsP 35회 기출 복원</a>
      <a href="/blog/past-exam/adsp-2022-32">2022년 ADsP 32회 기출 복원</a>
    </section>

    <!-- Non-exam noise links (must be ignored by discovery) -->
    <section class="guides">
      <a href="/blog/general/adsp-43-preparation">ADsP 43회 수험 가이드</a>
      <a href="/blog/concept/data-governance">데이터 거버넌스 체계 정리</a>
      <a href="/blog/strategy/study-tips">3주 완성 ADsP 합격 전략</a>
      <a href="/blog/reviews/2026-exam-review">ADsP 시험 후기 모음</a>
    </section>
  </main>
</body>
</html>
"""


def _generate_question_html(
    q_no: int,
    q_type: str = "4지선다",
    prompt_text: str = "다음 설명 중 가장 타당한 것은?",
    options: list[str] = None,
    answer_raw: str = "2<!-- -->번",
    has_table: bool = False,
    has_bailout_code: bool = False,
    has_svg: bool = False,
) -> str:
    """Generate realistic sqldpass DOM markup for a single question."""
    if options is None and q_type == "4지선다":
        options = [
            f"선택지 1번 내용 for Q{q_no}",
            f"선택지 2번 내용 for Q{q_no}",
            f"선택지 3번 내용 for Q{q_no}",
            f"선택지 4번 내용 for Q{q_no}",
        ]

    table_html = ""
    if has_table:
        table_html = """
        <div aria-label="문항 표" class="my-4 overflow-x-auto overscroll-x-contain" role="region" tabindex="0">
          <table class="w-max min-w-full border-collapse border border-zinc-500 bg-white text-left font-sans text-sm text-zinc-950">
            <thead class="bg-zinc-100 text-zinc-950">
              <tr>
                <th class="border border-zinc-500 px-3 py-2 font-semibold">요인</th>
                <th class="border border-zinc-500 px-3 py-2 font-semibold">제곱합</th>
                <th class="border border-zinc-500 px-3 py-2 font-semibold">자유도</th>
                <th class="border border-zinc-500 px-3 py-2 font-semibold">평균제곱</th>
                <th class="border border-zinc-500 px-3 py-2 font-semibold">F</th>
                <th class="border border-zinc-500 px-3 py-2 font-semibold">p-value</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="border border-zinc-500 px-3 py-2">회귀</td>
                <td class="border border-zinc-500 px-3 py-2">100</td>
                <td class="border border-zinc-500 px-3 py-2">1</td>
                <td class="border border-zinc-500 px-3 py-2">( )</td>
                <td class="border border-zinc-500 px-3 py-2">( )</td>
                <td class="border border-zinc-500 px-3 py-2">3.41e-05</td>
              </tr>
              <tr>
                <td class="border border-zinc-500 px-3 py-2">잔차</td>
                <td class="border border-zinc-500 px-3 py-2">( )</td>
                <td class="border border-zinc-500 px-3 py-2">10</td>
                <td class="border border-zinc-500 px-3 py-2">( )</td>
                <td class="border border-zinc-500 px-3 py-2"></td>
                <td class="border border-zinc-500 px-3 py-2"></td>
              </tr>
              <tr>
                <td class="border border-zinc-500 px-3 py-2">합계</td>
                <td class="border border-zinc-500 px-3 py-2">120</td>
                <td class="border border-zinc-500 px-3 py-2">11</td>
                <td class="border border-zinc-500 px-3 py-2"></td>
                <td class="border border-zinc-500 px-3 py-2"></td>
                <td class="border border-zinc-500 px-3 py-2"></td>
              </tr>
            </tbody>
          </table>
        </div>
        """

    code_html = ""
    if has_bailout_code:
        code_html = """
        <pre><!--$!--><template data-dgst="BAILOUT_TO_CLIENT_SIDE_RENDERING"></template><div class="my-3 h-24 rounded-lg border border-zinc-800 bg-zinc-900/60 animate-pulse"></div><!--/$--></pre>
        """

    svg_html = ""
    if has_svg:
        svg_html = """
        <svg class="w-full h-32" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="40" stroke="black" stroke-width="2" fill="none" />
        </svg>
        """

    options_html = ""
    if q_type == "4지선다" and options:
        opt_items = []
        for i, opt in enumerate(options, 1):
            opt_items.append(f"""
            <li class="flex items-start gap-2 rounded-md border border-border bg-bg px-3 py-2 text-sm">
              <span class="font-semibold tabular-nums">{i}<!-- -->.</span>
              <span class="min-w-0 flex-1">
                <div class="question-md question-md-past-exam mcq-option">
                  <p class="my-2 text-sm leading-relaxed whitespace-pre-line break-words">{opt}</p>
                </div>
              </span>
            </li>
            """)
        options_html = f"""<ul class="mt-4 space-y-1.5">{''.join(opt_items)}</ul>"""

    ans_label = "정답" if q_type == "4지선다" else "모범답안"

    return f"""
    <li class="rounded-2xl border border-border bg-surface/40 p-5">
      <div class="flex items-center justify-between">
        <p class="text-xs font-semibold tabular-nums text-text-muted">문제 <!-- -->{q_no}</p>
        <span class="text-[10px] font-medium uppercase tracking-wider text-text-subtle">{q_type}</span>
      </div>
      <div class="mt-3">
        <div class="question-md question-md-past-exam">
          <p class="my-2 text-sm leading-relaxed whitespace-pre-line break-words">{prompt_text}</p>
          {table_html}
          {code_html}
          {svg_html}
        </div>
      </div>
      {options_html}
      <details class="mt-4 group">
        <summary class="cursor-pointer select-none rounded-md px-3 py-2 text-xs font-medium text-text-muted hover:bg-surface-hover">
          정답·해설 보기
          <span class="ml-2 text-xs">▾</span>
        </summary>
        <div class="mt-3 space-y-3 rounded-md border border-border bg-bg p-4 text-sm">
          <div>
            <p class="text-xs font-semibold text-text-muted">{ans_label}</p>
            <p class="mt-1 text-base font-semibold text-success">{answer_raw}</p>
          </div>
          <div>
            <p class="text-xs font-semibold text-text-muted">해설</p>
            <div class="mt-1 leading-relaxed">
              <div class="question-md question-md-past-exam">
                <p>정답 상세 풀이 내용입니다.</p>
                <p><strong class="font-semibold text-foreground">오답 풀이</strong></p>
                <ul class="my-2 ml-5 list-disc space-y-1 text-sm">
                  <li>오답 1: 잘못된 접근입니다.</li>
                  <li>오답 2: 정의가 부합하지 않습니다.</li>
                </ul>
                <p><strong class="font-semibold text-foreground">보충 개념</strong></p>
                <p>참고 관련 기본 핵심 개념 정리입니다.</p>
              </div>
            </div>
          </div>
        </div>
      </details>
    </li>
    """


def generate_round_50_html() -> str:
    """Generate Round 50 SSR HTML with 50 questions, ANOVA table in Q25, R code in Q26."""
    items = []
    flight_chunks = []

    for q in range(1, 51):
        if q == 25:
            # ANOVA Table
            prompt_text = "다음은 단순선형회귀분석 결과로 얻은 분산분석표이다. 빈칸 ( )을 채워 해석한 내용으로 옳지 않은 것은?"
            items.append(_generate_question_html(
                q_no=25,
                q_type="4지선다",
                prompt_text=prompt_text,
                answer_raw="3<!-- -->번",
                has_table=True,
            ))
            flight_markdown = (
                "다음은 단순선형회귀분석 결과로 얻은 분산분석표이다. 빈칸 ( )을 채워 해석한 내용으로 옳지 않은 것은?\n\n"
                "| 요인 | 제곱합 | 자유도 | 평균제곱 | F | p-value |\n"
                "|---|---:|---:|---:|---:|---:|\n"
                "| 회귀 | 100 | 1 | ( ) | ( ) | 3.41e-05 |\n"
                "| 잔차 | ( ) | 10 | ( ) |  |  |\n"
                "| 합계 | 120 | 11 |  |  |  |"
            )
            flight_chunks.append(flight_markdown)

        elif q == 26:
            # R Code block PCA summary
            prompt_text = "다음은 표준화한 자료에 주성분분석을 수행한 결과 중 PC1부터 PC7까지를 옮긴 것이다. 해석으로 옳지 않은 것은?"
            items.append(_generate_question_html(
                q_no=26,
                q_type="4지선다",
                prompt_text=prompt_text,
                answer_raw="4<!-- -->번",
                has_bailout_code=True,
            ))
            flight_markdown = (
                "다음은 표준화한 자료에 주성분분석을 수행한 결과 중 PC1부터 PC7까지를 옮긴 것이다. 해석으로 옳지 않은 것은?\n\n"
                "```\n"
                "> pca <- prcomp(X, scale. = TRUE)\n"
                "> summary(pca)\n"
                "Importance of components:\n"
                "                          PC1    PC2    PC3     PC4     PC5     PC6    PC7\n"
                "Standard deviation     2.0494 1.4491 1.0000 0.89443 0.77460 0.67082 0.6000\n"
                "Proportion of Variance 0.4200 0.2100 0.1000 0.08000 0.06000 0.04500 0.0360\n"
                "Cumulative Proportion  0.4200 0.6300 0.7300 0.81000 0.87000 0.91500 0.9510\n"
                "```"
            )
            flight_chunks.append(flight_markdown)

        elif q == 34:
            # SVG diagram
            prompt_text = "다음 ROC 곡선 그래프에 대한 설명으로 옳은 것을 고르시오."
            items.append(_generate_question_html(
                q_no=34,
                q_type="4지선다",
                prompt_text=prompt_text,
                answer_raw="1<!-- -->번",
                has_svg=True,
            ))
            flight_markdown = prompt_text
            flight_chunks.append(flight_markdown)

        else:
            prompt_text = f"ADsP 50회 {q}번 문제입니다. 다음 설명 중 알맞은 것을 고르시오."
            items.append(_generate_question_html(
                q_no=q,
                q_type="4지선다",
                prompt_text=prompt_text,
                answer_raw=f"{(q % 4) + 1}<!-- -->번",
            ))
            flight_markdown = prompt_text
            flight_chunks.append(flight_markdown)

    # Build Next.js flight payload chunk push statements
    flight_pushes = []
    for chunk in flight_chunks:
        escaped_chunk = json.dumps(chunk)[1:-1]
        payload = (
            f'["$","div",null,{{"className":"mt-3","children":["$","$L21",null,'
            f'{{"content":"{escaped_chunk}","variant":"pastExam"}}]}}]'
        )
        clean_payload = payload.replace('"', '\\"')
        flight_pushes.append(
            f'<script>self.__next_f.push([1, "{clean_payload}"])</script>'
        )

    # Reference resolution chunk test ($51)
    ref_push = (
        '<script>self.__next_f.push([1, '
        '"51:T20,참조형 텍스트 청크 내용입니다."])</script>'
    )

    body_content = "\n".join(items)
    flight_scripts = "\n".join(flight_pushes) + "\n" + ref_push

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>2026년 ADsP 50회 기출 복원 전문 50문항</title>
</head>
<body>
  <h1>2026년 ADsP 50회 기출 복원 전문 50문항</h1>
  <ul class="space-y-4">
    {body_content}
  </ul>
  {flight_scripts}
</body>
</html>
"""


def generate_round_38_html() -> str:
    """Generate Round 38 HTML: 49 questions (missing Q50), 39 MCQs, 10 short answers."""
    items = []
    flight_chunks = []

    short_answers = {
        40: "IoT",
        41: "SCM",
        42: "하향식 접근 방법",
        43: "0.4",
        44: "57.5%",
        45: "1/5",
        46: "a / (a+b)",
        47: "데이터베이스",
        48: "군집분석",
        49: "1.2",
    }

    # Questions 1 to 49 only (Q50 is absent on sqldpass)
    for q in range(1, 50):
        if q < 40:
            prompt_text = f"ADsP 38회 {q}번 객관식 문제입니다."
            items.append(_generate_question_html(
                q_no=q,
                q_type="4지선다",
                prompt_text=prompt_text,
                answer_raw=f"{(q % 4) + 1}<!-- -->번",
            ))
        else:
            model_ans = short_answers[q]
            prompt_text = f"ADsP 38회 {q}번 단답형 문제입니다. 알맞은 용어나 수식을 작성하시오."
            items.append(_generate_question_html(
                q_no=q,
                q_type="단답형",
                prompt_text=prompt_text,
                options=[],
                answer_raw=model_ans,
            ))
        flight_chunks.append(prompt_text)

    flight_pushes = []
    for chunk in flight_chunks:
        escaped_chunk = json.dumps(chunk)[1:-1]
        payload = (
            f'["$","div",null,{{"className":"mt-3","children":["$","$L21",null,'
            f'{{"content":"{escaped_chunk}","variant":"pastExam"}}]}}]'
        )
        clean_payload = payload.replace('"', '\\"')
        flight_pushes.append(
            f'<script>self.__next_f.push([1, "{clean_payload}"])</script>'
        )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>2023년 ADsP 38회 문제·정답·해설 전문 49문항</title>
</head>
<body>
  <h1>2023년 ADsP 38회 문제·정답·해설 전문 49문항</h1>
  <ul class="space-y-4">
    {''.join(items)}
  </ul>
  {''.join(flight_pushes)}
</body>
</html>
"""


def generate_round_40_html() -> str:
    """Generate Round 40 HTML: 49 questions (missing Q50), 49 MCQs."""
    items = []
    flight_chunks = []

    for q in range(1, 50):
        prompt_text = f"ADsP 40회 {q}번 객관식 문제입니다."
        items.append(_generate_question_html(
            q_no=q,
            q_type="4지선다",
            prompt_text=prompt_text,
            answer_raw=f"{(q % 4) + 1}<!-- -->번",
        ))
        flight_chunks.append(prompt_text)

    flight_pushes = []
    for chunk in flight_chunks:
        escaped_chunk = json.dumps(chunk)[1:-1]
        payload = (
            f'["$","div",null,{{"className":"mt-3","children":["$","$L21",null,'
            f'{{"content":"{escaped_chunk}","variant":"pastExam"}}]}}]'
        )
        clean_payload = payload.replace('"', '\\"')
        flight_pushes.append(
            f'<script>self.__next_f.push([1, "{clean_payload}"])</script>'
        )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>2024년 ADsP 40회 문제·정답·해설 전문 49문항</title>
</head>
<body>
  <h1>2024년 ADsP 40회 문제·정답·해설 전문 49문항</h1>
  <ul class="space-y-4">
    {''.join(items)}
  </ul>
  {''.join(flight_pushes)}
</body>
</html>
"""


def generate_full_15_rounds_dataset() -> dict[int, list[dict]]:
    """Generate authoritative 748-question dataset across all 15 rounds for census testing."""
    target_rounds = [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]
    all_rounds_data = {}

    for r in target_rounds:
        q_count = 49 if r in (38, 40) else 50
        has_short_answer = r in (32, 35, 37, 38)
        round_questions = []

        for q in range(1, q_count + 1):
            if r == 38:
                is_short = has_short_answer and q >= 40
            else:
                is_short = has_short_answer and q >= 41
            if is_short:
                q_type = "단답형"
                options = []
                ans = f"정답용어_{r}_{q}"
            else:
                q_type = "4지선다"
                options = [
                    f"R{r}-Q{q} 보기 1번",
                    f"R{r}-Q{q} 보기 2번",
                    f"R{r}-Q{q} 보기 3번",
                    f"R{r}-Q{q} 보기 4번",
                ]
                ans = str((q % 4) + 1)

            prompt = f"ADsP {r}회 {q}번 문항 지문입니다."
            if r == 50 and q == 25:
                prompt += "\n\n| 요인 | 제곱합 |\n|---|---:|\n| 회귀 | 100 |"
            elif r == 50 and q == 26:
                prompt += "\n\n```r\n> summary(pca)\n```"

            round_questions.append({
                "question_no": q,
                "question_type": q_type,
                "prompt": prompt,
                "options": options,
                "answer": ans,
            })

        all_rounds_data[r] = round_questions

    return all_rounds_data
