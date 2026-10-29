"""Tier 5: Adversarial, Stress, and Robustness Verification Test Suite.

Authoritative source:
- ORIGINAL_REQUEST.md Acceptance Criteria & Robustness Requirements
- PROJECT.md Architecture, Interface Contracts, and Edge Cases
- Challenger tasks: malformed HTML, missing fields, invalid types, empty options in MCQ,
  leak edge cases, unusual markdown tables, invalid CLI parameters, empirical bug verification.
"""

from __future__ import annotations

from pathlib import Path
import re
import pytest

from bs4 import BeautifulSoup

from tests.conftest import (
    get_cli,
    get_config,
    get_parser,
    get_storage,
    get_validator,
)
from tests.fixtures.mock_data import _generate_question_html


# ==============================================================================
# 1. Malformed HTML & Parser Robustness
# ==============================================================================
class TestMalformedHtmlAndParserRobustness:
    """Stress-test parser with malformed HTML, unexpected tags, and broken payloads."""

    def test_parser_empty_or_whitespace_html(self):
        """Parser must gracefully return empty list for empty or whitespace HTML."""
        parser = get_parser()
        assert parser.parse_adsp_post("") == []
        assert parser.parse_adsp_post("   \n\t  ") == []

    def test_parser_none_or_non_string_resilience(self):
        """Parser must return empty list when given None or falsy input."""
        parser = get_parser()
        assert parser.parse_adsp_post(None) == []

    def test_parser_non_html_plain_text(self):
        """Parser must return empty list for non-HTML plain text with no question containers."""
        parser = get_parser()
        assert parser.parse_adsp_post("This is just some plain text without any HTML tags.") == []
        assert parser.parse_adsp_post("<html><body><div>No questions here</div></body></html>") == []

    def test_parser_unclosed_html_tags(self):
        """Parser must handle unclosed HTML tags without throwing unhandled exceptions."""
        parser = get_parser()
        unclosed_html = """
        <li class="rounded-2xl border">
          <div class="flex items-center justify-between">
            <p class="tabular-nums">문제 1</p>
            <span>4지선다</span>
          </div>
          <div class="mt-3">
            <p>Unclosed paragraph <b>bold <i>italic
            <pre><code>x <- 10
            <table><tr><th>H1<th>H2<tr><td>D1<td>D2
          <ul class="mt-4">
            <li><span class="min-w-0">Option 1</span>
            <li><span class="min-w-0">Option 2</span>
            <li><span class="min-w-0">Option 3</span>
            <li><span class="min-w-0">Option 4</span>
          <details>
            <p class="text-success">2번
        """
        questions = parser.parse_adsp_post(unclosed_html)
        assert len(questions) == 1
        q = questions[0]
        assert q["question_no"] == 1
        assert q["question_type"] == "4지선다"
        # When HTML li tags are unclosed/malformed, BeautifulSoup may nest them resulting in fewer than 4 options.
        # The validator MUST catch this defect and reject the question.
        validator = get_validator()
        if len(q["options"]) != 4:
            with pytest.raises(validator.ValidationError):
                validator.validate_question(q)
        else:
            assert len(q["options"]) == 4

    def test_parser_empty_question_container(self):
        """Parser must extract container even if child elements are missing."""
        parser = get_parser()
        html = '<li class="rounded-2xl"></li>'
        questions = parser.parse_adsp_post(html)
        assert len(questions) == 1
        q = questions[0]
        assert q["question_no"] == 1
        assert q["prompt"] == ""
        assert q["options"] == []
        assert q["answer"] == ""

    def test_parser_corrupted_flight_payload(self):
        """Parser must fall back to DOM when flight script payload is corrupted or has unresolvable hex refs."""
        parser = get_parser()
        html = """
        <script>self.__next_f.push([1, "corrupted \\x-not-json"]) </script>
        <script>self.__next_f.push([2, "[\\"$\\",\\"div\\",null,{\\"className\\\":\\"mt-3\\",\\"children\\\":[\\"$\\",\\"$L1\\",null,{\\"content\\\":\\"$99\\"}]}]"]) </script>
        <li class="rounded-2xl">
          <div class="flex"><p class="tabular-nums">1</p><span>4지선다</span></div>
          <div class="mt-3">DOM Fallback Prompt Text</div>
          <ul class="mt-4">
            <li><span class="min-w-0">A</span></li>
            <li><span class="min-w-0">B</span></li>
            <li><span class="min-w-0">C</span></li>
            <li><span class="min-w-0">D</span></li>
          </ul>
          <details><p class="text-success">1번</p></details>
        </li>
        """
        questions = parser.parse_adsp_post(html)
        assert len(questions) == 1
        assert "DOM Fallback Prompt Text" in questions[0]["prompt"]
        assert questions[0]["answer"] == "1"


