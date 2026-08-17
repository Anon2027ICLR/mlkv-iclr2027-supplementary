#!/usr/bin/env python3
"""Preregistered readout for the V-trace arm (docs/iclr-v-trace-preregister.md).

Committed BEFORE the data exists; run unedited on the finished db. R2 only,
never stored `correct`. This file is the single source of the V dose-response
table — the lesson from the old 3,200-pair V-band table, whose composition
was never pinned by a committed script.

  UV_NO_SYNC=1 uv run --with statsmodels python scripts/v_trace_bins.py
  UV_NO_SYNC=1 uv run python scripts/v_trace_bins.py --db results/v_trace.db
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402
from mlkv.tasks.mrag import TYDIQA_LANGS, XQUAD_LANGS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Locked c (measure_c.py fallback rule, 2026-08-14 Qwen3-4B). The driver
# derives the window grid from the same measurement; override with --c if an
# on-pod re-measure ever disagrees.
C_LOCK = {"te": 167, "bn": 107, "en": 25, "th": 45, "sw": 47}

BIN_EDGES = [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0)]


def golds(s: str | None) -> list[str]:
    s = (s or "").strip()
    if s.startswith("["):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, list):
                return [str(x) for x in v]
        except Exception:
            pass
    return [s] if s else []


def mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


def sign_test_p(pos: int, neg: int) -> float:
    return mcnemar_p(pos, neg)  # same two-sided exact binomial


def question_lengths(lang: str, model: str, qids: set[str]) -> dict[str, int]:
    """qid -> question token count on the run tokenizer."""
    from datasets import load_dataset
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model)
    out: dict[str, int] = {}
    if lang in TYDIQA_LANGS:
        name = TYDIQA_LANGS[lang]
        ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
        rows = [r for r in ds["validation"] if r["id"].startswith(f"{name}-")]
    elif lang in XQUAD_LANGS:
        from datasets import load_dataset as _ld
        rows = list(_ld("google/xquad", f"xquad.{lang}", split="validation"))
    else:
        raise ValueError(f"no question source for lang {lang}")
    for r in rows:
        if r["id"] in qids:
            out[r["id"]] = len(tok.encode(r["question"], add_special_tokens=False))
    missing = qids - set(out)
    if missing:
        raise ValueError(f"{lang}: {len(missing)} qids not found in source")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "results" / "v_trace.db"))
    ap.add_argument("--c", default=None,
                    help='override c per lang, e.g. "te=167,bn=107"')
    args = ap.parse_args()

    c_of = dict(C_LOCK)
    if args.c:
        for part in args.c.split(","):
            k, v = part.split("=")
            c_of[k.strip()] = int(v)

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = list(conn.execute(
        "SELECT item_id, model, lang, config, output, answer_gold, meta, stack_id "
        "FROM generations"))
    conn.close()

    stacks = sorted({r["stack_id"] for r in rows})
    print(f"db={args.db}  rows={len(rows)}  stacks={stacks}")
    if len(stacks) != 1:
        print("WARNING: more than one stack in this db — comparisons must stay "
              "within-stack; investigate before trusting the tables below.")

    by_lang: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        by_lang[r["lang"]].append(r)

    for lang in sorted(by_lang):
        lrows = by_lang[lang]
        model = lrows[0]["model"]
        c = c_of[lang]
        print("\n" + "=" * 74)
        print(f"lang={lang}  model={model}  c={c}  (R2, paired within this db)")

        score: dict[str, dict[str, bool]] = defaultdict(dict)  # config -> item -> bool
        qid_of: dict[str, str] = {}
        for r in lrows:
            score[r["config"]][r["item_id"]] = bool(containment_match_lenient(
                r["output"] or "", golds(r["answer_gold"]), lang))
            m = json.loads(r["meta"] or "{}")
            if "qid" in m:
                qid_of[r["item_id"]] = m["qid"]

        base = score.get("baseline", {})
        if not base:
            print("  no baseline in db — cannot pair; aborting this lang")
            continue

        wcfgs = sorted(
            (int(mm.group(1)), cfg)
            for cfg in score
            if (mm := re.search(r":w(\d+)$", cfg))
        )

        qlens = question_lengths(lang, model, {qid_of[i] for i in base if i in qid_of})

        def v_of(w: int, item: str) -> float:
            q = qlens[qid_of[item]]
            return max(0.0, min(1.0, (w - c) / q))

        # ---- Prediction 1: per-window paired table (monotone in dose)
        print(f"\n  ## per-window paired damage (n={len(base)})")
        print(f"  {'w':>5} {'w-c':>5} {'medV':>6} {'acc':>6} {'d_pp':>7} "
              f"{'fix/brk':>8} {'p':>8}")
        base_acc = 100 * sum(base.values()) / len(base)
        print(f"  {'base':>5} {'':>5} {'':>6} {base_acc:6.1f}")
        prev_d = None
        monotone_ok = True
        for w, cfg in wcfgs:
            m = score[cfg]
            common = sorted(set(base) & set(m))
            fixed = sum(1 for i in common if not base[i] and m[i])
            broken = sum(1 for i in common if base[i] and not m[i])
            d = 100 * (sum(m[i] for i in common) - sum(base[i] for i in common)) / len(common)
            medv = sorted(v_of(w, i) for i in common)[len(common) // 2]
            print(f"  {w:>5} {w - c:>5} {medv:6.2f} "
                  f"{100 * sum(m[i] for i in common) / len(common):6.1f} {d:+7.1f} "
                  f"{fixed:>4}/{broken:<3} {mcnemar_p(fixed, broken):8.4f}")
            if prev_d is not None and d < prev_d - 3.0:
                monotone_ok = False
            prev_d = d
        print(f"  pred1 monotone(±3pp slack): {'HOLD' if monotone_ok else 'MISS'}")

        # ---- Prediction 2: V bins pooled over treated cells
        print("\n  ## V bins (pooled over all treated cells, paired delta vs baseline)")
        recs = []  # (item, w, V, y_treat, y_base)
        for w, cfg in wcfgs:
            for i, y in score[cfg].items():
                if i in base and i in qid_of:
                    recs.append((i, w, v_of(w, i), int(y), int(base[i])))
        bins: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for _, _, v, y, yb in recs:
            if v == 1.0:
                key = "V=1"
            else:
                for lo, hi in BIN_EDGES:
                    if lo <= v < hi:
                        key = f"{lo:.2f}-{hi:.2f}"
                        break
            bins[key].append((y, yb))
        order = [f"{lo:.2f}-{hi:.2f}" for lo, hi in BIN_EDGES] + ["V=1"]
        means = {}
        for key in order:
            cell = bins.get(key, [])
            if not cell:
                print(f"  {key:>10}  n=0")
                continue
            d = 100 * (sum(y for y, _ in cell) - sum(yb for _, yb in cell)) / len(cell)
            fixed = sum(1 for y, yb in cell if y and not yb)
            broken = sum(1 for y, yb in cell if yb and not y)
            means[key] = d
            print(f"  {key:>10}  n={len(cell):4d}  d={d:+6.1f}pp  "
                  f"fix/brk={fixed}/{broken}  p={mcnemar_p(fixed, broken):.2e}")
        seq = [means[k] for k in order if k in means]
        p2 = (means.get("V=1") is not None and abs(means["V=1"]) <= 3
              and means.get("0.00-0.25") is not None and means["0.00-0.25"] <= -8
              and all(seq[i] <= seq[i + 1] + 1e-9 for i in range(len(seq) - 1)))
        print(f"  pred2 (V=1 flat, V<.25 ≤−8, monotone): {'HOLD' if p2 else 'MISS'}")

        # ---- Prediction 3a: sign test on switching items
        by_item: dict[str, list[tuple[float, int]]] = defaultdict(list)
        for i, w, v, y, _ in recs:
            by_item[i].append((v, y))
        pos = neg = 0
        for i, cells in by_item.items():
            cells.sort()
            ys = [y for _, y in cells]
            if len(set(ys)) < 2:
                continue
            lo_y, hi_y = ys[0], ys[-1]
            if hi_y > lo_y:
                pos += 1
            elif hi_y < lo_y:
                neg += 1
        print(f"\n  pred3 sign test on switching items: correct-at-high-V {pos} "
              f"vs reverse {neg}  p={sign_test_p(pos, neg):.4f}")

        # ---- Prediction 3b + 4: cluster logit and AIC (statsmodels optional)
        try:
            import pandas as pd
            import statsmodels.formula.api as smf

            df = pd.DataFrame(recs, columns=["item", "w", "V", "y", "y_base"])
            df["wmc"] = df["w"] - c
            df["Q"] = [qlens[qid_of[i]] for i in df["item"]]
            m_v = smf.logit("y ~ V", data=df).fit(
                disp=False, cov_type="cluster", cov_kwds={"groups": df["item"]})
            print("\n  ## cluster-robust logit  y ~ V  (clusters=item)")
            print(f"  coef V={m_v.params['V']:+.3f}  z={m_v.tvalues['V']:.2f}  "
                  f"p={m_v.pvalues['V']:.2e}")
            m_wc = smf.logit("y ~ wmc", data=df).fit(disp=False)
            m_v2 = smf.logit("y ~ V", data=df).fit(disp=False)
            m_wcq = smf.logit("y ~ wmc + Q", data=df).fit(disp=False)
            print("  ## AIC on treated rows (lower better)")
            for name, m in [("V", m_v2), ("(w-c)", m_wc), ("(w-c)+Q", m_wcq)]:
                print(f"    {name:8}  AIC={m.aic:8.1f}  k={int(m.df_model) + 1}")
            print(f"  pred4 AIC(V) < AIC(w-c): "
                  f"{'HOLD' if m_v2.aic < m_wc.aic else 'MISS'}")
        except ImportError:
            print("\n  statsmodels/pandas missing — rerun with "
                  "`uv run --with statsmodels,pandas python scripts/v_trace_bins.py` "
                  "for pred3b/pred4")

    print("\ndone")


if __name__ == "__main__":
    main()
