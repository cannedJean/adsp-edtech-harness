# ADsP Top-Down Multi-Agent Adaptive Learning Harness (`AGENTS.md` / `GEMINI.md`)

이 워크스페이스는 국가공인 **ADsP(데이터분석 준전문가)** 자격증 기출 데이터셋([`adsp_crawler/data/adsp_all.json`](file:///c:/Users/SSAFY/Desktop/ADsP/adsp_crawler/data/adsp_all.json), 15개 회차 총 748문항)을 기반으로 설계된 **하향식(Top-Down) 멀티 에이전트 적응형 학습 하네스**입니다.

## 1. 핵심 교육공학·뇌과학·계량심리학 원칙

1. **하향식(Top-Down) 선행 인출 학습**:
   - 방대한 이론 암기보다 기출문제를 먼저 풀게 하여 **사전 테스트 효과(Pretesting Effect)**와 **생산적 실패(Productive Failure)**를 유도합니다.
2. **오답 정리 시간 단축 & 2-턴 소크라테스 양방향 문답 (Chi's ICAP Framework)**:
   - 학습자가 해설지를 베껴 쓰는 수동적 시간을 **자동 오답 노트 생성(`AutoErrorNoteAgent` - Gemini 3.8 Flash)**으로 즉시 단축(문항당 4분 절약)하고, 절약된 시간에 **2턴 이내의 짧은 소크라테스식 양방향 문답(`SocraticTutorAgent` - Claude Sonnet 5.5)**을 진행하여 도파민 보상예측오차(RPE)와 과교정 효과(Hypercorrection)를 극대화합니다.
3. **2×2 메타인지 매트릭스 및 확신도 가중 채점 (Confidence-Weighted Scoring)**:
   - 모든 문항 풀이 시 정답 번호와 함께 **확신도(1: 찍음/모름 25%, 2: 헷갈림 50%, 3: 대체로 확신 75%, 4: 완전 확신 95%)**를 함께 수집합니다:
     - `Q1: MASTERED` (정답 + 고확신): 즉시 통과 (장기 복습 주기 편입)
     - `Q2: LUCKY_GUESS_CONFUSED` (정답 + 저확신): **찍어서 맞힌 헷갈린 문제** — 반드시 추가 학습 큐에 편입하여 고민했던 오답 선지와의 변별 기준을 확립합니다.
     - `Q3: ILLUSION_OF_COMPETENCE` (오답 + 고확신): **착각된 유능감 / 오개념** — 최우선 과교정(Hypercorrection) 타겟으로 소크라테스 반문을 수행합니다.
     - `Q4: KNOWN_UNKNOWN` (오답 + 저확신): 핵심 불변 개념 요약(Core Invariant) 제공 후 확인 질문을 수행합니다.
4. **데이터 기반 전역 취약점 분석 및 과락(40%) 통제**:
   - 학습자의 주관적 느낌에 의존하지 않고 **5대 오답 유형(`POLARITY_TRAP`, `QUANTIFIER_TRAP`, `CONCEPT_SWAP`, `TABLE_CALC_ERROR`, `R_OUTPUT_MISREAD`)**, **Q-Matrix 선수 개념 결함 네트워크**, **Murphy Brier 3분해($\text{REL}, \text{RES}, \text{UNC}$) 및 $\text{ECE}$**, 그리고 **베이지안 몬테카를로 합격·과락 시뮬레이션(총점 60점 & 과목별 40% 과락 기준)**으로 학습을 통제합니다.
5. **최신 기출 트렌드 외삽 및 신유형(OOD) 인지부조화 백신**:
   - 제46~50회 최신 기출의 개념 표류(Concept Drift: `SMOTE`, `Elastic Net`, `ESD`, `GMM`, `SECI`, `MLP 활성화 함수`, `ANOVA/회귀 결과표 역산` 등)를 바탕으로 기출에 없던 신유형을 생성·검증(`OODTrendGeneratorAgent` - Claude Opus 5.5 & `PsychometricCriticAgent` - Gemini 4 Argon)하고, **스트레스 접종(SIT) 소거법 프로토콜**을 훈련하여 시험장에서 신유형을 만났을 때 발생하는 인지부조화를 차단합니다.

## 2. 이종(Heterogeneous) 멀티 에이전트 토큰 최적화 라우팅 규칙

하네스 실행 시 [`adsp_harness/quota_router.py`](file:///c:/Users/SSAFY/Desktop/ADsP/adsp_harness/quota_router.py)를 통해 실시간 잔여 토큰(Quota)을 확인하고 역할을 분담합니다:
- **Gemini 3.8 Flash (`gemini-3.8-flash-high`)**: 초고속 오답 노트 자동 합성, 5대 오류 유형 태깅, 빠른 복습 퀴즈 채점
- **Claude Sonnet 5.5 (`claude-sonnet-5-5-high`)**: 양방향 소크라테스 튜터링(Phase 1) 및 메타인지 보정 코칭(Phase 2)
- **Claude Opus 5.5 (`claude-opus-5-5-high`)**: 전역 오답 공발생 근본 원인 진단(Phase 2) 및 고난도 신유형(OOD) 문항 설계(Phase 3)
- **Gemini 4 Argon (`gemini-4-argon-high`) / GPT-OSS 120B**: 메인 오케스트레이션, 통계/R코드 수리 검증, 신유형 문항 블라인드 교차 검증(Psychometric Critic)

## 3. CLI 빠른 실행 명령어 및 에이전트 실행 규칙

- **불필요한 멀티라인 `python -c` 지양**: 기출 데이터 조회나 채점·진단 시 매번 긴 멀티라인 `python -c "..."` 스크립트를 새로 짜서 권한 확인(Permission Prompt)을 유발하지 말고, 이미 구축된 `python -m adsp_harness.cli` 명령어나 단일 라인 명령어를 사용하십시오.

```powershell
# 실시간 모델별 잔여 토큰(Quota) 및 에이전트 라우팅 매트릭스 확인
python -m adsp_harness.cli quota

# 단일 문항 조회 및 채점 (대화형 1문항 루프)
python -m adsp_harness.cli show --round 50 --qno 32
python -m adsp_harness.cli submit --item R50-Q32 --ans 2 --conf 4

# 소크라테스 문답 완료 후 학습자의 오개념(misconception)과 교정된 개념(correction) DB 영구 기록 (필수!)
python -m adsp_harness.cli resolve --item R50-Q32 --misconception "학습자가 헷갈렸던 오개념 요약" --correction "교정된 핵심 불변 원리 및 해설 요약"

# "내가 학습한 내용들 전부 정리된 노트 생성해줘" 요청 시 개인 맞춤형 마스터 정리 노트 자동 생성
python -m adsp_harness.cli notes --output docs/MY_MASTER_STUDY_NOTE.md

# Phase 1: 하향식 기출 풀이 + 자동 오답노트 + 소크라테스 문답 (대화형 또는 시뮬레이션)
python -m adsp_harness.cli phase1 --round 50 --limit 5

# Phase 2: 전역 취약점 데이터 분석 + 메타인지(Brier/ECE) 진단 + 몬테카를로 합격/과락 시뮬레이션
python -m adsp_harness.cli phase2

# Phase 3: 최신 기출 동향(46~50회) 외삽 기반 신유형(OOD) 생성 및 인지부조화 백신 훈련
python -m adsp_harness.cli phase3 --count 5

# 전 과정(Phase 1 -> Phase 2 -> Phase 3) 엔드투엔드 데모 및 리포트 생성
python -m adsp_harness.cli demo
```

