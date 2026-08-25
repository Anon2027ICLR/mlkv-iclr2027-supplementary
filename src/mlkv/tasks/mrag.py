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

    logger.info("mrag[%s]: loading passage pool", lang)
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
    logger.info("mrag[%s]: pool ready (%d questions, %d passages)",
                lang, len(questions), len(passages))
    return questions, sorted(passages)


# Neutral filler for the padded-instruction dose-response (same-language causal
# test: does ENGLISH break once its instruction tail outgrows the observation
# window?). Content-free by design; repeated and truncated to hit a token target.
_PAD_SENTENCE = {
    "en": "Remember to read every passage carefully and check your answer "
          "against the text before responding.",
}

# Frozen English tails for the fate-changer arm. Same prepend mechanic as
# prose filler so the #### spec stays last.
_JSON_SCHEMA = (
    "Respond only as JSON matching this schema : "
    "{ answer : string , span : string , confidence : number , "
    "citations : [ { passage_id : integer , quote : string } ] } . "
    "Do not write any text outside the JSON object ."
)
_TOOL_BLOCK = (
    "Available tools : search_passages ( query : string , k : integer ) "
    "returns a list of id and text ; submit_answer ( span : string , "
    "passage_id : integer ) returns none . Call a tool by emitting "
    "{ name : string , arguments : object } before the final answer ."
)
TAIL_FILLERS = {
    "prose": _PAD_SENTENCE["en"],
    "json": _JSON_SCHEMA,
    "tools": _TOOL_BLOCK,
}
TAIL_PREFIX = {"prose": "mragPAD", "json": "mragJSON", "tools": "mragTOOL"}

# The "refine" layout (docs/iclr-refine-preregister.md, reviewer-5 W2):
# LlamaIndex's shipped DEFAULT_REFINE_PROMPT_TMPL, verbatim from the frozen
# survey record (docs/template-survey-report.md, T06, commit-pinned source).
# The query stands FIRST and the passages fill the {context_msg} slot, so at
# any small observation window the scorer sees none of the question (V=0 for
# every language by construction). The existing-answer slot takes a fixed
# neutral stub, identical across items and languages, carrying no
# information about the gold answer; it is pinned by the unit test.
REFINE_PREFIX = "The original query is as follows: "
REFINE_MID_1 = "\nWe have provided an existing answer: "
REFINE_MID_2 = ("\nWe have the opportunity to refine the existing answer "
                "(only if needed) with some more context below.\n"
                "------------\n")
REFINE_SUFFIX = ("\n------------\n"
                 "Given the new context, refine the original answer to "
                 "better answer the query. If the context isn't useful, "
                 "return the original answer.\nRefined Answer: ")
REFINE_EXISTING_ANSWER = ("I do not yet have enough information to answer "
                          "this question.")


def _pad_instruction(instruction: str, lang: str, tokenizer,
                     target_tokens: int, tail: str = "prose") -> str:
    """Extend the instruction with filler until it reaches target_tokens.
    The original instruction stays last-most so the #### spec is adjacent
    to generation."""
    if tail not in TAIL_FILLERS:
        raise ValueError(f"unknown mrag tail: {tail}")
    filler_unit = _PAD_SENTENCE[lang] if tail == "prose" else TAIL_FILLERS[tail]
    padded = instruction
    while len(tokenizer.encode(padded, add_special_tokens=False)) < target_tokens:
        padded = filler_unit + " " + padded
    return padded


