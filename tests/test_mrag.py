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

    def test_max_items_governs_over_n_questions(self):
        # The depth arm asked for the full pool and the old slice order --
        # [:n_questions] before [:max_items] -- silently cut it to the
        # n_questions default. max_items, when given, governs outright.
        items = mrag.build("en", self.tokenizer, [1024], pool=self.pool,
                           n_questions=3, max_items=7)
        assert len(items) == 7

    def test_extending_max_items_never_changes_earlier_items(self):
        # Item construction is keyed on the item index alone, so a larger
        # max_items must reproduce the earlier items byte-for-byte. This is
        # the invariant that makes resuming a partially built store safe.
        short = mrag.build("en", self.tokenizer, [1024], pool=self.pool,
                           max_items=5)
        full = mrag.build("en", self.tokenizer, [1024], pool=self.pool,
                          max_items=9)
        for a, b in zip(short, full):
            assert a["item_id"] == b["item_id"]
            assert a["prompt"] == b["prompt"]
            assert a["meta"]["position"] == b["meta"]["position"]

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


class TestCrossLanguageInstruction:
    """xinstr arm (docs/iclr-xinstr-preregister.md): English instruction with
    non-English items, so c is set by the instruction language while the
    questions stay in the item language."""

    def test_english_instruction_on_bengali_items(self):
        from mlkv.languages import LANGUAGES
        tok = FakeTokenizer()
        pool = make_pool(n_questions=2)
        items = mrag.build("bn", tok, [512], pool=pool, instr_lang="en")
        en_instr = LANGUAGES["en"].qa_instruction
        bn_instr = LANGUAGES["bn"].qa_instruction
        for it in items:
            assert it["prompt"].endswith(en_instr)
            assert bn_instr not in it["prompt"]
            assert it["lang"] == "bn"
            assert it["meta"]["instr_lang"] == "en"
            assert it["item_id"].startswith("mragXen-bn-")

    def test_ids_cannot_collide_and_passages_invariant(self):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=2)
        a = mrag.build("bn", tok, [512], pool=pool)
        b = mrag.build("bn", tok, [512], pool=pool, instr_lang="en")
        assert a[0]["item_id"].startswith("mrag-bn-")
        assert b[0]["item_id"].startswith("mragXen-bn-")
        # same seed -> same distractor selection; only the last block
        # (the instruction) differs
        for x, y in zip(a, b):
            assert x["prompt"].split("\n\n")[:-1] == y["prompt"].split("\n\n")[:-1]
            assert x["prompt"].split("\n\n")[-1] != y["prompt"].split("\n\n")[-1]
            assert x["meta"]["n_passages"] == y["meta"]["n_passages"]

    def test_same_language_instr_lang_is_identity_prompt(self):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=2)
        a = mrag.build("en", tok, [512], pool=pool)
        b = mrag.build("en", tok, [512], pool=pool, instr_lang="en")
        assert [x["prompt"] for x in a] == [x["prompt"] for x in b]
        assert b[0]["item_id"].startswith("mragXen-en-")

    def test_rejects_padding_and_instr_first(self):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=1)
        with pytest.raises(ValueError):
            mrag.build("bn", tok, [512], pool=pool, instr_lang="en",
                       instr_pad_tokens=64)
        with pytest.raises(ValueError):
            mrag.build("bn", tok, [512], pool=pool, instr_lang="en",
                       layout="instr-first")


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

    def test_json_tail_namespaces_and_keeps_spec_last(self):
        from mlkv.languages import LANGUAGES
        tok = FakeTokenizer()
        pool = make_pool(n_questions=1)
        items = mrag.build(
            "en", tok, [512], pool=pool, instr_pad_tokens=80, tail="json",
        )
        instr = LANGUAGES["en"].qa_instruction
        it = items[0]
        assert it["item_id"].startswith("mragJSON80-en-")
        assert it["meta"]["tail"] == "json"
        assert it["prompt"].endswith(instr)
        assert "Respond only as JSON" in it["prompt"]
        tail = it["prompt"][it["prompt"].index("Respond only as JSON"):]
        assert len(tok.encode(tail)) >= 80

    def test_tools_tail_does_not_collide_with_prose_ids(self):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=1)
        prose = mrag.build("en", tok, [512], pool=pool, instr_pad_tokens=60)
        tools = mrag.build(
            "en", tok, [512], pool=pool, instr_pad_tokens=60, tail="tools",
        )
        assert prose[0]["item_id"].startswith("mragPAD60-")
        assert tools[0]["item_id"].startswith("mragTOOL60-")
        assert prose[0]["item_id"] != tools[0]["item_id"]
        assert "Available tools" in tools[0]["prompt"]


