import random

import pytest
import sympy

from mlkv.tasks.mgsm_canary import (
    ChainError,
    build_canary_item,
    choose_perturbation,
    evaluate_chain,
    parse_annotations,
    substitute_number,
    verify_chain,
)

# Real GSM8K item 0 (Janet's ducks), gold 18.
JANET_Q = (
    "Janet's ducks lay 16 eggs per day. She eats three for breakfast every "
    "morning and bakes muffins for her friends every day with four. She sells "
    "the remainder at the farmers' market daily for $2 per fresh duck egg. "
    "How much in dollars does she make every day at the farmers' market?"
)
JANET_R = (
    "Janet sells 16 - 3 - 4 = <<16-3-4=9>>9 duck eggs a day.\n"
    "She makes 9 * 2 = $<<9*2=18>>18 every day at the farmer's market.\n#### 18"
)


class TestParseAnnotations:
    def test_extracts_expr_result_pairs(self):
        pairs = parse_annotations(JANET_R)
        assert pairs == [("16-3-4", 9), ("9*2", 18)]

    def test_strips_commas_in_numbers(self):
        pairs = parse_annotations("<<35,000*2=70,000>>")
        assert pairs == [("35000*2", 70000)]

    def test_no_annotations_raises(self):
        with pytest.raises(ChainError):
            parse_annotations("no annotations here #### 5")


class TestEvaluateChain:
    def test_reproduces_originals_without_substitutions(self):
        assert evaluate_chain(parse_annotations(JANET_R)) == [9, 18]

    def test_substitution_propagates_through_intermediates(self):
        # 16 -> 20 changes the first result 9 -> 13, which the second
        # expression references as "9" and must pick up as 13.
        results = evaluate_chain(
            parse_annotations(JANET_R), {sympy.Rational(16): sympy.Rational(20)}
        )
        assert results == [13, 26]

    def test_exact_rational_arithmetic(self):
        # 0.1 must be exact (sympy Rational), not float noise
        results = evaluate_chain(parse_annotations("<<35000*0.1=3500>>"))
        assert results == [3500]

    def test_ambiguous_intermediate_raises(self):
        # Both expressions originally produce 5 but get different new values
        # -> downstream references to "5" are ambiguous.
        annotations = [("4+1", 5), ("9-4", 5), ("5*10", 50)]
        annotations = [(e, sympy.Rational(r)) for e, r in annotations]
        with pytest.raises(ChainError):
            evaluate_chain(annotations, {sympy.Rational(4): sympy.Rational(6)})

    def test_malformed_expression_raises(self):
        with pytest.raises(ChainError):
            evaluate_chain([("16-", sympy.Rational(9))])


class TestVerifyChain:
    def test_valid_chain(self):
        assert verify_chain(parse_annotations(JANET_R), sympy.Rational(18))

    def test_wrong_gold_fails(self):
        assert not verify_chain(parse_annotations(JANET_R), sympy.Rational(19))

    def test_wrong_intermediate_fails(self):
        bad = [("16-3-4", sympy.Rational(8)), ("8*2", sympy.Rational(16))]
        assert not verify_chain(bad, sympy.Rational(16))


class TestChoosePerturbation:
    def test_finds_valid_perturbation(self):
        p = choose_perturbation(JANET_Q, JANET_R, 18, random.Random("t"))
        assert p is not None
        # "$2" is denylisted and three/four are words, so 16 is the only candidate
        assert p.old == 16
        assert p.new != 16 and p.new >= 1
        assert p.gold_old == 18
        # recompute independently: (new - 3 - 4) * 2
        assert p.gold_new == (p.new - 7) * 2
        assert p.gold_new != 18

    def test_deterministic_given_same_rng_seed(self):
        a = choose_perturbation(JANET_Q, JANET_R, 18, random.Random("s"))
        b = choose_perturbation(JANET_Q, JANET_R, 18, random.Random("s"))
        assert a == b

    def test_integer_constraint_respected(self):
        # 48/2 must stay integral -> only even perturbations of 48 survive
        q = "A tank holds 48 liters. Half is used. How many liters are used?"
        r = "Half of 48 is <<48/2=24>>24 liters.\n#### 24"
        for seed in range(10):
            p = choose_perturbation(q, r, 24, random.Random(seed))
            assert p is not None and p.new % 2 == 0

    def test_denylisted_values_never_perturbed(self):
        q = "Tom works 7 hours and earns 100 dollars per hour. Total?"
        r = "Total is <<7*100=700>>700 dollars.\n#### 700"
        # 7 and 100 are denylisted -> no candidates at all
        assert choose_perturbation(q, r, 700, random.Random(0)) is None

    def test_broken_chain_rejected(self):
        assert choose_perturbation(JANET_Q, "gold is #### 18", 18, random.Random(0)) is None
        wrong = JANET_R.replace("#### 18", "#### 99")
        assert choose_perturbation(JANET_Q, wrong, 99, random.Random(0)) is None

    def test_number_not_in_question_not_a_candidate(self):
        # 16 appears only in the rationale, not the question -> no candidate
        q = "Janet's ducks lay some eggs. How much does she make?"
        assert choose_perturbation(q, JANET_R, 18, random.Random(0)) is None


class TestSubstituteNumber:
    def test_plain(self):
        assert substitute_number("has 16 eggs", 16, 19) == "has 19 eggs"

    def test_all_occurrences(self):
        assert substitute_number("16 in, 16 out", 16, 19) == "19 in, 19 out"

    def test_not_inside_larger_number(self):
        assert substitute_number("has 116 eggs and 16 hens", 16, 19) == (
            "has 116 eggs and 19 hens"
        )

    def test_not_part_of_decimal(self):
        assert substitute_number("2.5 kg and 5 boxes", 5, 6) == "2.5 kg and 6 boxes"

    def test_sentence_final_number(self):
        assert substitute_number("she has 16.", 16, 19) == "she has 19."

    def test_comma_grouping_preserved(self):
        assert substitute_number("earns $35,000 a year", 35000, 42000) == (
            "earns $42,000 a year"
        )

    def test_dot_grouping_preserved(self):
        # VI/DE grouping style
        assert substitute_number("kiếm được 35.000 đô", 35000, 42000) == (
            "kiếm được 42.000 đô"
        )

    def test_missing_number_returns_none(self):
        assert substitute_number("no such number", 16, 19) is None


class TestBuildCanaryItem:
    def test_parallel_item_across_languages(self):
        p = choose_perturbation(JANET_Q, JANET_R, 18, random.Random("t"))
        vi_q = "Vịt của Janet đẻ 16 quả trứng mỗi ngày."
        item = build_canary_item(0, "vi", vi_q, p)
        assert item["item_id"] == "mgsm-canary-vi-0"
        assert str(p.new) in item["question"]
        assert "16" not in item["question"]
        assert item["gold"] == p.gold_new
        assert item["lang"] == "vi"
        assert item["prompt"].startswith(item["question"])
        assert "####" in item["prompt"]  # native instruction appended

    def test_substitution_failure_returns_none(self):
        p = choose_perturbation(JANET_Q, JANET_R, 18, random.Random("t"))
        assert build_canary_item(0, "vi", "Không có số nào ở đây.", p) is None
