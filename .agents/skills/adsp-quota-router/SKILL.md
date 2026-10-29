---
name: adsp-quota-router
description: >-
  Use this skill when checking live model token quotas via the Antigravity Language Server RPC
  (GetUserStatus) or routing ADsP learning harness tasks across heterogeneous models
  (Gemini 3.8 Flash, Claude Sonnet 5.5, Claude Opus 5.5, Gemini 4 Argon, and GPT-OSS 120B).
---

# ADsP Quota-Aware Multi-Model Router Skill

이 스킬은 Antigravity Language Server (`GetUserStatus`) RPC와 연동하여 현재 워크스페이스의 모델별 잔여 토큰(Quota Fraction)을 실시간 점검하고, 각 학습 에이전트 역할을 최적의 모델 티어로 라우팅합니다.

## 실행 명령

```powershell
python -m adsp_harness.cli quota
```

## 에이전트 역할별 기본 모델 매핑

| 에이전트 역할 (`role`) | 1순위 배정 모델 | 2순위 폴백 모델 | 주요 담당 기능 |
| :--- | :--- | :--- | :--- |
| `error_note_synthesizer` | `gemini-3.8-flash-high` | `gemini-4-argon-medium` | 초고속 자동 오답 노트 생성 및 5대 함정 분류 (시간 단축) |
| `socratic_tutor` | `claude-sonnet-5.5-high` | `gemini-4-argon-medium` | 2-턴 소크라테스 양방향 문답 (과교정 & 헷갈린 문제 정복) |
| `weakness_root_cause_analyst` | `claude-opus-5.5-high` | `gemini-4-argon-high` | Q-Matrix 공발생 네트워크 및 선수 개념 결함 역추적 |
| `metacognition_calibrator` | `claude-sonnet-5.5-high` | `gemini-4-argon-high` | Murphy Brier 3분해 & ECE 기반 메타인지 교정 |
| `ood_trend_generator` | `claude-opus-5.5-high` | `gemini-4-argon-high` | 최신 기출(46~50회) 트렌드 외삽 기반 신유형(OOD) 문항 생성 |
| `psychometric_critic` | `gemini-4-argon-high` | `gpt-oss-120b-medium` | 신유형 문항 블라인드 검증 및 스트레스 접종(SIT) 소거법 설계 |

