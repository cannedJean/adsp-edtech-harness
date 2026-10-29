# Project: ADsP Crawler & Hierarchical JSON Pipeline

## Architecture
A modular, high-reliability Python data collection and processing pipeline:
1. `adsp_crawler.config`: Target URLs, 15 exam rounds configuration, rate limits (1.0~2.0s jitter), polite headers, validation constants.
2. `adsp_crawler.fetcher`: Hub discovery (`/blog/category/ADsP`), exam post SSR HTML fetcher with retry and rate limiting.
3. `adsp_crawler.parser`: Hybrid parser combining Next.js RSC Flight payload resolution (for 100% fidelity Markdown prompts, GFM tables, and fenced ````r ```` code blocks) with DOM parsing (for question numbers, question types, 4-choice options, and `<details>` answer keys). Negative filter rigorously eliminating explanation text and AST artifacts.
4. `adsp_crawler.validator`: Comprehensive JSON schema validation (`question_no`, `question_type`, `prompt`, `options`, `answer`), total census validation (748 questions across 15 rounds), and content integrity assertions.
5. `adsp_crawler.storage`: Hierarchical JSON persistence to `data/adsp_round_{round}.json` (15 files) and `data/adsp_all.json`.
6. `adsp_crawler.cli` / `main.py`: CLI interface supporting `--round`, `--all`, `--output-dir`.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | Hub Discovery | Index all 15 exam post URLs from `https://www.sqldpass.com/blog/category/ADsP` | M2 | ORIGINAL_REQUEST R1 | VERIFIED |
| 2 | Rate Limiter | Polite 1.0~2.0s random jitter delay between post requests | M2 | ORIGINAL_REQUEST R1 | VERIFIED |
| 3 | Polite Headers | Realistic browser User-Agent and Accept headers | M2 | ORIGINAL_REQUEST R1 | VERIFIED |
| 4 | CLI Round Selector | Support single round (`--round 50`), multiple rounds, or all rounds by default | M4 | ORIGINAL_REQUEST R1 | VERIFIED |
| 5 | Custom Output Dir | Allow overriding output destination via `--output-dir` (default `data/`) | M4 | ORIGINAL_REQUEST R3 | VERIFIED |
| 6 | Question Item Extraction | Extract all `li.rounded-2xl` question containers | M3 | ORIGINAL_REQUEST R2 | VERIFIED |
| 7 | Question Number Parser | Extract integer `question_no` from `p.tabular-nums` | M3 | ORIGINAL_REQUEST R2 | VERIFIED |
| 8 | Question Type Classifier | Classify as '4지선다' or '단답형' | M3 | ORIGINAL_REQUEST R2 | VERIFIED |
| 9 | GFM Table Preservation | Preserve/convert HTML tables into clean GitHub Flavored Markdown `| ... |` | M3 | ORIGINAL_REQUEST R2 | VERIFIED |
| 10 | R Code Block Converter | Ensure R code snippets are enclosed in fenced code blocks (````r ... ````) | M3 | ORIGINAL_REQUEST R2 | VERIFIED |
| 11 | Options Extractor | Extract 4 options for 4지선다, strictly empty `[]` for 단답형 | M3 | ORIGINAL_REQUEST R2 | VERIFIED |
| 12 | Answer Key Extractor | Extract answer from `<details>`, strip `"번"` for 4지선다, keep text for 단답형 | M3 | ORIGINAL_REQUEST R2 | VERIFIED |
| 13 | Negative Exclusion Filter | Strictly exclude all explanation text ("오답 풀이", "보충 개념", button text) | M3 | ORIGINAL_REQUEST R2 | VERIFIED |
| 14 | Schema Integrity Validator | Validate each question dictionary against strict schema | M4 | ORIGINAL_REQUEST R3 | VERIFIED |
| 15 | Total Count Validator | Validate full census: 748 questions (13 rounds x 50 + R38 x 49 + R40 x 49) | M4 | ORIGINAL_REQUEST R3 | VERIFIED |
| 16 | Per-Round Storage | Persist each round to `data/adsp_round_{round}.json` | M4 | ORIGINAL_REQUEST R3 | VERIFIED |
| 17 | Consolidated Storage | Persist all 748 questions to `data/adsp_all.json` | M4 | ORIGINAL_REQUEST R3 | VERIFIED |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | E2E Testing Suite (Dual Track) | Comprehensive 4-tier opaque-box test suite (`tests/`), runner, `TEST_INFRA.md`, and `TEST_READY.md` | none | DONE |
| M2 | Ingestion & Fetcher | `config.py`, `fetcher.py`: Hub discovery, jitter delay, polite headers, post fetching | none | DONE |
| M3 | Semantic Parser & Markdown Converter | `parser.py`: Hybrid flight stream + DOM parsing, GFM tables, ````r code fence, option extraction, answer extraction, explanation scrubber | M2 | DONE |
| M4 | Validator, Storage & CLI | `validator.py`, `storage.py`, `cli.py`, `main.py`: Schema validation, census checks, JSON persistence, CLI interface | M2, M3 | DONE |
| M5 | Full Harvest & E2E Test Pass + Adversarial Hardening | End-to-end harvest of all 15 rounds (748 questions), 100% pass of E2E test suite (Tiers 1-5, 80 tests passing) | M1, M2, M3, M4 | DONE |

## Code Layout
```
adsp_crawler/
├── __init__.py
├── config.py           # Constants, URL patterns, target rounds, headers
├── fetcher.py          # Category hub discovery & SSR HTML fetching with jitter
├── parser.py           # Hybrid Next.js RSC flight + DOM question parser
├── validator.py        # Schema and census integrity validators
├── storage.py          # Per-round and consolidated JSON writers
└── cli.py              # CLI argument parser and execution coordinator
main.py                 # Top-level entrypoint script
data/                   # Output directory for crawled JSON datasets
├── adsp_round_32.json  # 50 questions
├── adsp_round_35.json  # 50 questions
├── adsp_round_37.json  # 50 questions
├── adsp_round_38.json  # 49 questions
├── adsp_round_39.json  # 50 questions
├── adsp_round_40.json  # 49 questions
├── adsp_round_41.json  # 50 questions
├── adsp_round_42.json  # 50 questions
├── adsp_round_44.json  # 50 questions
├── adsp_round_45.json  # 50 questions
├── adsp_round_46.json  # 50 questions
├── adsp_round_47.json  # 50 questions
├── adsp_round_48.json  # 50 questions
├── adsp_round_49.json  # 50 questions
├── adsp_round_50.json  # 50 questions
└── adsp_all.json       # 748 questions (consolidated)
tests/                  # E2E test suite (Tiers 1-5, 80 tests)
├── conftest.py
├── test_tier1_feature_coverage.py   # 17 tests
├── test_tier2_boundary_corner.py    # 8 tests
├── test_tier3_cross_feature.py      # 6 tests
├── test_tier4_scenarios.py          # 3 tests
├── test_tier5_adversarial.py        # 41 tests
├── test_live_corpus.py              # 5 tests
└── test_runner.py                   # Standalone CLI test runner
```
