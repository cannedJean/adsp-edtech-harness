---
name: adsp-phase1-topdown-loop
description: >-
  Use this skill when the user wants to run Phase 1 of the ADsP Top-Down Learning Harness:
  solving past exam questions (Rounds 32-50), capturing retrospective confidence (RCJ 1-4),
  auto-generating structured error notes (via Gemini 3.8 Flash), conducting 2-turn Socratic
  Q&A on wrong or lucky-guess/confused items (via Claude Sonnet 5.5), and scheduling FSRS-6/IRT
  adaptive re-testing.
---

# ADsP Phase 1: 하향식 기출 풀이 & 양방향 오답·혼동 개념 정복 루프

이 스킬은 이론 선행 없이 기출문제를 먼저 풀고(Pretesting Effect & Productive Failure), 틀린 문제(`Q3`, `Q4`)와 찍어서 맞힌 헷갈린 문제(`Q2`)를 자동 분류하여 오답 정리 시간을 85% 단축하면서 양방향 소크라테스 문답으로 학습 성과를 극대화합니다.

## 실행 절차 (Workflow)

1. **문항 제시 (Item Presentation)**:
   - [`adsp_harness/data/q_matrix_748.json`](file:///c:/Users/SSAFY/Desktop/ADsP/adsp_harness/data/q_matrix_748.json)에서 요청된 회차(예: 최신 50회부터 역순, 또는 학습자의 현재 $\theta$ 기준 피셔 정보량 최대 문항)를 로드하여 마크다운 표와 ````r ```` 코드 블록을 보존한 채 제시합니다.
2. **정답 및 확신도 동시 수집 (Response + RCJ Capture)**:
   - 학습자로부터 **선택한 정답 번호(1~4)**와 **확신도(1: 찍음 25%, 2: 헷갈림 50%, 3: 대체로 확신 75%, 4: 완전 확신 95%)**를 함께 입력받습니다.
3. **2×2 메타인지 사분면 분류 및 즉시 조치**:
   - `Q1 (MASTERED: 정답 + 확신도 3~4)`: 해설/오답노트 생략 후 즉시 다음 문항으로 이동하여 시간 절약.
   - `Q2 (LUCKY_GUESS_CONFUSED: 정답 + 확신도 1~2)`: **우연히 맞힌 혼동 문항**으로 플래그 지정.
   - `Q3 (ILLUSION_OF_COMPETENCE: 오답 + 확신도 3~4)`: **착각된 유능감(과교정 타겟)**으로 플래그 지정.
   - `Q4 (KNOWN_UNKNOWN: 오답 + 확신도 1~2)`: **기초 개념 미숙지**로 플래그 지정.
4. **초고속 자동 오답 노트 합성 (`AutoErrorNoteAgent` - Flash)**:
   - `Q2`, `Q3`, `Q4` 문항에 대해 학습자가 수동으로 필기할 필요 없이 **핵심 불변 원리(1줄) + 5대 함정 분류 + 선택지 vs 정답 1:1 대조표**를 자동 생성하여 SQLite(`learner_state.db`)에 저장합니다.
5. **2-턴 소크라테스 양방향 문답 및 교정 기록 (`SocraticTutorAgent` - Sonnet)**:
   - 일방적 해설 주입 대신, 왜 해당 보기가 매력적 함정이었는지 묻는 **Turn 1 소크라테스 질문**을 던지고, 학습자의 짧은 답변을 받아 **Turn 2 기억 각인 피드백**으로 마무리합니다.
   - 문답이 끝나는 즉시 반드시 `python -m adsp_harness.cli resolve --item <문항ID> --misconception "<학습자가 헷갈렸던 오개념>" --correction "<교정된 핵심 개념 및 선지 해설>"` 명령어를 실행하여 나중에 마스터 정리 노트를 생성할 때 교정 전/후 개념이 완벽히 반영되도록 DB에 기록합니다.
6. **CLI 실행 명령 (멀티라인 `python -c` 금지, 반드시 아래 단일 명령 사용)**:
   ```powershell
   # 특정 1문항 조회 (정답 숨김)
   python -m adsp_harness.cli show --round 50 --qno 1

   # 학습자 정답 및 확신도(1~4) 제출 + 실제 Flash 자동 오답노트 + 실제 Claude Sonnet 5.5 소크라테스 질문 생성
   python -m adsp_harness.cli submit --item R50-Q01 --ans 2 --conf 4

   # 학습자가 개념/수식 심층 질문을 던졌을 때 실제 Claude Opus 5.5 / Sonnet 5.5 호출 및 노트 자동 저장
   python -m adsp_harness.cli ask --item R50-Q01 --question "학습자의 질문 내용" --tier opus

   # 소크라테스 문답 종료 후 학습자의 오개념과 교정된 해설 DB 영구 기록
   python -m adsp_harness.cli resolve --item R50-Q01 --misconception "헷갈렸던 포인트" --correction "교정된 불변 개념 및 해설"

   # 학습한 전체 오답·혼동·교정 개념 마스터 노트 생성
   python -m adsp_harness.cli notes --output docs/MY_MASTER_STUDY_NOTE.md

   # 연속 문항 풀이
   python -m adsp_harness.cli phase1 --round 50 --limit 5
   ```