# ==============================================================================
# 2. Missing Fields and Invalid Types (Schema Validator)
# ==============================================================================
class TestMissingFieldsAndInvalidTypes:
    """Empirically test validator rejection of schema defects, missing keys, and bad types."""

    @pytest.fixture
    def valid_mcq(self):
        return {
            "question_no": 1,
            "question_type": "4지선다",
            "prompt": "정상적인 지문입니다.",
            "options": ["선택지 1", "선택지 2", "선택지 3", "선택지 4"],
            "answer": "1",
        }

    @pytest.fixture
    def valid_sa(self):
        return {
            "question_no": 9,
            "question_type": "단답형",
            "prompt": "단답형 지문입니다.",
            "options": [],
            "answer": "IoT",
        }

    def test_validator_rejects_non_dict(self):
        """Validator must reject non-dictionary inputs."""
        validator = get_validator()
        for bad_input in [None, [], [1, 2, 3], "string", 123, True]:
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(bad_input)
            assert "dict" in str(exc.value)

    def test_validator_rejects_missing_keys(self, valid_mcq):
        """Validator must reject questions with any missing required schema key."""
        validator = get_validator()
        for key in ["question_no", "question_type", "prompt", "options", "answer"]:
            corrupted = dict(valid_mcq)
            del corrupted[key]
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(corrupted)
            assert "keys mismatch" in str(exc.value).lower()

    def test_validator_rejects_extra_forbidden_keys(self, valid_mcq):
        """Validator must reject unexpected extra keys (except optional 'round')."""
        validator = get_validator()
        corrupted = dict(valid_mcq, extra_key="unexpected", metadata={"score": 10})
        with pytest.raises(validator.ValidationError) as exc:
            validator.validate_question(corrupted)
        assert "keys mismatch" in str(exc.value).lower()

    def test_validator_rejects_invalid_question_no_types(self, valid_mcq):
        """Validator must reject non-integer question_no (including booleans, floats, strings)."""
        validator = get_validator()
        for bad_no in [True, False, 1.0, 2.5, "1", None, [1]]:
            corrupted = dict(valid_mcq, question_no=bad_no)
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(corrupted)
            assert "question_no" in str(exc.value).lower()

    def test_validator_rejects_out_of_bound_question_no(self, valid_mcq):
        """Validator must reject question_no outside 1..50 range."""
        validator = get_validator()
        for bad_no in [0, -1, -50, 51, 100]:
            corrupted = dict(valid_mcq, question_no=bad_no)
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(corrupted)
            assert "between 1 and 50" in str(exc.value).lower()

    def test_validator_rejects_invalid_question_type(self, valid_mcq):
        """Validator must reject any question_type other than '4지선다' or '단답형'."""
        validator = get_validator()
        for bad_type in ["multiple_choice", "객관식", "선다형", "5지선다", "주관식", "", None, 123]:
            corrupted = dict(valid_mcq, question_type=bad_type)
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(corrupted)
            assert "question_type" in str(exc.value).lower()

    def test_validator_rejects_invalid_prompt_types_and_blanks(self, valid_mcq):
        """Validator must reject non-string, empty, or whitespace-only prompts."""
        validator = get_validator()
        for bad_prompt in ["", "   ", "\n\t  \r\n", None, 123, ["prompt"], {"text": "hello"}]:
            corrupted = dict(valid_mcq, prompt=bad_prompt)
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(corrupted)
            assert "prompt" in str(exc.value).lower()

    def test_validator_rejects_invalid_answer_types_and_blanks(self, valid_mcq, valid_sa):
        """Validator must reject non-string, empty, or whitespace-only answers."""
        validator = get_validator()
        # For MCQ: must be string "1", "2", "3", "4"
        for bad_ans in [1, 2, 3, 4, True, None, "", "   ", "5", "0", "1번", ["1"]]:
            corrupted = dict(valid_mcq, answer=bad_ans)
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(corrupted)
            assert "answer" in str(exc.value).lower()

        # For SA: must be non-empty string
        for bad_ans in ["", "   ", "\n\t", None, 123, True, []]:
            corrupted = dict(valid_sa, answer=bad_ans)
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(corrupted)
            assert "answer" in str(exc.value).lower()

    def test_validator_round_field_type_checking(self, valid_mcq):
        """When optional 'round' field is present, it must be a valid target round integer."""
        validator = get_validator()
        # Valid round
        valid_with_round = dict(valid_mcq, round=50)
        assert validator.validate_question(valid_with_round) is True

        # Invalid rounds (boolean, float, unsupported round 43, out-of-range 99)
        for bad_round in [True, False, 50.0, 43, 99, -1, "50", None]:
            corrupted = dict(valid_mcq, round=bad_round)
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(corrupted)
            assert "round" in str(exc.value).lower()


