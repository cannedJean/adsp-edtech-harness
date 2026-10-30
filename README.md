# ADsP Top-Down Multi-Agent Adaptive Learning Harness (`adsp-edtech-harness`)

국가공인 **ADsP(데이터분석 준전문가)** 자격증 기출 데이터셋(`adsp_crawler/data/adsp_all.json`, 15개 회차 총 748문항)을 기반으로 설계된 **하향식(Top-Down) 멀티 에이전트 적응형 학습 하네스**입니다.

---

## 📚 문서 및 진행 중인 학습 기록 (In-Progress Study State)

- **[심층 학술 리서치 보고서 (`docs/DEEP_RESEARCH_REPORT.md`)](docs/DEEP_RESEARCH_REPORT.md)**: 뇌과학, 교육공학, 데이터 분석, 데이터 엔지니어링, 계량심리학(IRT/BKT/FSRS-6/Brier Score) 기반 하네스 아키텍처 설계 보고서 (116개 학술 문헌 기반)
- **[제50회 기출 학습 진행 현황 리포트 (`docs/LEARNING_PROGRESS_R50.md`)](docs/LEARNING_PROGRESS_R50.md)**: `R50-Q01` ~ `R50-Q31` 문항별 풀이 정오표, 2×2 메타인지 사분면(`MASTERED`, `LUCKY_GUESS_CONFUSED`, `ILLUSION_OF_COMPETENCE`, `KNOWN_UNKNOWN`), 자동 생성 오답 노트 및 개념별 BKT/IRT/FSRS-6 숙달도
- **[제50회 인터랙티브 소크라테스 학습 대화록 (`docs/SESSION_TRANSCRIPT_R50.md`)](docs/SESSION_TRANSCRIPT_R50.md)**: `agy` CLI에서 진행한 양방향 문답 및 핵심 개념 복습 전체 로그
- **실시간 학습자 상태 DB 및 이벤트 스토어**:
  - `adsp_harness/data/learner_state.db` (SQLite ACID 상태 저장소)
  - `adsp_harness/data/learner_events.jsonl` (Append-only 이벤트 소싱 로그)

---

## 🚀 학습 이어하기 (`R50-Q32`부터 재개)

```powershell
# AGY CLI 실행 (권한 프롬프트 자동 허용 설정 완료)
agy --model gemini-3.8-flash-high

# 또는 단일 문항 즉시 조회 및 채점 CLI
python -m adsp_harness.cli show --round 50 --qno 32
python -m adsp_harness.cli submit --item R50-Q32 --ans <정답번호> --conf <확신도1~4>

# Phase 2 전역 취약점 & 메타인지(Brier/ECE) & 몬테카를로 합격/과락 시뮬레이션
python -m adsp_harness.cli phase2

# Phase 3 최신 기출(46~50회) 동향 외삽 기반 신유형(OOD) 백신 훈련
python -m adsp_harness.cli phase3 --count 5
```

---

## 🏗️ 프로젝트 구조

- `adsp_crawler/`: ADsP 15개 회차(32~50회, 총 748문항) 크롤러 및 정규화 데이터셋 (`adsp_all.json`)
- `adsp_harness/`:
  - `knowledge_graph.py`: 748문항 × 28개 핵심 개념 Q-Matrix 이분 그래프 및 46~50회 개념 표류(Concept Drift) 감지기
  - `psychometrics.py`: 3PL IRT, BKT + FSRS-6 망각 곡선 결합 모델, Murphy Brier 3분해 및 5,000회 베이지안 몬테카를로 합격·과락 시뮬레이터
  - `telemetry.py`: SQLite + JSONL 이벤트 스토어, 오답 원인 분류(Error Taxonomy), 공발생 클러스터링 및 Phase Gate 판정기
  - `quota_router.py`: Antigravity Language Server RPC 기반 실시간 모델 토큰 잔량 조회 및 이종 멀티 에이전트 라우터
  - `agents.py` & `orchestrator.py`: `AutoErrorNoteAgent`, `SocraticTutorAgent`, `WeaknessAnalyzerAgent`, `OODTrendGeneratorAgent`, `PsychometricCriticAgent` 오케스트레이션
  - `cli.py`: `quota`, `show`, `submit`, `phase1`, `phase2`, `phase3`, `demo` CLI 인터페이스
- `.agents/`: Antigravity 커스텀 플러그인, 4대 학습 스킬(`SKILL.md`), 서브에이전트 정의

