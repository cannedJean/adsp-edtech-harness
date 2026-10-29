# Original User Request

## 2026-10-29T00:29:03Z

문어CBT(sqldpass.com)에서 ADsP 기출문제 복원 전체 회차(15개 회차, 총 748문항)를 크롤링하여 표와 R 코드가 마크다운으로 보존된 계층형 JSON 데이터셋으로 추출하는 데이터 수집 및 정제 파이프라인 구축.

Working directory: C:/Users/SSAFY/Desktop/ADsP/adsp_crawler
Integrity mode: development

## Requirements

### R1. Category Hub Discovery & Ingestion
The crawler must automatically discover and index all ADsP past exam restoration posts from `https://www.sqldpass.com/blog/category/ADsP` (15 rounds: 32, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50). It must fetch the full SSR HTML of each post with polite rate limiting (1.0~2.0s random jitter delay between requests) and appropriate User-Agent headers. Support running specific rounds via CLI arguments.

### R2. Semantic Parsing & Rich Element Markdown Conversion
For each exam post, extract all question items (`li.rounded-2xl`).
- Distinguish question types: '4지선다' (multiple choice) vs '단답형' (short answer for pre-2024 rounds 32~39).
- Convert all HTML tables (`<table>`) inside question prompts into clean GitHub Flavored Markdown tables (`| ... |`).
- Convert all R code blocks (`<pre><code>`) inside question prompts into fenced code blocks (```r ... ```).
- Extract multiple choice options (1~4) into a structured string array for 4지선다 questions (empty array for 단답형).
- Extract the answer key (e.g. "3" for 4지선다, model answer text for 단답형) from the `<details>` container.
- Completely exclude all explanation paragraphs, incorrect choice analysis (오답 풀이), and supplementary concepts (보충 개념) from the dataset.

### R3. Data Validation & Hierarchical Storage
Validate extracted data against schema integrity rules and persist the dataset into both round-specific JSON files (`data/adsp_round_{round}.json`) and a consolidated JSON file (`data/adsp_all.json`) within the working directory.

## Acceptance Criteria

### Execution & Output Integrity
- [ ] Running the crawler successfully creates 15 individual JSON files (`adsp_round_{round}.json`) and one consolidated `adsp_all.json` in `data/`.
- [ ] Total questions harvested across all rounds is at least 740 (expected 748 questions).
- [ ] Every question entry strictly adheres to the schema: `question_no` (int), `question_type` (str), `prompt` (str), `options` (list of str), `answer` (str).

### Quality & Content Verification
- [ ] No question prompt or options array contains explanation text such as "오답 풀이", "보충 개념", or the "정답·해설 보기" button text.
- [ ] Questions containing tables (e.g., Round 50 Question 25 ANOVA table) contain valid markdown table syntax with pipes (`|`).
- [ ] Questions containing R outputs (e.g., Round 50 Question 26 PCA summary) contain fenced code block syntax (` ```r `).
- [ ] Short-answer questions in rounds 32~39 have `options: []` and contain the correct model answer in the `answer` field.
