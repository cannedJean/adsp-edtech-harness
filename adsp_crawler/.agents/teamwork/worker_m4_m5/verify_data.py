"""Data verification script for harvested ADsP dataset."""

import json
from pathlib import Path
import sys

DATA_DIR = Path("C:/Users/SSAFY/Desktop/ADsP/adsp_crawler/data")
EXPECTED_ROUNDS = [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]
EXPECTED_ROUND_COUNTS = {r: (49 if r in (38, 40) else 50) for r in EXPECTED_ROUNDS}
EXPECTED_SA_ROUNDS = {32: 10, 35: 10, 37: 10, 38: 10}

FORBIDDEN_TERMS = [
    "오답 풀이",
    "오답풀이",
    "보충 개념",
    "보충개념",
    "정답·해설 보기",
    "정답해설보기",
]

def verify():
    print("=" * 70)
    print(" ADsP Harvested Dataset Verification Report")
    print("=" * 70)

    # 1. Check all 15 round JSON files exist
    print("[1] Checking 15 Round JSON Files...")
    missing_files = []
    for r in EXPECTED_ROUNDS:
        round_file = DATA_DIR / f"adsp_round_{r}.json"
        if not round_file.exists():
            missing_files.append(f"adsp_round_{r}.json")
        else:
            print(f"  - Round {r}: {round_file.name} (size: {round_file.stat().st_size:,} bytes)")
    if missing_files:
        print(f"ERROR: Missing round files: {missing_files}")
        sys.exit(1)
    print("  -> All 15 round files exist!\n")

    # 2. Check adsp_all.json exists
    print("[2] Checking adsp_all.json...")
    all_file = DATA_DIR / "adsp_all.json"
    if not all_file.exists():
        print("ERROR: adsp_all.json does not exist!")
        sys.exit(1)
    print(f"  - adsp_all.json exists (size: {all_file.stat().st_size:,} bytes)\n")

    # 3. Check question counts and distributions per round
    print("[3] Checking Per-Round Counts & Types...")
    total_questions = 0
    total_mcq = 0
    total_sa = 0

    for r in EXPECTED_ROUNDS:
        round_file = DATA_DIR / f"adsp_round_{r}.json"
        with open(round_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        expected_len = EXPECTED_ROUND_COUNTS[r]
        assert len(data) == expected_len, f"Round {r} expected {expected_len}, got {len(data)}"
        
        r_mcq = sum(1 for q in data if q["question_type"] == "4지선다")
        r_sa = sum(1 for q in data if q["question_type"] == "단답형")
        
        expected_sa = EXPECTED_SA_ROUNDS.get(r, 0)
        assert r_sa == expected_sa, f"Round {r} expected {expected_sa} short answers, got {r_sa}"
        
        # Verify 단답형 has options: []
        for q in data:
            if q["question_type"] == "단답형":
                assert q["options"] == [], f"Round {r} Q{q['question_no']} has non-empty options!"
                assert len(q["answer"].strip()) > 0
            elif q["question_type"] == "4지선다":
                assert len(q["options"]) == 4, f"Round {r} Q{q['question_no']} does not have 4 options!"
                assert q["answer"] in ("1", "2", "3", "4"), f"Round {r} Q{q['question_no']} invalid answer: {q['answer']}"
        
        total_questions += len(data)
        total_mcq += r_mcq
        total_sa += r_sa
        print(f"  - Round {r:>2}: {len(data):>2} questions (MCQ: {r_mcq:>2}, 단답형: {r_sa:>2}) - OK")

    print(f"\n  -> Total from per-round files: {total_questions} questions (MCQ: {total_mcq}, 단답형: {total_sa})")
    assert total_questions == 748, f"Expected 748, got {total_questions}"
    assert total_mcq == 708, f"Expected 708 MCQ, got {total_mcq}"
    assert total_sa == 40, f"Expected 40 short answer, got {total_sa}"
    print("  -> Question counts and distribution per round match 100%!\n")

    # 4. Check adsp_all.json content
    print("[4] Checking adsp_all.json content...")
    with open(all_file, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    assert len(all_data) == 748, f"adsp_all.json expected 748, got {len(all_data)}"
    all_mcq = sum(1 for q in all_data if q["question_type"] == "4지선다")
    all_sa = sum(1 for q in all_data if q["question_type"] == "단답형")
    assert all_mcq == 708, f"Expected 708 MCQ, got {all_mcq}"
    assert all_sa == 40, f"Expected 40 SA, got {all_sa}"
    print(f"  - Total questions in adsp_all.json: {len(all_data)}")
    print(f"  - MCQ (4지선다): {all_mcq}")
    print(f"  - Short Answer (단답형): {all_sa}")
    print("  -> adsp_all.json verified!\n")

    # 5. Check GFM tables (e.g. Round 50 Q25)
    print("[5] Checking GFM Markdown Tables...")
    r50_file = DATA_DIR / "adsp_round_50.json"
    with open(r50_file, "r", encoding="utf-8") as f:
        r50_data = json.load(f)
    q25 = next(q for q in r50_data if q["question_no"] == 25)
    print("  - Round 50 Q25 prompt excerpt:")
    for line in q25["prompt"].splitlines()[:6]:
        print(f"    {line}")
    assert "|" in q25["prompt"], "Q25 table missing pipe syntax"
    assert "제곱합" in q25["prompt"]
    print("  -> Table GFM syntax verified!\n")

    # 6. Check R code syntax (e.g. Round 50 Q26)
    print("[6] Checking R Code Syntax (```r)...")
    q26 = next(q for q in r50_data if q["question_no"] == 26)
    print("  - Round 50 Q26 prompt excerpt:")
    for line in q26["prompt"].splitlines()[:6]:
        print(f"    {line}")
    assert "```r" in q26["prompt"], "Q26 R code fence missing ```r"
    print("  -> R code syntax ```r verified!\n")

    # 7. Check Negative Exclusion Filter across all JSON files
    print("[7] Checking Negative Exclusion Filter Across All Files...")
    all_json_files = list(DATA_DIR.glob("*.json"))
    assert len(all_json_files) == 16, f"Expected 16 JSON files, got {len(all_json_files)}"
    leak_count = 0
    for jf in all_json_files:
        content = jf.read_text(encoding="utf-8")
        for term in FORBIDDEN_TERMS:
            occurrences = content.count(term)
            if occurrences > 0:
                print(f"ERROR: Forbidden term '{term}' found {occurrences} times in {jf.name}!")
                leak_count += occurrences
    if leak_count == 0:
        print("  -> Zero leaks of forbidden explanation terms across all 16 JSON files (0 occurrences)!")
    else:
        print(f"ERROR: Total {leak_count} explanation leaks found!")
        sys.exit(1)

    print("\n" + "=" * 70)
    print(" ALL DATA VERIFICATION CHECKS PASSED WITH ZERO ERRORS!")
    print("=" * 70)

if __name__ == "__main__":
    verify()
