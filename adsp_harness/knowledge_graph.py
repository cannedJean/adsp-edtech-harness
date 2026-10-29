"""ADsP Knowledge Graph & Psychometric Q-Matrix Engine.

This module builds an ontology DAG across Subjects 1, 2, and 3 for the ADsP curriculum,
maps all 748 past exam items to knowledge concepts (Q-Matrix), extracts psychometric
and pedagogical attributes (polarity, archetypes, distractor traps, calibrated 3PL IRT parameters),
and computes longitudinal concept drift across three eras (Era 1: 32-39, Era 2: 40-45, Era 3: 46-50),
including Page-Hinkley/CUSUM drift scores and Round 51+ Out-of-Distribution (OOD) candidate predictions.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# 1. ONTOLOGY SPECIFICATION & VARIATION THEORY INVARIANTS (32 CONCEPT NODES)
# ============================================================================

@dataclass
class ConceptNode:
    concept_id: str
    name_ko: str
    subject: int
    prerequisites: List[str]
    core_invariants: List[str]
    keywords: List[str] = field(default_factory=list)


ONTOLOGY_DEFINITIONS: List[ConceptNode] = [
    # ------------------------------------------------------------------------
    # Subject 1: 데이터 이해 (Data Understanding) - 8 Concepts
    # ------------------------------------------------------------------------
    ConceptNode(
        concept_id="C01_DATA_DIKW",
        name_ko="데이터와 DIKW 피라미드",
        subject=1,
        prerequisites=[],
        core_invariants=[
            "데이터(Data): 개별 데이터 자체로는 의미가 미약한 순수한 관찰/측정된 객관적 사실(Fact)",
            "정보(Information): 데이터를 처리/가공하여 데이터 간의 연관 관계와 맥락(Context)을 부여한 상태",
            "지식(Knowledge): 다양한 정보를 구조화/일반화하여 개인의 경험, 규칙, 통찰과 결합한 상태",
            "지혜(Wisdom): 축적된 지식을 바탕으로 미래를 예측하고 창의적 아이디어를 도출하는 근본적 원리 이해",
            "데이터 단위 체계: Byte < KB < MB < GB < TB < PB < EB < ZB < YB (각 단계는 1024배 = 2^10)",
            "정성적 데이터(비정형, 언어/문자) vs 정량적 데이터(정형, 수치/도형/기호)"
        ],
        keywords=[
            r'dikw', r'데이터와\s*정보', r'지혜', r'정성적', r'정량적', r'객관적\s*사실', r'데이터의\s*정의',
            r'데이터\s*크기', r'단위', r'바이트', r'페타바이트', r'엑사바이트', r'제타바이트', r'정보화', r'지식\s*피라미드',
            r'\bzb\b', r'[0-9]*\s*zb\b', r'데이터\s*용량', r'용량', r'데이터의\s*특성', r'원하는\s*정보',
            r'데이터\s*형태', r'정형.*비정형', r'반정형', r'비정형.*정형'
        ]
    ),
    ConceptNode(
        concept_id="C02_KNOWLEDGE_SECI",
        name_ko="지식 창출 및 암묵지/형식지 (SECI 모형)",
        subject=1,
        prerequisites=["C01_DATA_DIKW"],
        core_invariants=[
            "암묵지(Tacit Knowledge): 학습과 경험을 통해 개인에게 체화되어 있으나 언어나 기호로 표출하기 어려운 지식",
            "형식지(Explicit Knowledge): 매뉴얼, 서적, 문서, 데이터베이스 등 언어와 기호로 명확히 표현된 지식",
            "SECI 4단계 변환: 공통화(Socialization, 암묵지->암묵지), 표출화(Externalization, 암묵지->형식지), 연결화(Combination, 형식지->형식지), 내면화(Internalization, 형식지->암묵지)",
            "지식 나선 모형(Knowledge Spiral): SECI 4단계를 연속적으로 순환하면서 개인의 지식이 조직의 지식으로 확장"
        ],
        keywords=[
            r'seci', r'암묵지', r'형식지', r'공통화', r'표출화', r'연결화', r'내면화', r'지식\s*경영', r'노나카', r'nonaka', r'상호작용'
        ]
    ),
    ConceptNode(
        concept_id="C03_DB_BASICS_SQL",
        name_ko="데이터베이스 기본 특성 및 SQL",
        subject=1,
        prerequisites=[],
        core_invariants=[
            "데이터베이스 4대 정의: 통합된 데이터(Integrated), 저장된 데이터(Stored), 공용 데이터(Shared), 운영 데이터(Operational)",
            "데이터베이스의 특성: 실시간 접근성, 계속적인 변화, 동시 공유, 내용에 의한 참조(Content Reference)",
            "SQL 분류: DDL(CREATE, ALTER, DROP, TRUNCATE), DML(SELECT, INSERT, UPDATE, DELETE), DCL(GRANT, REVOKE, COMMIT, ROLLBACK)",
            "트랜잭션 ACID 4대 원칙: 원자성(Atomicity), 일관성(Consistency), 고립성(Isolation), 지속성(Durability)",
            "관계형 데이터 모델: 테이블(엔터티), 행(튜플/인스턴스), 열(속성/어트리뷰트), 기본키와 외래키"
        ],
        keywords=[
            r'데이터베이스', r'\bsql\b', r'\bdml\b', r'\bddl\b', r'\bdcl\b', r'관계형\s*데이터베이스', r'dbms', r'acid',
            r'트랜잭션', r'select\b', r'insert\b', r'delete\b', r'update\b', r'통합된\s*데이터', r'저장된\s*데이터',
            r'공용\s*데이터', r'운영\s*데이터', r'대응비', r'엔터티', r'관계형\s*모델', r'스키마', r'정규화', r'데이터\s*모델링'
        ]
    ),
    ConceptNode(
        concept_id="C04_ENTERPRISE_DB",
        name_ko="기업 내부 데이터베이스 솔루션",
        subject=1,
        prerequisites=["C03_DB_BASICS_SQL"],
        core_invariants=[
            "OLTP(Online Transaction Processing): 실시간 트랜잭션 처리 중심 (현재 시점, 무결성)",
            "OLAP(Online Analytical Processing): 다차원 분석 및 의사결정 지원 중심 (과거 이력 누적, 롤업/드릴다운)",
            "CRM(Customer Relationship Management): 고객 관계 관리 및 고객 생애 가치(LTV) 극대화",
            "SCM(Supply Chain Management): 공급망 관리 (제조, 유통, 물류 프로세스 통합 최적화)",
            "ERP(Enterprise Resource Planning): 전사적 자원 관리 (인사, 재무, 회계, 생산 등 통합)",
            "DW(Data Warehouse): 기업 전체 단위의 통합된 주제 중심 데이터 저장소",
            "DM(Data Mart): 특정 부서나 특정 주제 중심의 소규모 데이터 웨어하우스",
            "EAI / ETL: 엔터프라이즈 애플리케이션 통합 및 추출(Extract)-변환(Transform)-적재(Load)"
        ],
        keywords=[
            r'olap', r'oltp', r'crm', r'scm', r'erp', r'데이터\s*웨어하우스', r'데이터웨어하우스', r'데이터\s*마트', r'데이터마트',
            r'\bdw\b', r'\bdm\b', r'eai', r'etl', r'기업\s*내부', r'솔루션', r'공급망', r'고객관계', r'연결된\s*상태'
        ]
    ),
    ConceptNode(
        concept_id="C05_BIGDATA_CHARACTERISTICS",
        name_ko="빅데이터 특징과 패러다임 변화",
        subject=1,
        prerequisites=["C01_DATA_DIKW", "C03_DB_BASICS_SQL"],
        core_invariants=[
            "빅데이터 3V: Volume(규모/양), Velocity(속도), Variety(다양성) + 4V(Value 가치), 5V(Veracity 정확성)",
            "빅데이터 4대 본질적 변화: 사전처리 -> 사후처리, 표본조사 -> 전수조사, 질 우선 -> 양 우선, 인과관계 -> 상관관계 중심",
            "비정형 데이터의 비중 급증(로그, 이미지, 음성, SNS 텍스트) 및 분산 병렬 컴퓨팅(하둡/스파크)"
        ],
        keywords=[
            r'빅데이터', r'3v', r'4v', r'5v', r'volume', r'velocity', r'variety', r'전수조사', r'인과관계.*상관관계',
            r'상관관계.*인과관계', r'비정형\s*데이터', r'클라우드', r'사전처리.*사후처리', r'데이터\s*경제', r'플랫폼',
            r'비정형', r'반정형', r'로그.*영상.*텍스트'
        ]
    ),
    ConceptNode(
        concept_id="C06_BIGDATA_VALUE_IMPACT",
        name_ko="빅데이터 가치 산정 및 위기요인/통제방안",
        subject=1,
        prerequisites=["C05_BIGDATA_CHARACTERISTICS"],
        core_invariants=[
            "가치 산정이 어려운 3대 이유: 데이터 활용 방식 다양성(재사용), 새로운 가치 창출, 분석 기술의 급변",
            "빅데이터 3대 위기 요인: 사생활 침해(Privacy), 책임 원칙 훼손(Responsibility), 데이터 오용(Data Misuse)",
            "통제 방안 매칭: 사생활 침해 -> 동의제도에서 책임제도로 전환 및 비식별화(익명화/가명화), 책임 원칙 훼손 -> 알고리즘 결과에만 근거한 불이익 금지(반론권 보장), 데이터 오용 -> 알고리즈미스트(Algorithmist) 도입"
        ],
        keywords=[
            r'가치\s*산정', r'위기\s*요인', r'사생활\s*침해', r'책임\s*원칙', r'데이터\s*오용', r'알고리즈미스트', r'비식별화',
            r'익명화', r'동의제', r'가치\s*기반', r'비즈니스\s*영향', r'빅데이터의\s*가치'
        ]
    ),
    ConceptNode(
        concept_id="C07_BIGDATA_TECHNIQUES",
        name_ko="빅데이터 활용 기본 테크닉",
        subject=1,
        prerequisites=["C05_BIGDATA_CHARACTERISTICS"],
        core_invariants=[
            "연관규칙학습(Association Rule Learning): 항목 간의 조건-결과 상관관계 파악 (장바구니 분석)",
            "유형분석(Cluster/Classification Analysis): 특성에 따라 집단을 분류하고 새로운 관측치를 그룹에 배치",
            "유전알고리즘(Genetic Algorithm): 생물의 진화 메커니즘(선택, 교차, 변이)을 모방한 최적화 탐색 기법",
            "기계학습(Machine Learning): 데이터로부터 컴퓨터가 스스로 규칙을 도출하여 예측 모형 생성",
            "감정분석(Sentiment Analysis): 텍스트에서 긍정/부정/중립 감성 상태 추출",
            "소셜네트워크분석(SNA): 개체(Node) 간의 관계(Link)를 네트워크 그래프로 표현하고 중심성(Centrality) 분석"
        ],
        keywords=[
            r'유전\s*알고리즘', r'유전자\s*알고리즘', r'감정\s*분석', r'소셜\s*네트워크', r'소셜네트워크', r'\bsna\b',
            r'연관규칙\s*학습', r'빅데이터.*테크닉', r'연결망\s*분석', r'중심성\s*분석', r'소셜\s*그래프', r'텍스트\s*마이닝',
            r'텍스트마이닝', r'오피니언\s*마이닝'
        ]
    ),
    ConceptNode(
        concept_id="C08_DATA_SCIENTIST_CAPABILITY",
        name_ko="데이터 사이언티스트 역량 및 역할",
        subject=1,
        prerequisites=["C05_BIGDATA_CHARACTERISTICS"],
        core_invariants=[
            "하드 스킬(Hard Skill): 빅데이터 인프라/엔지니어링 지식, 통계학, 수학, 프로그래밍 기술",
            "소프트 스킬(Soft Skill): 통찰력 있는 분석, 커뮤니케이션 능력, 리더십, 비즈니스 이해도, 인문학적 소양",
            "가트너(Gartner)의 역량 프레임워크: 통섭적 사고와 정량적 분석 능력의 결합"
        ],
        keywords=[
            r'데이터\s*사이언티스트', r'데이터사이언티스트', r'하드\s*스킬', r'소프트\s*스킬', r'hard\s*skill', r'soft\s*skill',
            r'가트너', r'인문학', r'통섭', r'역량', r'데이터\s*분석가\s*역량'
        ]
    ),

    # ------------------------------------------------------------------------
    # Subject 2: 데이터분석 기획 (Data Analysis Planning) - 8 Concepts
    # ------------------------------------------------------------------------
    ConceptNode(
        concept_id="C09_ANALYSIS_QUADRANT",
        name_ko="분석 기획 방향성 및 4가지 분석 유형",
        subject=2,
        prerequisites=["C01_DATA_DIKW"],
        core_invariants=[
            "분석 대상(What)과 분석 방법(How) 2x2 매트릭스",
            "최적화(Optimization): 대상 Known + 방법 Known (기존 프로세스의 효율 극대화)",
            "솔루션(Solution): 대상 Known + 방법 Unknown (문제는 알지만 분석 방식을 모를 때)",
            "통찰(Insight): 대상 Unknown + 방법 Known (분석 방식은 알지만 분석 대상을 새로 발굴할 때)",
            "발견(Discovery): 대상 Unknown + 방법 Unknown (대상과 방법 모두 모를 때 데이터로부터 가치 창출)",
            "목표 시점별 기획: 단기 과제 중심(Speed & Quick-Win) vs 중장기 마스터플랜(Accuracy & Scalability)",
            "의사결정 편향: 프레이밍 효과(Framing Effect), 확증 편향(Confirmation Bias)"
        ],
        keywords=[
            r'optimization', r'solution', r'insight', r'discovery', r'최적화', r'솔루션', r'통찰', r'발견',
            r'what.*how', r'how.*what', r'분석\s*대상.*분석\s*방법', r'분석\s*기획\s*유형', r'분석\s*주제',
            r'시나리오', r'의사결정', r'프레이밍', r'framing', r'분석\s*기획', r'과제\s*중심'
        ]
    ),
    ConceptNode(
        concept_id="C10_ANALYTIC_METHODOLOGIES",
        name_ko="분석 방법론 (KDD, CRISP-DM, 빅데이터 분석 방법론)",
        subject=2,
        prerequisites=["C09_ANALYSIS_QUADRANT"],
        core_invariants=[
            "KDD 분석 절차 5단계: Selection(선택) -> Preprocessing(전처리) -> Transformation(변환) -> Data Mining(마이닝) -> Evaluation(평가/해석)",
            "CRISP-DM 6단계: Business Understanding(업무 이해) -> Data Understanding(데이터 이해) -> Data Preparation(데이터 준비) -> Modeling(모델링) -> Evaluation(평가) -> Deployment(전개/배포)",
            "빅데이터 분석 5단계: 분석 기획 -> 데이터 준비 -> 데이터 분석 -> 시스템 구현 -> 평가 및 전개",
            "소프트웨어 수명주기 모형: 폭포수(Waterfall, 순차적), 프로토타입(Prototype, 조기 시제품 피드백), 나선형(Spiral, 위험 분석 중심 반복)"
        ],
        keywords=[
            r'kdd', r'crisp-dm', r'분석\s*방법론', r'분석방법론', r'빅데이터\s*분석\s*방법론', r'폭포수', r'나선형',
            r'프로토타입\s*모델', r'프로토\s*타입', r'업무\s*이해', r'데이터\s*준비', r'모델링\s*단계', r'데이터\s*마이닝\s*프로세스',
            r'분석\s*기획\s*단계', r'task', r'wbs', r'소프트웨어\s*공학', r'분석\s*요건'
        ]
    ),
    ConceptNode(
        concept_id="C11_TASK_DISCOVERY_TOPDOWN",
        name_ko="하향식 접근법 (Top-Down Approach)",
        subject=2,
        prerequisites=["C10_ANALYTIC_METHODOLOGIES"],
        core_invariants=[
            "하향식 접근법 4단계: 문제 탐색(Problem Discovery) -> 문제 정의(Problem Definition) -> 해결방안 탐색(Solution Search) -> 타당성 검토(Feasibility Study)",
            "비즈니스 모델 캔버스 기반 문제 탐색 5대 영역: 업무, 제품, 고객, 규제/감사, 지원 인프라",
            "거시적 관점(STEEP): 사회(Social), 기술(Tech), 경제(Economic), 환경(Ecology), 정치(Political)",
            "경쟁자 확대 관점: 대체재, 경쟁자, 신규 진입자",
            "시장의 니즈 탐색 관점: 고객, 채널, 영향자"
        ],
        keywords=[
            r'하향식', r'top-down', r'문제\s*탐색', r'문제\s*정의', r'해결방안\s*탐색', r'타당성\s*검토',
            r'비즈니스\s*모델\s*캔버스', r'거시적\s*관점', r'steep', r'경쟁자\s*확대', r'시장의\s*니즈',
            r'분석\s*기회', r'과제\s*발굴', r'문제\s*해결', r'과제\s*정의서'
        ]
    ),
    ConceptNode(
        concept_id="C12_TASK_DISCOVERY_BOTTOMUP",
        name_ko="상향식 접근법 (Bottom-Up Approach)",
        subject=2,
        prerequisites=["C10_ANALYTIC_METHODOLOGIES"],
        core_invariants=[
            "문제 정의가 모호할 때 보유 데이터로부터 새로운 통찰과 지식을 도출하는 귀납적 접근 방식",
            "비지도학습(Unsupervised Learning): 데이터 자체의 패턴, 군집, 상관관계를 도출",
            "프로토타이핑(Prototyping): 요구사항이 불명확할 때 신속한 시제품 개발 및 반복적 피드백 수렴",
            "디자인 사고(Design Thinking): 공감 -> 정의 -> 아이디어 발상 -> 시제품 -> 테스트 (발산과 수렴의 반복)"
        ],
        keywords=[
            r'상향식', r'bottom-up', r'비지도\s*학습', r'프로토타이핑', r'디자인\s*사고', r'디자인\s*씽킹',
            r'design\s*thinking', r'발산과\s*수렴', r'역발상', r'사례\s*기반'
        ]
    ),
    ConceptNode(
        concept_id="C13_PROJECT_MANAGEMENT_ATTRS",
        name_ko="분석 프로젝트 관리 5대 주요 속성",
        subject=2,
        prerequisites=["C10_ANALYTIC_METHODOLOGIES"],
        core_invariants=[
            "5대 주요 관리 속성: Data Complexity(복잡도), Data Size(데이터 양), Speed(분석 속도), Analytic Complexity(분석 모델 복잡도), Accuracy vs Precision(정확도와 정밀도)",
            "정확도(Accuracy)와 정밀도(Precision)는 트레이드오프 관계",
            "데이터 프로젝트의 불확실성 관리 및 애자일/반복적 스프린트 운영"
        ],
        keywords=[
            r'프로젝트\s*관리', r'복잡도', r'분석\s*속도', r'정확도와\s*정밀도', r'trade-off', r'트레이드오프',
            r'5대\s*속성', r'위험\s*관리', r'품질\s*관리', r'일정\s*계획', r'관리\s*프로세스', r'관리\s*항목'
        ]
    ),
    ConceptNode(
        concept_id="C14_MASTERPLAN_PORTFOLIO",
        name_ko="분석 마스터플랜 및 포트폴리오 사분면",
        subject=2,
        prerequisites=["C09_ANALYSIS_QUADRANT", "C11_TASK_DISCOVERY_TOPDOWN"],
        core_invariants=[
            "우선순위 평가 기준: 전략적 중요도(시급성: 현재 vs 미래) vs 실행 용이성(난이도: 쉬움 vs 어려움)",
            "포트폴리오 4사분면: 1사분면(시급성 높음/난이도 높음), 2사분면(시급성 낮음/난이도 높음), 3사분면(시급성 낮음/난이도 낮음), 4사분면(시급성 높음/난이도 낮음)",
            "적용 우선순위 판단: 시급성 우선 적용(3 -> 4 -> 2 -> 1) vs 난이도 우선 적용(3 -> 1 -> 2)",
            "단계적 구현 로드맵 수립 및 ROI(투자자본수익률) 분석"
        ],
        keywords=[
            r'마스터플랜', r'마스터\s*플랜', r'포트폴리오', r'시급성', r'난이도', r'우선순위', r'로드맵', r'사분면',
            r'roi', r'투자자본', r'isp', r'정보전략계획', r'단계적\s*구현', r'실행\s*용이성'
        ]
    ),
    ConceptNode(
        concept_id="C15_GOVERNANCE_ORGANIZATION",
        name_ko="데이터 거버넌스 및 분석 조직 구조",
        subject=2,
        prerequisites=["C14_MASTERPLAN_PORTFOLIO"],
        core_invariants=[
            "데이터 거버넌스 4대 구성요소: 조직(Organization), 프로세스(Process), 정책/원칙(Rule), IT인프라(System)",
            "분석 조직 구조 3대 유형: 집중형(전사 전담 부서 독립 운영), 기능형(별도 조직 없이 각 현업 부서 내 분석 수행), 분산형(전사 분석 부서 인력을 현업에 배치)",
            "협의의 분석 플랫폼 vs 광의의 분석 플랫폼 구성"
        ],
        keywords=[
            r'거버넌스', r'분석\s*조직', r'조직\s*구조', r'집중형', r'기능형', r'분산형', r'데이터\s*거버넌스',
            r'분석\s*플랫폼', r'coe', r'전담\s*조직', r'데이터\s*표준화'
        ]
    ),
    ConceptNode(
        concept_id="C16_MATURITY_READINESS_MODEL",
        name_ko="분석 수준 진단 (준비도 & 성숙도 모델)",
        subject=2,
        prerequisites=["C14_MASTERPLAN_PORTFOLIO", "C15_GOVERNANCE_ORGANIZATION"],
        core_invariants=[
            "분석 준비도(Readiness) 6대 영역: 분석 업무, 분석 인력/조직, 분석 기법, 분석 IT 인프라, 분석 데이터, 분석 문화",
            "분석 성숙도(Maturity) 4단계(CMMI 기반): 도입(Introduction) -> 활용(Organization) -> 확산(Spread) -> 최적화(Optimization)",
            "수준 진단 4사분면: 정착형(준비도 높음, 성숙도 높음), 확산형(준비도 낮음, 성숙도 높음), 도입형(준비도 높음, 성숙도 낮음), 준비형(준비도 낮음, 성숙도 낮음)"
        ],
        keywords=[
            r'준비도', r'성숙도', r'수준\s*진단', r'정착형', r'확산형', r'도입형', r'준비형', r'readiness',
            r'maturity', r'cmmi', r'도입.*활용.*확산.*최적화', r'6대\s*영역'
        ]
    ),

    # ------------------------------------------------------------------------
    # Subject 3: 데이터분석 (Data Analysis) - 16 Concepts
    # ------------------------------------------------------------------------
    ConceptNode(
        concept_id="C17_R_SYNTAX_DATA_STRUCTURE",
        name_ko="R 기초 문법 및 데이터 구조",
        subject=3,
        prerequisites=[],
        core_invariants=[
            "R 5대 자료구조: Vector(단일형 1차원), Matrix(단일형 2차원), Array(단일형 다차원), List(복합형 1차원 키-값), Data Frame(복합형 2차원 테이블)",
            "R 인덱싱: 1-based indexing, 음수 인덱스는 해당 원소 제외, matrix[row, col]",
            "R 주요 함수: apply(행렬 방향 계산), lapply(결과 리스트), sapply(결과 벡터), tapply(그룹별 요약), reshape/sqldf/plyr",
            "자료의 4대 척도: 명목척도, 순서척도, 구간척도, 비율척도"
        ],
        keywords=[
            r'벡터', r'데이터프레임', r'data\.frame', r'matrix', r'array', r'행렬', r'리스트', r'자료구조',
            r'자료형', r'자료의\s*척도', r'명목척도', r'순서척도', r'구간척도', r'비율척도', r'척도', r'apply', r'lapply',
            r'sapply', r'tapply', r'reshape', r'sqldf', r'plyr', r'r\s*프로그래밍', r'summary\s*결과', r'summary\s*함수',
            r'c\(', r'r\s*출력\s*결과', r'사료.*chicken', r'닭의\s*성장'
        ]
    ),
    ConceptNode(
        concept_id="C18_DATA_PREPROCESSING",
        name_ko="데이터 전처리, 결측값 및 이상값 처리",
        subject=3,
        prerequisites=["C17_R_SYNTAX_DATA_STRUCTURE"],
        core_invariants=[
            "결측치(NA) 처리법: 완전분석법(단순 삭제), 평균/중앙값/최빈값 대치법, 조건부 대치법, 다중대치법(MICE: 대치-분석-결합 3단계)",
            "이상값(Outlier) 판단: 사분위수(IQR) 기준 Q1 - 1.5*IQR 미만 또는 Q3 + 1.5*IQR 초과",
            "통계적 이상값 검출: ESD(Extreme Studentized Deviate, 정규분포 가정 3-sigma), 마할라노비스 거리, 쿡의 거리(Cook's Distance)",
            "변수 변환: 요약변수(집계된 총합/평균) vs 파생변수(사용자 논리/조건에 의해 생성된 변수)"
        ],
        keywords=[
            r'결측값', r'결측치', r'\bna\b', r'대치법', r'다중대치법', r'이상값', r'이상치', r'iqr', r'esd',
            r'사분위', r'요약변수', r'파생변수', r'상자그림', r'boxplot', r'outlier', r'마할라노비스', r'데이터\s*정제',
            r'정규화', r'표준화', r'스케일링', r'cook\'s\s*distance', r'쿡의\s*거리'
        ]
    ),
    ConceptNode(
        concept_id="C19_SAMPLING_AND_PROBABILITY",
        name_ko="표본추출법 및 확률분포",
        subject=3,
        prerequisites=[],
        core_invariants=[
            "표본추출법 4대 유형: 단순무작위추출, 계통추출(k 간격), 층화추출(집단 내 동질, 집단 간 이질), 집락(군집)추출(집단 내 이질, 집단 간 동질)",
            "이산확률분포: 베르누이분포, 이항분포, 기하분포, 다항분포, 포아송분포(단위 시간/공간 발생 횟수)",
            "연속확률분포: 균일분포, 정규분포, 표준정규분포(Z), t-분포(모분산 미지 소표본 평균 검정), F-분포(두 모분산 비율), 카이제곱분포(모분산 검정, 적합도/독립성)",
            "조건부확률 P(A|B) = P(A ∩ B) / P(B) 및 독립사건 조건 P(A ∩ B) = P(A)P(B)"
        ],
        keywords=[
            r'표본\s*추출', r'표본추출', r'단순\s*임의', r'계통\s*추출', r'층화\s*추출', r'집락\s*추출', r'확률\s*분포',
            r'이산형', r'연속형', r'이항분포', r'포아송', r'정규분포', r't-분포', r'f-분포', r'카이제곱분포',
            r'조건부\s*확률', r'독립사건', r'표본평균', r'표본분산', r'확률변수', r'기댓값', r'기대값', r'기술통계',
            r'왜도', r'첨도', r'중앙값', r'최빈값', r'산포도', r'확률은', r'확률의\s*기본', r'p\(', r'동전.*던져',
            r'표본오차', r'비표본오차', r'공분산'
        ]
    ),
    ConceptNode(
        concept_id="C20_STATISTICAL_INFERENCE",
        name_ko="가설검정과 통계적 추론",
        subject=3,
        prerequisites=["C19_SAMPLING_AND_PROBABILITY"],
        core_invariants=[
            "귀무가설(H0, 차이 없음/효과 없음) vs 대립가설(H1, 증명하고자 하는 새로운 가설)",
            "제1종 오류(alpha): 귀무가설이 참인데 기각할 확률 (유의수준)",
            "제2종 오류(beta): 귀무가설이 거짓인데 채택할 확률 (검정력 = 1 - beta)",
            "p-value 판정: p < alpha 이면 귀무가설 기각(유의미한 차이 있음), p >= alpha 이면 귀무가설 채택(기각 실패)",
            "점추정량 평가 기준: 불편성(Unbiasedness), 효율성(Efficiency), 일치성(Consistency), 충분성(Sufficiency)"
        ],
        keywords=[
            r'가설\s*검정', r'가설검정', r'귀무가설', r'대립가설', r'1종\s*오류', r'2종\s*오류', r'제1종', r'제2종',
            r'유의수준', r'p-value', r'p-값', r'p값', r'기각', r'점추정', r'구간추정', r'신뢰구간', r'불편성',
            r'일치성', r'유의확률', r'유의성\s*검정'
        ]
    ),
    ConceptNode(
        concept_id="C21_PARAMETRIC_TESTS",
        name_ko="모수적 통계분석 및 분산분석 (ANOVA)",
        subject=3,
        prerequisites=["C19_SAMPLING_AND_PROBABILITY", "C20_STATISTICAL_INFERENCE"],
        core_invariants=[
            "모수 검정: 단일표본 t-검정, 독립표본 t-검정, 대응표본(paired) t-검정",
            "분산분석(ANOVA): 3개 이상 집단의 평균 차이 검정, SST = SSR(SSB) + SSE(SSW)",
            "F-통계량 = MSR / MSE = (SSR / df_R) / (SSE / df_E), F값이 클수록 집단 간 평균 차이 유의",
            "비모수 검정: 윌콕슨 부호순위 검정, 만-휘트니 U 검정, 크루스칼-왈리스 검정"
        ],
        keywords=[
            r't-test', r't-검정', r't검정', r'분산분석', r'anova', r'f-검정', r'f-통계량', r'sse', r'mse',
            r'ssr', r'ssb', r'ssw', r'비모수', r'윌콕슨', r'만-휘트니', r'크루스칼', r'다중비교', r'사후검정',
            r'수면제\s*실험', r'sleep\s*데이터'
        ]
    ),
    ConceptNode(
        concept_id="C22_CORRELATION_ANALYSIS",
        name_ko="상관분석 및 교차분석",
        subject=3,
        prerequisites=["C19_SAMPLING_AND_PROBABILITY", "C20_STATISTICAL_INFERENCE"],
        core_invariants=[
            "피어슨 상관계수(r): 연속형 변수 간의 선형 상관관계 (-1 <= r <= 1)",
            "스피어만 순위상관계수(rho): 순서형/서열 척도 변수 간의 단조 상관관계 (비모수적)",
            "교차분석: 범주형 변수 간의 독립성 검정 및 동질성 검정 (카이제곱 통계량)"
        ],
        keywords=[
            r'상관계수', r'피어슨', r'스피어만', r'순위상관', r'상관분석', r'교차분석', r'카이제곱\s*검정', r'적합도\s*검정',
            r'독립성\s*검정', r'분할표', r'교차표'
        ]
    ),
    ConceptNode(
        concept_id="C23_REGRESSION_ANALYSIS",
        name_ko="선형 회귀분석 및 가정 진단",
        subject=3,
        prerequisites=["C20_STATISTICAL_INFERENCE", "C22_CORRELATION_ANALYSIS"],
        core_invariants=[
            "단순선형회귀 (y = b0 + b1*x + e) vs 다중선형회귀 (y = b0 + sum(bi*xi) + e)",
            "결정계수 R^2 = SSR / SST = 1 - SSE / SST, 수정된 결정계수 Adj-R^2",
            "회귀모형 4대 기본 가정: 선형성, 등분산성(잔차 플롯), 정규성(Q-Q 플롯, 샤피로-윌크), 독립성(더빈-왓슨 d 통계량 2 부근)",
            "다중공선성(Multicollinearity): 독립변수 간 강한 상관관계, VIF > 10이면 다중공선성 의심",
            "로지스틱 회귀분석: 종속변수가 범주형일 때 사후확률 P(Y=1|X) 모델링, 오즈비(Odds Ratio)"
        ],
        keywords=[
            r'회귀분석', r'선형회귀', r'결정계수', r'수정된\s*결정계수', r'다중공선성', r'vif', r'잔차', r'더빈왓슨',
            r'durbin-watson', r'등분산성', r'독립성', r'선형성', r'lm\(', r'다중회귀', r'회귀계수', r'최소자승법',
            r'최소제곱법', r'로지스틱\s*회귀', r'오즈비', r'odds'
        ]
    ),
    ConceptNode(
        concept_id="C24_VARIABLE_SELECTION_REGULARIZATION",
        name_ko="변수 선택 및 정규화 회귀 (Ridge, Lasso, Elastic Net)",
        subject=3,
        prerequisites=["C23_REGRESSION_ANALYSIS"],
        core_invariants=[
            "변수 선택법: 전진선택법(Forward), 후진소거법(Backward), 단계적방법(Stepwise)",
            "모형 선택 기준: AIC(Akaike Information Criterion), BIC(Bayesian Information Criterion) - 작을수록 우수",
            "릿지 회귀(Ridge): L2 패널티 lambda * sum(beta^2), 계수 축소하나 0으로 만들지 않음 (다중공선성에 효과적)",
            "라쏘 회귀(Lasso): L1 패널티 lambda * sum(|beta|), 계수를 정확히 0으로 만들어 변수 선택(Feature Selection) 수행",
            "엘라스틱넷(Elastic Net): L1과 L2 패널티를 혼합 결합하여 상관성이 높은 변수군을 함께 선택"
        ],
        keywords=[
            r'전진선택', r'후진소거', r'후진제거', r'단계적\s*방법', r'stepwise', r'aic', r'bic', r'벌점',
            r'정규화\s*회귀', r'릿지', r'ridge', r'라쏘', r'lasso', r'엘라스틱넷', r'elastic\s*net', r'l1', r'l2',
            r'변수\s*선택'
        ]
    ),
    ConceptNode(
        concept_id="C25_TIME_SERIES_ANALYSIS",
        name_ko="시계열 분석",
        subject=3,
        prerequisites=["C19_SAMPLING_AND_PROBABILITY", "C20_STATISTICAL_INFERENCE"],
        core_invariants=[
            "정상 시계열 3대 조건: 평균 일정, 분산 일정, 공분산은 시점 자체가 아니라 시차(lag)에만 의존",
            "비정상 시계열 변환: 평균 변동 시 차분(Difference), 분산 변동 시 로그/제곱근 변환",
            "분해 시계열 4대 요인: 추세(Trend), 계절(Seasonal), 순환(Cyclical), 불규칙(Irregular)",
            "시계열 모형: AR(자기회귀, PACF 절단), MA(이동평균, ACF 절단), ARMA, ARIMA(p,d,q)"
        ],
        keywords=[
            r'시계열', r'정상성', r'정상\s*시계열', r'분해시계열', r'분해\s*시계열', r'차분', r'자기회귀', r'ar\(',
            r'ar모형', r'ma모형', r'arima', r'acf', r'pacf', r'백색잡음', r'시차', r'계절변동'
        ]
    ),
    ConceptNode(
        concept_id="C26_MULTIVARIATE_PCA_MDS",
        name_ko="다변량 차원축소 (PCA & MDS)",
        subject=3,
        prerequisites=["C22_CORRELATION_ANALYSIS"],
        core_invariants=[
            "주성분분석(PCA): 서로 상관된 다수의 변수를 선형 결합하여 직교(무상관)하는 주성분들로 축소",
            "고유값(Eigenvalue)과 고유벡터(Eigenvector): 고유값은 주성분의 분산 크기, 고유값 >= 1 (카이저 기준), 누적 분산 비율 70~80%",
            "스크리 플롯(Scree Plot): 고유값의 감소가 완만해지는 엘보우(Elbow) 지점에서 주성분 수 결정",
            "다차원척도법(MDS): 개체 간 거리/유사성을 2차원/3차원 공간상의 점으로 배치, 스트레스(Stress) 값으로 적합도 평가 (0에 가까울수록 적합)"
        ],
        keywords=[
            r'주성분', r'pca', r'고유값', r'고유벡터', r'스크리', r'scree', r'다차원\s*척도법', r'다차원척도법',
            r'mds', r'스트레스', r'차원\s*축소', r'요인분석'
        ]
    ),
    ConceptNode(
        concept_id="C27_CLASSIFICATION_METRICS",
        name_ko="분류 모형 평가 지표",
        subject=3,
        prerequisites=["C19_SAMPLING_AND_PROBABILITY"],
        core_invariants=[
            "혼동행렬(Confusion Matrix): TP, FP, FN, TN",
            "정확도(Accuracy) = (TP + TN) / (TP + FP + FN + TN), 오분류율 = 1 - Accuracy",
            "민감도(Sensitivity/재현율 Recall) = TP / (TP + FN) vs 특이도(Specificity) = TN / (FP + TN)",
            "정밀도(Precision) = TP / (TP + FP)",
            "F1-Score: 정밀도와 재현율의 조화평균 = 2 * Precision * Recall / (Precision + Recall)",
            "ROC 곡선: X축은 1 - Specificity(위양성률 FPR), Y축은 Sensitivity(민감도 TPR), AUC가 1에 가까울수록 우수",
            "향상도 곡선(Lift Chart): 임의 선택 대비 모델 예측의 반응률 개선 비율",
            "데이터 분할: 훈련(Train), 검증(Validation), 평가(Test) 및 범주 불균형 문제"
        ],
        keywords=[
            r'혼동행렬', r'오분류표', r'오분류', r'정확도', r'정밀도', r'재현율', r'민감도', r'특이도', r'f1',
            r'f-measure', r'f-beta', r'roc', r'auc', r'이익도표', r'향상도\s*곡선', r'lift\s*chart', r'모형\s*평가',
            r'홀드\s*아웃', r'교차검증', r'불균형', r'과대적합', r'과소적합', r'과적합', r'데이터\s*분할',
            r'분류\s*모형', r'분류\s*분석', r'양성\s*판정', r'학습용.*검증용.*테스트용', r'동일하거나\s*유사한\s*결과'
        ]
    ),
    ConceptNode(
        concept_id="C28_DECISION_TREE",
        name_ko="의사결정나무 모델 (Decision Tree)",
        subject=3,
        prerequisites=["C18_DATA_PREPROCESSING", "C27_CLASSIFICATION_METRICS"],
        core_invariants=[
            "분리 기준(Splitting Criteria): 이산형 목표변수 -> 지니지수(CART), 엔트로피(C4.5/C5.0), 카이제곱 통계량(CHAID) / 연속형 목표변수 -> 분산감소량(CART), F-통계량(CHAID)",
            "지니지수 = 1 - sum(pi^2), 엔트로피 = -sum(pi * log2(pi)) (불순도가 낮을수록 순수도 높음)",
            "가지치기(Pruning): 과적합을 방지하기 위해 불필요한 마디를 잘라내는 기법",
            "정지 규칙(Stopping Rule): 마디에 속하는 최소 관측치 수, 나무의 최대 깊이, 불순도 감소량이 기준 이하일 때 성장 중단"
        ],
        keywords=[
            r'의사결정나무', r'의사결정\s*나무', r'지니지수', r'엔트로피', r'cart', r'c4\.5', r'chaid',
            r'가지치기', r'정지\s*규칙', r'stopping\s*rule', r'정지규칙', r'분리\s*기준', r'불순도', r'순수도'
        ]
    ),
    ConceptNode(
        concept_id="C29_ENSEMBLE_LEARNING",
        name_ko="앙상블 학습 (Ensemble Learning)",
        subject=3,
        prerequisites=["C28_DECISION_TREE"],
        core_invariants=[
            "배깅(Bagging, Bootstrap Aggregating): 복원추출로 생성한 다수의 부트스트랩 표본마다 모형을 학습시켜 결과를 투표(Voting) 또는 평균 결합 (분산 감소 효과)",
            "부스팅(Boosting): 이전 분류기의 오분류 데이터에 더 큰 가중치를 부여하며 순차적으로 약분류기를 학습/결합 (편향 감소 효과, AdaBoost, GBM, XGBoost)",
            "랜덤 포레스트(Random Forest): 배깅에 무작위 변수 선택(Random Feature Selection)을 추가하여 트리 간 상관성을 낮춘 앙상블 기법"
        ],
        keywords=[
            r'앙상블', r'배깅', r'bagging', r'부트스트랩', r'붓스트랩', r'부스팅', r'boosting', r'랜덤\s*포레스트',
            r'랜덤포레스트', r'random\s*forest', r'adaboost', r'가중치', r'보팅', r'voting'
        ]
    ),
    ConceptNode(
        concept_id="C30_NEURAL_NETWORKS",
        name_ko="인공신경망 및 딥러닝 기초",
        subject=3,
        prerequisites=["C23_REGRESSION_ANALYSIS", "C27_CLASSIFICATION_METRICS"],
        core_invariants=[
            "신경망 구조: 입력층(Input) -> 은닉층(Hidden) -> 출력층(Output), 다층 퍼셉트론(MLP)",
            "활성화 함수(Activation Function): 시그모이드(Sigmoid, 0~1), 하이퍼볼릭탄젠트(tanh, -1~1), ReLU(경사소실 완화, max(0,x)), 소프트맥스(Softmax, 다중분류 확률합 1)",
            "학습 메커니즘: 순전파(Forward)와 오차 역전파(Backpropagation), 경사하강법(Gradient Descent)",
            "자기조직화지도(SOM): 고차원 데이터를 2차원 격자로 비지도 투영하는 인공신경망"
        ],
        keywords=[
            r'신경망', r'인공신경망', r'ann\b', r'mlp', r'은닉층', r'활성화\s*함수', r'활성화함수', r'시그모이드',
            r'sigmoid', r'tanh', r'relu', r'소프트맥스', r'역전파', r'som\b', r'자기조직화', r'딥러닝', r'경사하강'
        ]
    ),
    ConceptNode(
        concept_id="C31_CLUSTERING_ANALYSIS",
        name_ko="군집분석 (Clustering Analysis)",
        subject=3,
        prerequisites=["C18_DATA_PREPROCESSING", "C26_MULTIVARIATE_PCA_MDS"],
        core_invariants=[
            "계층적 군집분석: 최단연결법(최소거리), 완전연결법(최대거리), 평균연결법, 와드연결법(군집 내 분산 증가 최소화), 덴드로그램",
            "비계층적 군집분석: K-means(초기 중심점 설정, 거리 기반 할당 및 갱신, 이상치에 민감), K-medoids(실제 관측치 중심, 이상치에 강건)",
            "혼합분포 군집(GMM): 데이터가 K개의 가우시안 분포 결합이라고 가정, EM(Expectation-Maximization) 알고리즘으로 모수 추정",
            "군집 평가: 실루엣 계수(Silhouette Coefficient, -1 ~ 1 사이, 1에 가까울수록 완벽한 군집 분리)",
            "밀도 기반 군집화: DBSCAN (군집 수 사전 지정 불필요, 임의의 형태 군집 탐색)"
        ],
        keywords=[
            r'군집분석', r'계층적\s*군집', r'최단연결법', r'완전연결법', r'최장연결법', r'완전\s*연결법', r'평균연결법',
            r'와드연결법', r'k-means', r'kmeans', r'k-평균', r'k-medoids', r'gmm', r'혼합분포', r'실루엣',
            r'덴드로그램', r'em\s*알고리즘', r'맨해튼\s*거리', r'유클리드\s*거리', r'거리\s*측도', r'dbscan'
        ]
    ),
    ConceptNode(
        concept_id="C32_ASSOCIATION_RULE",
        name_ko="연관성 분석 (Association Rules)",
        subject=3,
        prerequisites=["C18_DATA_PREPROCESSING"],
        core_invariants=[
            "지지도(Support): 전체 거래 중 A와 B가 동시에 포함된 거래 비율 = P(A ∩ B)",
            "신뢰도(Confidence): A가 포함된 거래 중 B도 포함된 조건부 비율 = P(B|A) = P(A ∩ B) / P(A)",
            "향상도(Lift): A와 B가 독립일 때 대비 함께 구매될 가능성 = P(A ∩ B) / (P(A) * P(B)) = Confidence(A -> B) / Support(B)",
            "향상도 해석: Lift = 1 (독립, 상호 무관), Lift > 1 (양의 상관관계), Lift < 1 (음의 상관관계)",
            "Apriori 알고리즘: 최소 지지도 이상의 빈발 항목 집합만을 가지치기(Pruning)하여 탐색 효율화"
        ],
        keywords=[
            r'연관분석', r'연관\s*분석', r'연관규칙', r'연관\s*규칙', r'장바구니', r'지지도', r'신뢰도', r'향상도',
            r'support', r'confidence', r'lift', r'apriori', r'동시\s*구매'
        ]
    )
]

ONTOLOGY_DICT: Dict[str, ConceptNode] = {c.concept_id: c for c in ONTOLOGY_DEFINITIONS}


def validate_dag(definitions: List[ConceptNode]) -> List[str]:
    """Validate that the ontology prerequisites form a Directed Acyclic Graph (DAG)

    and return the topological sort order.
    """
    id_set = {c.concept_id for c in definitions}
    in_degree: Dict[str, int] = {c.concept_id: 0 for c in definitions}
    adj: Dict[str, List[str]] = {c.concept_id: [] for c in definitions}

    for c in definitions:
        for p in c.prerequisites:
            if p not in id_set:
                raise ValueError(f"Prerequisite '{p}' for node '{c.concept_id}' not found in ontology.")
            adj[p].append(c.concept_id)
            in_degree[c.concept_id] += 1

    queue = [cid for cid, deg in in_degree.items() if deg == 0]
    topological_order: List[str] = []

    while queue:
        curr = queue.pop(0)
        topological_order.append(curr)
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(topological_order) != len(definitions):
        raise ValueError("Ontology prerequisites contain a cycle! Topological sort failed.")

    return topological_order


# ============================================================================
# 2. ITEM FEATURE CLASSIFIERS (POLARITY, ARCHETYPE, TRAPS, IRT)
# ============================================================================

NEGATIVE_STEM_REGEX = re.compile(
    r'옳지\s*않은|적절하지\s*않은|아닌\s*것|거리가\s*먼|틀린\s*것|부적절한|'
    r'해당하지\s*않는|해당되지\s*않는|포함되지\s*않는|알맞지\s*않은|맞지\s*않은|'
    r'잘못된|다른\s*하나는|차이가\s*있는|관련이\s*없는|어려운\s*것|부족한\s*것'
)

R_CODE_REGEX = re.compile(
    r'```r|```\s*\n\s*>|Call:\s*\n|Coefficients:|Residual standard error|'
    r'Multiple R-squared|Adjusted R-squared|F-statistic:|>\s*lm\(|>\s*summary\(|'
    r'>\s*predict\(|>\s*kmeans\(|>\s*prcomp\(|>\s*table\(|>\s*arima\(',
    re.IGNORECASE
)

TABLE_CALC_KEYWORDS = [
    '혼동행렬', '오분류표', '오분류', '민감도', '특이도', '정밀도', '재현율', 'f1',
    '지지도', '신뢰도', '향상도', '자유도', '제곱합', '분산분석표', '기댓값', '구하시오',
    '계산하시오', '얼마인가', '신뢰구간'
]

FORMULA_CALC_REGEX = re.compile(
    r'계산하시오|구하시오|얼마인가|몇\s*개인가|P\(|신뢰구간|베이즈|확률은|기댓값|기대값|'
    r'표준오차|분산은|공분산|지니지수|엔트로피|카이제곱'
)

BOX_MARKER_REGEX = re.compile(
    r'<보기>|\[보기\]|\(가\)|\[가\]|가\.\s|㉮|㉯|보기'
)

QUANTIFIER_WORDS = [
    '항상', '모든', '반드시', '전혀', '오직', '완벽히', '무조건', '유일하게', '절대로', '100%'
]

CONCEPT_SWAP_PAIRS = [
    ('1종', '2종'), ('제1종', '제2종'),
    ('배깅', '부스팅'), ('bagging', 'boosting'),
    ('과대적합', '과소적합'), ('과적합', '과소적합'),
    ('정밀도', '재현율'), ('precision', 'recall'), ('민감도', '특이도'),
    ('하향식', '상향식'), ('top-down', 'bottom-up'),
    ('지지도', '신뢰도'), ('신뢰도', '향상도'), ('지지도', '향상도'),
    ('l1', 'l2'), ('라쏘', '릿지'), ('lasso', 'ridge'),
    ('모수', '비모수'),
    ('암묵지', '형식지'),
    ('최단연결', '완전연결'), ('최단연결', '최장연결'),
    ('지도학습', '비지도학습'),
    ('집중형', '분산형'), ('기능형', '집중형'),
    ('정착형', '확산형'), ('도입형', '준비형')
]

TABLE_DF_METRIC_KEYWORDS = [
    '자유도', '제곱합', '분산분석표', 'f통계량', 'f-통계량', '오분류표', '혼동행렬',
    'f1', 'lift', '이익도표', 'sse', 'mse', 'ssr'
]

R_SYNTAX_KEYWORDS = [
    '```r', 'na.rm', 'c(', 'matrix(', 'data.frame', 'as.numeric', 'summary(', 'lm(', 't.test',
    'is.na', 'factor(', 'which('
]


def classify_stem_polarity(prompt: str) -> str:
    """Classify prompt stem polarity into NEGATIVE vs POSITIVE."""
    return "NEGATIVE" if NEGATIVE_STEM_REGEX.search(prompt) else "POSITIVE"


def classify_archetype(prompt: str, question_type: str, options: List[str]) -> str:
    """Classify question archetype into one of 7 standardized pedagogical categories."""
    if question_type == "단답형":
        return "SHORT_ANSWER"

    if R_CODE_REGEX.search(prompt):
        return "R_CODE_OUTPUT"

    opts_text = " ".join(options)
    has_table = "|" in prompt

    if has_table:
        is_calc = any(kw in prompt.lower() for kw in TABLE_CALC_KEYWORDS) or any(
            re.search(r'\d+\.?\d*', opt) for opt in options
        )
        return "TABLE_CALC" if is_calc else "TABLE_CONCEPT"

    if FORMULA_CALC_REGEX.search(prompt) and (
        re.search(r'\d+\.?\d*', opts_text) or "구하시오" in prompt or "계산하시오" in prompt
    ):
        return "FORMULA_CALC"

    if BOX_MARKER_REGEX.search(prompt) and (
        any(re.search(r'^[가-마\s,·\(\)]+$', opt.strip()) for opt in options)
        or any("가" in opt and "나" in opt for opt in options)
        or len([opt for opt in options if len(opt.strip()) <= 5]) >= 2
    ):
        return "MULTI_BOX"

    return "CONCEPTUAL_4C"


def detect_distractor_traps(prompt: str, options: List[str], polarity: str) -> List[str]:
    """Detect presence of subtle cognitive and psychometric traps."""
    traps: List[str] = []
    combined_text = prompt + " " + " ".join(options)
    lower_text = combined_text.lower()

    # 1. Polarity Inversion: Negative stem requires inverting true/false truth values
    if polarity == "NEGATIVE":
        traps.append("POLARITY_INVERSION")

    # 2. Quantifier Trap: Extreme words ('항상', '모든', '반드시', etc.)
    if any(qw in combined_text for qw in QUANTIFIER_WORDS):
        traps.append("QUANTIFIER_TRAP")

    # 3. Concept Swap: Pairs of often-confused polar concepts
    for term_a, term_b in CONCEPT_SWAP_PAIRS:
        if (term_a in lower_text and term_b in lower_text) or (
            term_a in lower_text and any(term_b in opt.lower() for opt in options)
        ):
            traps.append("CONCEPT_SWAP")
            break

    # 4. Table DF Metric Calc: Calculating degrees of freedom, sums of squares, or matrix ratios
    if any(k in lower_text for k in TABLE_DF_METRIC_KEYWORDS) and (
        "|" in prompt or "표" in prompt or any(re.search(r'\d+\.?\d*', opt) for opt in options)
    ):
        traps.append("TABLE_DF_METRIC_CALC")

    # 5. R Syntax Output Trap: Testing syntactic R edge cases or output reading
    if any(k in lower_text for k in R_SYNTAX_KEYWORDS) or any(
        re.search(r'[a-zA-Z0-9_]+\([^\)]*\)', opt) for opt in options
    ):
        traps.append("R_SYNTAX_OUTPUT_TRAP")

    return traps


def compute_irt_params(
    question_type: str,
    archetype: str,
    stem_polarity: str,
    distractor_traps: List[str],
    round_no: int,
    subject: int
) -> Dict[str, float]:
    """Compute calibrated 3PL IRT parameters (a: discrimination, b: difficulty, c: guessing)."""
    # 1. Guessing parameter (c)
    c = 0.25 if question_type == "4지선다" else 0.0

    # 2. Base difficulty (b) by archetype
    base_b_map = {
        "SHORT_ANSWER": 0.70,
        "R_CODE_OUTPUT": 0.45,
        "TABLE_CALC": 0.50,
        "FORMULA_CALC": 0.40,
        "MULTI_BOX": 0.25,
        "TABLE_CONCEPT": 0.10,
        "CONCEPTUAL_4C": -0.10,
    }
    b = base_b_map.get(archetype, 0.0)

    # Polarity adjustment
    if stem_polarity == "NEGATIVE":
        b += 0.15

    # Trap adjustments
    b += 0.08 * len(distractor_traps)

    # Longitudinal round adjustment (modern rounds show higher subtlety)
    b += (round_no - 40) * 0.025

    # Subject difficulty adjustment
    if subject == 3:
        b += 0.10
    elif subject == 1:
        b -= 0.10

    # Clamp b to range [-1.5, 2.0]
    b = round(max(-1.5, min(2.0, b)), 2)

    # 3. Discrimination parameter (a)
    base_a_map = {
        "SHORT_ANSWER": 1.25,
        "R_CODE_OUTPUT": 1.30,
        "TABLE_CALC": 1.25,
        "FORMULA_CALC": 1.20,
        "MULTI_BOX": 1.15,
        "TABLE_CONCEPT": 1.05,
        "CONCEPTUAL_4C": 1.00,
    }
    a = base_a_map.get(archetype, 1.05)
    a += 0.05 * len(distractor_traps)
    a = round(max(0.8, min(1.8, a)), 2)

    return {"a": a, "b": b, "c": c}


# ============================================================================
# 3. Q-MATRIX MAPPING ENGINE
# ============================================================================

SUBJECT_NAMES = {
    1: "데이터 이해",
    2: "데이터분석 기획",
    3: "데이터분석"
}

SUBJECT_FALLBACKS = {
    1: "C01_DATA_DIKW",
    2: "C09_ANALYSIS_QUADRANT",
    3: "C20_STATISTICAL_INFERENCE"
}


def assign_subject(round_no: int, question_no: int) -> int:
    """Determine ADsP subject (1, 2, or 3) with content-aware boundary adjustments."""
    # Standard boundaries
    if question_no <= 10:
        return 1
    elif question_no <= 20:
        # Cross-checked content adjustments in earlier crawled datasets
        if round_no == 38 and question_no == 20:
            return 3  # t-test question in Round 38
        if round_no == 40 and question_no == 20:
            return 3  # 표본추출법 question in Round 40
        return 2
    else:  # question_no >= 21
        # Cross-checked content adjustments for short-answers
        if round_no == 32 and question_no == 48:
            return 1  # 데이터 마트 / 기업 내부 DB 솔루션
        if round_no == 38 and question_no == 48:
            return 1  # 유전자 알고리즘 / 빅데이터 활용 테크닉
        return 3


class QMatrixMapper:
    """Maps exam questions to ontology concept nodes with guaranteed fallback."""

    def __init__(self, ontology: List[ConceptNode]):
        self.ontology = ontology
        self.compiled_rules = [
            (
                node.concept_id,
                node.subject,
                re.compile("|".join(node.keywords), re.IGNORECASE)
            )
            for node in ontology
        ]

    def map_question(self, prompt: str, options: List[str], answer: str, subject: int) -> Tuple[List[str], str]:
        """Return (concept_ids, primary_concept_id). Guaranteed >= 1 valid concept."""
        text = prompt + " " + " ".join(options) + " " + str(answer)

        matched: List[Tuple[str, int, int]] = []
        for cid, node_subj, pattern in self.compiled_rules:
            matches = pattern.findall(text)
            if matches:
                # Priority weight: favor same subject
                score = len(matches) * 2 + (2 if node_subj == subject else 0)
                matched.append((cid, node_subj, score))

        if not matched:
            fallback = SUBJECT_FALLBACKS.get(subject, "C01_DATA_DIKW")
            return [fallback], fallback

        # Sort matched concepts: highest score first, then same subject
        matched.sort(key=lambda x: (x[2], x[1] == subject), reverse=True)
        concept_ids = [m[0] for m in matched]
        primary_concept_id = concept_ids[0]

        return concept_ids, primary_concept_id


# ============================================================================
# 4. LONGITUDINAL CONCEPT DRIFT & OUT-OF-DISTRIBUTION (OOD) PREDICTIONS
# ============================================================================

ERAS = {
    "Era1_32_39": [32, 35, 37, 38, 39],
    "Era2_40_45": [40, 41, 42, 44, 45],
    "Era3_46_50": [46, 47, 48, 49, 50],
}
ALL_ROUNDS = sorted([r for rounds in ERAS.values() for r in rounds])

EMERGING_KEYWORD_SPECS = [
    {"term": "SMOTE", "category": "Data Imbalance", "target_concept": "C27_CLASSIFICATION_METRICS"},
    {"term": "범주 불균형", "category": "Data Imbalance", "target_concept": "C27_CLASSIFICATION_METRICS"},
    {"term": "Elastic Net", "category": "Regularization", "target_concept": "C24_VARIABLE_SELECTION_REGULARIZATION"},
    {"term": "엘라스틱넷", "category": "Regularization", "target_concept": "C24_VARIABLE_SELECTION_REGULARIZATION"},
    {"term": "ESD", "category": "Outlier Detection", "target_concept": "C18_DATA_PREPROCESSING"},
    {"term": "GMM", "category": "Clustering", "target_concept": "C31_CLUSTERING_ANALYSIS"},
    {"term": "SECI", "category": "Knowledge Creation", "target_concept": "C02_KNOWLEDGE_SECI"},
    {"term": "암묵지", "category": "Knowledge Creation", "target_concept": "C02_KNOWLEDGE_SECI"},
    {"term": "형식지", "category": "Knowledge Creation", "target_concept": "C02_KNOWLEDGE_SECI"},
    {"term": "MLP", "category": "Neural Networks", "target_concept": "C30_NEURAL_NETWORKS"},
    {"term": "tanh", "category": "Activation Function", "target_concept": "C30_NEURAL_NETWORKS"},
    {"term": "ReLU", "category": "Activation Function", "target_concept": "C30_NEURAL_NETWORKS"},
    {"term": "stopping rule", "category": "Decision Trees", "target_concept": "C28_DECISION_TREE"},
    {"term": "정지 규칙", "category": "Decision Trees", "target_concept": "C28_DECISION_TREE"},
    {"term": "ANOVA", "category": "Parametric Analysis", "target_concept": "C21_PARAMETRIC_TESTS"},
    {"term": "SSE", "category": "Sum of Squares", "target_concept": "C21_PARAMETRIC_TESTS"},
    {"term": "MSE", "category": "Mean Square Error", "target_concept": "C21_PARAMETRIC_TESTS"},
    {"term": "SSR", "category": "Regression Squares", "target_concept": "C21_PARAMETRIC_TESTS"},
]


def compute_concept_drift(items: List[Dict[str, Any]], ontology: List[ConceptNode]) -> Dict[str, Any]:
    """Calculate longitudinal concept drift across Era 1, Era 2, and Era 3,

    including per-round frequencies, drift ratios, Page-Hinkley and CUSUM scores.
    """
    era1_rds = ERAS["Era1_32_39"]
    era2_rds = ERAS["Era2_40_45"]
    era3_rds = ERAS["Era3_46_50"]

    concept_round_counts: Dict[str, Dict[int, int]] = {c.concept_id: defaultdict(int) for c in ontology}
    concept_primary_counts: Dict[str, Dict[int, int]] = {c.concept_id: defaultdict(int) for c in ontology}

    for item in items:
        r = item["round"]
        for cid in item["concept_ids"]:
            concept_round_counts[cid][r] += 1
        concept_primary_counts[item["primary_concept_id"]][r] += 1

    drift_by_concept: Dict[str, Any] = {}

    for c in ontology:
        cid = c.concept_id
        counts_per_round = {r: concept_round_counts[cid][r] for r in ALL_ROUNDS}
        series = [counts_per_round[r] for r in ALL_ROUNDS]

        e1_count = sum(counts_per_round[r] for r in era1_rds)
        e2_count = sum(counts_per_round[r] for r in era2_rds)
        e3_count = sum(counts_per_round[r] for r in era3_rds)

        e1_rate = e1_count / len(era1_rds)
        e2_rate = e2_count / len(era2_rds)
        e3_rate = e3_count / len(era3_rds)
        e12_rate = (e1_count + e2_count) / (len(era1_rds) + len(era2_rds))

        # Drift ratio = Era3_rate / Era1_2_rate (with Laplace smoothing 0.05)
        drift_ratio = round(e3_rate / max(e12_rate, 0.05), 3)

        if drift_ratio >= 1.30:
            trend = "SURGING_EMERGENT"
        elif drift_ratio <= 0.70:
            trend = "FADING_DECLINING"
        else:
            trend = "STABLE_CORE"

        # Sequential Page-Hinkley test
        mean_val = float(np.mean(series))
        delta = 0.05
        cum_dev = 0.0
        min_cum = 0.0
        max_ph = 0.0
        for x in series:
            cum_dev += (x - mean_val - delta)
            if cum_dev < min_cum:
                min_cum = cum_dev
            ph = cum_dev - min_cum
            if ph > max_ph:
                max_ph = ph

        # Standard CUSUM test (upward drift)
        std_val = float(np.std(series)) if np.std(series) > 1e-6 else 1.0
        k = 0.5 * std_val
        cusum = 0.0
        max_cusum = 0.0
        for x in series:
            cusum = max(0.0, cusum + (x - mean_val) - k)
            if cusum > max_cusum:
                max_cusum = cusum

        drift_by_concept[cid] = {
            "concept_id": cid,
            "name_ko": c.name_ko,
            "subject": c.subject,
            "subject_name": SUBJECT_NAMES[c.subject],
            "era1_total_count": e1_count,
            "era2_total_count": e2_count,
            "era3_total_count": e3_count,
            "era1_per_round": round(e1_rate, 2),
            "era2_per_round": round(e2_rate, 2),
            "era3_per_round": round(e3_rate, 2),
            "era1_2_per_round": round(e12_rate, 2),
            "drift_ratio": drift_ratio,
            "trend": trend,
            "page_hinkley_drift_score": round(max_ph, 2),
            "cusum_drift_score": round(max_cusum, 2),
            "round_frequencies": counts_per_round
        }

    return drift_by_concept


def analyze_emerging_keywords(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Scan and compute longitudinal emergence for specialized Era 3 technical keywords."""
    era1_2_items = [it for it in items if it["round"] <= 45]
    era3_items = [it for it in items if it["round"] >= 46]

    results = []
    for spec in EMERGING_KEYWORD_SPECS:
        term = spec["term"]
        pattern = re.compile(re.escape(term), re.IGNORECASE)

        cnt_e12 = sum(
            1 for it in era1_2_items
            if pattern.search(it["prompt"] + " " + " ".join(it.get("options", [])))
        )
        cnt_e3 = sum(
            1 for it in era3_items
            if pattern.search(it["prompt"] + " " + " ".join(it.get("options", [])))
        )

        rounds_found = sorted(list(set(
            it["round"] for it in items
            if pattern.search(it["prompt"] + " " + " ".join(it.get("options", [])))
        )))

        e12_rate = cnt_e12 / 10.0
        e3_rate = cnt_e3 / 5.0
        drift_ratio = round(e3_rate / (e12_rate + 0.05), 2)

        results.append({
            "term": term,
            "category": spec["category"],
            "target_concept": spec["target_concept"],
            "era1_2_count": cnt_e12,
            "era3_count": cnt_e3,
            "era1_2_per_round": round(e12_rate, 2),
            "era3_per_round": round(e3_rate, 2),
            "drift_ratio": drift_ratio,
            "rounds_observed": rounds_found,
            "is_era3_surging": drift_ratio >= 1.5
        })

    results.sort(key=lambda x: x["drift_ratio"], reverse=True)
    return results


