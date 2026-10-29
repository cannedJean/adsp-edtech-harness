"""Live network verification test for Milestone 2: Ingestion & Fetcher Module."""

import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from adsp_crawler import (
    BASE_URL,
    HUB_URL,
    TARGET_ROUNDS,
    TOTAL_EXPECTED_ROUNDS,
    TOTAL_EXPECTED_QUESTIONS,
    apply_polite_delay,
    create_session,
    discover_rounds,
    fetch_hub_html,
    fetch_post,
    fetch_round_post,
)


def run_live_verification():
    print("=== Milestone 2 Live Verification ===")
    
    # 1. Test jitter delay timing
    print("[1/4] Verifying polite rate limiting jitter timing...")
    t0 = time.time()
    slept = apply_polite_delay(1.0, 1.2)
    elapsed = time.time() - t0
    print(f"  Jitter reported: {slept:.3f}s, wall clock elapsed: {elapsed:.3f}s")
    assert 1.0 <= slept <= 1.2, f"Jitter {slept} out of bounds [1.0, 1.2]"
    assert elapsed >= 0.99, f"Elapsed {elapsed} shorter than minimum bound"
    print("  -> Jitter delay verified!")

    # 2. Test live category hub fetch
    print(f"[2/4] Fetching category hub from {HUB_URL}...")
    session = create_session()
    hub_html = fetch_hub_html(session=session)
    print(f"  Hub HTML received: {len(hub_html):,} bytes")
    assert len(hub_html) > 50000, "Hub HTML unexpectedly small"
    print("  -> Hub fetch verified!")

    # 3. Test dynamic discovery of all 15 rounds
    print("[3/4] Discovering exam rounds from live hub HTML...")
    discovered = discover_rounds(hub_html, base_url=BASE_URL)
    discovered_rounds = sorted(discovered.keys())
    print(f"  Discovered {len(discovered_rounds)} rounds: {discovered_rounds}")
    assert discovered_rounds == TARGET_ROUNDS, f"Discovered rounds {discovered_rounds} != expected {TARGET_ROUNDS}"
    assert len(discovered_rounds) == TOTAL_EXPECTED_ROUNDS, f"Round count mismatch: {len(discovered_rounds)} != {TOTAL_EXPECTED_ROUNDS}"
    for r in discovered_rounds:
        url = discovered[r]
        assert url.startswith(f"{BASE_URL}/blog/past-exam/adsp-"), f"Invalid post URL format: {url}"
        print(f"    Round {r:02d}: {url}")
    print("  -> Hub discovery verified! All 15 rounds correctly mapped.")

    # 4. Test live fetch of an individual exam post (Round 50)
    print("[4/4] Fetching Round 50 exam post HTML...")
    r50_html = fetch_round_post(50, hub_urls=discovered, session=session, delay_min=0.5, delay_max=0.8)
    print(f"  Round 50 HTML received: {len(r50_html):,} bytes")
    assert len(r50_html) > 400000, f"Round 50 HTML suspiciously small: {len(r50_html)} bytes"
    assert "rounded-2xl" in r50_html, "Missing question containers (li.rounded-2xl)"
    assert "ADsP 50회" in r50_html or "50회" in r50_html, "Round title not found in HTML"
    print("  -> Post fetching verified! Question containers confirmed.")

    print("\n=== ALL MILESTONE 2 LIVE CHECKS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    run_live_verification()
