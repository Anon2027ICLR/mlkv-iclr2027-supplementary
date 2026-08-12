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


class TestLayoutIntervention:
    """E1 (docs/mrag-mechanism-pivot.md): instr-first puts the question last so
    it is always inside a press's observation window."""

    def test_instr_first_reorders_but_keeps_passages(self):
        from mlkv.languages import LANGUAGES
        tok = FakeTokenizer()
        questions, distractors = make_pool(n_questions=1)
        q = questions[0]
        last, m1 = mrag.assemble(q, distractors, tok, 512, "middle",
                                 random.Random("s"), "en", layout="instr-last")
        first, m2 = mrag.assemble(q, distractors, tok, 512, "middle",
                                  random.Random("s"), "en", layout="instr-first")
        instr = LANGUAGES["en"].qa_instruction
        assert last.endswith(instr) and not first.endswith(instr)
        assert first.startswith(instr)
        assert first.endswith(q["question"])
        # same seed -> identical passage selection, layout-invariant
        assert m1["n_passages"] == m2["n_passages"]
        assert sorted(last.split("\n\n")) == sorted(first.split("\n\n"))

    def test_instr_first_item_ids_cannot_collide(self):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=2)
        a = mrag.build("en", tok, [512], pool=pool)
        b = mrag.build("en", tok, [512], pool=pool, layout="instr-first")
        assert a[0]["item_id"].startswith("mrag-en-")
        assert b[0]["item_id"].startswith("mragIF-en-")
        assert b[0]["meta"]["layout"] == "instr-first"
        assert a[0]["meta"]["layout"] == "instr-last"


class TestInstructionPadding:
    """Padded-instruction dose-response (same-language window causal test)."""

    def test_padding_reaches_target_and_keeps_marker_spec_last(self):
        from mlkv.languages import LANGUAGES
        tok = FakeTokenizer()
        pool = make_pool(n_questions=2)
        items = mrag.build("en", tok, [512], pool=pool, instr_pad_tokens=64)
        instr = LANGUAGES["en"].qa_instruction
        for it in items:
            assert it["prompt"].endswith(instr)  # original spec stays last
            tail = it["prompt"][it["prompt"].index("Remember to read"):]
            assert len(tok.encode(tail)) >= 64
            assert it["item_id"].startswith("mragPAD64-en-")
            assert it["meta"]["instr_pad_tokens"] == 64

    def test_unpadded_items_unchanged(self):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=2)
        a = mrag.build("en", tok, [512], pool=pool)
        b = mrag.build("en", tok, [512], pool=pool, instr_pad_tokens=None)
        assert [x["prompt"] for x in a] == [x["prompt"] for x in b]
        assert a[0]["item_id"].startswith("mrag-en-")
