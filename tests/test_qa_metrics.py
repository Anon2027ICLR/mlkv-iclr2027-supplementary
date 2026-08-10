import pytest

from mlkv.qa_metrics import exact_match, extract_span, f1, normalize, span_scores


class TestExtractSpan:
    def test_after_last_marker(self):
        assert extract_span("reasoning... #### 308") == "308"
        assert extract_span("#### first\nmore #### second") == "second"

    def test_no_marker_full_text(self):
        assert extract_span("  the answer  ") == "the answer"

    def test_placeholder_echo_stripped(self):
        # observed Qwen3 outputs on mRAG (would score 0 without stripping)
        assert extract_span("The defense gave up 308. \n\n#### <exact answer span>308####") == "308"
        assert extract_span("Luke led (118). \n\n#### <exact answer span>118</exact answer span>") == "118"

    def test_trailing_marker_falls_back_to_previous(self):
        assert extract_span("led the NFL with 24. \n\n#### 24#### <exact answer span>") == "24"

    def test_all_markers_empty_falls_back_to_text(self):
        # a bare echoed KNOWN placeholder leaves no content -> fall back to text
        assert extract_span("the answer is here ####  #### <exact answer span>") == "the answer is here"

    def test_unknown_bracket_content_is_kept(self):
        # unknown bracket content counts as content (can't enumerate all echoes);
        # scoring against gold decides its fate
        assert extract_span("#### <42>") == "42"


class TestNormalize:
    def test_case_and_punctuation(self):
        assert normalize("The Answer!", "vi") == "the answer"

    def test_articles_stripped_only_where_language_has_them(self):
        assert normalize("the cat", "en") == "cat"
        assert normalize("la casa", "es") == "casa"
        # 'the'/'la' are ordinary words in languages without those articles
        assert normalize("the cat", "sw") == "the cat"

    def test_vietnamese_diacritics_preserved(self):
        assert normalize("Hà Nội", "vi") == "hà nội"
        assert normalize("Hà Nội", "vi") != normalize("Ha Noi", "vi")

    def test_nfkc_fullwidth_digits(self):
        # full-width digits (common in zh/ja output) unify with ASCII
        assert normalize("３０８", "zh") == normalize("308", "zh")

    def test_punctuation_is_token_boundary(self):
        assert normalize("308,000", "en") == "308 000"


class TestExactMatch:
    def test_exact(self):
        assert exact_match("308", ["308"], "en")

    def test_case_punct_insensitive(self):
        assert exact_match("The Panthers.", ["panthers"], "en")

    def test_multiple_golds(self):
        assert exact_match("b", ["a", "b"], "en")

    def test_no_match(self):
        assert not exact_match("309", ["308"], "en")


class TestF1:
    def test_partial_overlap(self):
        # pred tokens (en, articles stripped): [answer, is, 308]; gold: [308]
        assert f1("the answer is 308", ["308"], "en") == pytest.approx(0.5)

    def test_chinese_char_level(self):
        # pred chars: 北京市; gold chars: 北京 -> P=2/3, R=1, F1=0.8
        assert f1("北京市", ["北京"], "zh") == pytest.approx(0.8)

    def test_whitespace_tokens_for_vi(self):
        # word-level, not char-level: half the words overlap
        assert f1("thành phố", ["thành phố Hà Nội"], "vi") == pytest.approx(2 * 1 * 0.5 / 1.5)

    def test_max_over_golds(self):
        assert f1("308", ["309", "308"], "en") == pytest.approx(1.0)

    def test_empty_prediction(self):
        assert f1("", ["308"], "en") == 0.0

    def test_zero_overlap(self):
        assert f1("cat", ["dog"], "en") == 0.0


class TestSpanScores:
    def test_marker_answer_scores_em(self):
        scores = span_scores("Long reasoning about 42 things.\n#### 308", ["308"], "en")
        assert scores["em"] is True
        assert scores["f1"] == pytest.approx(1.0)

    def test_verbose_answer_counts_via_containment(self):
        # sentence-wrapped correct answer: containment True, strict EM False
        scores = span_scores("It lost 308 points", ["308"], "en")
        assert scores["em"] is True and scores["em_strict"] is False
        assert 0 < scores["f1"] < 1

    def test_answer_inside_angle_brackets_survives(self):
        # observed: model mimics the template -> "#### <308>"
        scores = span_scores("Đội thủ chỉ thua 308 điểm. \n\n#### <308>", ["308"], "vi")
        assert scores["em"] is True and scores["em_strict"] is True

    def test_zh_sentence_plus_empty_placeholder(self):
        # observed: correct zh sentence, then a bare echoed placeholder
        out = "黑豹队的防守只丢了308分。\n\n#### <原文中的答案片段>"
        scores = span_scores(out, ["308"], "zh")
        assert scores["em"] is True and scores["em_strict"] is False

    def test_containment_respects_token_boundaries(self):
        assert span_scores("the answer is 245", ["24"], "en")["em"] is False

    def test_containment_wrong_answer_stays_wrong(self):
        # genuinely wrong retrieval must not be rescued
        out = "贾里德在职业生涯中有24次擒杀。#### <原文中的答案片段>"
        assert span_scores(out, ["136 次"], "zh")["em"] is False
