import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import json
from adsp_crawler.fetcher import fetch_hub_html, discover_rounds, fetch_round_post
from adsp_crawler.parser import parse_adsp_post

print("Connecting to live sqldpass.com...")
hub_html = fetch_hub_html()
rounds = discover_rounds(hub_html)
print(f"Live Discovered rounds ({len(rounds)}): {list(rounds.keys())}")

print("Fetching Round 50 from live site...")
r50_html = fetch_round_post(50, hub_urls=rounds, delay_min=0, delay_max=0)
r50_live = parse_adsp_post(r50_html)

with open("data/adsp_round_50.json", "r", encoding="utf-8") as f:
    r50_saved = json.load(f)

print(f"Round 50 Live Count: {len(r50_live)}, Saved Count: {len(r50_saved)}")
match = (r50_live == r50_saved)
print(f"Round 50 Bit-for-bit Parity Match: {match}")
if not match:
    for i, (l_q, s_q) in enumerate(zip(r50_live, r50_saved)):
        if l_q != s_q:
            print(f"Difference in Q{i+1}:")
            print(f"  Live:  {l_q}")
            print(f"  Saved: {s_q}")
            break
assert match, "Live data does not match saved data!"

print("Fetching Round 38 from live site...")
r38_html = fetch_round_post(38, hub_urls=rounds, delay_min=0, delay_max=0)
r38_live = parse_adsp_post(r38_html)

with open("data/adsp_round_38.json", "r", encoding="utf-8") as f:
    r38_saved = json.load(f)

print(f"Round 38 Live Count: {len(r38_live)}, Saved Count: {len(r38_saved)}")
match_38 = (r38_live == r38_saved)
print(f"Round 38 Bit-for-bit Parity Match: {match_38}")
assert match_38, "Live data does not match saved data for Round 38!"

print("SUCCESS: Live site verification passed for both Round 50 and Round 38!")
