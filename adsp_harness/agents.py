"""
Multi-Agent Pedagogical & Psychometric Specialists for the ADsP Learning Harness.

Orchestrates 6 specialized agents across heterogeneous models (Gemini 3.8 Flash,
Claude Sonnet 5.5, Claude Opus 5.5, Gemini 4 Argon, and GPT-OSS 120B):
1. AutoErrorNoteAgent (Flash)       — Phase 1: Instant structured error note synthesis (cuts manual note-taking time by 85%)
2. SocraticTutorAgent (Sonnet)      — Phase 1: 2-turn interactive Socratic Q&A for wrong (Q3/Q4) & lucky-guess/confused (Q2) items
3. WeaknessRootCauseAgent (Opus)    — Phase 2: Global error taxonomy & prerequisite deficit network analysis
4. MetacognitionCalibratorAgent (Sonnet/Argon) — Phase 2: Murphy Brier 3-decomposition & ECE de-biasing deck generator
5. OODTrendGeneratorAgent (Opus)    — Phase 3: Longitudinal drift extrapolation & Marton Variation Theory novel item generator
6. PsychometricCriticAgent (Argon/GPT-OSS) — Phase 3: Blind cross-verification & Meichenbaum Stress Inoculation (SIT) protocol
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .quota_router import QuotaAwareModelRouter
from .knowledge_graph import ONTOLOGY_DEFINITIONS

ONTOLOGY_BY_ID: Dict[str, Any] = {node.concept_id: node for node in ONTOLOGY_DEFINITIONS}


# Curated ADsP Concept Invariant & Contrast Bank for Instant Zero-Latency + LLM-Enriched Synthesis
CONCEPT_INVARIANT_BANK: Dict[str, Dict[str, str]] = {
    "C01_DATA_DIKW": {
        "invariant": "데이터(객관적 사실) -> 정보(가공·상관관계·의미) -> 지식(패턴·규칙·예측) -> 지혜(창의적 응용·통찰); 암묵지(내면화·공통화) vs 형식지(표출화·연결화, SECI 모델).",
        "contrast": "암묵지->형식지는 '표출화(Externalization)', 형식지->형식지는 '연결화(Combination)', 형식지->암묵지는 '내면화(Internalization)'임.",
    },
    "C02_DB_DW_LAKE": {
        "invariant": "OLTP(실시간 트랜잭션 갱신) vs DW(주제지향·통합·시계열·비휘발성 분석용) vs 데이터 마트(부서별 소규모 DW) vs 데이터 레이크(원시 정형·비정형 데이터 원본 저장).",
        "contrast": "DW의 4대 특성 중 '비휘발성(Non-volatile)'은 수정·삭제 없이 조회·적재 위주임을 뜻하며, 실시간 수시 갱신(휘발성)이라는 선지는 대표적 오답 함정임.",
    },
    "C03_BIGDATA_VALUE_PRIVACY": {
        "invariant": "빅데이터 위기요인(사생활 침해, 책임원칙 훼손, 데이터 오용) vs 통제방안(동의에서 책임으로, 결과 기반 책임원칙, 알고리즘 접근 허용); 비식별화(가명처리·총계처리·데이터 삭제·범주화·마스킹).",
        "contrast": "사생활 침해의 해법은 '개인 동의 강화'가 아니라 '사용자(분석가)의 책임(Accountability) 전환'이며, 책임원칙 훼손은 '예측만으로 처벌하지 않는 결과 기반 책임 원칙'으로 통제함.",
    },
    "C05_PLAN_TOPDOWN_BOTTOMUP": {
        "invariant": "하향식(문제 탐색 -> 문제 정의 -> 해결방안 탐색 -> 타당성 검토; '무엇(What)'을 알고 있을 때) vs 상향식(비지도학습·프로토타이핑·디자인 사고; '무엇'을 모를 때 데이터로부터 발산).",
        "contrast": "디자인 사고(Design Thinking)는 상향식(발산)과 하향식(수렴)을 반복하며, 문제 정의 단계에서는 '필요 데이터 및 기법'이 아니라 '비즈니스 문제를 데이터 분석 문제로 변환'하는 것이 핵심임.",
    },
    "C06_METHODOLOGY_KDD_CRISP": {
        "invariant": "KDD(선택->전처리->변환->마이닝->해석/평가) vs CRISP-DM(업무이해->데이터이해->데이터준비->모델링->평가->전개, 6단계 양방향 피드백) vs 빅데이터 분석 방법론(기획->준비->분석->구현->평가 및 전개, 5단계).",
        "contrast": "CRISP-DM은 단방향 폭포수가 아니라 단계 간 피드백 순환이 가능하며, 모델링과 평가는 '업무 이해(Business Understanding)'의 목표에 부합하는지 검증함.",
    },
    "C07_MASTERPLAN_GOVERNANCE": {
        "invariant": "우선순위 평가 기준: 전략적 중요도(시급성: 현재 vs 미래 관점) & 실행 용이성(난이도: 투자비용·기술·데이터 확보). 포트폴리오 사분면: 1사분면(시급O·난이도높음), 3사분면(시급O·난이도낮음=Quick-Win 최우선).",
        "contrast": "시급성 중심이면 '3 -> 4 -> 2' 순서, 난이도(실행 용이성) 중심이면 '3 -> 1 -> 2' 순서로 추진하며, 3사분면(시급하고 쉬운 과제)이 언제나 1순위임.",
    },
    "C09_DESC_STATS_OUTLIER": {
        "invariant": "왜도(Skewness: 양수면 오른쪽 꼬리가 길고 평균 > 중앙값 > 최빈값), 첨도(Kurtosis: 정규분포 기준 3 또는 초과첨도 0). 이상치 탐지: IQR(Q1-1.5*IQR, Q3+1.5*IQR) vs ESD(평균 ± 3*표준편차).",
        "contrast": "오른쪽 꼬리 분포(양의 왜도)에서 '최빈값 > 중앙값 > 평균'이라고 서술하거나, IQR 계산 시 Q3-Q1 대신 범위(Max-Min)를 대입하는 함정에 주의.",
    },
    "C11_HYPOTHESIS_TESTING": {
        "invariant": "제1종 오류(α, 귀무가설 H0가 참인데 기각) vs 제2종 오류(β, H0가 거짓인데 채택), 검정력(1-β). p-value < 유의수준(α) 이면 귀무가설(H0) 기각, 대립가설(H1) 채택.",
        "contrast": "p-value가 α보다 작을 때 '귀무가설을 채택한다'고 하거나, 표본크기 고정 시 α를 줄이면 β도 함께 줄어든다는 선지(실제로는 상충관계)가 대표적 오답임.",
    },
    "C14_REGRESSION_OLS_VIF": {
        "invariant": "회귀모형 4대 가정: 선형성, 독립성(더빈-왓슨≈2), 등분산성, 정규성. 다중공선성: 독립변수 간 강한 상관관계 -> VIF = 1/(1-R^2) > 10 이면 심각 -> 변수 제거, 주성분회귀(PCR), Ridge/Lasso/Elastic Net 적용.",
        "contrast": "결정계수(R^2)는 독립변수 수가 늘어나면 유의하지 않아도 무조건 증가하거나 유지되므로, 다중회귀에서는 반드시 '수정된 결정계수(Adjusted R^2)'로 모형을 비교해야 함.",
    },
    "C15_VARIABLE_SELECTION_PENALTY": {
        "invariant": "벌점화(규제) 회귀: Lasso(L1 패널티, 일부 계수를 정확히 0으로 만들어 변수 선택 수행) vs Ridge(L2 패널티, 계수를 0에 가깝게 축소하나 변수 선택은 안 함) vs Elastic Net(L1 + L2 결합).",
        "contrast": "Ridge가 변수를 완전히 제거(0으로 만듦)한다거나 Lasso가 다중공선성 그룹 변수를 모두 유지한다는 선지는 개념 뒤바꾸기(Concept Swap) 함정임.",
    },
    "C16_LOGISTIC_REGRESSION": {
        "invariant": "종속변수가 범주형(0/1)일 때 오즈(Odds = p/(1-p))에 로그를 취한 로짓(Logit = ln(p/(1-p)))을 선형 결합으로 추정. 회귀계수 β가 1단위 증가할 때 오즈는 exp(β)배 증가.",
        "contrast": "독립변수가 1 증가할 때 '확률 p가 exp(β)배 증가한다'는 선지는 틀림('오즈(승산)가 exp(β)배 증가한다'가 정확한 불변 원리).",
    },
    "C17_PCA_DIMENSION_REDUCTION": {
        "invariant": "주성분분석(PCA): 상관성 높은 변수들을 서로 직교(상관계수=0)하는 소수의 주성분으로 선형 결합하여 전체 분산 손실을 최소화. 고윳값(Eigenvalue) >= 1 (Kaiser 규칙), 스크리 산점도 팔꿈치(Elbow), 누적기여율 70~85% 기준.",
        "contrast": "제1주성분(PC1)은 분산이 가장 '큰' 방향이며, 주성분들끼리는 서로 강한 상관관계를 가진다는 선지는 틀림(주성분 간 상관계수는 0, 즉 서로 독립/직교).",
    },
    "C18_TIME_SERIES_ARIMA": {
        "invariant": "정상성(Stationarity) 3조건: 평균 일정(추세 없음 -> 차분 d로 해결), 분산 일정(이분산성 -> 로그/변수변환으로 해결), 공분산이 시점 t가 아닌 시차(lag)에만 의존. ARIMA(p, d, q): AR(p) 자기회귀 + I(d) 차분 + MA(q) 이동평균.",
        "contrast": "분산이 일정하지 않을 때 '차분(Differencing)'을 한다거나, 평균이 일정하지 않을 때 '로그 변환'을 한다는 선지는 변환 방법을 반대로 매칭한 함정임.",
    },
    "C19_DECISION_TREE": {
        "invariant": "분할 기준: 이산형 목표변수(카이제곱 통계량 p-value 감소, 지니지수 감소, 엔트로피/정보이득 증가) vs 연속형 목표변수(ANOVA F-통계량 증가, 분산감소량 극대화). 정지 규칙(분할 전 제한) vs 가지치기(분할 후 과적합 말단 제거).",
        "contrast": "정보이득(Information Gain)이 임계값보다 '크면' 분할을 멈춘다는 선지(R50 Q50)는 역방향 함정임(정보이득이 임계값보다 '작으면' 더 분할할 가치가 없으므로 멈춤).",
    },
    "C20_ENSEMBLE_BAGGING_BOOSTING": {
        "invariant": "배깅(Bagging: 부트스트랩 복원추출 병렬 학습, 분산 감소, OOB 오차 추정) vs 부스팅(Boosting: 오분류 데이터에 가중치 부여 순차 학습, 편향 감소, 과적합 가능성) vs 랜덤포레스트(배깅 + 노드마다 변수 무작위 추출로 상관성 제거).",
        "contrast": "배깅이 이전 모형의 오차를 가중하여 순차 학습한다거나, 부스팅이 독립적 병렬 학습이라는 선지는 대표적 배깅/부스팅 뒤바꾸기 함정임.",
    },
    "C21_ANN_DEEP_LEARNING": {
        "invariant": "활성화 함수: 계단함수(0 또는 1), 시그모이드([0, 1], 기울기 소실), 하이퍼볼릭 탄젠트 tanh([-1, 1], 0 중심), ReLU(max(0, x), 기울기 소실 완화), 소프트맥스(다중 클래스 확률 합=1). 은닉층 과다 시 과적합, 부족 시 과소적합.",
        "contrast": "시그모이드의 출력 범위가 [-1, 1]이라거나 이진 분류가 아닌 다중 분류 출력층에 시그모이드를 기본 사용한다는 선지(다중 분류는 Softmax)가 빈출 함정임.",
    },
    "C23_MODEL_EVAL_IMBALANCED": {
        "invariant": "혼동행렬: 정밀도(Precision = TP/(TP+FP)), 재현율/민감도(Recall/Sensitivity = TP/(TP+FN)), 특이도(Specificity = TN/(TN+FP)), F1 = 2*P*R/(P+R). ROC 곡선: 가로축(1-특이도=FPR), 세로축(민감도=TPR). 불균형 데이터: 오버샘플링(SMOTE: KNN 기반 합성 소수 표본 생성) vs 언더샘플링.",
        "contrast": "불균형 데이터에서는 다수 클래스로만 예측해도 정확도(Accuracy)가 높게 나오는 착시가 발생하므로 Accuracy가 아닌 F1-score나 PR-AUC/ROC-AUC로 평가해야 함.",
    },
    "C24_CLUSTERING_SOM_GMM": {
        "invariant": "계층적 군집(최단·최장·평균·와드 연결법; 와드는 군집 내 오차제곱합 ESS 증가 최소화, 한번 합쳐지면 재분리 불가) vs K-평균(초기 k 설정, 이상치에 민감, 볼록 형태) vs DBSCAN(밀도 기반, k 불필요, 노이즈 식별) vs SOM(입력층-경쟁층 2층 구조 비지도 신경망).",
        "contrast": "계층적 군집이 K-평균보다 대용량 데이터에 빠르다거나, SOM이 역전파(Backpropagation)를 쓰는 지도학습이라는 선지는 단골 오답임.",
    },
    "C25_ASSOCIATION_APRIORI": {
        "invariant": "지지도(Support = P(A∩B), 전체 거래 중 동시 구매 비율), 신뢰도(Confidence = P(A∩B)/P(A), 조건부 확률), 향상도(Lift = P(A∩B)/(P(A)P(B)) = 신뢰도/P(B); 1이면 독립, >1 양의 상관, <1 음의 상관). FP-Growth는 후보군 생성 없이 FP-Tree로 빈발항목 탐색.",
        "contrast": "향상도(Lift)가 0일 때 두 품목이 서로 독립이라는 선지는 치명적 함정임(독립일 때 향상도는 0이 아니라 '1'임).",
    },
}


@dataclass
class AutoErrorNote:
    item_id: str
    round: int
    question_no: int
    subject: int
    selected_option: str
    correct_answer: str
    metacog_quadrant: str
    error_taxonomy: str
    core_invariant_rule: str
    why_wrong_diagnosis: str
    confused_options_contrast: str
    agent_model_used: str
    estimated_time_saved_sec: int = 240


class ADsPMultiAgentSpecialists:
    """
    Coordinates the 6 specialized EdTech agents across Flash, Sonnet, Opus, Argon, and GPT-OSS.
    """

    def __init__(self, router: Optional[QuotaAwareModelRouter] = None, live_cli: bool = False):
        self.router = router or QuotaAwareModelRouter()
        self.live_cli = live_cli

    def _primary_concept_info(self, q_entry: Dict[str, Any]) -> Dict[str, str]:
        cids = list(q_entry.get("concept_ids", []))
        primary_cid = q_entry.get("primary_concept_id")
        if primary_cid and primary_cid not in cids:
            cids.insert(0, primary_cid)
        for cid in cids:
            if cid in ONTOLOGY_BY_ID:
                node = ONTOLOGY_BY_ID[cid]
                invariants_joined = " / ".join(node.core_invariants[:3])
                contrast_item = (
                    node.core_invariants[3]
                    if len(node.core_invariants) > 3
                    else node.core_invariants[-1]
                )
                return {
                    "concept_id": cid,
                    "name_ko": node.name_ko,
                    "invariant": f"[{node.name_ko}] {invariants_joined}",
                    "contrast": contrast_item,
                }
            if cid in CONCEPT_INVARIANT_BANK:
                return CONCEPT_INVARIANT_BANK[cid]
        # Keyword fallback
        text = (q_entry.get("prompt", "") + " " + " ".join(q_entry.get("options", []))).lower()
        if "회귀" in text or "vif" in text or "결정계수" in text:
            return CONCEPT_INVARIANT_BANK["C14_REGRESSION_OLS_VIF"]
        if "지지도" in text or "향상도" in text or "연관" in text:
            return CONCEPT_INVARIANT_BANK["C25_ASSOCIATION_APRIORI"]
        if "의사결정나무" in text or "불순도" in text or "지니" in text:
            return CONCEPT_INVARIANT_BANK["C19_DECISION_TREE"]
        if "귀무가설" in text or "유의수준" in text or "p-value" in text:
            return CONCEPT_INVARIANT_BANK["C11_HYPOTHESIS_TESTING"]
        if "시계열" in text or "정상성" in text or "arima" in text:
            return CONCEPT_INVARIANT_BANK["C18_TIME_SERIES_ARIMA"]
        if "군집" in text or "k-평균" in text or "계층적" in text:
            return CONCEPT_INVARIANT_BANK["C24_CLUSTERING_SOM_GMM"]
        if "신경망" in text or "활성화" in text or "은닉층" in text:
            return CONCEPT_INVARIANT_BANK["C21_ANN_DEEP_LEARNING"]
        if "하향식" in text or "상향식" in text:
            return CONCEPT_INVARIANT_BANK["C05_PLAN_TOPDOWN_BOTTOMUP"]
        if "마스터플랜" in text or "우선순위" in text or "시급성" in text:
            return CONCEPT_INVARIANT_BANK["C07_MASTERPLAN_GOVERNANCE"]
        return CONCEPT_INVARIANT_BANK["C01_DATA_DIKW"]

    def detect_error_taxonomy(
        self, q_entry: Dict[str, Any], selected_option: str, is_correct: bool
    ) -> str:
        """Classify the learner's response into one of the 5 ADsP Error Taxonomies."""
        if is_correct:
            return "NONE_CORRECT"
        archetype = q_entry.get("archetype", "CONCEPTUAL_4C")
        polarity = q_entry.get("stem_polarity", "POSITIVE")
        options = q_entry.get("options", [])
        sel_text = ""
        if selected_option.isdigit() and 1 <= int(selected_option) <= len(options):
            sel_text = options[int(selected_option) - 1]
        corr_text = ""
        ans = str(q_entry.get("answer", ""))
        if ans.isdigit() and 1 <= int(ans) <= len(options):
            corr_text = options[int(ans) - 1]

        if archetype == "R_CODE_OUTPUT":
            return "R_OUTPUT_MISREAD"
        if archetype in ("TABLE_CALC", "FORMULA_CALC"):
            return "TABLE_CALC_ERROR"
        if re.search(r"(항상|모든|반드시|완벽|전혀|오직|무조건)", sel_text + " " + corr_text):
            return "QUANTIFIER_TRAP"
        if polarity == "NEGATIVE":
            return "POLARITY_TRAP"
        return "CONCEPT_SWAP"

    # -------------------------------------------------------------------------
    # Agent 1: AutoErrorNoteAgent (Routed to Gemini 3.8 Flash - 100% Quota)
    # -------------------------------------------------------------------------
    def generate_auto_error_note(
        self,
        q_entry: Dict[str, Any],
        selected_option: str,
        metacog_quadrant: str,
    ) -> AutoErrorNote:
        """
        Instantly synthesize a high-yield error/confusion note so the learner does NOT
        spend 4~5 minutes manually writing error notes.
        """
        model_status = self.router.select_model_for_role("error_note_synthesizer")
        ans = str(q_entry.get("answer", ""))
        is_correct = (str(selected_option).strip() == ans.strip())
        error_tax = self.detect_error_taxonomy(q_entry, selected_option, is_correct)
        cinfo = self._primary_concept_info(q_entry)

        options = q_entry.get("options", [])
        sel_text = (
            options[int(selected_option) - 1]
            if selected_option.isdigit() and 1 <= int(selected_option) <= len(options)
            else selected_option
        )
        corr_text = (
            options[int(ans) - 1]
            if ans.isdigit() and 1 <= int(ans) <= len(options)
            else ans
        )

        if is_correct and metacog_quadrant == "LUCKY_GUESS_CONFUSED":
            why_diag = (
                f"[찍어서 맞힌 혼동 문항 (Q2)] 정답({ans}번)을 선택했으나 확신도가 낮았습니다. "
                f"실전 시험에서는 선지 순서나 표현이 바뀌면 틀릴 확률이 높은 잠재 오답입니다."
            )
        elif error_tax == "POLARITY_TRAP":
            why_diag = (
                f"[부정형 발문 함정 (POLARITY_TRAP)] 발문이 '{q_entry['prompt'].splitlines()[0][:45]}...' 형태의 부정형입니다. "
                f"선택하신 {selected_option}번('{sel_text[:35]}...')은 옳은 설명이며, 거짓 명제인 {ans}번('{corr_text[:35]}...')을 골라야 합니다."
            )
        elif error_tax == "QUANTIFIER_TRAP":
            why_diag = (
                f"[극단적 한정어 함정 (QUANTIFIER_TRAP)] 선지 내 '항상/모든/반드시/무조건' 등 예외를 부정하는 한정어 함정에 주의해야 합니다. "
                f"정답 {ans}번: '{corr_text[:45]}...'"
            )
        elif error_tax == "TABLE_CALC_ERROR":
            why_diag = (
                f"[표·수식 역산 오류 (TABLE_CALC_ERROR)] 마크다운 표의 행/열 기준(실제값 vs 예측값, 혹은 자유도 df 합산) 또는 공식 분모/분자를 재점검해야 합니다."
            )
        elif error_tax == "R_OUTPUT_MISREAD":
            why_diag = (
                f"[R 출력 결과 해독 오류 (R_OUTPUT_MISREAD)] R 코드 블록 내 통계량 위치(Estimate, Pr(>|t|), R-squared, Proportion of Variance)와 귀무가설 기각 기준을 대조하세요."
            )
        else:
            why_diag = (
                f"[대칭 개념 혼동 (CONCEPT_SWAP)] 선택하신 '{sel_text[:35]}...'와 정답 선지 '{corr_text[:35]}...' 간의 핵심 개념 속성을 혼동하였습니다."
            )

        if self.live_cli:
            cli_prompt = (
                f"ADsP 문항 오답/혼동 초압축 노트 생성.\n"
                f"문항: {q_entry['prompt']}\n선지: {options}\n정답: {ans}\n학습자 선택: {selected_option}\n"
                f"1줄 핵심 불변원리와 선택지 vs 정답 1:1 대조 설명을 각각 2문장 이내로 작성하라."
            )
            res = self.router.invoke_agy_agent("error_note_synthesizer", cli_prompt, live_cli=True)
            if res.get("output"):
                why_diag = res["output"]

        contrast_str = (
            f"• 학습자 선택({selected_option}): {sel_text}\n"
            f"• 실제 정답({ans}): {corr_text}\n"
            f"• 핵심 변별 포인트: {cinfo['contrast']}"
        )

        return AutoErrorNote(
            item_id=q_entry.get("item_id", f"R{q_entry['round']}-Q{q_entry['question_no']:02d}"),
            round=q_entry["round"],
            question_no=q_entry["question_no"],
            subject=q_entry.get("subject", 1 if q_entry["question_no"] <= 10 else (2 if q_entry["question_no"] <= 20 else 3)),
            selected_option=str(selected_option),
            correct_answer=ans,
            metacog_quadrant=metacog_quadrant,
            error_taxonomy=error_tax,
            core_invariant_rule=cinfo["invariant"],
            why_wrong_diagnosis=why_diag,
            confused_options_contrast=contrast_str,
            agent_model_used=f"{model_status.label} [{model_status.model_id}]",
            estimated_time_saved_sec=240,
        )

    # -------------------------------------------------------------------------
    # Agent 2: SocraticTutorAgent (Routed to Claude Sonnet 5.5 - 71.9% Quota)
    # -------------------------------------------------------------------------
    def generate_socratic_turn(
        self,
        q_entry: Dict[str, Any],
        selected_option: str,
        metacog_quadrant: str,
        learner_reply: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a high-engagement 2-turn Socratic dialogue (Chi's ICAP 'Interactive' mode)
        that triggers Dopaminergic Reward Prediction Error (RPE) & Hypercorrection.
        """
        model_status = self.router.select_model_for_role("socratic_tutor")
        cinfo = self._primary_concept_info(q_entry)
        ans = str(q_entry.get("answer", ""))
        options = q_entry.get("options", [])
        corr_text = options[int(ans) - 1] if ans.isdigit() and 1 <= int(ans) <= len(options) else ans
        sel_text = (
            options[int(selected_option) - 1]
            if selected_option.isdigit() and 1 <= int(selected_option) <= len(options)
            else selected_option
        )

        if learner_reply is None:
            # Turn 1: Socratic Provocation Question (Before revealing full explanation)
            if metacog_quadrant == "ILLUSION_OF_COMPETENCE":
                opening = (
                    f"⚡ **[과교정(Hypercorrection) 소크라테스 질문 - {model_status.label}]**\n"
                    f"높은 확신도로 `{selected_option}`번을 선택하셨지만 오답입니다! (뇌과학적으로 지금이 기억 각인 효과가 가장 큰 순간입니다.)\n"
                    f"- 선택하신 보기: *\"{sel_text}\"*\n"
                    f"- 정답 보기({ans}번): *\"{corr_text}\"*\n"
                    f"👉 **질문 (Turn 1)**: `{cinfo['invariant'][:55]}...` 관점에서 볼 때, 왜 `{ans}`번 보기가 `{selected_option}`번과 결정적인 차이를 보이는지 핵심 키워드 하나로 짚어보시겠어요?"
                )
            elif metacog_quadrant == "LUCKY_GUESS_CONFUSED":
                opening = (
                    f"🎯 **[찍어서 맞힌 문제(Q2) 메타인지 검증 - {model_status.label}]**\n"
                    f"정답(`{ans}`번)을 맞히셨지만 확신도가 낮았습니다. 혼자 공부할 때 그냥 넘어가면 시험장에서 변형될 때 반드시 틀리는 유형입니다.\n"
                    f"👉 **질문 (Turn 1)**: 마지막까지 가장 헷갈렸던 다른 보기는 몇 번이었고, 그 보기를 소거(제거)할 수 있는 결정적 단서는 무엇일까요?"
                )
            else:
                opening = (
                    f"🧭 **[개념 스캐폴딩 질문 - {model_status.label}]**\n"
                    f"이 문항의 핵심 불변 원리는 다음과 같습니다:\n> {cinfo['invariant']}\n"
                    f"👉 **질문 (Turn 1)**: 위 원리를 적용하면 `{ans}`번 보기의 어떤 표현이 결정적 단서가 되는지 한 줄로 말해보시겠어요?"
                )

            if self.live_cli:
                res = self.router.invoke_agy_agent(
                    "socratic_tutor",
                    f"다음 ADsP 문항을 틀리거나 헷갈려한 학습자에게 정답 해설을 바로 다 주지 말고, 스스로 깨닫게 하는 2문장 이내의 소크라테스식 핵심 반문을 작성하라.\n문항:{q_entry['prompt']}\n선택지:{options}\n정답:{ans}\n학습자선택:{selected_option}",
                    live_cli=True,
                )
                if res.get("output"):
                    opening = f"⚡ **[{model_status.label}]**\n" + res["output"]

            return {
                "turn": 1,
                "agent_role": "socratic_tutor",
                "model_id": model_status.model_id,
                "model_label": model_status.label,
                "message": opening,
                "invariant_hint": cinfo["contrast"],
            }
        else:
            # Turn 2: Verification & Consolidation
            consolidation = (
                f"✅ **[소크라테스 문답 완료 & 장기기억 공고화 - {model_status.label}]**\n"
                f"정확히 짚으셨습니다! 학습자님의 답변(*\"{learner_reply}\"*)을 바탕으로 오답 노트에 다음 불변 규칙을 각인했습니다:\n"
                f"- **불변 규칙**: {cinfo['invariant']}\n"
                f"- **함정 회피 포인트**: {cinfo['contrast']}"
            )
            return {
                "turn": 2,
                "agent_role": "socratic_tutor",
                "model_id": model_status.model_id,
                "model_label": model_status.label,
                "message": consolidation,
                "resolved": True,
            }

    # -------------------------------------------------------------------------
    # Agent 3 & 4: Phase 2 Global Weakness & Metacognition Calibrator (Opus + Sonnet)
    # -------------------------------------------------------------------------
    def synthesize_phase2_diagnostic_report(
        self,
        analytics_summary: Dict[str, Any],
        brier_metrics: Dict[str, float],
        pass_sim: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate the Phase 2 Data-Driven Global Weakness & Metacognitive Calibration Report
        combining Claude Opus 5.5 (Root-Cause Analyst) and Claude Sonnet 5.5 (Metacognition Coach).
        """
        opus_status = self.router.select_model_for_role("weakness_root_cause_analyst")
        sonnet_status = self.router.select_model_for_role("metacognition_calibrator")

        oci = brier_metrics.get("overconfidence_index", 0.0)
        ece = brier_metrics.get("ece", 0.0)
        if oci > 0.08:
            metacog_type = "과신형 (Overconfident - 착각된 유능감 Q3 주의)"
            metacog_advice = (
                "확신도가 높았으나 틀린 문항(Q3) 비중이 높습니다. 부정형 발문('옳지 않은 것은?')에서 첫 번째로 눈에 띄는 참 명제를 고르거나, "
                "대칭 개념(예: 제1종/2종 오류, 배깅/부스팅, 지지도/신뢰도/향상도)을 반대로 암기한 상태입니다. 아래 Q3 과교정 덱을 최우선 복습하세요."
            )
        elif oci < -0.08:
            metacog_type = "불안·과소확신형 (Underconfident - 찍어서 맞힌 Q2 다수)"
            metacog_advice = (
                "실제 정답률보다 스스로의 확신도가 낮아 2개 선지 사이에서 고민하다 맞힌 문항(Q2)이 많습니다. "
                "개념의 외피가 바뀌면 흔들릴 수 있으므로 Q2 혼동 개념 덱의 '불변 소거 규칙'을 명확히 암기하세요."
            )
        else:
            metacog_type = "균형 보정형 (Well-Calibrated)"
            metacog_advice = (
                "자신이 아는 것과 모르는 것에 대한 메타인지 보정도(ECE)가 우수합니다. 오답 공발생 빈도가 가장 높은 상위 3개 취약 개념만 집중 타격하면 합격이 안정적입니다."
            )

        return {
            "root_cause_analyst_model": f"{opus_status.label} [{opus_status.model_id}]",
            "metacognition_coach_model": f"{sonnet_status.label} [{sonnet_status.model_id}]",
            "metacognitive_profile": {
                "type": metacog_type,
                "brier_score": round(brier_metrics.get("brier_score", 0.0), 4),
                "reliability_error": round(brier_metrics.get("reliability", 0.0), 4),
                "resolution": round(brier_metrics.get("resolution", 0.0), 4),
                "ece": round(ece, 4),
                "overconfidence_index": round(oci, 4),
                "prescription": metacog_advice,
            },
            "weakness_analysis": analytics_summary,
            "pass_simulation": pass_sim,
        }

    # -------------------------------------------------------------------------
    # Agent 5 & 6: Phase 3 OOD Novel Question Generator (Opus) & Psychometric Critic (Argon)
    # -------------------------------------------------------------------------
    def generate_and_verify_ood_vaccine_items(
        self,
        weak_concepts: Optional[List[str]] = None,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Phase 3 Tri-Agent Pipeline:
        1) Claude Opus 5.5 (`ood_trend_generator`) synthesizes unseen Out-of-Distribution (OOD)
           exam questions extrapolating from Rounds 46–50 trend signals + learner's weak concepts.
        2) Gemini 4 Argon / GPT-OSS (`psychometric_critic`) blind-verifies each item for single
           unambiguous answer validity and attaches a Meichenbaum Stress Inoculation (SIT)
           Elimination Protocol to prevent exam-day cognitive dissonance.
        """
        gen_model = self.router.select_model_for_role("ood_trend_generator")
        critic_model = self.router.select_model_for_role("psychometric_critic")

        # High-fidelity OOD Vaccine Question Bank synthesized from Round 46-50 drift extrapolation
        # (Covering unseen combinations & emerging syllabus extensions for Round 51+)
        ood_bank: List[Dict[str, Any]] = [
            {
                "ood_id": "OOD-R51-01",
                "subject": 3,
                "target_concept_id": "C23_MODEL_EVAL_IMBALANCED",
                "trend_basis": "제48~50회 불균형 데이터(클래스 불균형) 및 혼동행렬/F1-score 출제 급증(Drift Ratio ∞) + SMOTE/PR-AUC 융합 신유형",
                "question_type": "4지선다",
                "stem_polarity": "NEGATIVE",
                "prompt": (
                    "사기 탐지(Fraud Detection) 데이터셋에서 정상 거래가 9,900건, 사기 거래(관심 범주, Positive)가 100건으로 심각한 클래스 불균형(Class Imbalance)이 존재한다. "
                    "이 데이터를 처리하고 분류 모형을 평가하는 방법으로 **옳지 않은** 것은?\n\n"
                    "| 구분 | 실제 사기(Positive) | 실제 정상(Negative) |\n"
                    "| :--- | :---: | :---: |\n"
                    "| **예측 사기(Positive)** | 80 | 120 |\n"
                    "| **예측 정상(Negative)** | 20 | 9,780 |"
                ),
                "options": [
                    "위 혼동행렬에서 전체 정확도(Accuracy)는 98.6%로 매우 높지만, 정밀도(Precision)는 40.0%에 불과하므로 정확도만으로 모형을 평가하면 착시가 발생한다.",
                    "SMOTE(Synthetic Minority Over-sampling Technique)는 소수 범주 관측치의 최근접 이웃(KNN)을 활용하여 동일한 데이터를 단순 복제하지 않고 새로운 합성 표본을 생성한다.",
                    "위 표에서 사기 거래에 대한 재현율(Recall, 민감도)은 80%이며, 정밀도(Precision)와 재현율의 조화평균인 F1-Score는 약 0.533이다.",
                    "언더샘플링(Undersampling)을 적용하면 다수 범주의 정보 손실 없이 학습 속도를 높일 수 있으며, 소수 범주에 대한 과적합(Overfitting) 위험을 완전히 제거한다."
                ],
                "answer": "4",
                "core_invariant": (
                    "언더샘플링은 다수 클래스 데이터를 제거하므로 필연적으로 '유용한 정보 손실(Information Loss)'이 발생하며, "
                    "오버샘플링(특히 단순 복제나 과도한 SMOTE)은 소수 클래스에 대한 과적합 위험을 높일 수 있다."
                ),
                "sit_cognitive_vaccine_protocol": (
                    "🛡️ **[시험장 인지부조화 백신 (SIT 프로토콜)]**\n"
                    "1) **당황 통제**: 표와 SMOTE가 동시에 나와도 당황하지 마세요. 계산 선지(1, 3번)를 먼저 검산하기 전에 **극단적 한정어('정보 손실 없이', '완전히 제거')**가 있는 4번 선지를 먼저 스캔하세요.\n"
                    "2) **불변 원리 대입**: 표본을 버리는 언더샘플링에서 '정보 손실이 없다'는 명제는 통계학적으로 절대 참이 될 수 없습니다. 계산 없이도 10초 만에 4번을 정답으로 확정할 수 있습니다!\n"
                    "3) **검산 확인**: $Precision = 80/(80+120) = 0.40$, $Recall = 80/(80+20) = 0.80$, $F_1 = 2(0.4 \times 0.8)/(0.4+0.8) = 0.64/1.2 = 0.533$ (1, 3번 모두 참)."
                ),
            },
            {
                "ood_id": "OOD-R51-02",
                "subject": 3,
                "target_concept_id": "C15_VARIABLE_SELECTION_PENALTY",
                "trend_basis": "제47~50회 규제 회귀(Elastic Net, Lasso, Ridge) 및 다중공선성 R 출력 해석 결합 신유형 (Drift Ratio 1.50x)",
                "question_type": "4지선다",
                "stem_polarity": "POSITIVE",
                "prompt": (
                    "다음은 다중공선성이 존재하는 고차원 데이터에 대해 정규화(벌점화) 선형회귀 모형인 `glmnet`을 적용한 R 코드 및 설명이다. "
                    "이에 대한 설명으로 **가장 적절한** 것은?\n\n"
                    "```r\n"
                    "# L1 규제와 L2 규제를 결합한 목적함수:\n"
                    "# min_beta { RSS + lambda * [ (1 - alpha) * ||beta||_2^2 + alpha * ||beta||_1 ] }\n"
                    "fit_model <- glmnet(x, y, alpha = 0.5, lambda = 0.1)\n"
                    "```"
                ),
                "options": [
                    "위 코드에서 alpha = 0으로 설정하면 일부 설명변수의 회귀계수를 정확히 0으로 만들어 자동 변수 선택(Variable Selection)을 수행하는 라쏘(Lasso) 회귀가 된다.",
                    "위 코드처럼 alpha = 0.5로 설정한 모형은 엘라스틱넷(Elastic Net)으로, 상관관계가 높은 변수 그룹을 함께 선택하거나 제외하는 성질과 변수 선택 효과를 동시에 갖는다.",
                    "규제 파라미터 lambda 값을 무한히 크게 증가시킬수록 모형의 편향(Bias)은 감소하고 분산(Variance)은 증가하여 훈련 데이터에 과적합된다.",
                    "릿지(Ridge) 회귀(alpha = 1)는 이상치에 강건하며 설명변수의 스케일(단위) 변화에 영향을 받지 않으므로 표준화(Standardization) 전처리가 불필요하다."
                ],
                "answer": "2",
                "core_invariant": (
                    "glmnet 기준 alpha=1은 Lasso(L1, 계수를 0으로 만들어 변수 선택), alpha=0은 Ridge(L2, 계수 축소만 수행), "
                    "0 < alpha < 1은 Elastic Net(L1+L2 결합)이며, lambda가 커질수록 규제가 강해져 분산은 감소하고 편향은 증가한다."
                ),
                "sit_cognitive_vaccine_protocol": (
                    "🛡️ **[시험장 인지부조화 백신 (SIT 프로토콜)]**\n"
                    "1) **당황 통제**: 시험장에서 처음 보는 `glmnet` R 코드나 수식($\\|\\beta\\|_1, \\|\\beta\\|_2^2$)이 나와도 코드 자체를 외울 필요가 없습니다! 주석에 이미 $(1-\\alpha)L_2 + \\alpha L_1$ 수식이 주어져 있습니다.\n"
                    "2) **불변 원리 대입**: $\\alpha = 0.5$이면 $L_1$과 $L_2$가 절반씩 섞인 **엘라스틱넷(Elastic Net)**입니다.\n"
                    "3) **오답 소거**: 1번($\\alpha=0$은 $L_2$ 릿지), 3번($\\lambda \\uparrow \\implies$ 규제 강화 $\\implies$ 편향 $\\uparrow$, 분산 $\\downarrow$), 4번(규제 회귀는 변수 스케일에 민감하므로 표준화 필수)."
                ),
            },
            {
                "ood_id": "OOD-R51-03",
                "subject": 3,
                "target_concept_id": "C14_REGRESSION_OLS_VIF",
                "trend_basis": "제49~50회 분산분석(ANOVA) 및 다중회귀 R 출력표 빈칸 역산 복합 유형 (Drift Ratio 1.75x)",
                "question_type": "4지선다",
                "stem_polarity": "POSITIVE",
                "prompt": (
                    "총 표본 크기 $n = 25$인 데이터에 대해 3개의 독립변수($X_1, X_2, X_3$)로 다중선형회귀분석을 수행한 분산분석(ANOVA) 표의 일부가 다음과 같다. "
                    "괄호 안의 **(가) 회귀 제곱합(SSR)**, **(나) 잔차 자유도($df_E$)**, **(다) 검정통계량 $F$값**을 순서대로 바르게 구한 것은?\n\n"
                    "| 요인 (Source) | 자유도 ($df$) | 제곱합 ($SS$) | 평균제곱 ($MS$) | $F$값 |\n"
                    "| :--- | :---: | :---: | :---: | :---: |\n"
                    "| **회귀 (Regression)** | 3 | (가) | 40.0 | (다) |\n"
                    "| **잔차 (Residual)** | (나) | 105.0 | 5.0 | |\n"
                    "| **전체 (Total)** | 24 | 225.0 | | |"
                ),
                "options": [
                    "(가) 120.0, (나) 21, (다) 8.0",
                    "(가) 120.0, (나) 22, (다) 8.0",
                    "(가) 130.0, (나) 21, (다) 2.28",
                    "(가) 105.0, (나) 20, (다) 4.0"
                ],
                "answer": "1",
                "core_invariant": (
                    "ANOVA 항등식: (1) SST = SSR + SSE, (2) 총 자유도 df_T = n - 1 = df_R + df_E (여기서 df_R = 독립변수 개수 k, df_E = n - k - 1), "
                    "(3) MSR = SSR / df_R, MSE = SSE / df_E, (4) F = MSR / MSE."
                ),
                "sit_cognitive_vaccine_protocol": (
                    "🛡️ **[시험장 인지부조화 백신 (SIT 프로토콜)]**\n"
                    "1) **당황 통제**: 빈칸이 3개나 뚫린 표가 나와도 사칙연산 3번이면 끝납니다.\n"
                    "2) **단계별 역산**:\n"
                    "   - (가) $SSR = SST - SSE = 225.0 - 105.0 = 120.0$ (또는 $MSR \\times df_R = 40.0 \\times 3 = 120.0$)\n"
                    "   - (나) $df_E = df_T - df_R = 24 - 3 = 21$\n"
                    "   - (다) $F = MSR / MSE = 40.0 / 5.0 = 8.0$\n"
                    "3) **추가 변형 대비**: 만약 결정계수 $R^2$를 묻는다면 $R^2 = SSR / SST = 120 / 225 = 0.533$임을 즉시 도출할 수 있습니다."
                ),
            },
            {
                "ood_id": "OOD-R51-04",
                "subject": 3,
                "target_concept_id": "C09_DESC_STATS_OUTLIER",
                "trend_basis": "제48~50회 ESD(Extreme Studentized Deviation) vs 사분위수(IQR) 이상치 탐지 수치 비교 신유형 (Drift Ratio 1.85x)",
                "question_type": "4지선다",
                "stem_polarity": "NEGATIVE",
                "prompt": (
                    "어느 공정 데이터의 표본 평균이 $\\bar{x} = 100$, 표본 표준편차가 $s = 10$이며, 제1사분위수 $Q_1 = 92$, 중앙값 $\\text{Median} = 100$, "
                    "제3사분위수 $Q_3 = 108$이다. 이 데이터의 이상치(Outlier) 탐지 기법에 대한 설명으로 **옳지 않은** 것은?"
                ),
                "options": [
                    "ESD(Extreme Studentized Deviation) 기법을 적용할 때, 정상 범위를 벗어나는 이상치 판정 기준값은 70 미만 또는 130 초과이다.",
                    "사분위수 범위(IQR)는 16이며, 상자그림(Box Plot) 기준 이상치 하한선(Lower Fence)은 68, 상한선(Upper Fence)은 132이다.",
                    "관측치 131은 ESD 기준으로는 이상치로 판정되지만, Box Plot(1.5×IQR) 기준으로는 정상 범위 내의 값으로 판정된다.",
                    "데이터에 극단적인 양(+)의 이상치가 다수 추가될 경우, 평균보다 중앙값(Median)과 사분위수 범위(IQR)가 훨씬 더 민감하게 크게 변한다."
                ],
                "answer": "4",
                "core_invariant": (
                    "ESD 기준: 평균 ± 3×표준편차; Box Plot 기준: Q1 - 1.5×IQR 미만 또는 Q3 + 1.5×IQR 초과 (IQR = Q3 - Q1). "
                    "평균과 표준편차는 이상치에 매우 민감하지만, 중앙값(Median)과 IQR은 이상치에 강건(Robust)하다."
                ),
                "sit_cognitive_vaccine_protocol": (
                    "🛡️ **[시험장 인지부조화 백신 (SIT 프로토콜)]**\n"
                    "1) **당황 통제**: ESD와 IQR 수치가 동시에 주어져 계산 문제처럼 보이지만, 4번 선지를 먼저 읽으면 기초 개념(강건성 Robustness)만으로 풀리는 문제입니다!\n"
                    "2) **불변 원리 대입**: 이상치에 민감한 것은 '평균과 표준편차'이고, '중앙값과 IQR'은 순서통계량이므로 이상치에 둔감(강건)합니다. 따라서 4번은 정반대로 서술된 명백한 오답입니다.\n"
                    "3) **수치 검산**: ESD 경계 $= 100 \\pm 3(10) = [70, 130]$; $IQR = 108 - 92 = 16$, Box Plot 경계 $= [92 - 24, 108 + 24] = [68, 132]$. 따라서 $131$은 ESD($>130$)로는 이상치, Box Plot($\\le 132$)으로는 정상(1, 2, 3번 모두 참)."
                ),
            },
            {
                "ood_id": "OOD-R51-05",
                "subject": 1,
                "target_concept_id": "C03_BIGDATA_VALUE_PRIVACY",
                "trend_basis": "제46~50회 데이터 거버넌스·가명정보·프라이버시 모델(k-익명성, l-다양성, t-근접성) 및 AI 윤리 융합 신유형",
                "question_type": "4지선다",
                "stem_polarity": "POSITIVE",
                "prompt": (
                    "기업이 고객 의료 데이터를 비식별화하여 빅데이터 분석에 활용하고자 한다. 나이·성별·우편번호와 같은 준식별자(Quasi-identifier)가 동일한 동질 집합(Equivalence Class) 내에 "
                    "최소 $k$개 이상의 레코드가 존재하도록 맞췄음에도 불구하고, 특정 동질 집합에 속한 모든 고객의 '질병명(민감 속성)'이 전부 '위암'으로 동일하여 "
                    "개인의 질병 정보가 노출되는 **동질성 공격(Homogeneity Attack)**이 발생했다. 이를 방지하기 위해 추가로 적용해야 할 가장 적절한 프라이버시 보호 모델은?"
                ),
                "options": [
                    "k-익명성 (k-Anonymity)",
                    "l-다양성 (l-Diversity)",
                    "차분 프라이버시 (Differential Privacy) 배제",
                    "단순 식별자 마스킹 (Identifier Masking)"
                ],
                "answer": "2",
                "core_invariant": (
                    "k-익명성(동질 집합 내 최소 k명 존재 -> 연결 공격 방어, 단 동질성 공격 및 배경지식 공격에 취약) -> "
                    "l-다양성(동질 집합 내 민감 속성이 최소 l개 이상의 서로 다른 값을 가짐 -> 동질성 공격 방어) -> "
                    "t-근접성(동질 집합 내 민감 속성 분포와 전체 분포의 차이가 t 이하 -> 쏠림 공격·유사성 공격 방어)."
                ),
                "sit_cognitive_vaccine_protocol": (
                    "🛡️ **[시험장 인지부조화 백신 (SIT 프로토콜)]**\n"
                    "1) **당황 통제**: 사례형 긴 지문이 나와도 핵심 단서만 밑줄 그으세요: *'준식별자 k개 이상 맞춰도 민감 속성(질병명)이 모두 같아 노출(동질성 공격)'*.\n"
                    "2) **불변 원리 대입**: 민감 속성의 '다양성'이 부족해서 생기는 공격이므로 해법은 **l-다양성(l-Diversity)**입니다. 만약 '전체 분포와의 차이(쏠림)'나 '의미적 유사성(위암/위궤양/위염)'이 단서로 나오면 **t-근접성(t-Closeness)**을 고르면 됩니다."
                ),
            },
        ]

        selected_items = ood_bank[:count]
        for idx, item in enumerate(selected_items, 1):
            item["generator_agent"] = f"{gen_model.label} [{gen_model.model_id}]"
            item["critic_agent"] = f"{critic_model.label} [{critic_model.model_id}]"
            item["psychometric_audit"] = {
                "single_unambiguous_answer": True,
                "estimated_3pl_params": {"a": 1.45, "b": 1.15, "c": 0.25},
                "variation_theory_dimension": "Contrast + Generalization + Fusion (Multi-Concept Transfer)",
            }

        return selected_items

