#!/usr/bin/env python3
"""Measure trailing-token count c for a PADDED instruction (schema-fix arm).

The S arm failure was a construction miss: AutoWindow used unpadded English
c+16=41 while the JSON tail pushed the true c far past 64. This script
computes the schema-adjusted c by building the padded instruction with the
SAME `_pad_instruction` the mRAG builder uses (single source of truth), then
c_schema = I_padded + s where s is the assistant-header suffix of a tiny
chat turn (same fallback rule that locked the Qwen c table on 2026-08-14).

hat_w = c_schema + Q90(lang), with Q90 read from a q_percentiles.json
produced by measure_q.py on the SAME model. Never copy these numbers from a
doc — run this on-pod before generate.

Usage:
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models Qwen/Qwen3-4B --langs en
  UV_NO_SYNC=1 uv run python scripts/measure_c_schema.py --models Qwen/Qwen3-4B \
      --pads 60,120,200
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mlkv.languages import LANGUAGES
from mlkv.tasks.mrag import _pad_instruction


def _n(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def suffix_tokens(tokenizer) -> int:
    """Assistant-header suffix of a tiny turn (measure_c.py fallback rule)."""
    tiny = tokenizer.apply_chat_template(
        [{"role": "user", "content": "x"}],
        tokenize=False,
        add_generation_prompt=True,
    )
    tiny_ids = tokenizer.encode(tiny, add_special_tokens=False)
    x_ids = tokenizer.encode("x", add_special_tokens=False)
    last = None
    for i in range(len(tiny_ids) - len(x_ids) + 1):
        if tiny_ids[i : i + len(x_ids)] == x_ids:
            last = i
    if last is None:
        return 6
    return len(tiny_ids) - (last + len(x_ids))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models", required=True)
    p.add_argument("--lang", default="en")
    p.add_argument("--pads", default="60,120,200")
    p.add_argument("--tail", default="json")
    p.add_argument("--qfile", default=None,
                   help="q_percentiles.json path (default results/q_percentiles.json)")
    args = p.parse_args()

    from transformers import AutoTokenizer

    qfile = Path(args.qfile) if args.qfile else (
        Path(__file__).resolve().parents[1] / "results" / "q_percentiles.json")
    q_rows = json.loads(qfile.read_text())

    print(f"{'model':<28}{'pad':>5}{'I_pad':>7}{'suf':>5}{'c_sch':>7}{'Q90':>5}{'w_hat':>7}  tail")
    for model in args.models.split(","):
        model = model.strip()
        tok = AutoTokenizer.from_pretrained(model)
        q90 = next(int(r["Q90"]) for r in q_rows
                   if r["lang"] == args.lang and r["model"] == model)
        s = suffix_tokens(tok)
        instr = LANGUAGES[args.lang].qa_instruction
        for pad in args.pads.split(","):
            pad = int(pad)
            padded = _pad_instruction(instr, args.lang, tok, pad, tail=args.tail)
            i_pad = _n(tok, padded)
            c = i_pad + s
            print(f"{model[:27]:<28}{pad:>5}{i_pad:>7}{s:>5}{c:>7}{q90:>5}{c + q90:>7}  {args.tail}")


if __name__ == "__main__":
    main()
