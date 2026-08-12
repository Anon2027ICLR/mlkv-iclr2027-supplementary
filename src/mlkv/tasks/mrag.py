"""mRAG-QA builder (design doc §2.4): the KV-pressure task.

Question in language L + gold passage + same-language distractor passages
filling the context to a token budget {8k, 16k, 32k}; gold passage position
rotated front/middle/back by question index to expose eviction position bias.
Scored with deterministic span EM/F1 (qa_metrics).

Sources: XQuAD (en/es/de/ru/th/vi/zh) and TyDiQA-GoldP (sw/bn/te); MLQA
contexts supplement the distractor pool where available (XQuAD alone tops out
around ~35k EN tokens, less after fertility). FLORES-based passages are a
possible future supplement (design doc) — not implemented.

Determinism: distractor sampling is seeded per (lang, budget, question index);
the same question keeps its gold position across budgets so the budget effect
is within-question. Token counts use the RUN model's tokenizer, so items are
model-specific — fine, run_keys include the model.
"""

from __future__ import annotations

import logging
import random

from mlkv.languages import LANGUAGES

logger = logging.getLogger(__name__)

SEED = "mlkv-mrag-v1"
DEFAULT_N_QUESTIONS = 300
POSITIONS = ("front", "middle", "back")

XQUAD_LANGS = {"en", "es", "de", "ru", "th", "vi", "zh"}
TYDIQA_LANGS = {"sw": "swahili", "bn": "bengali", "te": "telugu"}
MLQA_LANGS = {"en", "es", "de", "vi", "zh"}


def _n_tokens(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def load_pool(lang: str) -> tuple[list[dict], list[str]]:
    """(questions, distractor passages) for a language. Network access.

    questions: {qid, question, context, answers: [str, ...]}
    distractors: unique passage texts (gold contexts included — they only
    serve as distractors for OTHER questions).
    """
    from datasets import load_dataset

    if lang in XQUAD_LANGS:
        rows = list(load_dataset("google/xquad", f"xquad.{lang}", split="validation"))
    elif lang in TYDIQA_LANGS:
        name = TYDIQA_LANGS[lang]
        ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
        rows = [r for r in ds["validation"] if r["id"].startswith(f"{name}-")]
    else:
        raise ValueError(f"no mRAG-QA source for language: {lang}")

    questions = [
        {
            "qid": row["id"],
            "question": row["question"],
            "context": row["context"],
            "answers": list(dict.fromkeys(row["answers"]["text"])),
        }
        for row in rows
    ]

    passages = {row["context"] for row in rows}
    if lang in TYDIQA_LANGS:  # validation pool is small; add train contexts
        name = TYDIQA_LANGS[lang]
        passages |= {
            r["context"] for r in ds["train"] if r["id"].startswith(f"{name}-")
        }
    if lang in MLQA_LANGS:
        # facebook/mlqa is script-based (unsupported by datasets>=3); read the
        # HF auto-converted parquet branch instead.
        mlqa = load_dataset(
            "parquet",
            data_files=f"hf://datasets/facebook/mlqa@refs/convert/parquet"
                       f"/mlqa.{lang}.{lang}/test/*.parquet",
            split="train",
        )
        passages |= {r["context"] for r in mlqa}
    return questions, sorted(passages)


def assemble(question_item: dict, distractors: list[str], tokenizer,
             ctx_tokens: int, position: str, rng: random.Random,
             lang: str, layout: str = "instr-last") -> tuple[str, dict]:
    """One prompt. layout "instr-last" (frozen Main A order): passages +
    question + instruction. layout "instr-first" (E1 intervention, see
    docs/mrag-mechanism-pivot.md): instruction + passages + question, so the
    question is always inside a press's observation window. Token accounting
    and distractor selection are layout-invariant: same seed, same passages."""
    instruction = LANGUAGES[lang].qa_instruction
    gold_passage = question_item["context"]
    joiner = "\n\n"
    used = (
        _n_tokens(tokenizer, gold_passage)
        + _n_tokens(tokenizer, question_item["question"])
        + _n_tokens(tokenizer, instruction)
        + 3 * len(joiner)
    )

    pool = [p for p in distractors if p != gold_passage]
    rng.shuffle(pool)
    chosen = []
    for passage in pool:
        cost = _n_tokens(tokenizer, passage) + len(joiner)
        if used + cost > ctx_tokens:
            continue
        chosen.append(passage)
        used += cost
    if used < 0.8 * ctx_tokens:
        logger.warning(
            "mrag[%s]: pool exhausted at ~%d/%d tokens for %s",
            lang, used, ctx_tokens, question_item["qid"],
        )

    gold_index = {"front": 0, "middle": len(chosen) // 2, "back": len(chosen)}[position]
    passages = chosen[:gold_index] + [gold_passage] + chosen[gold_index:]
    if layout == "instr-first":
        parts = [instruction, joiner.join(passages), question_item["question"]]
    else:
        parts = [joiner.join(passages), question_item["question"], instruction]
    prompt = joiner.join(parts)
    meta = {
        "position": position,
        "n_passages": len(passages),
        "approx_prompt_tokens": used,
        "qid": question_item["qid"],
    }
    return prompt, meta


def build(lang: str, tokenizer, ctx_tokens_list: list[int],
          max_items: int | None = None, n_questions: int = DEFAULT_N_QUESTIONS,
          pool: tuple[list[dict], list[str]] | None = None,
          layout: str = "instr-last") -> list[dict]:
    """Items for all budgets; `pool` injectable for tests (else loaded)."""
    questions, distractors = pool if pool is not None else load_pool(lang)
    if len(questions) < n_questions:
        logger.warning(
            "mrag[%s]: only %d questions available (wanted %d)",
            lang, len(questions), n_questions,
        )
    questions = questions[:n_questions]
    if max_items:
        questions = questions[:max_items]

    items = []
    for ctx_tokens in ctx_tokens_list:
        for i, q in enumerate(questions):
            position = POSITIONS[i % len(POSITIONS)]
            rng = random.Random(f"{SEED}:{lang}:{ctx_tokens}:{i}")
            prompt, meta = assemble(
                q, distractors, tokenizer, ctx_tokens, position, rng, lang,
                layout=layout,
            )
            meta["ctx_tokens"] = ctx_tokens
            meta["layout"] = layout
            # Distinct id prefix per layout: run_keys must never collide with
            # the frozen instr-last rows.
            prefix = "mragIF" if layout == "instr-first" else "mrag"
            items.append({
                "item_id": f"{prefix}-{lang}-{ctx_tokens // 1024}k-{i}",
                "prompt": prompt,
                "gold": q["answers"],
                "lang": lang,
                "meta": meta,
            })
    return items


def score(output: str, item: dict) -> tuple[bool, dict]:
    """Runner score_fn: correct = span EM; F1 and item meta go to `meta`."""
    from mlkv import qa_metrics

    scores = qa_metrics.span_scores(output, item["gold"], item["lang"])
    return scores["em"], {**item.get("meta", {}), **scores}