class TestRefineLayout:
    """The T06 shipped-template layout (docs/iclr-refine-preregister.md)."""

    def _build(self, lang="en", n=2):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=n)
        return mrag.build(lang, tok, [512], pool=pool, layout="refine"), pool

    def test_question_first_template_verbatim(self):
        items, pool = self._build()
        questions, _ = pool
        for it, q in zip(items, questions):
            p = it["prompt"]
            # The query opens the prompt; the scorer's window at any small w
            # therefore holds none of it (V=0 by construction).
            assert p.startswith(mrag.REFINE_PREFIX + q["question"])
            # The T06 text is verbatim (348-char trailing block of the
            # frozen survey record, split around the two placeholders).
            assert mrag.REFINE_MID_1 + mrag.REFINE_EXISTING_ANSWER in p
            assert p.endswith(mrag.REFINE_SUFFIX)
            assert it["item_id"].startswith("mragRF-en-")
            assert it["meta"]["layout"] == "refine"

    def test_existing_answer_stub_pinned_and_gold_free(self):
        # The stub is the exact registered sentence and cannot leak gold.
        assert mrag.REFINE_EXISTING_ANSWER == (
            "I do not yet have enough information to answer this question.")
        items, pool = self._build()
        for it in items:
            for gold in it["gold"]:
                assert gold not in mrag.REFINE_EXISTING_ANSWER

    def test_passages_between_separators(self):
        items, _ = self._build()
        for it in items:
            body = it["prompt"].split("------------\n")[1]
            assert it["meta"]["n_passages"] >= 1
            assert body.count("\n\n") == it["meta"]["n_passages"] - 1

    def test_same_items_larger_overhead_never_more_passages(self):
        # Same seed and pool as instr-last; the T06 template is longer than
        # the English instruction, so the refine prompt may fit fewer
        # passages but never more, and the qid pairing is unchanged.
        tok = FakeTokenizer()
        pool = make_pool(n_questions=2)
        a = mrag.build("en", tok, [512], pool=pool)
        b = mrag.build("en", tok, [512], pool=pool, layout="refine")
        for x, y in zip(a, b):
            assert y["meta"]["n_passages"] <= x["meta"]["n_passages"]
            assert y["meta"]["qid"] == x["meta"]["qid"]
            assert x["item_id"] != y["item_id"]

    def test_rejects_instruction_options(self):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=1)
        with pytest.raises(ValueError):
            mrag.build("en", tok, [512], pool=pool, layout="refine",
                       instr_lang="en")
        with pytest.raises(ValueError):
            mrag.build("en", tok, [512], pool=pool, layout="refine",
                       instr_pad_tokens=64)


class TestQTokensMeta:
    def test_every_layout_records_q_tokens(self):
        tok = FakeTokenizer()
        pool = make_pool(n_questions=2)
        questions, _ = pool
        for layout in ("instr-last", "instr-first", "refine"):
            items = mrag.build("en", tok, [512], pool=pool, layout=layout)
            for it, q in zip(items, questions):
                assert it["meta"]["q_tokens"] == len(q["question"].split())
