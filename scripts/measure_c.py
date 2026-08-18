#!/usr/bin/env python3
"""Measure trailing-token count c from tokenizer + chat template.

c = tokens after the last critical content (the question, in instr-last).
AutoWindow w = c + 16. Never copy these numbers from a doc — run this.

--no-marker re-measures c with the answer-format sentence removed, which
is what a deployment that scores some other way would carry. The format
sentence is the one holding the '####' marker; it is separated at the
last sentence-ending punctuation before that marker. Thai joins the two
clauses with a conjunction and no punctuation, so it has no separable
format sentence and is reported as such rather than cut on a guess.

Usage:
  uv run python scripts/measure_c.py --models Qwen/Qwen3-4B --langs en,th,bn,te
  uv run python scripts/measure_c.py --models Qwen/Qwen3-4B --no-marker
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mlkv.languages import LANGUAGES, resolve

DELTA = 16
PROBE_Q = "What is the capital?"
PROBE_PASSAGE = "Some passage about a city."
MARKER = "####"
# Sentence enders across the eight languages' scripts. Latin/Telugu use ".",
# Chinese "。", Bengali the danda "।". Thai uses none.
SENTENCE_END = ".。।!?۔؟"


def strip_marker_sentence(instr: str) -> str | None:
    """The instruction without its answer-format sentence.

    Returns None when the format clause is not separable by punctuation --
    Thai joins it with a conjunction -- so callers report that rather than
    inventing a cut.
    """
    at = instr.find(MARKER)
    if at < 0:
        return instr.strip()
    cut = max((instr.rfind(ch, 0, at) for ch in SENTENCE_END), default=-1)
    if cut < 0:
        return None
    return instr[: cut + 1].strip()


def _n(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def _find_subseq(hay: list[int], needle: list[int]) -> int | None:
    if not needle or len(needle) > len(hay):
        return None
    last = None
    for i in range(len(hay) - len(needle) + 1):
        if hay[i : i + len(needle)] == needle:
            last = i
    return last


def measure_one(tokenizer, lang: str, instr: str | None = None) -> dict:
    instr = LANGUAGES[lang].qa_instruction if instr is None else instr
    i_tok = _n(tokenizer, instr)
    user = f"{PROBE_PASSAGE}\n\n{PROBE_Q}\n\n{instr}"
    try:
        templated = tokenizer.apply_chat_template(
            [{"role": "user", "content": user}],
            tokenize=False,
            add_generation_prompt=True,
        )
    except (TypeError, ValueError):
        templated = tokenizer.apply_chat_template(
            [{"role": "user", "content": user}],
            tokenize=False,
            add_generation_prompt=True,
        )
    ids = tokenizer.encode(templated, add_special_tokens=False)
    q_ids = tokenizer.encode(PROBE_Q, add_special_tokens=False)
    at = _find_subseq(ids, q_ids)
    if at is None:
        # Fallback: I plus the assistant-header suffix of a tiny turn.
        tiny = tokenizer.apply_chat_template(
            [{"role": "user", "content": "x"}],
            tokenize=False,
            add_generation_prompt=True,
        )
        x_ids = tokenizer.encode("x", add_special_tokens=False)
        tiny_ids = tokenizer.encode(tiny, add_special_tokens=False)
        x_at = _find_subseq(tiny_ids, x_ids)
        suffix = len(tiny_ids) - (x_at + len(x_ids)) if x_at is not None else 6
        c = i_tok + suffix
        how = "fallback_I_plus_suffix"
    else:
        c = len(ids) - (at + len(q_ids))
        how = "after_question"
        suffix = c - i_tok
    return {
        "lang": lang,
        "I": i_tok,
        "suffix": suffix,
        "c": c,
        "autowin": c + DELTA,
        "how": how,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models", required=True)
    p.add_argument("--langs", default="en,zh,es,vi,th,sw,bn,te")
    p.add_argument("--no-marker", action="store_true",
                   help="measure c with the answer-format sentence removed")
    args = p.parse_args()

    from transformers import AutoTokenizer

    print(f"{'model':<28}{'lang':<6}{'I':>5}{'suf':>5}{'c':>5}{'aw':>5}  how")
    for model in args.models.split(","):
        tok = AutoTokenizer.from_pretrained(model.strip())
        for lang in resolve(args.langs):
            instr = None
            if args.no_marker:
                instr = strip_marker_sentence(LANGUAGES[lang.code].qa_instruction)
                if instr is None:
                    print(f"{model.strip()[:27]:<28}{lang.code:<6}"
                          f"{'—':>5}{'—':>5}{'—':>5}{'—':>5}  "
                          f"no separable format sentence")
                    continue
            m = measure_one(tok, lang.code, instr=instr)
            print(
                f"{model.strip()[:27]:<28}{m['lang']:<6}"
                f"{m['I']:>5}{m['suffix']:>5}{m['c']:>5}{m['autowin']:>5}  {m['how']}"
            )


if __name__ == "__main__":
    main()