def assemble(question_item: dict, distractors: list[str], tokenizer,
             ctx_tokens: int, position: str, rng: random.Random,
             lang: str, layout: str = "instr-last",
             instr_pad_tokens: int | None = None,
             tail: str = "prose",
             instr_lang: str | None = None) -> tuple[str, dict]:
    """One prompt. layout "instr-last" (frozen Main A order): passages +
    question + instruction. layout "instr-first" (E1 intervention, see
    docs/mrag-mechanism-pivot.md): instruction + passages + question, so the
    question is always inside a press's observation window. Token accounting
    and distractor selection are layout-invariant: same seed, same passages.
    instr_lang (xinstr arm, docs/iclr-xinstr-preregister.md): use another
    language's frozen instruction with this language's items, so c is set by
    the instruction language while the questions stay in `lang`."""
    if instr_lang and instr_pad_tokens:
        raise ValueError("instr_lang cannot be combined with instr_pad_tokens")
    if instr_lang and layout != "instr-last":
        raise ValueError("instr_lang is only defined for the instr-last layout")
    if layout == "refine" and (instr_lang or instr_pad_tokens):
        raise ValueError("the refine layout takes no instruction options")
    instruction = LANGUAGES[instr_lang or lang].qa_instruction
    if layout == "refine":
        # The T06 template replaces the frozen instruction entirely; the
        # fixed overhead is the template text plus the existing-answer stub.
        instruction = (REFINE_PREFIX + REFINE_MID_1 + REFINE_EXISTING_ANSWER
                       + REFINE_MID_2 + REFINE_SUFFIX)
    if instr_pad_tokens:
        instruction = _pad_instruction(
            instruction, lang, tokenizer, instr_pad_tokens, tail=tail,
        )
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
    if layout == "refine":
        prompt = (REFINE_PREFIX + question_item["question"]
                  + REFINE_MID_1 + REFINE_EXISTING_ANSWER + REFINE_MID_2
                  + joiner.join(passages) + REFINE_SUFFIX)
    elif layout == "instr-first":
        parts = [instruction, joiner.join(passages), question_item["question"]]
        prompt = joiner.join(parts)
    else:
        parts = [joiner.join(passages), question_item["question"], instruction]
        prompt = joiner.join(parts)
    meta = {
        "position": position,
        "n_passages": len(passages),
        "approx_prompt_tokens": used,
        "qid": question_item["qid"],
        # |Q_i| on the run tokenizer: the per-item input the ":wq" oracle
        # window consumes (docs/iclr-oracle-preregister.md). Recorded for
        # every layout; costs one encode.
        "q_tokens": _n_tokens(tokenizer, question_item["question"]),
    }
    return prompt, meta


def build(lang: str, tokenizer, ctx_tokens_list: list[int],
          max_items: int | None = None, n_questions: int = DEFAULT_N_QUESTIONS,
          pool: tuple[list[dict], list[str]] | None = None,
          layout: str = "instr-last",
          instr_pad_tokens: int | None = None,
          tail: str = "prose",
          instr_lang: str | None = None) -> list[dict]:
    """Items for all budgets; `pool` injectable for tests (else loaded)."""
    questions, distractors = pool if pool is not None else load_pool(lang)
    # max_items, when given, governs outright: the n_questions default is a
    # working-set cap, not a ceiling on explicit requests. (The depth arm
    # asked for the full 669-item Telugu pool and the old order of slices --
    # [:n_questions] before [:max_items] -- silently cut it to 300.) Item
    # construction is keyed on the item index alone, so extending the slice
    # never changes the items before the old boundary; the regression test
    # pins that invariant, which is what makes mid-store resumes safe.
    limit = max_items if max_items else n_questions
    if len(questions) < limit:
        logger.warning(
            "mrag[%s]: only %d questions available (wanted %d)",
            lang, len(questions), limit,
        )
    questions = questions[:limit]

    logger.info("mrag[%s]: building %d questions × %s tokens "
                "(layout=%s pad=%s tail=%s instr_lang=%s)",
                lang, len(questions), ctx_tokens_list, layout,
                instr_pad_tokens, tail, instr_lang)
    items = []
    for ctx_tokens in ctx_tokens_list:
        for i, q in enumerate(questions):
            position = POSITIONS[i % len(POSITIONS)]
            rng = random.Random(f"{SEED}:{lang}:{ctx_tokens}:{i}")
            prompt, meta = assemble(
                q, distractors, tokenizer, ctx_tokens, position, rng, lang,
                layout=layout, instr_pad_tokens=instr_pad_tokens, tail=tail,
                instr_lang=instr_lang,
            )
            meta["ctx_tokens"] = ctx_tokens
            meta["layout"] = layout
            if instr_pad_tokens:
                meta["instr_pad_tokens"] = instr_pad_tokens
                meta["tail"] = tail
            if instr_lang:
                meta["instr_lang"] = instr_lang
            # Distinct id prefix per layout/padding/instruction-language:
            # run_keys must never collide with the frozen rows.
            prefix = {"instr-first": "mragIF", "refine": "mragRF"}.get(
                layout, "mrag")
            if instr_pad_tokens:
                prefix = f"{TAIL_PREFIX[tail]}{instr_pad_tokens}"
            if instr_lang:
                prefix = f"mragX{instr_lang}"
            items.append({
                "item_id": f"{prefix}-{lang}-{ctx_tokens // 1024}k-{i}",
                "prompt": prompt,
                "gold": q["answers"],
                "lang": lang,
                "meta": meta,
            })
    logger.info("mrag[%s]: built %d items", lang, len(items))
    return items


def score(output: str, item: dict) -> tuple[bool, dict]:
    """Runner score_fn: correct = span EM; F1 and item meta go to `meta`."""
    from mlkv import qa_metrics

    scores = qa_metrics.span_scores(output, item["gold"], item["lang"])
    return scores["em"], {**item.get("meta", {}), **scores}
