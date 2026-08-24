#!/usr/bin/env python3
"""Preregistered readout for the four ICLR9 Group B arms (fourth review).

Preregisters: docs/iclr-slack-depth-preregister.md (B1),
docs/iclr-xinstr-preregister.md (B2), docs/iclr-if-depth-preregister.md (B4),
docs/iclr-thsw-preregister.md (B3). All scoring offline (R2,
containment_match_lenient; marker-only beside it as robustness) — never the
stored `correct`. Enrichment/item audits are reported in proportion-test form
(Fisher exact on the 2x2), per the fourth-review readout format.

  UV_NO_SYNC=1 uv run python scripts/iclr9_readout.py
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
MODEL = "Qwen/Qwen3-4B"

# Locked constants (campaign measurements; the driver re-derived each on-pod
# and the chain log confirms every match).
C_LOCK = {"en": 25, "th": 45, "sw": 47, "bn": 107, "te": 167}


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


def load(db: str, scorer):
    """lang -> config -> item_id -> bool, plus item meta (qid, position)."""
    con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
    out: dict[str, dict[str, dict[str, bool]]] = defaultdict(lambda: defaultdict(dict))
    meta: dict[str, dict] = {}
    for iid, lang, cfg, o, g, m in con.execute(
        "SELECT item_id, lang, config, output, answer_gold, meta FROM generations"
    ):
        out[lang][cfg][iid] = bool(scorer(o or "", golds(g), lang))
        if iid not in meta:
            meta[iid] = json.loads(m or "{}")
    con.close()
    return out, meta


def discordants(base, comp):
    common = sorted(set(base) & set(comp))
    f = sum(1 for i in common if not base[i] and comp[i])
    b = sum(1 for i in common if base[i] and not comp[i])
    return f, b, len(common)


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


def mcnemar_p(f: int, b: int) -> float:
    n = f + b
    if n == 0:
        return 1.0
    k = min(f, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


def fisher_exact_p(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact on [[a, b], [c, d]] (point-probability method)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def hyp(x):
        return (math.comb(c1, x) * math.comb(n - c1, r1 - x)) / math.comb(n, r1)

    p_obs = hyp(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return min(1.0, sum(hyp(x) for x in range(lo, hi + 1)
                        if hyp(x) <= p_obs * (1 + 1e-9)))


def ci_row(label, base, comp, closure=True):
    f, b, n = discordants(base, comp)
    d = 100.0 * (f - b) / n
    lo_p, hi_p = clopper_pearson(f, f + b)
    d_lo = 100.0 * (2 * lo_p - 1) * (f + b) / n
    d_hi = 100.0 * (2 * hi_p - 1) * (f + b) / n
    p = mcnemar_p(f, b)
    verdict = ("" if not closure
               else "non-inferior at -3pp" if d_lo >= -3
               else "certified residual" if d_hi < -3
               else "confirmed residual" if d_hi < 0
               else "interval too wide for +-3pp")
    print(f"  {label:32} d={d:+5.1f}  f/b={f:>3}/{b:<3}  "
          f"95% CI [{d_lo:+6.1f}, {d_hi:+6.1f}]  p={p:.4f}  {verdict}")
    return d, d_lo, d_hi, p


def acc(cell):
    return 100.0 * sum(cell.values()) / len(cell)


def question_lengths(lang: str, qids: set[str]) -> dict[str, int]:
    from datasets import load_dataset
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    from mlkv.tasks.mrag import TYDIQA_LANGS, XQUAD_LANGS

    out: dict[str, int] = {}
    if lang in TYDIQA_LANGS:
        name = TYDIQA_LANGS[lang]
        ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
        rows = [r for r in ds["validation"] if r["id"].startswith(f"{name}-")]
    elif lang in XQUAD_LANGS:
        rows = list(load_dataset("google/xquad", f"xquad.{lang}",
                                 split="validation"))
    else:
        raise ValueError(lang)
    for r in rows:
        if r["id"] in qids:
            out[r["id"]] = len(tok.encode(r["question"], add_special_tokens=False))
    missing = qids - set(out)
    if missing:
        raise ValueError(f"{lang}: {len(missing)} qids missing from source")
    return out


def enrichment(label, flag_of, broken, pool):
    """Proportion-test form: share of flagged items among broken vs among the
    non-broken remainder; Fisher exact on the 2x2."""
    nb = [i for i in pool if i not in broken]
    a = sum(1 for i in broken if flag_of(i))
    b = len(broken) - a
    c = sum(1 for i in nb if flag_of(i))
    d = len(nb) - c
    sb = 100.0 * a / len(broken) if broken else float("nan")
    sp = 100.0 * (a + c) / len(pool)
    p = fisher_exact_p(a, b, c, d)
    print(f"    {label:28} broken {a}/{len(broken)} ({sb:5.1f}%)  "
          f"pool {a + c}/{len(pool)} ({sp:5.1f}%)  Fisher p={p:.4f}")


def broken_by(base, comp):
    return [i for i in set(base) & set(comp) if base[i] and not comp[i]]


def stack_of(db):
    con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
    stacks = [r[0] for r in con.execute(
        "SELECT DISTINCT stack_id FROM generations")]
    con.close()
    return stacks


def main() -> None:
    for db in ("slack_depth.db", "xinstr.db", "if_depth.db", "thsw.db"):
        s = stack_of(db)
        assert len(s) == 1, f"{db}: multiple stacks {s}"
        print(f"{db:16} stack={s[0][:12]}")

    for scorer, tag in ((containment_match_lenient, "R2 lenient"),
                        (containment_match_marker_only, "marker-only")):
        print("\n" + "#" * 74)
        print(f"# Scoring: {tag}")
        print("#" * 74)

        # ---------------- B1: slack ablation at depth ----------------
        S, _ = load("slack_depth.db", scorer)
        te = S["te"]
        print(f"\n== B1 slack_depth.db  te n={len(te['baseline'])}  "
              f"baseline acc={acc(te['baseline']):.1f}")
        for w, name in ((183, "c+16"), (199, "c+32"), (247, "w-hat=c+Q90")):
            ci_row(f"te w{w} ({name}) vs baseline", te["baseline"],
                   te[f"snapkv@r0.75:w{w}"])
        print("  head-to-head (base=rival, comp=w-hat; f = w-hat fixes):")
        ci_row("te w-hat vs c+16 (PRIMARY)", te["snapkv@r0.75:w183"],
               te["snapkv@r0.75:w247"], closure=False)
        ci_row("te w-hat vs c+32", te["snapkv@r0.75:w199"],
               te["snapkv@r0.75:w247"], closure=False)
        for w in (183, 199, 247):
            print(f"    acc w{w} = {acc(te[f'snapkv@r0.75:w{w}']):.1f}")

        # ---------------- B2: English instruction ----------------
        X, xm = load("xinstr.db", scorer)
        c_en = C_LOCK["en"]
        for lang, wh in (("bn", 101), ("te", 105)):
            cell = X[lang]
            base = cell["baseline"]
            print(f"\n== B2 xinstr.db  {lang} (en instruction, c={c_en})  "
                  f"n={len(base)}  baseline acc={acc(base):.1f}")
            ci_row(f"{lang} w64 vs baseline", base, cell["snapkv@r0.75"])
            ci_row(f"{lang} w{wh} (w-hat) vs baseline", base,
                   cell[f"snapkv@r0.75:w{wh}"])
            qid_of = {i: xm[i]["qid"] for i in base}
            qlens = question_lengths(lang, set(qid_of.values()))
            slack = 64 - c_en

            def vlt1(i, q=qlens, qo=qid_of, s=slack):
                return q[qo[i]] > s

            n_v = sum(1 for i in base if vlt1(i))
            print(f"    V<1 at w64 (|Q|>{slack}): {n_v}/{len(base)} items")
            br = broken_by(base, cell["snapkv@r0.75"])
            print(f"    broken by w64 (baseline right -> w64 wrong): {len(br)}")
            enrichment("V<1 enrichment among broken", vlt1, br, list(base))
            sl_wh = wh - c_en
            n_v1 = sum(1 for i in base if qlens[qid_of[i]] <= sl_wh)
            print(f"    V=1 at w-hat={wh}: {n_v1}/{len(base)} items "
                  f"(prereg predicts >=90%)")

        # ---------------- B4: instruction-first at depth ----------------
        F, fm = load("if_depth.db", scorer)
        te = F["te"]
        base = te["baseline"]
        print(f"\n== B4 if_depth.db  te instr-first  n={len(base)}  "
              f"baseline acc={acc(base):.1f}")
        ci_row("te IF w64 vs IF baseline", base, te["snapkv@r0.75"])
        print("    (reference: w-hat residual on full pool, depth.db: "
              "-5.7 [-7.8, -3.1])")
        br = broken_by(base, te["snapkv@r0.75"])
        print(f"    item audit — broken n={len(br)} vs pool n={len(base)}:")
        for pos in ("front", "middle", "back"):
            enrichment(f"gold position = {pos}",
                       lambda i, p=pos: fm[i]["position"] == p, br, list(base))
        qid_of = {i: fm[i]["qid"] for i in base}
        qlens = question_lengths("te", set(qid_of.values()))
        qs = sorted(qlens[qid_of[i]] for i in base)
        med = qs[len(qs) // 2]
        d9 = qs[int(0.9 * len(qs))]
        enrichment(f"|Q| > median ({med})",
                   lambda i: qlens[qid_of[i]] > med, br, list(base))
        enrichment(f"|Q| > 90th pct ({d9})",
                   lambda i: qlens[qid_of[i]] > d9, br, list(base))

        # ---------------- B3: th/sw at their own w-hat ----------------
        T, _ = load("thsw.db", scorer)
        for lang, wh, camp in (("th", 91, 85.0), ("sw", 67, 56.0)):
            cell = T[lang]
            base = cell["baseline"]
            b_acc = acc(base)
            drift = b_acc - camp
            print(f"\n== B3 thsw.db  {lang}  n={len(base)}  baseline "
                  f"acc={b_acc:.1f} (campaign {camp:.0f}, drift {drift:+.1f})")
            d, lo, hi, _ = ci_row(f"{lang} w{wh} (w-hat) vs baseline (GATE)",
                                  base, cell[f"snapkv@r0.75:w{wh}"])
            print(f"    gate |d|<=3pp: {'MET' if abs(d) <= 3 else 'MISSED'}")
            ci_row(f"{lang} w64 (default) vs baseline", base,
                   cell["snapkv@r0.75"])


if __name__ == "__main__":
    main()
