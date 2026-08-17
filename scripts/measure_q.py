#!/usr/bin/env python3
"""Held-out question-length percentiles for AutoWindow-Q90.

Q_p = percentile of tokenizer.encode(question) on a split that excludes
the 100 mRAG eval items (pool order[:100]). See
docs/iclr-autowin-q90-preregister.md.

Usage:
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models Qwen/Qwen3-4B --langs en,bn,te
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mlkv.languages import resolve
from mlkv.tasks.mrag import TYDIQA_LANGS, XQUAD_LANGS, load_pool

EVAL_N = 100


def _n(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def held_out_questions(lang: str) -> list[str]:
    """Question strings not used as the first EVAL_N mRAG items."""
    from datasets import load_dataset

    if lang in XQUAD_LANGS:
        rows = list(load_dataset("google/xquad", f"xquad.{lang}", split="validation"))
        # load_pool uses this same list; eval = [:100]
        return [r["question"] for r in rows[EVAL_N:]]

    if lang in TYDIQA_LANGS:
        name = TYDIQA_LANGS[lang]
        ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
        val = [r for r in ds["validation"] if r["id"].startswith(f"{name}-")]
        eval_ids = {r["id"] for r in val[:EVAL_N]}
        return [
            r["question"]
            for r in ds["train"]
            if r["id"].startswith(f"{name}-") and r["id"] not in eval_ids
        ]

    # Fallback: skip the eval slice of whatever load_pool returns.
    questions, _ = load_pool(lang)
    return [q["question"] for q in questions[EVAL_N:]]


def percentile(xs: list[int], p: float) -> int:
    if not xs:
        raise ValueError("empty question list")
    ys = sorted(xs)
    if p <= 0:
        return ys[0]
    if p >= 100:
        return ys[-1]
    k = (len(ys) - 1) * (p / 100.0)
    lo, hi = int(k), min(int(k) + 1, len(ys) - 1)
    t = k - lo
    return int(round(ys[lo] * (1 - t) + ys[hi] * t))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models", required=True)
    p.add_argument("--langs", default="en,bn,te")
    p.add_argument("--out", default=None,
                   help="output JSON path (default results/q_percentiles.json). "
                        "Pass a model-specific path when measuring a non-Qwen "
                        "tokenizer so the locked Qwen file is not overwritten.")
    args = p.parse_args()

    from transformers import AutoTokenizer

    print(
        f"{'model':<28}{'lang':<6}{'n':>6}"
        f"{'Q50':>6}{'Q90':>6}{'Qmax':>6}  source"
    )
    blob = []
    for model in args.models.split(","):
        tok = AutoTokenizer.from_pretrained(model.strip())
        for lang in resolve(args.langs):
            qs = held_out_questions(lang.code)
            lens = [_n(tok, q) for q in qs]
            rec = {
                "model": model.strip(),
                "lang": lang.code,
                "n": len(lens),
                "Q50": percentile(lens, 50),
                "Q90": percentile(lens, 90),
                "Qmax": max(lens),
                "source": "xquad.val[100:]" if lang.code in XQUAD_LANGS else "tydi.train\\eval100",
            }
            blob.append(rec)
            print(
                f"{model.strip()[:27]:<28}{lang.code:<6}{rec['n']:6d}"
                f"{rec['Q50']:6d}{rec['Q90']:6d}{rec['Qmax']:6d}  {rec['source']}"
            )
    default_out = Path(__file__).resolve().parents[1] / "results" / "q_percentiles.json"
    out = Path(args.out) if args.out else default_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blob, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
