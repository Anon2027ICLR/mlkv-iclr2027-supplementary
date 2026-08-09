import pytest

from mlkv.metrics import extract_candidates, is_correct, parse_gold


class TestNumberFormats:
    """The harness must not manufacture per-language damage via number parsing."""

    def test_english_grouping(self):
        assert is_correct("The total is #### 1,234", 1234)

    def test_vietnamese_grouping_dot(self):
        # VI/DE/ES write one thousand two hundred thirty-four as 1.234
        assert is_correct("Đáp số là #### 1.234", 1234)

    def test_decimal_comma(self):
        assert is_correct("#### 12,5", 12.5)

    def test_decimal_dot(self):
        assert is_correct("#### 12.5", 12.5)

    def test_mixed_separators_en(self):
        assert is_correct("#### 1,234.5", 1234.5)

    def test_mixed_separators_eu(self):
        assert is_correct("#### 1.234,5", 1234.5)

    def test_plain_integer(self):
        assert is_correct("#### 42", 42)

    def test_negative(self):
        assert is_correct("#### -7", -7)

    def test_trailing_punctuation(self):
        assert is_correct("#### 42.", 42)
        assert is_correct("Kết quả: #### 500,", 500)

    def test_ambiguous_dot_matches_both_readings(self):
        # "1.234" could be 1234 (grouping) or 1.234 (decimal) — both candidates
        candidates = extract_candidates("#### 1.234")
        assert 1234.0 in candidates
        assert 1.234 in candidates


class TestExtraction:
    def test_prefers_after_last_marker(self):
        text = "Step 1 gives 10. #### 10\nWait, correcting: #### 20"
        assert is_correct(text, 20)
        assert not is_correct(text, 10)

    def test_falls_back_to_last_number_without_marker(self):
        assert is_correct("The answer is 99", 99)

    def test_marker_without_number_falls_back(self):
        assert is_correct("computed 55 total #### (see above)", 55)

    def test_no_numbers(self):
        assert extract_candidates("no digits here") == set()
        assert not is_correct("no digits here", 5)

    def test_number_inside_reasoning_not_preferred(self):
        text = "We have 3 apples and 4 pears so 3+4=7 items. #### 7"
        assert is_correct(text, 7)


class TestGold:
    def test_gold_int(self):
        assert parse_gold(18) == 18.0

    def test_gold_string_with_commas(self):
        assert parse_gold("1,234") == 1234.0

    def test_gold_bad(self):
        with pytest.raises(ValueError):
            parse_gold("N/A")
