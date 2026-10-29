import glob
import json
from pathlib import Path
import re
import sys

project_root = Path(r"C:\Users\SSAFY\Desktop\ADsP\adsp_crawler")
data_dir = project_root / "data"

print("--- 1. File Inventory Check ---")
assert data_dir.exists(), f"Data dir {data_dir} does not exist!"
target_rounds = [32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50]

for r in target_rounds:
    fpath = data_dir / f"adsp_round_{r}.json"
    assert fpath.exists(), f"Missing file: {fpath.name}"
    assert fpath.stat().st_size > 0, f"File empty: {fpath.name}"

all_path = data_dir / "adsp_all.json"
assert all_path.exists(), "Missing adsp_all.json"
assert all_path.stat().st_size > 0, "adsp_all.json is empty"
all_json_files = list(data_dir.glob("*.json"))
assert len(all_json_files) == 16, f"Expected 16 json files in data/, got {len(all_json_files)}"
print(f"PASS: 15 individual round JSON files + 1 consolidated file verified (Total 16 files).")

print("\n--- 2. Census & Schema Compliance Check ---")
expected_round_counts = {
    32: 50, 35: 50, 37: 50, 38: 49, 39: 50,
    40: 49, 41: 50, 42: 50, 44: 50, 45: 50,
    46: 50, 47: 50, 48: 50, 49: 50, 50: 50,
}
expected_sa_counts = {
    32: 10, 35: 10, 37: 10, 38: 10, 39: 0,
    40: 0, 41: 0, 42: 0, 44: 0, 45: 0,
    46: 0, 47: 0, 48: 0, 49: 0, 50: 0,
}

total_harvested = 0
total_mcq = 0
total_sa = 0
reconstructed_all = []

for r in target_rounds:
    fpath = data_dir / f"adsp_round_{r}.json"
    with open(fpath, "r", encoding="utf-8") as f:
        questions = json.load(f)

    assert isinstance(questions, list), f"Round {r} is not a list"
    assert len(questions) == expected_round_counts[r], f"Round {r} count mismatch: {len(questions)} != {expected_round_counts[r]}"

    round_mcq = 0
    round_sa = 0
    q_nos = []

    for q in questions:
        assert isinstance(q, dict), f"Question not dict in Round {r}"
        required_keys = {"question_no", "question_type", "prompt", "options", "answer"}
        assert set(q.keys()) == required_keys, f"Keys mismatch in Round {r} Q{q.get('question_no')}: {set(q.keys())}"

        q_no = q["question_no"]
        q_type = q["question_type"]
        prompt = q["prompt"]
        options = q["options"]
        answer = q["answer"]

        assert isinstance(q_no, int) and not isinstance(q_no, bool), f"Invalid q_no type: {type(q_no)}"
        assert 1 <= q_no <= 50, f"q_no out of range: {q_no}"
        q_nos.append(q_no)

        assert q_type in ("4지선다", "단답형"), f"Invalid q_type: {q_type}"
        assert isinstance(prompt, str) and len(prompt.strip()) > 0, f"Empty prompt in Round {r} Q{q_no}"
        assert isinstance(options, list), f"Options not list in Round {r} Q{q_no}"
        assert isinstance(answer, str) and len(answer.strip()) > 0, f"Empty answer in Round {r} Q{q_no}"

        if q_type == "4지선다":
            round_mcq += 1
            assert len(options) == 4, f"Round {r} Q{q_no} MCQ options count is {len(options)}"
            for opt_idx, opt in enumerate(options, 1):
                assert isinstance(opt, str) and len(opt.strip()) > 0, f"Round {r} Q{q_no} opt {opt_idx} empty"
            assert answer in ("1", "2", "3", "4"), f"Round {r} Q{q_no} MCQ answer invalid: {answer}"
        else: # 단답형
            round_sa += 1
            assert options == [], f"Round {r} Q{q_no} 단답형 options not empty: {options}"
            assert len(answer.strip()) > 0, f"Round {r} Q{q_no} 단답형 answer empty"

        q_with_round = dict(q)
        q_with_round["round"] = r
        reconstructed_all.append(q_with_round)

    assert round_sa == expected_sa_counts[r], f"Round {r} SA count mismatch: {round_sa} != {expected_sa_counts[r]}"
    if r in (38, 40):
        assert q_nos == list(range(1, 50)), f"Round {r} question nos not 1..49: {q_nos}"
    else:
        assert q_nos == list(range(1, 51)), f"Round {r} question nos not 1..50: {q_nos}"

    total_harvested += len(questions)
    total_mcq += round_mcq
    total_sa += round_sa

