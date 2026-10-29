# E2E Test Suite Ready

## Test Runner
- Command: `python tests/test_runner.py` (or `python -m pytest tests/ -p no:cacheprovider`)
- Expected: all 34 tests pass with exit code 0

## Coverage Summary
| Tier | Count | Description |
|------|------:|-------------|
| 1. Feature Coverage | 17 | 17/17 features from Feature Inventory verified |
| 2. Boundary & Corner | 8 | Empty options (단답형), missing Q50 (R38/R40), sparse tables, flight stream R codes, suffix stripping |
| 3. Cross-Feature | 6 | End-to-end pipeline (fetch-parse-validate, CLI-storage, transient 500 retry recovery) |
| 4. Real-World Application | 3 | Full 15-round census (748 questions: 708 MCQ, 40 short answer), single-round flow, negative leak audit |
| **Total** | **34** | **100% Pass Rate** |

## Feature Checklist
| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---------|:------:|:------:|:------:|:------:|
| F1: Hub Discovery | ✓ | ✓ | ✓ | ✓ |
| F2: Rate Limiter | ✓ | | ✓ | |
| F3: Polite Headers | ✓ | | | |
| F4: CLI Round Selector | ✓ | ✓ | ✓ | |
| F5: Custom Output Dir | ✓ | | ✓ | |
| F6: Question Item Extractor | ✓ | | ✓ | ✓ |
| F7: Question Number Parser | ✓ | | ✓ | ✓ |
| F8: Question Type Classifier | ✓ | ✓ | ✓ | ✓ |
| F9: GFM Table Preservation | ✓ | ✓ | ✓ | ✓ |
| F10: R Code Block Converter | ✓ | ✓ | ✓ | ✓ |
| F11: Options Extractor | ✓ | ✓ | ✓ | ✓ |
| F12: Answer Key Extractor | ✓ | ✓ | ✓ | ✓ |
| F13: Negative Exclusion Filter | ✓ | | ✓ | ✓ |
| F14: Schema Integrity Validator | ✓ | ✓ | ✓ | ✓ |
| F15: Total Count Validator | ✓ | ✓ | ✓ | ✓ |
| F16: Per-Round Storage | ✓ | | ✓ | ✓ |
| F17: Consolidated Storage | ✓ | | ✓ | ✓ |
