#!/usr/bin/env python3
"""Exact-conditional 95% CIs for every closure cell in the paper.

Both reviews of the finished draft made the same objection: the registered
closure rule (|delta| <= 3pp, point estimate, n=100) is a decision rule,
not an equivalence demonstration, and the paper reported no interval. This
script is the pinned source of the interval column: it recomputes the
discordant counts from the stores (never from a doc) and derives an exact
CI by conditioning on the discordant total N = fixed + broken; given N,
fixed ~ Binomial(N, p) and delta = (2p - 1) N / n, so a Clopper--Pearson
interval for p maps monotonically onto an interval for delta. Pure stdlib
(bisection on the binomial tails), no scipy.

Vocabulary the paper uses, fixed here:
  "meets the registered gate"  point |delta| <= 3pp
  "non-inferior at -3pp"       CI lower bound >= -3pp
  "confirmed residual"         CI entirely below 0
  "certified residual"         CI entirely below -3pp, i.e. below the gate
                               itself and not merely below zero. Strictly
                               stronger than "confirmed"; the depth arm is
                               the first cell in the paper to reach it, and
                               the distinction is why app:ci now prints two
                               different words for two different readings.

  UV_NO_SYNC=1 uv run python scripts/closure_cis.py
"""
from __future__ import annotations

import ast
import math
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

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


def load(db, key=None):
    con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
    out = defaultdict(lambda: defaultdict(dict))
    for iid, lang, cfg, o, g in con.execute(
        "SELECT item_id, lang, config, output, answer_gold FROM generations"
    ):
        out[key(iid) if key else lang][cfg][iid] = bool(
            containment_match_lenient(o or "", golds(g), lang))
    con.close()
    return out


def discordants(base, comp):
    common = sorted(set(base) & set(comp))
    f = sum(1 for i in common if not base[i] and comp[i])
    b = sum(1 for i in common if base[i] and not comp[i])
    return f, b, len(common)


def _binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k, n, alpha=0.05):
    """Exact CI for a binomial proportion, by bisection on the tails."""
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


def ci_row(label, base, comp, closure=True):
    """closure=False for a head-to-head between two rivals: the verdict
    vocabulary above is defined against an uncompressed baseline, and
    "non-inferior at -3pp" would mean something entirely different when the
    comparator is another window. Those rows print the interval and stop."""
    f, b, n = discordants(base, comp)
    N = f + b
    d = 100.0 * (f - b) / n
    lo_p, hi_p = clopper_pearson(f, N)
    d_lo = 100.0 * (2 * lo_p - 1) * N / n
    d_hi = 100.0 * (2 * hi_p - 1) * N / n
    verdict = ("" if not closure
               else "non-inferior at -3pp" if d_lo >= -3
               else "certified residual" if d_hi < -3
               else "confirmed residual" if d_hi < 0
               else "interval too wide for +-3pp")
    print(f"{label:26} d={d:+5.1f}  f/b={f}/{b}  "
          f"95% CI [{d_lo:+6.1f}, {d_hi:+6.1f}]  {verdict}")
    return d, d_lo, d_hi


print("Closure cells: paired delta at w-hat vs own uncompressed baseline,")
print("exact-conditional 95% CI (n=100 per cell).\n")

D = load("autowin-final.db")
Q = load("autowin_q90.db")
for lang, what in [("en", 43), ("bn", 183), ("te", 247)]:
    ci_row(f"4B {lang}", D[lang]["baseline"], Q[lang][f"snapkv@r0.75:w{what}"])

SF = load("schema_fix.db", key=lambda i: re.search(r"JSON(\d+)", i).group(1))
for pad, what in [("60", 90), ("120", 184), ("200", 231)]:
    ci_row(f"JSON-{pad}", SF[pad]["baseline"], SF[pad][f"snapkv@r0.75:w{what}"])

G = load("gemma_q90.db")
ci_row("Gemma bn", G["bn"]["baseline"], G["bn"]["snapkv@r0.75:w50"])
# Gemma Telugu is the cell Section 6 uses to say the shipped constant can
# already pass, so the paper needs its interval as much as any other closure
# row. Here w-hat IS the default: Q90 puts Telugu's window back at 64.
ci_row("Gemma te", G["te"]["baseline"], G["te"]["snapkv@r0.75:w64"])

E = load("autowin_8b.db")
ci_row("8B bn", E["bn"]["baseline"], E["bn"]["snapkv@r0.75:w183"])

L = load("llama.db")
for lang, what in [("en", 43), ("bn", 212), ("te", 284)]:
    ci_row(f"Llama {lang}", L[lang]["baseline"], L[lang][f"snapkv@r0.75:w{what}"])

# The depth arm: the same two headline cells re-run on the entire validation
# pools under the preregistered stopping rule. Own baselines, own store, so
# these pair only within depth.db and are never mixed with the n=100 rows.
DP = load("depth.db")
for lang, what in [("te", 247), ("bn", 183)]:
    ci_row(f"full pool {lang}", DP[lang]["baseline"], DP[lang][f"snapkv@r0.75:w{what}"])

# The constant at scale (app:rivals, "The constant at scale"). Two things
# are being measured and they are not the same test: w=256 against its own
# uncompressed baseline, which is a closure cell like the rest of this
# table, and w=256 against w-hat, which is a head-to-head between rivals.
# The head-to-heads pair across two stores -- the w-hat cells live in
# depth.db -- which is legal here and only here because the two stores'
# baselines are byte-identical on all 782 shared rows, the guard the driver
# checked and the audit re-checks. Direction: base = w256, comp = w-hat, so
# "fixed" counts items the constant gets wrong and the computed integer
# gets right.
CD = load("constant_depth.db")
DPT = load("depth.db")
for lang in ("te", "bn"):
    ci_row(f"full pool {lang} w256", CD[lang]["baseline"],
           CD[lang]["snapkv@r0.75:w256"])
for lang, what in (("te", 247), ("bn", 183)):
    ci_row(f"h2h {lang} what-vs-w256", CD[lang]["snapkv@r0.75:w256"],
           DPT[lang][f"snapkv@r0.75:w{what}"], closure=False)

# The instruction-first cells are mechanism-gate cells, not w-hat closures:
# the treatment is the default window with the question last (V=1 by
# construction), judged by the same |delta| <= 3pp gate and CI vocabulary.
F = load("instr_first.db")
for lang in ["bn", "te"]:
    ci_row(f"IF {lang} @w64", F[lang]["baseline"], F[lang]["snapkv@r0.75"])

print("\ndone")