print(f"PASS: 15 individual rounds verified.")
print(f"  Total questions: {total_harvested} (MCQ: {total_mcq}, SA: {total_sa})")
assert total_harvested >= 740, f"Total questions {total_harvested} < 740"
assert total_harvested == 748, f"Total questions {total_harvested} != 748"
assert total_mcq == 708, f"Total MCQ {total_mcq} != 708"
assert total_sa == 40, f"Total SA {total_sa} != 40"

print("\n--- 3. Consolidated Dataset Check ---")
with open(all_path, "r", encoding="utf-8") as f:
    adsp_all = json.load(f)

assert isinstance(adsp_all, list), "adsp_all.json is not a list"
assert len(adsp_all) == 748, f"adsp_all.json length is {len(adsp_all)} != 748"
assert adsp_all == reconstructed_all, "Consolidated dataset does not exactly match reconstructed round questions"
print("PASS: adsp_all.json bit-for-bit parity with individual round datasets confirmed.")

print("\n--- 4. Negative Exclusion Filter (Explanation Leaks) Check ---")
forbidden_terms = [
    "오답 풀이", "오답풀이",
    "보충 개념", "보충개념",
    "정답·해설 보기", "정답해설보기",
    '["$"', '{"className"', "rounded-2xl", "tabular-nums"
]

leak_count = 0
for fpath in all_json_files:
    raw_text = fpath.read_text(encoding="utf-8")
    for term in forbidden_terms:
        if term in raw_text:
            print(f"FAIL: Leak found in {fpath.name}: '{term}'")
            leak_count += 1

assert leak_count == 0, f"Total leaks found: {leak_count}"
print(f"PASS: Zero explanation or AST leakage across all 16 JSON files.")

print("\n--- 5. Rich Elements (GFM Tables and R Code Blocks) Check ---")
# Check Round 50 Q25 (ANOVA table)
r50_file = data_dir / "adsp_round_50.json"
with open(r50_file, "r", encoding="utf-8") as f:
    r50_qs = json.load(f)

q25 = next(q for q in r50_qs if q["question_no"] == 25)
print(f"R50 Q25 prompt excerpt:\n{q25['prompt'][:200]}...")
assert "|" in q25["prompt"], "R50 Q25 missing table pipes"
assert "---" in q25["prompt"], "R50 Q25 missing table markdown separator"
assert "제곱합" in q25["prompt"] and "p-value" in q25["prompt"], "R50 Q25 missing ANOVA table contents"

# Check Round 50 Q26 (R PCA summary)
q26 = next(q for q in r50_qs if q["question_no"] == 26)
print(f"R50 Q26 prompt excerpt:\n{q26['prompt'][:200]}...")
assert "```r" in q26["prompt"], "R50 Q26 missing ```r fence"
assert "```" in q26["prompt"], "R50 Q26 missing closing fence"
assert "prcomp" in q26["prompt"] or "pca" in q26["prompt"] or "PCA" in q26["prompt"], "R50 Q26 missing PCA contents"

# Check other tables across rounds
tables_found = 0
r_blocks_found = 0
for q in adsp_all:
    prompt = q["prompt"]
    if "|" in prompt and "\n| ---" in prompt or "\n|---" in prompt:
        tables_found += 1
    if "```r" in prompt:
        r_blocks_found += 1

print(f"Total questions with GFM tables across corpus: {tables_found}")
print(f"Total questions with ```r fenced code blocks across corpus: {r_blocks_found}")
assert tables_found > 0, "No markdown tables found in entire corpus"
assert r_blocks_found > 0, "No R code blocks found in entire corpus"
print("PASS: Rich elements (GFM tables and R code blocks) verified.")

print("\n--- 6. Short-Answer Format (R32~R39) Check ---")
sa_questions = [q for q in adsp_all if q["question_type"] == "단답형"]
print(f"Sample short-answer answers: {[q['answer'] for q in sa_questions[:5]]}")
for sa in sa_questions:
    assert sa["round"] in (32, 35, 37, 38), f"Unexpected SA in round {sa['round']}"
    assert sa["options"] == [], f"SA question has options: {sa}"
    assert len(sa["answer"].strip()) > 0, f"SA question has empty answer: {sa}"
print(f"PASS: All 40 short-answer questions verified strictly.")

print("\n=== ALL INDEPENDENT CHECKS PASSED SUCCESSFULLY ===")
