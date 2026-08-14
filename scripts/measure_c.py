#!/usr/bin/env python3
"""Measure trailing-token count c from tokenizer + chat template.

c = tokens after the last critical content (the question, in instr-last).
AutoWindow w = c + 16. Never copy these numbers from a doc — run this.

Usage:
  uv run python scripts/measure_c.py --models Qwen/Qwen3-4B --langs en,th,bn,te
  UV_NO_SYNC=1 uv run python scripts/measure_c.py --models google/gemma-3-4b-it
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


def measure_one(tokenizer, lang: str) -> dict:
    instr = LANGUAGES[lang].qa_instruction
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
    args = p.parse_args()

    from transformers import AutoTokenizer

    print(f"{'model':<28}{'lang':<6}{'I':>5}{'suf':>5}{'c':>5}{'aw':>5}  how")
    for model in args.models.split(","):
        tok = AutoTokenizer.from_pretrained(model.strip())
        for lang in resolve(args.langs):
            m = measure_one(tok, lang.code)
            print(
                f"{model.strip()[:27]:<28}{m['lang']:<6}"
                f"{m['I']:>5}{m['suffix']:>5}{m['c']:>5}{m['autowin']:>5}  {m['how']}"
            )


if __name__ == "__main__":
    main()
