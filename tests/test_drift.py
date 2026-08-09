from unittest.mock import patch

from mlkv.drift import _predict_label, drift_score, script_profile
from mlkv.languages import LANGUAGES


class TestPredictLabel:
    """fasttext's Python predict() breaks under NumPy 2 — we call the binding."""

    def test_uses_low_level_binding_when_present(self):
        class Binding:
            def predict(self, text, k, threshold, on_unicode_error):
                return [(0.99, "__label__vie_Latn")]

        class Model:
            f = Binding()

            def predict(self, text):  # the NumPy-2-broken path
                raise ValueError("copy=False")

        assert _predict_label(Model(), "xin chào") == "__label__vie_Latn"

    def test_falls_back_to_wrapper_without_binding(self):
        class Model:
            def predict(self, text):
                return (("__label__eng_Latn",), [0.9])

        assert _predict_label(Model(), "hello") == "__label__eng_Latn"

    def test_empty_prediction(self):
        class Binding:
            def predict(self, text, k, threshold, on_unicode_error):
                return []

        class Model:
            f = Binding()

        assert _predict_label(Model(), "") == ""

VI_TEXT = "Hãy giải bài toán từng bước. Tổng cộng có ba mươi quả táo."
EN_TEXT = "Let us solve the problem step by step. There are thirty apples."
TH_TEXT = "จงแก้โจทย์ทีละขั้นตอน มีแอปเปิลสามสิบลูก"
ZH_TEXT = "我们一步一步解决这个问题。一共有三十个苹果。"


def _no_glotlid(test):
    """Force the script-only fallback path."""
    return patch("mlkv.drift._glotlid_model", return_value=None)(test)


class TestScriptProfile:
    def test_thai(self):
        profile = script_profile(TH_TEXT)
        assert profile.get("Thai", 0) > 0
        assert profile.get("Latin", 0) == 0

    def test_mixed(self):
        profile = script_profile("hello 世界")
        assert profile["Latin"] == 5
        assert profile["Han"] == 2


class TestFallbackDrift:
    @_no_glotlid
    def test_thai_response_in_thai(self, _mock=None):
        assert drift_score(TH_TEXT, LANGUAGES["th"]) == 0.0

    @_no_glotlid
    def test_thai_prompt_english_response(self, _mock=None):
        # Full drift: expected Thai, got Latin
        assert drift_score(EN_TEXT, LANGUAGES["th"]) == 1.0

    @_no_glotlid
    def test_vietnamese_real_text_low_drift(self, _mock=None):
        score = drift_score(VI_TEXT, LANGUAGES["vi"])
        assert score is not None and score < 0.1

    @_no_glotlid
    def test_vietnamese_prompt_english_response_flagged(self, _mock=None):
        # No diacritics at all → likely drifted to English
        score = drift_score(EN_TEXT, LANGUAGES["vi"])
        assert score is not None and score > 0.9

    @_no_glotlid
    def test_english_undecidable_in_fallback(self, _mock=None):
        # EN vs SW/ES indistinguishable by script alone → None, not a guess
        assert drift_score(EN_TEXT, LANGUAGES["en"]) is None

    @_no_glotlid
    def test_chinese_response_for_chinese(self, _mock=None):
        assert drift_score(ZH_TEXT, LANGUAGES["zh"]) == 0.0

    @_no_glotlid
    def test_empty(self, _mock=None):
        assert drift_score("", LANGUAGES["vi"]) is None

    @_no_glotlid
    def test_nfd_vietnamese_not_flagged_as_drift(self, _mock=None):
        # The NFD experiment arm decomposes diacritics; drift_score must
        # canonicalize before the precomposed-character heuristic runs.
        import unicodedata
        nfd_text = unicodedata.normalize("NFD", VI_TEXT)
        score = drift_score(nfd_text, LANGUAGES["vi"])
        assert score is not None and score < 0.1