# ==============================================================================
# 3. Empty Options in MCQ & Option Structure
# ==============================================================================
class TestEmptyAndInvalidOptions:
    """Test boundary and stress scenarios for multiple choice options array."""

    def test_mcq_rejects_empty_options_array(self):
        """4지선다 with empty options [] must be rejected by validator."""
        validator = get_validator()
        q = {
            "question_no": 1,
            "question_type": "4지선다",
            "prompt": "문제",
            "options": [],
            "answer": "1",
        }
        with pytest.raises(validator.ValidationError) as exc:
            validator.validate_question(q)
        assert "exactly 4 options" in str(exc.value)

    def test_mcq_rejects_partial_options_counts(self):
        """4지선다 with 1, 2, 3, or 5 options must be rejected."""
        validator = get_validator()
        for count in [1, 2, 3, 5, 6]:
            q = {
                "question_no": 1,
                "question_type": "4지선다",
                "prompt": "문제",
                "options": [f"Option {i}" for i in range(count)],
                "answer": "1",
            }
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(q)
            assert "exactly 4 options" in str(exc.value)

    def test_mcq_rejects_empty_or_whitespace_strings_inside_options(self):
        """4지선다 must reject options containing empty strings or whitespace-only strings."""
        validator = get_validator()
        bad_options_cases = [
            ["Opt1", "", "Opt3", "Opt4"],
            ["", "Opt2", "Opt3", "Opt4"],
            ["Opt1", "Opt2", "Opt3", ""],
            ["Opt1", "   \t  ", "Opt3", "Opt4"],
            ["\n", "Opt2", "Opt3", "Opt4"],
        ]
        for bad_opts in bad_options_cases:
            q = {
                "question_no": 1,
                "question_type": "4지선다",
                "prompt": "문제",
                "options": bad_opts,
                "answer": "1",
            }
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(q)
            assert "non-empty string" in str(exc.value).lower()

    def test_mcq_rejects_non_string_elements_inside_options(self):
        """4지선다 must reject options containing integers, None, dicts, or lists."""
        validator = get_validator()
        bad_opts = ["Opt1", 123, None, {"text": "Opt4"}]
        q = {
            "question_no": 1,
            "question_type": "4지선다",
            "prompt": "문제",
            "options": bad_opts,
            "answer": "1",
        }
        with pytest.raises(validator.ValidationError) as exc:
            validator.validate_question(q)
        assert "non-empty string" in str(exc.value).lower()

    def test_short_answer_rejects_any_non_empty_options(self):
        """단답형 must strictly reject options with any elements."""
        validator = get_validator()
        for bad_opts in [["option"], [""], [None], [1, 2, 3, 4]]:
            q = {
                "question_no": 9,
                "question_type": "단답형",
                "prompt": "문제",
                "options": bad_opts,
                "answer": "IoT",
            }
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(q)
            assert "empty options []" in str(exc.value)


