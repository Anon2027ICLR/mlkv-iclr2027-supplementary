#!/usr/bin/env python3
"""Preregistered readout for the five ICLR10 arms (fifth review).

Preregisters: docs/iclr-refine-preregister.md (B1),
docs/iclr-oracle-preregister.md (B2), docs/iclr-32b-preregister.md (B3),
docs/iclr-ctx16k-preregister.md (B4),
docs/iclr-32b-depth-preregister.md (B5, the closing arm). All scoring offline (R2 lenient
primary, marker-only robustness beside it) — never the stored `correct`.
|Q_i| comes from meta["q_tokens"] (run tokenizer, recorded at build).

  UV_NO_SYNC=1 uv run python scripts/iclr10_readout.py
"""
from __future__ import annotations

import ast
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mlkv.qa_metrics import (  # noqa: E402
    containment_match_lenient,
    containment_match_marker_only,
)

RES = ROOT / "results"


def golds(s):
    s = (s or "").strip()
    if s.startswith("["):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, list):
                return [str(x) for x in v]
        except Exception:
            pass
    return [s] if s else []


def load(db, scorer):
    con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
    out = defaultdict(lambda: defaultdict(dict))
    meta = {}
    for iid, lang, cfg, o, g, m in con.execute(
        "SELECT item_id, lang, config, output, answer_gold, meta FROM generations"
    ):
        out[lang][cfg][iid] = bool(scorer(o or "", golds(g), lang))
        if iid not in meta:
            meta[iid] = json.loads(m or "{}")
    con.close()
    return out, meta


def _binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k, n, alpha=0.05):
    if n == 0:
        return 0.0, 1.0

    def solve(fn, lo=0.0, hi=1.0):
        for _ in range(200):
            mid = (lo + hi) / 2
            if fn(mid):
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    lower = 0.0 if k == 0 else solve(lambda p: 1 - _binom_cdf(k - 1, n, p) < alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: _binom_cdf(k, n, p) >= alpha / 2)
    return lower, upper


