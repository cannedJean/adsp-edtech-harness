---
name: adsp-phase3-ood-vaccine
description: >-
  Use this skill when the user wants to run Phase 3 of the ADsP Learning Harness:
  analyzing recent past exam trends (Rounds 46-50 concept drift), generating and verifying
  novel Out-of-Distribution (OOD) exam questions (via Claude Opus 5.5 Generator + Gemini 4 Argon
  Psychometric Critic), and training with Meichenbaum's Stress Inoculation (SIT) & Marton's
  Variation Theory protocols to eliminate exam-day cognitive dissonance.
---

# ADsP Phase 3: 최신 기출 동향 외삽 & 신유형(OOD) 인지부조화 백신 루프

기출문제 암기만으로는 대비할 수 없는 차기 시험의 신유형(OOD)을 최신 회차(46~50회)의 개념 표류(Concept Drift) 데이터로부터 외삽하여 생성하고, 시험장에서 낯선 문항을 만났을 때 발생하는 인지부조화(Cognitive Dissonance)와 작업기억 마비를 통제합니다.

## 실행 절차 (Workflow)

1. **최신 회차(46~50회) 개념 표류 시그널 로드**:
   - [`adsp_harness/data/concept_drift_report.json`](file:///c:/Users/SSAFY/Desktop/ADsP/adsp_harness/data/concept_drift_report.json)에서 최근 급부상한 토픽(`SMOTE/불균형 데이터`, `Elastic Net/glmnet`, `ESD vs IQR 이상치 탐지`, `ANOVA/회귀 출력표 빈칸 역산`, `k-익명성/l-다양성/t-근접성`, `MLP 활성화 함수`, `GMM/DBSCAN`)과 학습자의 취약 개념을 교차 선택합니다.
2. **삼중 에이전트 신유형 생성 및 무결성 검증 (`OODTrendGeneratorAgent` + `PsychometricCriticAgent`)**:
   - **Generator (`Claude Opus 5.5`)**: Marton의 변이 이론(Contrast, Generalization, Fusion)을 적용하여 기출에 없던 고난도 융합 신유형 4지선다 문항을 생성합니다.
   - **Critic (`Gemini 4 Argon` / `GPT-OSS 120B`)**: 블라인드 풀이로 단일 정답 무결성을 검증하고, 3PL IRT 난이도·변별도를 추정합니다.
3. **스트레스 접종 훈련 (SIT Cognitive Vaccine Protocol)**:
   - 학습자가 신유형 문항을 풀이한 직후, 시험장에서 처음 보는 용어나 복잡한 표를 마주했을 때 **10초 안에 핵심 불변 원리와 한정어 단서로 오답 3개를 소거하는 실전 행동 프로토콜**을 훈련시킵니다.
4. **CLI 실행 명령**:
   ```powershell
   python -m adsp_harness.cli phase3 --count 5
   ```