# ==============================================================================
# 4. Leak Edge Cases (Negative Exclusion Scrubber)
# ==============================================================================
class TestExplanationLeakEdgeCases:
    """Stress-test negative exclusion filters against leak edge cases."""

    FORBIDDEN_VARIANTS = [
        "오답 풀이",
        "오답풀이",
        "보충 개념",
        "보충개념",
        "정답·해설 보기",
        "정답해설보기",
    ]

    def test_leak_in_prompt_rejected(self):
        """Any forbidden term inside question prompt must be caught and rejected."""
        validator = get_validator()
        for term in self.FORBIDDEN_VARIANTS:
            q = {
                "question_no": 1,
                "question_type": "4지선다",
                "prompt": f"다음 중 올바른 것은? (참고: {term} 참조)",
                "options": ["A", "B", "C", "D"],
                "answer": "1",
            }
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(q)
            assert term in str(exc.value)

    def test_leak_in_options_rejected(self):
        """Any forbidden term inside any multiple choice option must be caught and rejected."""
        validator = get_validator()
        for term in self.FORBIDDEN_VARIANTS:
            q = {
                "question_no": 1,
                "question_type": "4지선다",
                "prompt": "정상적인 지문입니다.",
                "options": ["A", f"선택지 설명 ({term})", "C", "D"],
                "answer": "1",
            }
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(q)
            assert term in str(exc.value)

    def test_leak_in_answer_rejected(self):
        """Any forbidden term inside answer field must be caught and rejected."""
        validator = get_validator()
        for term in self.FORBIDDEN_VARIANTS:
            q = {
                "question_no": 9,
                "question_type": "단답형",
                "prompt": "정상적인 단답형 지문입니다.",
                "options": [],
                "answer": f"정답은 {term} 입니다.",
            }
            with pytest.raises(validator.ValidationError) as exc:
                validator.validate_question(q)
            assert term in str(exc.value)

    def test_details_explanation_paragraphs_not_leaked_into_dom_prompt(self):
        """Parser must not allow explanation text from <details> to leak into prompt."""
        parser = get_parser()
        html = """
        <li class="rounded-2xl">
          <p class="tabular-nums">1</p>
          <span>4지선다</span>
          <div class="mt-3">본문 질문 지문입니다.</div>
          <ul class="mt-4">
            <li><span class="min-w-0">Opt 1</span></li>
            <li><span class="min-w-0">Opt 2</span></li>
            <li><span class="min-w-0">Opt 3</span></li>
            <li><span class="min-w-0">Opt 4</span></li>
          </ul>
          <details>
            <summary>정답·해설 보기</summary>
            <p class="text-success">1번</p>
            <div class="mt-4">
              <p>오답 풀이: 2번은 왜 틀렸는지 설명...</p>
              <p>보충 개념: 관련 이론 요약...</p>
            </div>
          </details>
        </li>
        """
        questions = parser.parse_adsp_post(html)
        assert len(questions) == 1
        q = questions[0]
        assert "정답·해설 보기" not in q["prompt"]
        assert "오답 풀이" not in q["prompt"]
        assert "보충 개념" not in q["prompt"]
        for opt in q["options"]:
            assert "오답 풀이" not in opt