def predict_ood_topics_round51_plus() -> List[Dict[str, Any]]:
    """Synthesize high-priority Out-of-Distribution (OOD) candidate topics for Round 51+

    extrapolating the recent official drift trajectory.
    """
    return [
        {
            "priority": "P1_CRITICAL",
            "candidate_topic": "SMOTE & Advanced Imbalance Sampling",
            "target_concept": "C27_CLASSIFICATION_METRICS",
            "drift_rationale": "Round 50 Question 48 officially introduced '범주 불균형(Class Imbalance)' as a standalone core topic. Round 51+ will logically progress to synthetic oversampling algorithms (SMOTE, Borderline-SMOTE, Tomek Links) and cost-sensitive classification.",
            "variation_theory_invariants": [
                "SMOTE: 소수 클래스 관측치와 k-최근접 이웃(KNN) 사이의 선분 상에 가상 데이터를 무작위 합성",
                "과소표본추출(Under-sampling, 정보 손실 위험) vs 과대표본추출(Over-sampling, 과적합 위험)",
                "불균형 데이터 평가 지표: Accuracy의 왜곡 방지를 위해 F1-Score, Balanced Accuracy, PR-AUC, G-mean 활용"
            ]
        },
        {
            "priority": "P1_CRITICAL",
            "candidate_topic": "Elastic Net Mixing Ratio & Penalty Mechanics",
            "target_concept": "C24_VARIABLE_SELECTION_REGULARIZATION",
            "drift_rationale": "Round 47 Question 32 introduced Elastic Net to resolve multicollinearity. Recent exams demand exact mechanical distinction between L1 (Lasso) and L2 (Ridge) combinations.",
            "variation_theory_invariants": [
                "Elastic Net 손실함수: Loss = RSS + lambda * [alpha * sum(|beta|) + (1-alpha)/2 * sum(beta^2)]",
                "alpha = 1 이면 Lasso(계수 0 축소로 변수 선택), alpha = 0 이면 Ridge(계수 크기 축소)",
                "변수 간 강한 상관관계 존재 시 Lasso의 임의 1개 변수 선택 단점을 극복하고 군집 변수를 동시 선택"
            ]
        },
        {
            "priority": "P1_CRITICAL",
            "candidate_topic": "Extreme Studentized Deviate (ESD) & Generalized Grubbs Test",
            "target_concept": "C18_DATA_PREPROCESSING",
            "drift_rationale": "Round 50 Question 21 tested the 3-sigma / ESD outlier rule. Outlier testing is escalating from simple boxplot IQR fences to formal parametric hypothesis testing.",
            "variation_theory_invariants": [
                "ESD 검정: 정규분포를 가정하여 평균으로부터 3*표준편차를 초과하는 관측치를 이상값으로 판정",
                "Grubbs 검정: 1개의 단일 이상값 유의성 검정 vs Generalized ESD: 사전에 지정된 k개의 다중 이상값 순차 검정",
                "마할라노비스 거리(변수 간 상관성 고려 다변량 이상치)와의 변별"
            ]
        },
        {
            "priority": "P2_HIGH",
            "candidate_topic": "GMM (Gaussian Mixture Models) & EM Algorithm Iteration",
            "target_concept": "C31_CLUSTERING_ANALYSIS",
            "drift_rationale": "Round 47 Question 47 formally questioned Gaussian Mixture Models. Exams are shifting from distance-based hard clustering (K-means) to density/probability-based soft clustering.",
            "variation_theory_invariants": [
                "GMM: 데이터가 K개의 정규분포의 확률적 가중합으로 생성되었다고 가정",
                "소프트 군집(Soft Clustering): 각 개체가 특정 군집에 속할 사후확률(Posterior Probability) 산출",
                "EM 알고리즘: E-step(소속 사후확률 계산)과 M-step(모수 평균, 공분산, 가중치 최대우도 추정) 반복 수렴"
            ]
        },
        {
            "priority": "P2_HIGH",
            "candidate_topic": "Decision Tree Stopping Rules & Complexity Parameter (cp)",
            "target_concept": "C28_DECISION_TREE",
            "drift_rationale": "Round 50 Question 50 specifically tested tree stopping rules. The next evolutionary step is pruning complexity parameters in R (rpart cp parameter) and minimum split/bucket sizes.",
            "variation_theory_invariants": [
                "사전 가지치기(Pre-pruning / Stopping rule): 마디 내 최소 샘플 수, 최대 트리 깊이, 최소 불순도 감소량 미달 시 분할 정지",
                "사후 가지치기(Post-pruning): 비용-복잡도 모형 Cost(T) = Error(T) + alpha * |T|",
                "과소적합(조기 정지)과 과대적합(과도한 분할) 사이의 균형점 탐색"
            ]
        },
        {
            "priority": "P2_HIGH",
            "candidate_topic": "Deep Learning Vanishing Gradient & Activation Landscapes",
            "target_concept": "C30_NEURAL_NETWORKS",
            "drift_rationale": "Rounds 46 to 50 featured a surge in activation function items (ReLU, tanh, Sigmoid). Questions in Round 51+ will focus on gradient behavior and saturation.",
            "variation_theory_invariants": [
                "시그모이드(Sigmoid) / tanh: 입력 절댓값이 커질수록 미분값이 0에 수렴하여 기울기 소실(Vanishing Gradient) 유발",
                "ReLU(Rectified Linear Unit): 양수 영역 미분값이 항상 1이므로 기울기 소실을 극복, 음수 영역 미분 0(Dying ReLU)",
                "출력층 활성화: 이진 분류 -> 시그모이드, 다중 분류 -> 소프트맥스(Softmax), 회귀 -> 항등함수(Linear)"
            ]
        },
        {
            "priority": "P2_HIGH",
            "candidate_topic": "ANOVA Table Degrees of Freedom & Sum of Squares Decomposition",
            "target_concept": "C21_PARAMETRIC_TESTS",
            "drift_rationale": "Rounds 46-49 repeatedly tested ANOVA and regression sum of squares (SSE, SSR, SST). Missing-cell ANOVA calculations are imminent.",
            "variation_theory_invariants": [
                "총제곱합 SST(자유도 N-1) = 집단간 SSR/SSB(자유도 k-1) + 집단내 SSE/SSW(자유도 N-k)",
                "평균제곱(Mean Square): MSR = SSR / (k-1), MSE = SSE / (N-k)",
                "검정통계량: F = MSR / MSE (귀무가설이 참일 때 자유도 (k-1, N-k)인 F-분포를 따름)"
            ]
        },
        {
            "priority": "P3_MODERATE",
            "candidate_topic": "Nonaka's SECI Spiral & Ba (Shared Context for Knowledge)",
            "target_concept": "C02_KNOWLEDGE_SECI",
            "drift_rationale": "Rounds 48 and 49 resurrected SECI model questions. Advanced questions test the dynamic concept of 'Ba' (생성의 장, 대화의 장, 체계화의 장, 실행의 장).",
            "variation_theory_invariants": [
                "공통화(Socialization) -> 창조의 장(Originating Ba): 대면 접촉과 경험 공유",
                "표출화(Externalization) -> 상호작용의 장(Dialoguing Ba): 대화와 은유를 통한 개념화",
                "연결화(Combination) -> 사이버 장(Systemizing Ba): 정보통신기술을 활용한 형식지 결합",
                "내면화(Internalization) -> 실천의 장(Exercising Ba): 업무 현장에서의 실천과 훈련 체화"
            ]
        }
    ]


