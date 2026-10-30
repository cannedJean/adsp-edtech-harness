"""
CLI Entrypoint for the ADsP Top-Down Multi-Agent Adaptive Learning Harness.

Commands:
  python -m adsp_harness.cli quota                 # Inspect live model quotas & agent routing matrix
  python -m adsp_harness.cli phase1 --round 50     # Run Phase 1 top-down solving + Flash error note + Sonnet Socratic Q&A
  python -m adsp_harness.cli phase2                # Run Phase 2 global weakness analysis + Brier/ECE + Monte Carlo simulation
  python -m adsp_harness.cli phase3 --count 5      # Run Phase 3 OOD novel question generation & SIT cognitive vaccine
  python -m adsp_harness.cli demo                  # Run end-to-end 3-phase simulation & export full diagnostic markdown report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .orchestrator import ADsPHarnessOrchestrator
from .quota_router import QuotaAwareModelRouter


def cmd_quota(_args: argparse.Namespace) -> None:
    router = QuotaAwareModelRouter()
    summary = router.get_routing_summary()
    print("=" * 88)
    print(" [ADsP Harness] 실시간 모델별 잔여 토큰(Quota) 및 이종 에이전트 라우팅 매트릭스")
    print("=" * 88)
    print(f"{'Model Label':<30} | {'Model ID':<26} | {'Quota (%)':<10} | {'Reset Time'}")
    print("-" * 88)
    for mid, q in summary["quotas"].items():
        pct = f"{q['remaining_fraction'] * 100:.2f}%"
        print(f"{q['label']:<30} | {mid:<26} | {pct:<10} | {q['reset_time']}")

    print("\n" + "=" * 88)
    print(" [에이전트 역할별 최적 모델 배정 결과]")
    print("=" * 88)
    for role, info in summary["role_assignments"].items():
        print(f"• {role:<28} -> {info['assigned_model_label']} ({info['remaining_quota_pct']}% 잔여)")
        print(f"  └─ 역할: {info['description']}")


def cmd_phase1(args: argparse.Namespace) -> None:
    orch = ADsPHarnessOrchestrator(learner_id=args.learner, live_cli=args.live_cli)
    questions = orch.get_phase1_questions(round_no=args.round, limit=args.limit)
    print("=" * 88)
    print(f" [Phase 1: 하향식 기출 풀이 & 양방향 오답·혼동 정복 루프] 제{args.round}회 ({len(questions)}문항)")
    print("=" * 88)

    # Simulated realistic learner trajectory when non-interactive, or interactive stdin
    sample_responses = [
        # (offset_from_correct, confidence_rating, socratic_reply)
        (0, 4, None),  # Q1: MASTERED (Correct + High Conf -> Instant skip!)
        (0, 2, "2번 보기의 표현이 모호해서 헷갈렸는데 불변 기준을 적용하면 소거됩니다."),  # Q2: LUCKY_GUESS_CONFUSED
        (1, 4, "옳지 않은 것을 고르는 부정형 발문인데 1번 참 명제를 보고 바로 골랐습니다."),  # Q3: ILLUSION_OF_COMPETENCE
        (2, 1, "핵심 공식의 분모 기준을 반대로 적용했습니다."),  # Q4: KNOWN_UNKNOWN
        (0, 3, None),  # Q1: MASTERED
    ]

    for idx, q in enumerate(questions):
        print(f"\n[문항 {q['item_id']}] (제{q['subject']}과목 | 유형: {q['archetype']} | 극성: {q['stem_polarity']})")
        print(q["prompt"])
        for opt_idx, opt in enumerate(q.get("options", []), 1):
            print(f"  ({opt_idx}) {opt}")

        ans = str(q["answer"]).strip()
        if args.interactive:
            sel = input("\n👉 정답 번호 입력 (1~4 또는 단답): ").strip()
            conf = int(input("👉 확신도 입력 (1:찍음 25%, 2:헷갈림 50%, 3:대체로확신 75%, 4:완전확신 95%): ").strip() or "3")
            socratic_reply = None
        else:
            offset, conf, socratic_reply = sample_responses[idx % len(sample_responses)]
            if q["question_type"] == "4지선다" and ans.isdigit():
                sel = str(((int(ans) - 1 + offset) % 4) + 1)
            else:
                sel = ans if offset == 0 else "오답응답"

        res = orch.submit_phase1_attempt(
            item_id=q["item_id"],
            selected_option=sel,
            confidence_rating=conf,
            learner_socratic_reply=socratic_reply,
        )
        att = res["attempt"]
        print(
            f"\n  [채점 결과] 선택: {sel} | 정답: {ans} | 정오: {'⭕ 정답' if att['is_correct'] else '❌ 오답'} "
            f"| 확신도: {conf}단계({int(att['confidence_prob']*100)}%) -> 사분면: [{att['metacog_quadrant']}]"
        )

        if not res["needs_intervention"]:
            print("  🚀 [Q1: MASTERED] 완전 습득 문항! 수동 오답 정리를 생략하고 즉시 다음 문항으로 이동합니다 (절약 시간: 240초).")
        else:
            note = res["auto_error_note"]
            t1 = res["socratic_turn_1"]
            t2 = res["socratic_turn_2"]
            print(f"  📝 [자동 오답 노트 생성 완료 - {note['agent_model_used']}] (수동 정리 240초 절약)")
            print(f"     • 진단: {note['why_wrong_diagnosis']}")
            print(f"     • 핵심 불변 원리: {note['core_invariant_rule']}")
            if t1:
                print(f"  💬 {t1['message']}")
            if args.interactive and t1:
                user_ans = input("  ✍️ [소크라테스 답변 입력]: ").strip()
                t2 = orch.specialists.generate_socratic_turn(
                    q, sel, att["metacog_quadrant"], learner_reply=user_ans or "핵심 변별 기준을 확인했습니다."
                )
            if t2:
                print(f"  💬 {t2['message']}")


def cmd_phase2(args: argparse.Namespace) -> None:
    orch = ADsPHarnessOrchestrator(learner_id=args.learner, live_cli=args.live_cli)
    report = orch.run_phase2_global_analysis()
    print("=" * 88)
    print(" [Phase 2: 데이터 기반 전역 취약점 진단 & 메타인지 교정 리포트]")
    print("=" * 88)
    print(f"• 근본 원인 분석 에이전트 : {report['root_cause_analyst_model']}")
    print(f"• 메타인지 보정 에이전트   : {report['metacognition_coach_model']}")
    if report.get("opus_root_cause_diagnosis"):
        print("\n0. [Claude Opus 5.5 실시간 심층 근본 원인 진단]")
        print(f"   {report['opus_root_cause_diagnosis']}")

    mc = report["metacognitive_profile"]
    print("\n1. [메타인지 캘리브레이션 진단 (Murphy Brier 3분해 & ECE)]")
    print(f"   - 메타인지 유형       : {mc['type']}")
    print(f"   - Brier Score (BS)    : {mc['brier_score']} (REL={mc['reliability_error']}, RES={mc['resolution']})")
    print(f"   - 보정 오차 (ECE)     : {mc['ece']} | 과신 지수 (OCI): {mc['overconfidence_index']:+.4f}")
    print(f"   - 코칭 처방           : {mc['prescription']}")

    wa = report["weakness_analysis"]
    print("\n2. [데이터 기반 오답 유형(Error Taxonomy) 및 최우선 복습 타겟]")
    for item in wa["error_taxonomy"].get("taxonomy_breakdown", []):
        print(
            f"   - {item['error_type']:<24}: {item['error_count']}건 ({item['percentage_of_total_errors']}%) "
            f"[고확신 오답 비중: {item['high_confidence_ratio']}%]"
        )

    print("\n3. [RPE 우선순위 기반 Top 혼동/취약 개념 (Q3 과교정 + Q2 찍어서 맞힌 개념)]")
    for c in wa["top_confused_concepts"][:5]:
        print(
            f"   - [{c['concept_id']}] (제{c['subject']}과목) Priority={c['priority_score']} | "
            f"BKT숙련도={c['bkt_mastery']} | 고확신오답(Q3)={c['high_confidence_errors']}건 | "
            f"찍어서맞힘(Q2)={c['lucky_guesses']}건 -> 조치: {c['action_recommendation']}"
        )

    sim = report["pass_simulation"]
    print("\n4. [ADsP 실전 합격 확률 & 과목별 40% 과락 위험도 몬테카를로 시뮬레이션 (5,000회)]")
    print(f"   - 예상 총점           : {sim['expected_total_score']} / 100점 (합격 기준: 60점 이상 & 전 과목 과락 면제)")
    print(f"   - 최종 합격 확률      : {sim['pass_probability'] * 100:.1f}%")
    print(
        f"   - 과목별 과락 위험도  : "
        f"1과목({sim['subject_cutoff_risk'].get(1, sim['subject_cutoff_risk'].get('1', 0))*100:.1f}%), "
        f"2과목({sim['subject_cutoff_risk'].get(2, sim['subject_cutoff_risk'].get('2', 0))*100:.1f}%), "
        f"3과목({sim['subject_cutoff_risk'].get(3, sim['subject_cutoff_risk'].get('3', 0))*100:.1f}%)"
    )
    print(f"   - 최우선 방어 과목    : 제{sim['bottleneck_subject']}과목")


def cmd_phase3(args: argparse.Namespace) -> None:
    orch = ADsPHarnessOrchestrator(learner_id=args.learner, live_cli=args.live_cli)
    session = orch.run_phase3_ood_vaccine_session(count=args.count)
    print("=" * 88)
    print(" [Phase 3: 최신 기출(46~50회) 동향 외삽 신유형(OOD) & 시험장 인지부조화 백신 루프]")
    print("=" * 88)
    print(f"• 최근 기출 급부상 키워드 : {', '.join(session['recent_round_46_50_drift_highlights'][:8])}")
    print(f"• 학습자 타겟 취약 개념   : {', '.join(session['learner_weak_concepts_targeted']) or '전 과목 핵심 표류 토픽'}")

    for idx, item in enumerate(session["ood_vaccine_items"], 1):
        print("\n" + "-" * 88)
        print(f"[신유형 백신 문항 #{idx}: {item['ood_id']}] (제{item['subject']}과목 | 타겟: {item['target_concept_id']})")
        print(f"• 출제 동향 근거 : {item['trend_basis']}")
        print(f"• 생성 에이전트  : {item['generator_agent']} | 검증 에이전트: {item['critic_agent']}")
        print(f"\n{item['prompt']}\n")
        for opt_i, opt in enumerate(item["options"], 1):
            print(f"  ({opt_i}) {opt}")
        print(f"\n  ✔ [검증된 정답]: {item['answer']}번")
        print(f"  📌 [핵심 불변 원리 (Marton Variation Invariant)]: {item['core_invariant']}")
        print(f"  {item['sit_cognitive_vaccine_protocol']}")


def cmd_show(args: argparse.Namespace) -> None:
    """Display a single question without revealing the answer (for interactive chat turns)."""
    orch = ADsPHarnessOrchestrator(learner_id=args.learner, live_cli=args.live_cli)
    item_id = args.item or f"R{args.round}-Q{args.qno:02d}"
    q = orch.items_by_id.get(item_id)
    if not q:
        print(f"Error: Question {item_id} not found.")
        return
    print(f"[{q['item_id']}] (제{q['subject']}과목 | 유형: {q['archetype']} | 발문극성: {q['stem_polarity']})")
    print(q["prompt"])
    for idx, opt in enumerate(q.get("options", []), 1):
        print(f"  ({idx}) {opt}")


def cmd_submit(args: argparse.Namespace) -> None:
    """Submit a single question attempt + confidence rating and output auto error note & Socratic turn."""
    orch = ADsPHarnessOrchestrator(learner_id=args.learner, live_cli=args.live_cli)
    res = orch.submit_phase1_attempt(
        item_id=args.item,
        selected_option=str(args.ans),
        confidence_rating=int(args.conf),
        learner_socratic_reply=args.reply,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_resolve(args: argparse.Namespace) -> None:
    """Record the learner's initial misconception and Socratic corrected explanation into learner_state.db."""
    orch = ADsPHarnessOrchestrator(learner_id=args.learner, live_cli=args.live_cli)
    res = orch.resolve_item_socratic_note(
        item_id=args.item,
        learner_misconception=args.misconception,
        corrected_explanation=args.correction,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_ask(args: argparse.Namespace) -> None:
    """Invoke Claude Sonnet 5.5 or Claude Opus 5.5 for deep conceptual/math Q&A and record into learner_state.db."""
    orch = ADsPHarnessOrchestrator(learner_id=args.learner, live_cli=args.live_cli)
    res = orch.ask_deep_question(
        item_id=args.item,
        question=args.question,
        tier=args.tier,
        persist_to_note=True,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_notes(args: argparse.Namespace) -> None:
    """Generate a personalized master study note markdown file focusing on wrong/confused & corrected concepts."""
    orch = ADsPHarnessOrchestrator(learner_id=args.learner, live_cli=args.live_cli)
    res = orch.generate_personalized_study_note(output_path=args.output)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_demo(args: argparse.Namespace) -> None:
    """Run an end-to-end demonstration across Quota Check -> Phase 1 -> Phase 2 -> Phase 3."""
    cmd_quota(args)
    print("\n")
    args.round = 50
    args.limit = 5
    args.interactive = False
    cmd_phase1(args)
    print("\n")
    cmd_phase2(args)
    print("\n")
    args.count = 3
    cmd_phase3(args)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ADsP Top-Down Multi-Agent Adaptive Learning Harness CLI"
    )
    parser.add_argument("--learner", type=str, default="default_learner", help="Learner ID")
    parser.add_argument("--live-cli", dest="live_cli", action="store_true", default=True, help="Invoke live agy.exe multi-model agents (default: True)")
    parser.add_argument("--offline", dest="live_cli", action="store_false", help="Disable live agy.exe calls and use instant hybrid templates")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("quota", help="Check live model token quotas and routing matrix")

    p_show = sub.add_parser("show", help="Show a single exam question without answer")
    p_show.add_argument("--item", type=str, default=None, help="Item ID (e.g., R50-Q01)")
    p_show.add_argument("--round", type=int, default=50, help="Exam round (32..50)")
    p_show.add_argument("--qno", type=int, default=1, help="Question number (1..50)")

    p_sub = sub.add_parser("submit", help="Submit answer and confidence (1..4) for a single question")
    p_sub.add_argument("--item", type=str, required=True, help="Item ID (e.g., R50-Q01)")
    p_sub.add_argument("--ans", type=str, required=True, help="Selected option (1..4 or short answer)")
    p_sub.add_argument("--conf", type=int, default=3, help="Confidence rating (1..4)")
    p_sub.add_argument("--reply", type=str, default=None, help="Optional learner Socratic reply")

    p_res = sub.add_parser("resolve", help="Record learner misconception and corrected concept after Socratic Q&A")
    p_res.add_argument("--item", type=str, required=True, help="Item ID (e.g., R50-Q31)")
    p_res.add_argument("--misconception", type=str, required=True, help="What the learner confused or misunderstood")
    p_res.add_argument("--correction", type=str, required=True, help="Corrected core concept and explanation")

    p_ask = sub.add_parser("ask", help="Ask Claude Sonnet 5.5 or Claude Opus 5.5 a deep conceptual/math question")
    p_ask.add_argument("--item", type=str, required=True, help="Item ID (e.g., R50-Q33)")
    p_ask.add_argument("--question", type=str, required=True, help="Learner's conceptual or mathematical question")
    p_ask.add_argument("--tier", type=str, default="sonnet", choices=["sonnet", "opus"], help="Model tier: sonnet (Claude Sonnet 5.5) or opus (Claude Opus 5.5)")

    p_notes = sub.add_parser("notes", help="Generate personalized master study note markdown")
    p_notes.add_argument("--output", type=str, default=None, help="Output markdown path (default: docs/MY_MASTER_STUDY_NOTE.md)")

    p1 = sub.add_parser("phase1", help="Run Phase 1 Top-Down Past Exam Loop")
    p1.add_argument("--round", type=int, default=50, help="Exam round (32..50)")
    p1.add_argument("--limit", type=int, default=5, help="Number of questions to solve")
    p1.add_argument("--interactive", action="store_true", help="Interactive terminal input mode")

    sub.add_parser("phase2", help="Run Phase 2 Global Weakness & Metacognitive Calibration Analysis")

    p3 = sub.add_parser("phase3", help="Run Phase 3 OOD Novel Question Generation & SIT Vaccine")
    p3.add_argument("--count", type=int, default=5, help="Number of OOD vaccine questions")

    sub.add_parser("demo", help="Run full E2E demonstration (Quota -> Phase 1 -> Phase 2 -> Phase 3)")

    args = parser.parse_args()
    if args.command == "quota":
        cmd_quota(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "submit":
        cmd_submit(args)
    elif args.command == "resolve":
        cmd_resolve(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "notes":
        cmd_notes(args)
    elif args.command == "phase1":
        cmd_phase1(args)
    elif args.command == "phase2":
        cmd_phase2(args)
    elif args.command == "phase3":
        cmd_phase3(args)
    else:
        cmd_demo(args)


if __name__ == "__main__":
    main()

