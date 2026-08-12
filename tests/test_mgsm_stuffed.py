"""mgsm-stuffed: window-mechanism generality task (offline via injected data)."""

from mlkv.tasks import mgsm_stuffed


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return text.split()


def make_inputs():
    problems = [
        {"item_id": f"mgsm-en-{i}", "question": f"PROBLEM_{i} two plus two ?",
         "prompt": "x", "gold": 4.0, "lang": "en"}
        for i in range(4)
    ]
    passages = [f"PASSAGE_{k} " + "filler " * 40 for k in range(50)]
    return problems, passages


def test_problem_sits_between_passages_and_instruction():
    problems, passages = make_inputs()
    tok = FakeTokenizer()
    items = mgsm_stuffed.build("en", tok, [256], problems=problems, passages=passages)
    from mlkv.languages import LANGUAGES
    p = items[0]["prompt"]
    assert p.endswith(LANGUAGES["en"].instruction)
    q_pos = p.index("PROBLEM_0")
    assert q_pos > p.index("PASSAGE_")           # passages come first
    assert q_pos < p.index(LANGUAGES["en"].instruction)  # instruction last


def test_budget_respected_and_gold_numeric():
    problems, passages = make_inputs()
    tok = FakeTokenizer()
    items = mgsm_stuffed.build("en", tok, [256], problems=problems, passages=passages)
    for it in items:
        assert it["meta"]["approx_prompt_tokens"] <= 256
        assert isinstance(it["gold"], float)
        assert it["item_id"].startswith("mgsmst-en-0k-")


def test_deterministic_across_calls():
    problems, passages = make_inputs()
    tok = FakeTokenizer()
    a = mgsm_stuffed.build("en", tok, [256], problems=problems, passages=passages)
    b = mgsm_stuffed.build("en", tok, [256], problems=problems, passages=passages)
    assert [x["prompt"] for x in a] == [x["prompt"] for x in b]
