import random

import pytest

from mlkv.tasks import mrag


class FakeTokenizer:
    """Token count == whitespace word count (deterministic, offline)."""

    def encode(self, text, add_special_tokens=False):
        return text.split()


def make_pool(n_questions=9, n_distractors=200, words_per_passage=50):
    questions = [
        {
            "qid": f"q{i}",
            "question": f"question number {i} ?",
            "context": f"GOLD_{i} " + " ".join(
                f"gw{i}_{j}" for j in range(words_per_passage - 1)
            ),
            "answers": [f"GOLD_{i}"],
        }
        for i in range(n_questions)
    ]
    distractors = [
        f"DIST_{k} " + " ".join(f"dw{k}_{j}" for j in range(words_per_passage - 1))
        for k in range(n_distractors)
    ]
    return questions, distractors


class TestAssemble:
    def setup_method(self):
        self.tokenizer = FakeTokenizer()
        self.questions, self.distractors = make_pool()

    def _assemble(self, position, ctx=1000, i=0):
        return mrag.assemble(
            self.questions[i], self.distractors, self.tokenizer,
            ctx, position, random.Random("t"), "en",
        )

    def test_budget_respected(self):
        prompt, meta = self._assemble("front", ctx=1000)
        assert len(prompt.split()) <= 1000
        # and reasonably full: pool is large enough to get close to budget
        assert meta["approx_prompt_tokens"] > 800

    def test_gold_passage_present_exactly_once(self):
        prompt, _ = self._assemble("middle")
        assert prompt.count("GOLD_0 ") == 1

    def test_gold_position_front(self):
        prompt, _ = self._assemble("front")
        assert prompt.split()[0] == "GOLD_0"

    def test_gold_position_back(self):
        prompt, _ = self._assemble("back")
        # gold is the LAST passage, right before question + instruction
        passages = prompt.split("\n\n")
        assert passages[-3].startswith("GOLD_0")

    def test_gold_position_middle(self):
        prompt, meta = self._assemble("middle")
        words = prompt.split()
        idx = words.index("GOLD_0")
        assert 0.3 < idx / len(words) < 0.7

    def test_question_and_instruction_at_end(self):
        prompt, _ = self._assemble("front")
        blocks = prompt.split("\n\n")
        assert blocks[-2] == "question number 0 ?"
        assert blocks[-1].startswith("Answer the question")

    def test_deterministic(self):
        a, _ = self._assemble("front")
        b, _ = self._assemble("front")
        assert a == b

    def test_small_pool_warns_but_builds(self, caplog):
        questions, _ = make_pool()
        prompt, meta = mrag.assemble(
            questions[0], [], self.tokenizer, 8192, "front",
            random.Random("t"), "en",
        )
        assert "GOLD_0" in prompt
        assert meta["n_passages"] == 1
        assert any("pool exhausted" in r.message for r in caplog.records)


class TestBuild:
    def setup_method(self):
        self.tokenizer = FakeTokenizer()
        self.pool = make_pool(n_questions=9)

    def test_items_per_budget_and_ids(self):
        items = mrag.build("en", self.tokenizer, [1024, 2048], pool=self.pool)
        assert len(items) == 18
        assert items[0]["item_id"] == "mrag-en-1k-0"
        assert items[9]["item_id"] == "mrag-en-2k-0"

    def test_position_rotation_by_question_index(self):
        items = mrag.build("en", self.tokenizer, [1024], pool=self.pool)
        positions = [it["meta"]["position"] for it in items]
        assert positions == ["front", "middle", "back"] * 3

    def test_same_question_same_position_across_budgets(self):
        items = mrag.build("en", self.tokenizer, [1024, 2048], pool=self.pool)
        by_budget = {1024: items[:9], 2048: items[9:]}
        for a, b in zip(by_budget[1024], by_budget[2048]):
            assert a["meta"]["position"] == b["meta"]["position"]
            assert a["meta"]["qid"] == b["meta"]["qid"]

    def test_gold_answers_carried(self):
        items = mrag.build("en", self.tokenizer, [1024], pool=self.pool)
        assert items[0]["gold"] == ["GOLD_0"]

    def test_max_items_truncates_questions(self):
        items = mrag.build("en", self.tokenizer, [1024, 2048], pool=self.pool,
                           max_items=2)
        assert len(items) == 4

    def test_unsupported_language_raises(self):
        with pytest.raises(ValueError):
            mrag.load_pool("ja")


class TestScore:
    def _item(self):
        return {"gold": ["308"], "lang": "en", "meta": {"position": "front"}}

    def test_em_and_f1(self):
        correct, meta = mrag.score("blah blah\n#### 308", self._item())
        assert correct is True
        assert meta["f1"] == pytest.approx(1.0)
        assert meta["position"] == "front"  # item meta carried into store meta

    def test_wrong_answer(self):
        correct, meta = mrag.score("#### 309", self._item())
        assert correct is False
        assert meta["f1"] == 0.0
