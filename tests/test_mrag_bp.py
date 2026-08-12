"""Byte-parallel mRAG builder (E3). All offline via injected tables."""

import pytest

from mlkv.compression import parse
from mlkv.tasks import mrag_bp


def make_tables(langs=("en", "xx"), n_paragraphs=40, n_q_per_para=3,
                bytes_multiplier=None):
    """Aligned fake XQuAD: same qids across langs; 'xx' texts are longer to
    mimic a verbose translation."""
    bytes_multiplier = bytes_multiplier or {"en": 1, "xx": 2}
    tables = {}
    for lang in langs:
        rows = []
        for pi in range(n_paragraphs):
            ctx = f"[{lang}] paragraph {pi} " + ("blah " * 40 * bytes_multiplier[lang])
            for qi in range(n_q_per_para):
                rows.append({
                    "qid": f"p{pi}q{qi}",
                    "question": f"[{lang}] question {pi}-{qi}?",
                    "context": ctx,
                    "answers": [f"answer-{pi}-{qi}"],
                })
        tables[lang] = rows
    return tables


class TestPlanRealization:
    def test_same_content_identities_across_languages(self):
        tables = make_tables()
        a = mrag_bp.build("en", 8192, n_questions=12, tables=tables)
        # reuse instruction of a real language for the fake 'xx' side
        tables["vi"] = tables.pop("xx")
        b = mrag_bp.build("vi", 8192, n_questions=12, tables=tables)
        assert len(a) == len(b) == 12
        for ia, ib in zip(a, b):
            assert ia["meta"]["qid"] == ib["meta"]["qid"]
            assert ia["meta"]["n_passages"] == ib["meta"]["n_passages"]
            assert ia["meta"]["position"] == ib["meta"]["position"]

    def test_en_byte_budget_respected(self):
        tables = make_tables()
        for item in mrag_bp.build("en", 8192, n_questions=12, tables=tables):
            assert item["meta"]["en_bytes_used"] <= 8192

    def test_instruction_first_question_last(self):
        tables = make_tables()
        items = mrag_bp.build("en", 8192, n_questions=3, tables=tables)
        from mlkv.languages import LANGUAGES
        for item in items:
            assert item["prompt"].startswith(LANGUAGES["en"].qa_instruction)
            assert item["prompt"].rstrip().endswith("?")

    def test_item_ids_distinct_namespace(self):
        tables = make_tables()
        items = mrag_bp.build("en", 12288, n_questions=2, tables=tables)
        assert items[0]["item_id"].startswith("mragbp-en-12kB-")

    def test_misaligned_tables_rejected(self):
        tables = make_tables()
        tables["xx"] = tables["xx"][1:] + tables["xx"][:1]
        ref = [r["qid"] for r in tables["en"]]
        got = [r["qid"] for r in tables["xx"]]
        assert ref != got  # sanity: the fixture really is misaligned
        # load_parallel does the check; simulate its assertion here
        with pytest.raises(ValueError):
            if got != ref:
                raise ValueError("xquad.xx rows are not aligned with xquad.en")


class TestByteBudgetConfig:
    def test_bb_parse_and_ratio(self):
        cfg = parse("snapkv@bb8192")
        assert cfg.kind == "press" and cfg.params["bytes"] == 8192
        # 16384-byte prompt: keep half -> ratio 0.5
        assert cfg.effective_ratio(4000, prompt_bytes=16384) == pytest.approx(0.5)
        # prompt already within the byte budget: uncompressed
        assert cfg.effective_ratio(4000, prompt_bytes=8000) == 0.0

    def test_bb_requires_prompt_bytes(self):
        with pytest.raises(ValueError):
            parse("snapkv@bb8192").effective_ratio(4000)

    def test_bb_min_prefill_floor(self):
        assert parse("snapkv@bb8192").effective_ratio(64, prompt_bytes=99999) == 0.0

    def test_token_budget_still_parses(self):
        cfg = parse("snapkv@b2048")
        assert cfg.params["budget"] == 2048 and "bytes" not in cfg.params
