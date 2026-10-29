"""Standalone Test Runner for ADsP Crawler 4-Tier Test Suite.

Provides CLI execution for individual tiers or the entire test suite,
with structured summary metrics reporting and sandbox-safe configuration.

Usage:
    python tests/test_runner.py                  # Run all tiers (1~4)
    python tests/test_runner.py --tier 1         # Run Tier 1 only
    python tests/test_runner.py --tier 2 3       # Run Tiers 2 & 3
    python tests/test_runner.py --verbose        # Run with verbose pytest output
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
import pytest

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent

TIER_FILES = {
    1: TESTS_DIR / "test_tier1_feature_coverage.py",
    2: TESTS_DIR / "test_tier2_boundary_corner.py",
    3: TESTS_DIR / "test_tier3_cross_feature.py",
    4: TESTS_DIR / "test_tier4_scenarios.py",
}

TIER_NAMES = {
    1: "Tier 1: Feature Coverage (17 Features)",
    2: "Tier 2: Boundary & Corner Cases",
    3: "Tier 3: Cross-Feature Interactions",
    4: "Tier 4: Real-World Scenarios & Census",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ADsP Crawler 4-Tier E2E Test Suite Runner"
    )
    parser.add_argument(
        "--tier",
        type=int,
        nargs="+",
        choices=[1, 2, 3, 4],
        dest="tiers",
        help="Specify one or more tiers to execute (e.g. --tier 1 or --tier 1 2). Default: all",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run pytest in verbose mode (-v)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Run pytest in quiet mode (-q)",
    )
    return parser.parse_args(argv)


class TestMetricsCollector:
    """Pytest plugin to collect pass/fail/skip counts per tier."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = 0

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            if report.passed:
                self.passed += 1
            elif report.failed:
                self.failed += 1
            elif report.skipped:
                self.skipped += 1
        elif report.when == "setup" and report.failed:
            self.errors += 1


def run_tier(tier_no: int, verbose: bool = False, quiet: bool = False) -> tuple[int, TestMetricsCollector, float]:
    """Execute a single test tier and collect metrics."""
    test_file = TIER_FILES[tier_no]
    collector = TestMetricsCollector()

    pytest_args = [
        str(test_file),
        "-p", "no:cacheprovider",
        "-p", "no:anyio",
        "--import-mode=importlib",
    ]
    if verbose:
        pytest_args.append("-v")
    elif quiet:
        pytest_args.append("-q")

    start_time = time.perf_counter()
    exit_code = pytest.main(pytest_args, plugins=[collector])
    duration = time.perf_counter() - start_time

    return int(exit_code), collector, duration


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target_tiers = args.tiers or [1, 2, 3, 4]

    print("=" * 78)
    print(" ADsP Crawler 4-Tier Test Suite Execution")
    print("=" * 78)
    print(f"Target Tiers: {target_tiers}")
    print(f"Project Root: {PROJECT_ROOT}")
    print("-" * 78)

    tier_results = {}
    overall_start = time.perf_counter()
    overall_exit = 0

    for tier in target_tiers:
        print(f"\n>> Executing {TIER_NAMES[tier]}...")
        code, collector, dur = run_tier(tier, verbose=args.verbose, quiet=args.quiet)
        tier_results[tier] = {
            "code": code,
            "passed": collector.passed,
            "failed": collector.failed,
            "skipped": collector.skipped,
            "errors": collector.errors,
            "duration": dur,
        }
        if code != 0:
            overall_exit = 1

    overall_duration = time.perf_counter() - overall_start

    # Print Summary Report
    print("\n" + "=" * 78)
    print(" TEST EXECUTION SUMMARY REPORT")
    print("=" * 78)
    print(f"{'Tier':<42} | {'Passed':<7} | {'Failed':<7} | {'Time':<8} | {'Status'}")
    print("-" * 78)

    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for tier, res in tier_results.items():
        status_str = "PASS" if res["code"] == 0 and res["failed"] == 0 else "FAIL"
        print(
            f"{TIER_NAMES[tier]:<42} | "
            f"{res['passed']:<7} | "
            f"{res['failed']:<7} | "
            f"{res['duration']:>6.2f}s | "
            f"{status_str}"
        )
        total_passed += res["passed"]
        total_failed += res["failed"]
        total_skipped += res["skipped"]

    print("-" * 78)
    status_overall = "ALL TESTS PASSED" if overall_exit == 0 else "TEST SUITE FAILED"
    print(
        f"{'TOTAL (' + str(len(target_tiers)) + ' tiers)':<42} | "
        f"{total_passed:<7} | "
        f"{total_failed:<7} | "
        f"{overall_duration:>6.2f}s | "
        f"{status_overall}"
    )
    print("=" * 78)

    return overall_exit


if __name__ == "__main__":
    sys.exit(main())