# ==============================================================================
# 5. Unusual Markdown Tables
# ==============================================================================
class TestUnusualMarkdownTables:
    """Stress-test HTML to GFM table converter against irregular and unusual tables."""

    def test_table_conversion_empty_or_none(self):
        """html_table_to_gfm must handle None, empty table, and table with no cells."""
        parser = get_parser()
        assert parser.html_table_to_gfm(None) == ""

        soup_empty = BeautifulSoup("<table></table>", "html.parser").find("table")
        assert parser.html_table_to_gfm(soup_empty) == ""

        soup_no_cells = BeautifulSoup("<table><tr></tr></table>", "html.parser").find("table")
        assert parser.html_table_to_gfm(soup_no_cells) == ""

    def test_table_without_thead_uses_first_tr_as_header(self):
        """Table without <thead> must use the first <tr> as the GFM header."""
        parser = get_parser()
        html = """
        <table>
          <tr><td>구분</td><td>값</td></tr>
          <tr><td>F-value</td><td>12.34</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser").find("table")
        gfm = parser.html_table_to_gfm(soup)
        lines = [line.strip() for line in gfm.strip().split("\n")]
        assert len(lines) == 3
        assert lines[0] == "| 구분 | 값 |"
        assert lines[1] == "| --- | --- |"
        assert lines[2] == "| F-value | 12.34 |"

    def test_ragged_table_columns_padded(self):
        """Table with varying row lengths must pad all rows to max_cols."""
        parser = get_parser()
        html = """
        <table>
          <tr><th>Col1</th><th>Col2</th></tr>
          <tr><td>A</td><td>B</td><td>C</td><td>D</td></tr>
          <tr><td>X</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser").find("table")
        gfm = parser.html_table_to_gfm(soup)
        lines = [line.strip() for line in gfm.strip().split("\n")]
        # Max cols is 4. Header and all rows must have 4 columns.
        for line in lines:
            pipes = line.count("|")
            assert pipes == 5, f"Expected 4 columns (5 pipes), got line: {line}"

    def test_table_with_empty_cells_preserves_cell_alignment(self):
        """Table with empty cells (ANOVA residuals/total) must retain valid cell positions."""
        parser = get_parser()
        html = """
        <table>
          <thead><tr><th>요인</th><th>SS</th><th>DF</th><th>MS</th><th>F</th></tr></thead>
          <tbody>
            <tr><td>회귀</td><td>100</td><td>2</td><td>50</td><td>10.0</td></tr>
            <tr><td>잔차</td><td>20</td><td>4</td><td>5</td><td></td></tr>
            <tr><td>계</td><td>120</td><td>6</td><td></td><td></td></tr>
          </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser").find("table")
        gfm = parser.html_table_to_gfm(soup)
        lines = [line.strip() for line in gfm.strip().split("\n")]
        assert len(lines) == 5  # header + separator + 3 data rows
        # Check 잔차 row
        assert lines[3] == "| 잔차 | 20 | 4 | 5 |  |"
        # Check 계 row
        assert lines[4] == "| 계 | 120 | 6 |  |  |"


# ==============================================================================
# 6. Invalid CLI Parameters
# ==============================================================================
class TestInvalidCliParameters:
    """Stress-test CLI argument parsing and rejection of invalid options."""

    def test_cli_rejects_negative_rounds(self):
        """CLI must exit on negative round values."""
        cli = get_cli()
        with pytest.raises(SystemExit):
            cli.parse_args(["--round", "-5"])

    def test_cli_rejects_non_existent_round_43(self):
        """CLI must exit on round 43 with helpful diagnostic."""
        cli = get_cli()
        with pytest.raises(SystemExit):
            cli.parse_args(["--round", "43"])

    def test_cli_rejects_out_of_range_rounds(self):
        """CLI must exit on non-existent rounds (e.g. 1, 99, 100)."""
        cli = get_cli()
        for bad_r in ["1", "30", "51", "99", "100"]:
            with pytest.raises(SystemExit):
                cli.parse_args(["--round", bad_r])

    def test_cli_rejects_non_integer_round_argument(self):
        """CLI must exit on non-integer argument passed to --round."""
        cli = get_cli()
        with pytest.raises(SystemExit):
            cli.parse_args(["--round", "abc"])

    def test_cli_rejects_mixed_valid_and_invalid_rounds(self):
        """CLI must reject list if ANY round in the list is invalid."""
        cli = get_cli()
        with pytest.raises(SystemExit):
            cli.parse_args(["--round", "50", "43"])

    def test_cli_rejects_unknown_flags(self):
        """CLI must exit on unknown command line arguments."""
        cli = get_cli()
        with pytest.raises(SystemExit):
            cli.parse_args(["--some-invalid-flag"])


# ==============================================================================
# 7. Census and Storage Safety Assertions
# ==============================================================================
class TestCensusAndStorageIntegrity:
    """Empirically test census boundaries and storage safety."""

    def test_round_validation_fails_on_unsupported_round(self):
        """validate_round_dataset must reject rounds not in TARGET_ROUNDS."""
        validator = get_validator()
        with pytest.raises(validator.ValidationError) as exc:
            validator.validate_round_dataset(43, [])
        assert "Unknown exam round" in str(exc.value)

    def test_round_validation_fails_on_count_mismatch(self):
        """validate_round_dataset must reject wrong question counts."""
        validator = get_validator()
        base_q = {
            "question_no": 1,
            "question_type": "4지선다",
            "prompt": "문제",
            "options": ["1", "2", "3", "4"],
            "answer": "1",
        }
        # Round 50 expects 50 questions, given 49
        qs_49 = [dict(base_q, question_no=i) for i in range(1, 50)]
        with pytest.raises(validator.ValidationError) as exc:
            validator.validate_round_dataset(50, qs_49)
        assert "expected 50" in str(exc.value).lower()

        # Round 38 expects 49 questions, given 50
        qs_50 = [dict(base_q, question_no=i) for i in range(1, 51)]
        with pytest.raises(validator.ValidationError) as exc:
            validator.validate_round_dataset(38, qs_50)
        assert "expected 49" in str(exc.value).lower()

    def test_consolidated_validation_fails_on_missing_rounds(self):
        """validate_consolidated_dataset must reject dictionary missing any of 15 rounds."""
        validator = get_validator()
        # Create dict missing Round 50 (only 14 rounds)
        from tests.fixtures.mock_data import generate_full_15_rounds_dataset
        full_data = generate_full_15_rounds_dataset()
        del full_data[50]
        with pytest.raises(validator.ValidationError) as exc:
            validator.validate_consolidated_dataset(full_data)
        assert "Expected 15 rounds" in str(exc.value)

    def test_storage_does_not_write_file_on_validation_failure(self, tmp_path):
        """save_round_json must NOT write any file to disk if validation fails."""
        storage = get_storage()
        validator = get_validator()
        invalid_questions = [{"question_no": 1}]  # Missing required keys

        target_file = tmp_path / "adsp_round_50.json"
        assert not target_file.exists()

        with pytest.raises(validator.ValidationError):
            storage.save_round_json(50, invalid_questions, output_dir=tmp_path)

        assert not target_file.exists(), "File must not be written if validation failed!"


# ==============================================================================
# 8. EMPIRICAL REGRESSION CHALLENGES (Real Flaws & Gaps Uncovered)
# ==============================================================================
class TestEmpiricalChallengerFindings:
    """Specific empirical regression tests documenting bugs discovered during adversarial analysis."""

    def test_challenger_finding_mcq_decimal_option_prefix_stripping(self):
        """REGRESSION TEST for CRITICAL BUG:

        When MCQ options are decimal numbers (e.g. '1.0', '1.5', '2.0', '2.5'),
        the parser's regex `re.sub(r'^[1-4]\\s*[\\.\\)]\\s*', '', opt_txt)`
        in parser.py:379 strips '1.' or '2.' from the decimal numbers,
        corrupting '1.0' into '0' and '1.5' into '5'.
        
        This bug caused real data corruption in Round 46 Q24, Q30, Round 37 Q25, Round 47 Q31.
        """
        parser = get_parser()
        html = """
        <li class="rounded-2xl">
          <div class="flex items-center justify-between">
            <p class="tabular-nums">문제 24</p>
            <span>4지선다</span>
          </div>
          <div class="mt-3">확률변수 X의 기댓값은?</div>
          <ul class="mt-4">
            <li><span class="font-semibold tabular-nums">1.</span><span class="min-w-0">1.0</span></li>
            <li><span class="font-semibold tabular-nums">2.</span><span class="min-w-0">1.5</span></li>
            <li><span class="font-semibold tabular-nums">3.</span><span class="min-w-0">2.0</span></li>
            <li><span class="font-semibold tabular-nums">4.</span><span class="min-w-0">2.5</span></li>
          </ul>
          <details><p class="text-success">3번</p></details>
        </li>
        """
        questions = parser.parse_adsp_post(html)
        assert len(questions) == 1
        opts = questions[0]["options"]
        
        # In a correct implementation, decimal numbers must be preserved:
        # ['1.0', '1.5', '2.0', '2.5']
        # If buggy, opts will be ['0', '5', '0', '5'].
        assert opts == ["1.0", "1.5", "2.0", "2.5"], (
            f"CRITICAL BUG REPRODUCED: Decimal options were corrupted by prefix regex! "
            f"Expected ['1.0', '1.5', '2.0', '2.5'], but got {opts}"
        )

    def test_challenger_finding_round_38_allows_forbidden_q50(self):
        """REGRESSION TEST for VALIDATOR GAP:

        Rounds 38 and 40 have only 49 questions (Q1~Q49), and Q50 does not exist.
        Currently, `validate_round_dataset(38, questions)` checks `len(questions) == 49`
        and duplicate IDs, but does NOT verify that question_no 50 is absent.
        If a dataset contains Q1~Q48 and Q50 (missing Q49), the validator currently passes it!
        """
        validator = get_validator()
        base_q = {
            "question_no": 1,
            "question_type": "4지선다",
            "prompt": "문제",
            "options": ["1", "2", "3", "4"],
            "answer": "1",
        }
        # 49 questions: 1..48 and 50 (missing Q49)
        qs_with_forbidden_q50 = [dict(base_q, question_no=i) for i in range(1, 49)] + [
            dict(base_q, question_no=50)
        ]

        # The validator SHOULD reject Q50 in Round 38
        with pytest.raises(validator.ValidationError) as exc:
            # If the validator has the gap, this will NOT raise ValidationError and will fail the test!
            if 50 in [q["question_no"] for q in qs_with_forbidden_q50]:
                validator.validate_round_dataset(38, qs_with_forbidden_q50)
                # If we reached here without exception, document the gap
                pytest.fail("VALIDATOR GAP REPRODUCED: Round 38 validator permitted Q50 to exist!")

    def test_challenger_finding_consolidated_list_ignores_round_census(self):
        """REGRESSION TEST for CONSOLIDATED VALIDATOR GAP:

        When `validate_consolidated_dataset` is passed a flat list of 748 questions,
        it only counts total_questions, mcq, and sa, but does NOT verify that all 15 rounds
        are present. Passing 748 questions from a single round passes validation.
        """
        validator = get_validator()
        base_mcq = {
            "question_no": 1,
            "question_type": "4지선다",
            "prompt": "문제",
            "options": ["1", "2", "3", "4"],
            "answer": "1",
        }
        base_sa = {
            "question_no": 1,
            "question_type": "단답형",
            "prompt": "문제",
            "options": [],
            "answer": "IoT",
        }
        # 708 MCQ + 40 SA = 748 questions, all identical, no 'round' metadata
        homogeneous_list = [dict(base_mcq) for _ in range(708)] + [dict(base_sa) for _ in range(40)]

        # The consolidated validator SHOULD reject a dataset missing 14 rounds
        with pytest.raises(validator.ValidationError):
            validator.validate_consolidated_dataset(homogeneous_list)
            pytest.fail("VALIDATOR GAP REPRODUCED: validate_consolidated_dataset accepted homogeneous list without round census!")
