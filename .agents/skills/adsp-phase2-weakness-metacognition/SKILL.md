---
name: adsp-phase2-weakness-metacognition
description: >-
  Use this skill when the user wants to run Phase 2 of the ADsP Learning Harness:
  analyzing cumulative error patterns across completed past exams, tracing root-cause
  prerequisite deficits via the Q-Matrix bipartite graph, auditing metacognitive calibration
  (Murphy's Brier Score 3-component decomposition and ECE), reviewing confused/high-confidence-error
  decks, and running the Bayesian Monte Carlo ADsP pass & 40% subject cutoff risk simulation.
---

# ADsP Phase 2: 데이터 기반 전역 취약점 분석 & 메타인지 교정 루프

기출문제 풀이 데이터가 축적된 후, 학습자 스스로 분석할 때 발생하는 시간 소모와 주관적 편향을 제거하고 계량심리학 및 학습 분석 데이터에 근거해 취약점과 메타인지를 교정합니다.

## 실행 절차 (Workflow)

1. **5대 오답 메커니즘 정량 프로파일링**:
   - `POLARITY_TRAP` (부정형 발문 실수), `QUANTIFIER_TRAP` (극단적 한정어 함정), `CONCEPT_SWAP` (대칭 개념 혼동), `TABLE_CALC_ERROR` (분할표·ANOVA·수식 계산 오류), `R_OUTPUT_MISREAD` (R 통계 출력 해독 오류) 비중을 산출합니다.
2. **문항-개념 이분 그래프(Q-Matrix) 기반 근본 취약점 역추적 (`WeaknessRootCauseAgent` - Opus)**:
   - 표면적으로 많이 틀린 문항들의 공발생 네트워크와 선수 학습 DAG를 분석하여 가장 시급히 보완해야 할 **Root-Cause 취약 개념 Top 5**를 도출합니다.
3. **메타인지 보정도 진단 (`MetacognitionCalibratorAgent` - Sonnet/Argon)**:
   - Murphy의 Brier Score 3분해($\text{BS} = \text{REL} - \text{RES} + \text{UNC}$), $\text{ECE}$, 과신 지수($\text{OCI}$)를 산출하고, 그동안 누적된 **`Q3 (착각된 유능감)` 과교정 덱**과 **`Q2 (찍어서 맞힌 혼동 문제)` 재정리 덱**을 추출하여 집중 복습시킵니다.
4. **베이지안 몬테카를로 합격 확률 및 과목별 과락 위험도(40% 컷) 시뮬레이션**:
   - 5,000회 몬테카를로 시뮬레이션을 통해 예상 총점, 합격 확률 $P(\text{Pass})$, 그리고 과목별 과락 확률 $P(S_1 < 8), P(S_2 < 8), P(S_3 < 24)$을 정밀 보고합니다.
5. **CLI 실행 명령**:
   ```powershell
   python -m adsp_harness.cli phase2
   ```

