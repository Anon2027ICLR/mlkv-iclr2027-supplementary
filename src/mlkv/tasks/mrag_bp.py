"""Byte-parallel mRAG items from XQuAD (E3 — docs/mrag-mechanism-pivot.md §4).

The original mRAG builder fills every prompt to the same TOKEN length, which
algebraically cancels the content-per-token-budget mechanism it was meant to
test (pivot doc §1b). This builder inverts the construction: prompts carry
IDENTICAL content across languages — the same XQuAD questions and the same
passages via XQuAD's row-aligned translations — selected against a fixed
budget of ENGLISH bytes (the canonical, tokenizer-free axis). Token length
then varies with each language's fertility, so a fixed token budget delivers
unequal content (the treatment) while a byte budget delivers equal content
(the remedy).

Two deliberate departures from tasks/mrag.py:
- Layout is instruction-first (question last), so any press's observation
  window always contains the question — the window mechanism (pivot doc §1c)
  is excluded by construction rather than argued away.
- Selection is planned once on the English table and realized per language,
  so items are content-identical across languages AND across models (byte
  counting needs no tokenizer).

Item ids are ``mragbp-<lang>-<KiB>kB-<i>``; run_keys cannot collide with the
frozen mrag/mragIF rows.
"""

from __future__ import annotations

import logging
import random

from mlkv.languages import LANGUAGES

logger = logging.getLogger(__name__)

SEED = "mlkv-mrag-bp-v1"
BP_LANGS = ["en", "zh", "vi", "es", "de", "ru", "th", "hi", "el"]
POSITIONS = ["front", "middle", "back"]
DEFAULT_N_QUESTIONS = 100
# Reserved (canonical English bytes) for instruction + question + joiners; the
# per-language instruction is not part of the parallel content.
_OVERHEAD_BYTES = 400


def load_parallel(langs: list[str]) -> dict[str, list[dict]]:
    """Row-aligned XQuAD tables per language. Network access."""
    from datasets import load_dataset

    tables = {}
    for lang in langs:
        ds = load_dataset("google/xquad", f"xquad.{lang}", split="validation")
        tables[lang] = [
            {
                "qid": row["id"],
                "question": row["question"],
                "context": row["context"],
                "answers": list(dict.fromkeys(row["answers"]["text"])),
            }
            for row in ds
        ]
    ref = [r["qid"] for r in tables[langs[0]]]
    for lang in langs[1:]:
        if [r["qid"] for r in tables[lang]] != ref:
            raise ValueError(f"xquad.{lang} rows are not aligned with xquad.{langs[0]}")
    return tables


def _unique_contexts(rows: list[dict]) -> tuple[list[int], dict[str, int]]:
    """First-occurrence ROW index of each distinct context, plus context->slot."""
    first_rows, slot_of = [], {}
    for ri, row in enumerate(rows):
        if row["context"] not in slot_of:
            slot_of[row["context"]] = len(first_rows)
            first_rows.append(ri)
    return first_rows, slot_of


def plan(en_rows: list[dict], byte_budget: int,
         n_questions: int = DEFAULT_N_QUESTIONS) -> list[dict]:
    """Question + distractor selection, computed on English bytes only.

    Deterministic (seeded); realized identically in every language, so the
    plan IS the item identity."""
    first_rows, slot_of = _unique_contexts(en_rows)
    rng_q = random.Random(f"{SEED}:questions")
    q_indices = sorted(rng_q.sample(range(len(en_rows)), min(n_questions, len(en_rows))))

    plans = []
    for k, qi in enumerate(q_indices):
        gold_slot = slot_of[en_rows[qi]["context"]]
        pool = [s for s in range(len(first_rows)) if s != gold_slot]
        random.Random(f"{SEED}:{k}").shuffle(pool)
        budget = (
            byte_budget
            - len(en_rows[qi]["context"].encode("utf-8"))
            - len(en_rows[qi]["question"].encode("utf-8"))
            - _OVERHEAD_BYTES
        )
        chosen, used = [], 0
        for s in pool:
            b = len(en_rows[first_rows[s]]["context"].encode("utf-8")) + 2
            if used + b > budget:
                continue
            chosen.append(s)
            used += b
        plans.append({
            "k": k, "qi": qi, "gold_slot": gold_slot,
            "distractor_slots": chosen, "en_bytes_used": used,
            "position": POSITIONS[k % len(POSITIONS)],
        })
    return plans


def build(lang: str, byte_budget: int, max_items: int | None = None,
          n_questions: int = DEFAULT_N_QUESTIONS,
          tables: dict[str, list[dict]] | None = None) -> list[dict]:
    """Items for one language. `tables` injectable for tests (else loaded)."""
    if tables is None:
        tables = load_parallel(["en"] if lang == "en" else ["en", lang])
    en_rows, rows = tables["en"], tables[lang]
    first_rows, _ = _unique_contexts(en_rows)
    plans = plan(en_rows, byte_budget, n_questions)
    if max_items:
        plans = plans[:max_items]

    instruction = LANGUAGES[lang].qa_instruction
    joiner = "\n\n"
    items = []
    for p in plans:
        gold = rows[p["qi"]]["context"]
        distractors = [rows[first_rows[s]]["context"] for s in p["distractor_slots"]]
        gi = {"front": 0, "middle": len(distractors) // 2,
              "back": len(distractors)}[p["position"]]
        passages = distractors[:gi] + [gold] + distractors[gi:]
        # Instruction-first: the question is the last text before generation.
        prompt = joiner.join([instruction, joiner.join(passages),
                              rows[p["qi"]]["question"]])
        items.append({
            "item_id": f"mragbp-{lang}-{byte_budget // 1024}kB-{p['k']}",
            "prompt": prompt,
            "gold": rows[p["qi"]]["answers"],
            "lang": lang,
            "meta": {
                "qid": rows[p["qi"]]["qid"],
                "position": p["position"],
                "n_passages": len(passages),
                "en_bytes_used": p["en_bytes_used"],
                "byte_budget": byte_budget,
                "layout": "instr-first",
            },
        })
    return items