def mcnemar_p(f, b):
    n = f + b
    if n == 0:
        return 1.0
    k = min(f, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


def fisher_exact_p(a, b, c, d):
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def hyp(x):
        return (math.comb(c1, x) * math.comb(n - c1, r1 - x)) / math.comb(n, r1)

    p_obs = hyp(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return min(1.0, sum(hyp(x) for x in range(lo, hi + 1)
                        if hyp(x) <= p_obs * (1 + 1e-9)))


def ci_row(label, base, comp, closure=True, items=None):
    common = sorted(set(base) & set(comp))
    if items is not None:
        common = sorted(set(common) & set(items))
    f = sum(1 for i in common if not base[i] and comp[i])
    b = sum(1 for i in common if base[i] and not comp[i])
    n = len(common)
    d = 100.0 * (f - b) / n
    lo_p, hi_p = clopper_pearson(f, f + b)
    d_lo = 100.0 * (2 * lo_p - 1) * (f + b) / n
    d_hi = 100.0 * (2 * hi_p - 1) * (f + b) / n
    p = mcnemar_p(f, b)
    v = ("" if not closure
         else "non-inferior at -3pp" if d_lo >= -3
         else "certified residual" if d_hi < -3
         else "confirmed residual" if d_hi < 0
         else "interval too wide for +-3pp")
    print(f"  {label:34} n={n:<4} d={d:+5.1f}  f/b={f:>3}/{b:<3} "
          f"CI [{d_lo:+6.1f},{d_hi:+6.1f}]  p={p:.4f}  {v}")
    return d, d_lo, d_hi, p


def acc(cell):
    return 100.0 * sum(cell.values()) / len(cell)


def enrichment(label, flag_of, broken, pool):
    nb = [i for i in pool if i not in broken]
    a = sum(1 for i in broken if flag_of(i))
    b = len(broken) - a
    c = sum(1 for i in nb if flag_of(i))
    d = len(nb) - c
    sb = 100.0 * a / len(broken) if broken else float("nan")
    sp = 100.0 * (a + c) / len(pool)
    print(f"    {label:28} broken {a}/{len(broken)} ({sb:5.1f}%)  "
          f"pool {a + c}/{len(pool)} ({sp:5.1f}%)  Fisher "
          f"p={fisher_exact_p(a, b, c, d):.4f}")


def main() -> None:
    for db in ("refine.db", "oracle_depth.db", "ctx16k.db", "qwen32b.db",
               "qwen32b_depth.db"):
        con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
        stacks = [r[0] for r in con.execute(
            "SELECT DISTINCT stack_id FROM generations")]
        con.close()
        assert len(stacks) == 1, f"{db}: {stacks}"
        print(f"{db:16} stack={stacks[0][:12]}")

    for scorer, tag in ((containment_match_lenient, "R2 lenient"),
                        (containment_match_marker_only, "marker-only")):
        print("\n" + "#" * 74)
        print(f"# Scoring: {tag}")
        print("#" * 74)

        # ---------------- B1: refine layout ----------------
        R, _ = load("refine.db", scorer)
        for lang in ("en", "bn"):
            base = R[lang]["baseline"]
            print(f"\n== B1 refine.db  {lang}  n={len(base)}  "
                  f"baseline acc={acc(base):.1f}")
            ci_row(f"{lang} w64 vs refine baseline", base,
                   R[lang]["snapkv@r0.75"])

        # ---------------- B2: oracle at depth ----------------
        O, om = load("oracle_depth.db", scorer)
        te = O["te"]
        base = te["baseline"]
        print(f"\n== B2 oracle_depth.db  te n={len(base)}  "
              f"baseline acc={acc(base):.1f}")
        ci_row("te w247 (w-hat) vs baseline", base, te["snapkv@r0.75:w247"])
        ci_row("te wq167 (oracle) vs baseline", base,
               te["snapkv@r0.75:wq167"])
        print("  head-to-head (base=w-hat, comp=oracle; f = oracle fixes):")
        ci_row("te oracle vs w-hat", te["snapkv@r0.75:w247"],
               te["snapkv@r0.75:wq167"], closure=False)
        long_items = [i for i in base if om[i]["q_tokens"] > 80]
        print(f"  registered secondary: long decile |Q|>80 "
              f"(n={len(long_items)}, V<1 under w-hat, V=1 under oracle):")
        ci_row("long decile: oracle vs w-hat", te["snapkv@r0.75:w247"],
               te["snapkv@r0.75:wq167"], closure=False, items=long_items)
        ci_row("long decile: w-hat vs baseline", base,
               te["snapkv@r0.75:w247"], items=long_items)
        ci_row("long decile: oracle vs baseline", base,
               te["snapkv@r0.75:wq167"], items=long_items)
        broken = [i for i in base
                  if base[i] and not te["snapkv@r0.75:wq167"][i]]
        print(f"  oracle item audit (broken n={len(broken)}):")
        for pos in ("front", "middle", "back"):
            enrichment(f"gold position = {pos}",
                       lambda i, p=pos: om[i]["position"] == p,
                       broken, list(base))
        qs = sorted(om[i]["q_tokens"] for i in base)
        med = qs[len(qs) // 2]
        enrichment(f"|Q| > median ({med})",
                   lambda i: om[i]["q_tokens"] > med, broken, list(base))

        # ---------------- B4: 16k prefill ----------------
        C, cm = load("ctx16k.db", scorer)
        te = C["te"]
        base = te["baseline"]
        print(f"\n== B4 ctx16k.db  te @16k  n={len(base)}  "
              f"baseline acc={acc(base):.1f}")
        ci_row("te w64 vs 16k baseline (blind)", base, te["snapkv@r0.75"])
        d, *_ = ci_row("te w247 (w-hat) vs baseline (GATE)", base,
                       te["snapkv@r0.75:w247"])
        print(f"    gate |d|<=3pp: {'MET' if abs(d) <= 3 else 'MISSED'}")
        ci_row("te w247 vs w64 (recovery)", te["snapkv@r0.75"],
               te["snapkv@r0.75:w247"], closure=False)

        # ---------------- B3: Qwen3-32B ----------------
        Q, _ = load("qwen32b.db", scorer)
        for lang, wh in (("bn", 183), ("te", 247)):
            base = Q[lang]["baseline"]
            print(f"\n== B3 qwen32b.db  {lang}  n={len(base)}  "
                  f"baseline acc={acc(base):.1f}")
            ci_row(f"{lang} w64 vs baseline (hole)", base,
                   Q[lang]["snapkv@r0.75"])
            d, *_ = ci_row(f"{lang} w{wh} (w-hat) vs baseline (GATE)", base,
                           Q[lang][f"snapkv@r0.75:w{wh}"])
            print(f"    gate |d|<=3pp: {'MET' if abs(d) <= 3 else 'MISSED'}")
            ci_row(f"{lang} w{wh} vs w64 (recovery)", Q[lang]["snapkv@r0.75"],
                   Q[lang][f"snapkv@r0.75:w{wh}"], closure=False)

        # ---------------- B5: 32B Telugu at depth ----------------
        QD, qdm = load("qwen32b_depth.db", scorer)
        te = QD["te"]
        base = te["baseline"]
        print(f"\n== B5 qwen32b_depth.db  te n={len(base)}  "
              f"baseline acc={acc(base):.1f}")
        ci_row("te w64 vs baseline (PRIMARY)", base, te["snapkv@r0.75"])
        d, *_ = ci_row("te w247 (w-hat) vs baseline (GATE)", base,
                       te["snapkv@r0.75:w247"])
        print(f"    gate |d|<=3pp: {'MET' if abs(d) <= 3 else 'MISSED'}")
        ci_row("te w247 vs w64 (recovery)", te["snapkv@r0.75"],
               te["snapkv@r0.75:w247"], closure=False)
        broken = [i for i in base if base[i] and not te["snapkv@r0.75"][i]]
        print(f"  item audit (broken n={len(broken)}):")
        for pos in ("front", "middle", "back"):
            enrichment(f"gold position = {pos}",
                       lambda i, p=pos: qdm[i]["position"] == p,
                       broken, list(base))
        qs = sorted(qdm[i]["q_tokens"] for i in base)
        med = qs[len(qs) // 2]
        enrichment(f"|Q| > median ({med})",
                   lambda i: qdm[i]["q_tokens"] > med, broken, list(base))

    # qid overlap of the 16k eval set with the 8k one (registered reporting)
    _, cm = load("ctx16k.db", containment_match_lenient)
    _, dm = load("oracle_depth.db", containment_match_lenient)
    q16 = {m["qid"] for m in cm.values()}
    q8 = {dm[i]["qid"] for i in dm if i.endswith("k-" + i.split("-")[-1])
          and int(i.rsplit("-", 1)[1]) < 100}
    print(f"\n16k eval qids overlapping the 8k first-100 set: "
          f"{len(q16 & q8)}/{len(q16)}")

    # cross-stack determinism vs the campaign stack (informational)
    a = sqlite3.connect(f"file:{RES / 'depth.db'}?mode=ro", uri=True)
    b = sqlite3.connect(f"file:{RES / 'oracle_depth.db'}?mode=ro", uri=True)
    for cfg in ("baseline", "snapkv@r0.75:w247"):
        da = dict(a.execute("SELECT item_id, output FROM generations "
                            "WHERE lang='te' AND config=?", (cfg,)))
        db_ = dict(b.execute("SELECT item_id, output FROM generations "
                             "WHERE lang='te' AND config=?", (cfg,)))
        common = set(da) & set(db_)
        same = sum(1 for i in common if da[i] == db_[i])
        print(f"cross-stack {cfg}: shared={len(common)} byte-identical={same}")


if __name__ == "__main__":
    main()