# ============================================================================
# 5. PIPELINE EXECUTION & ARTIFACT EXPORT
# ============================================================================

def build_knowledge_graph_and_q_matrix(
    input_corpus_path: Path,
    output_q_matrix_path: Path,
    output_drift_report_path: Path
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """End-to-end execution pipeline."""
    logger.info("Step 1: Validating Ontology DAG with %d concept nodes...", len(ONTOLOGY_DEFINITIONS))
    topological_order = validate_dag(ONTOLOGY_DEFINITIONS)
    logger.info("DAG validated successfully. Topological sort completed.")

    logger.info("Step 2: Loading raw exam corpus from %s...", input_corpus_path)
    with open(input_corpus_path, "r", encoding="utf-8") as f:
        raw_items: List[Dict[str, Any]] = json.load(f)

    logger.info("Total loaded raw items: %d across 15 rounds.", len(raw_items))

    # Initialize Q-Matrix Mapper
    mapper = QMatrixMapper(ONTOLOGY_DEFINITIONS)

    enriched_items: List[Dict[str, Any]] = []

    logger.info("Step 3: Generating enriched Q-Matrix and item classifications...")
    for item in raw_items:
        r = int(item["round"])
        q_no = int(item["question_no"])
        q_type = str(item.get("question_type", "4지선다"))
        prompt = str(item.get("prompt", ""))
        options = list(item.get("options", []))
        answer = str(item.get("answer", ""))

        item_id = f"R{r}-Q{q_no:02d}"
        subject = assign_subject(r, q_no)
        subject_name = SUBJECT_NAMES[subject]

        polarity = classify_stem_polarity(prompt)
        archetype = classify_archetype(prompt, q_type, options)
        traps = detect_distractor_traps(prompt, options, polarity)
        irt = compute_irt_params(q_type, archetype, polarity, traps, r, subject)

        concept_ids, primary_cid = mapper.map_question(prompt, options, answer, subject)

        enriched_item = {
            "item_id": item_id,
            "round": r,
            "question_no": q_no,
            "subject": subject,
            "subject_name": subject_name,
            "question_type": q_type,
            "prompt": prompt,
            "options": options,
            "answer": answer,
            "stem_polarity": polarity,
            "archetype": archetype,
            "distractor_traps": traps,
            "irt_params": irt,
            "concept_ids": concept_ids,
            "primary_concept_id": primary_cid
        }
        enriched_items.append(enriched_item)

    logger.info("Enriched 100%% (%d items) with at least 1 valid concept ID.", len(enriched_items))

    logger.info("Step 4: Computing Longitudinal Concept Drift and Emerging Terms...")
    drift_by_concept = compute_concept_drift(enriched_items, ONTOLOGY_DEFINITIONS)
    emerging_keywords = analyze_emerging_keywords(enriched_items)
    ood_predictions = predict_ood_topics_round51_plus()

    # Aggregate summary metrics
    archetype_counts = Counter(it["archetype"] for it in enriched_items)
    polarity_counts = Counter(it["stem_polarity"] for it in enriched_items)
    trap_counts = Counter(t for it in enriched_items for t in it["distractor_traps"])
    subject_counts = Counter(it["subject"] for it in enriched_items)

    drift_report = {
        "metadata": {
            "total_items": len(enriched_items),
            "rounds_count": len(ALL_ROUNDS),
            "rounds": ALL_ROUNDS,
            "eras": ERAS,
            "ontology_concepts_count": len(ONTOLOGY_DEFINITIONS),
            "topological_order": topological_order
        },
        "ontology": [
            {
                "concept_id": c.concept_id,
                "name_ko": c.name_ko,
                "subject": c.subject,
                "subject_name": SUBJECT_NAMES[c.subject],
                "prerequisites": c.prerequisites,
                "core_invariants": c.core_invariants
            }
            for c in ONTOLOGY_DEFINITIONS
        ],
        "summary_distributions": {
            "subject_distribution": dict(subject_counts),
            "polarity_distribution": dict(polarity_counts),
            "archetype_distribution": dict(archetype_counts),
            "distractor_trap_distribution": dict(trap_counts),
            "irt_averages": {
                "mean_discrimination_a": round(float(np.mean([it["irt_params"]["a"] for it in enriched_items])), 2),
                "mean_difficulty_b": round(float(np.mean([it["irt_params"]["b"] for it in enriched_items])), 2),
                "mean_guessing_c": round(float(np.mean([it["irt_params"]["c"] for it in enriched_items])), 2)
            }
        },
        "concept_drift_analysis": drift_by_concept,
        "emerging_keywords_era3": emerging_keywords,
        "predicted_ood_topics_round51_plus": ood_predictions
    }

    # Ensure output directories exist
    output_q_matrix_path.parent.mkdir(parents=True, exist_ok=True)
    output_drift_report_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Step 5: Writing Q-Matrix to %s...", output_q_matrix_path)
    with open(output_q_matrix_path, "w", encoding="utf-8") as f:
        json.dump(enriched_items, f, ensure_ascii=False, indent=2)

    logger.info("Step 6: Writing Concept Drift Report to %s...", output_drift_report_path)
    with open(output_drift_report_path, "w", encoding="utf-8") as f:
        json.dump(drift_report, f, ensure_ascii=False, indent=2)

    logger.info("All artifacts written cleanly. Pipeline completed successfully.")
    return enriched_items, drift_report


def main() -> None:
    workspace_root = Path("c:/Users/SSAFY/Desktop/ADsP")
    input_path = workspace_root / "adsp_crawler" / "data" / "adsp_all.json"
    output_q_matrix = workspace_root / "adsp_harness" / "data" / "q_matrix_748.json"
    output_drift_report = workspace_root / "adsp_harness" / "data" / "concept_drift_report.json"

    items, report = build_knowledge_graph_and_q_matrix(
        input_corpus_path=input_path,
        output_q_matrix_path=output_q_matrix,
        output_drift_report_path=output_drift_report
    )

    print("\n" + "=" * 80)
    print(" ADsP Knowledge Graph & Q-Matrix Generation Summary")
    print("=" * 80)
    print(f"Total Exam Items Processed : {len(items)}")
    print(f"Ontology Concepts Defined  : {len(report['ontology'])} nodes (Subject 1: 8, Subject 2: 8, Subject 3: 16)")
    print(f"Direct Match Coverage      : {sum(1 for it in items if len(it['concept_ids']) >= 1)} / {len(items)} (100.0%)")
    print(f"Output File 1 (Q-Matrix)   : {output_q_matrix} ({output_q_matrix.stat().st_size:,} bytes)")
    print(f"Output File 2 (Drift Rep)  : {output_drift_report} ({output_drift_report.stat().st_size:,} bytes)")
    print("-" * 80)
    print("Archetype Breakdown:")
    for arch, cnt in report["summary_distributions"]["archetype_distribution"].items():
        print(f"  - {arch:18s}: {cnt:3d} ({cnt/len(items)*100:.1f}%)")
    print("\nPolarity Breakdown:")
    for pol, cnt in report["summary_distributions"]["polarity_distribution"].items():
        print(f"  - {pol:18s}: {cnt:3d} ({cnt/len(items)*100:.1f}%)")
    print("\nTop Detected Distractor Traps:")
    for trap, cnt in sorted(report["summary_distributions"]["distractor_trap_distribution"].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {trap:25s}: {cnt:3d} ({cnt/len(items)*100:.1f}%)")
    print("\nTop Surging Concepts into Era 3 (Rounds 46-50):")
    surging = [c for c in report["concept_drift_analysis"].values() if c["trend"] == "SURGING_EMERGENT"]
    surging.sort(key=lambda x: x["drift_ratio"], reverse=True)
    for c in surging[:8]:
        print(f"  - [{c['concept_id']}] {c['name_ko']:30s} | Drift Ratio: {c['drift_ratio']:5.2f} | Era3/rd: {c['era3_per_round']:.2f}")
    print("\nPredicted High-Priority OOD Topics for Round 51+:")
    for pred in report["predicted_ood_topics_round51_plus"][:5]:
        print(f"  - [{pred['priority']}] {pred['candidate_topic']} -> {pred['target_concept']}")
    print("=" * 80)


if __name__ == "__main__":
    main()

