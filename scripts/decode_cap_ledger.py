#!/usr/bin/env python3
"""Measure what a fixed decode cap does to a multilingual evaluation.

The campaign's first arms decoded under a 128-token cap and the main arms
were re-run at 384 because of what this script reports: a decode cap is a
token-denominated constant, so like the observation window it means
something different in every language. Three of the cap-128 languages
(el, hi, ru) were re-run at 384, which makes the effect isolable.

Greedy decoding means the 128-cap output is a byte prefix of the 384-cap
output for the same item, so "what the cap did" is a within-item
comparison rather than a between-condition one.

Nothing here may be pooled with the main tables: different stack,
different item variant (`mrag-bp`, whose inputs are byte-equal across
languages).

  UV_NO_SYNC=1 uv run python scripts/decode_cap_ledger.py
"""
from __future__ import annotations

import ast
import math
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

RES = ROOT / "results"
SHORT, LONG = "e3-final.db", "e3_384.db"
MARKER = "####"
FAILS: list[str] = []


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


def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n)


def load(db):
    """(lang, config, item) -> (output, golds, hit_cap); plus the cap itself."""
    con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
    cap = con.execute("SELECT MAX(n_output_tokens) FROM generations").fetchone()[0]
    rows = {}
    for lang, cfg, iid, out, gold, ntok in con.execute(
        "SELECT lang, config, item_id, output, answer_gold, n_output_tokens "
        "FROM generations"
    ):
        rows[(lang, cfg, iid)] = (out or "", golds(gold), ntok >= cap)
    con.close()
    return rows, cap


def check(label, got, want):
    if got != want:
        FAILS.append(f"{label}: expected {want!r}, measured {got!r}")
        print(f"  MISMATCH  {label}: expected {want!r}, measured {got!r}")


def pct(num, den):
    return round(100 * num / den) if den else None


def main() -> int:
    short, cap_short = load(SHORT)
    long, cap_long = load(LONG)
    print(f"caps: {cap_short} ({SHORT}) and {cap_long} ({LONG})")

    # ---- baseline truncation and marker survival, per language ----------
    def profile(rows, cap_label):
        out = {}
        for (lang, cfg, iid), (text, _g, hit) in rows.items():
            if cfg != "baseline":
                continue
            d = out.setdefault(lang, {"n": 0, "trunc": 0, "marker": 0})
            d["n"] += 1
            d["trunc"] += hit
            d["marker"] += MARKER in text
        print(f"\n  uncompressed baseline at cap {cap_label}")
        print(f"    {'lang':5} {'n':>4} {'truncated':>10} {'marker':>8}")
        for lang in sorted(out, key=lambda l: -out[l]["trunc"]):
            d = out[lang]
            print(f"    {lang:5} {d['n']:4} {pct(d['trunc'], d['n']):9}% "
                  f"{pct(d['marker'], d['n']):7}%")
        return out

    p_short = profile(short, cap_short)
    p_long = profile(long, cap_long)

    TRUNC_128 = {"el": 65, "hi": 50, "ru": 30, "th": 14, "de": 12,
                 "en": 6, "es": 4, "vi": 4, "zh": 1}
    MARKER_128 = {"el": 45, "hi": 59, "ru": 71, "th": 58, "de": 74,
                  "en": 95, "vi": 94, "es": 96, "zh": 98}
    TRUNC_384 = {"el": 17, "hi": 4, "ru": 2}
    MARKER_384 = {"el": 90, "hi": 97, "ru": 92}
    for lang, want in TRUNC_128.items():
        check(f"truncated@128 {lang}", pct(p_short[lang]["trunc"], p_short[lang]["n"]), want)
    for lang, want in MARKER_128.items():
        check(f"marker@128 {lang}", pct(p_short[lang]["marker"], p_short[lang]["n"]), want)
    for lang, want in TRUNC_384.items():
        check(f"truncated@384 {lang}", pct(p_long[lang]["trunc"], p_long[lang]["n"]), want)
    for lang, want in MARKER_384.items():
        check(f"marker@384 {lang}", pct(p_long[lang]["marker"], p_long[lang]["n"]), want)

    # ---- the prefix property, over every shared cell --------------------
    shared = sorted(set(short) & set(long))
    prefix = sum(1 for k in shared if long[k][0].startswith(short[k][0]))
    print(f"\n  the cap-{cap_short} output is a byte prefix of the cap-{cap_long} "
          f"output on {prefix} of {len(shared)} shared generations")
    check("shared cells", len(shared), 1200)
    check("prefix property", prefix, 1124)

    # ---- what the cap costs, within item, where it destroys the marker --
    # Restricted to cells where the prefix property holds, so the only
    # difference between the two rows is the truncation itself.
    per_lang, pooled = {}, []
    for k in shared:
        if not long[k][0].startswith(short[k][0]):
            continue
        if MARKER in short[k][0] or MARKER not in long[k][0]:
            continue
        lang = k[0]
        a = containment_match_lenient(short[k][0], short[k][1], lang)
        b = containment_match_lenient(long[k][0], long[k][1], lang)
        per_lang.setdefault(lang, []).append((a, b))
        pooled.append((a, b))

    def score(pairs):
        n = len(pairs)
        fixed = sum(1 for a, b in pairs if not a and b)
        broken = sum(1 for a, b in pairs if a and not b)
        acc_s = pct(sum(a for a, _ in pairs), n)
        acc_l = pct(sum(b for _, b in pairs), n)
        # Round the paired difference, never the difference of two rounded
        # accuracies -- the campaign's convention everywhere else. Pooled over
        # the three languages the two differ: 12/327 is 3.7, not 54 minus 51.
        delta = round(100 * (fixed - broken) / n)
        return n, acc_s, acc_l, delta, fixed, broken, mcnemar_p(fixed, broken)

    print(f"\n  where truncation destroyed the answer marker "
          f"(marker at {cap_long}, none at {cap_short})")
    print(f"    {'lang':5} {'n':>4} {'@128':>6} {'@384':>6} {'delta':>6} "
          f"{'fixed/broken':>13} {'p':>8}")
    for lang in sorted(per_lang, key=lambda l: -len(per_lang[l])):
        n, a, b, d, f, br, p = score(per_lang[lang])
        print(f"    {lang:5} {n:4} {a:5}% {b:5}% {d:+6} {f:6}/{br:<6} {p:8.4f}")
    n, a, b, d, f, br, p = score(pooled)
    print(f"    {'all':5} {n:4} {a:5}% {b:5}% {d:+6} {f:6}/{br:<6} {p:8.4f}")

    check("marker-destroyed cells", n, 327)
    check("marker-destroyed accuracy at 128", a, 51)
    check("marker-destroyed accuracy at 384", b, 54)
    check("marker-destroyed paired delta", d, 4)
    check("marker-destroyed fixed/broken", (f, br), (19, 7))
    check("marker-destroyed significant", p < 0.05, True)
    check("marker-destroyed el delta", score(per_lang["el"])[3], 2)
    check("marker-destroyed hi delta", score(per_lang["hi"])[3], 1)
    check("marker-destroyed ru delta", score(per_lang["ru"])[3], 11)
    check("marker-destroyed ru significant", score(per_lang["ru"])[6] < 0.05, True)

    print()
    if FAILS:
        print(f"{len(FAILS)} mismatches against the values the paper quotes")
        return 1
    print("every value the appendix quotes reproduces from the stores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
