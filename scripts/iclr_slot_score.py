#!/usr/bin/env python3
"""R2 readout of ICLR slot dbs (A/B/D/S). Never quotes stored correct."""
from __future__ import annotations

import ast
import math
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "results"

# Locked 2026-08-14 Qwen3-4B (I / c / AutoWindow w=c+16)
C = {"en": 25, "zh": 29, "es": 35, "vi": 39, "th": 45, "sw": 47, "bn": 107, "te": 167}
AW = {k: v + 16 for k, v in C.items()}


def mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def parse_golds(s: str | None) -> list[str]:
    if not s:
        return []
    s = s.strip()
    if s.startswith("["):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, list):
                return [str(x) for x in v]
        except Exception:
            pass
    return [s]


def score_row(output: str, gold: str, lang: str) -> bool:
    return bool(containment_match_lenient(output or "", parse_golds(gold), lang))


def load(db: str) -> list[sqlite3.Row]:
    conn = sqlite3.connect(f"file:{ROOT / db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = list(conn.execute(
        "SELECT item_id, lang, config, output, answer_gold FROM generations"
    ))
    conn.close()
    return rows


def maps(rows, key_fn=None):
    """lang -> config -> item_id -> bool. key_fn(row) overrides item_id."""
    out = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        kid = key_fn(r) if key_fn else r["item_id"]
        out[r["lang"]][r["config"]][kid] = score_row(r["output"], r["answer_gold"], r["lang"])
    return out


def pair(a: dict, b: dict) -> dict:
    common = sorted(set(a) & set(b))
    n = len(common)
    if n == 0:
        return {"n": 0}
    acc_a = sum(a[i] for i in common) / n
    acc_b = sum(b[i] for i in common) / n
    fixed = sum(1 for i in common if not a[i] and b[i])
    broken = sum(1 for i in common if a[i] and not b[i])
    return {
        "n": n,
        "acc_a": acc_a,
        "acc_b": acc_b,
        "d_pp": (acc_b - acc_a) * 100,
        "fixed": fixed,
        "broken": broken,
        "p": mcnemar_p(fixed, broken),
    }


def fmt(cmp: dict, label: str) -> str:
    if cmp.get("n", 0) == 0:
        return f"  {label:28}  n=0"
    return (
        f"  {label:28}  n={cmp['n']:3d}  "
        f"{cmp['acc_a']*100:5.1f} → {cmp['acc_b']*100:5.1f}  "
        f"Δ {cmp['d_pp']:+6.1f}pp  "
        f"fix/brk {cmp['fixed']}/{cmp['broken']}  p={cmp['p']:.3f}"
    )


def pad_of(item_id: str) -> str:
    m = re.search(r"(PAD|JSON)(\d+)", item_id)
    return m.group(2) if m else "?"


print("=" * 78)
print("ICLR slot R2 readout  ·  Grok 4.6  ·  containment_match_lenient")
print("Never stored `correct`. Paired on item_id (A/S: pad+item).")
print("=" * 78)

# ---------------------------------------------------------------------------
# D — AutoWindow
# ---------------------------------------------------------------------------
print("\n## D  AutoWindow   baseline vs default w=64 vs w=c+16")
print("Pred: bn/te damage at w=64 closes under AutoWindow; en |Δ|≤3pp vs baseline.\n")
D = maps(load("autowin-final.db"))
d_kill = False
for lang in ["en", "zh", "es", "vi", "th", "sw", "bn", "te"]:
    cfgs = D[lang]
    base = cfgs.get("baseline", {})
    default = cfgs.get("snapkv@r0.75", {})
    aw_name = f"snapkv@r0.75:w{AW[lang]}"
    aw = cfgs.get(aw_name, {})
    print(f"{lang}  c={C[lang]}  AutoWindow w={AW[lang]}")
    print(fmt(pair(base, default), "baseline → default64"))
    print(fmt(pair(base, aw), f"baseline → AW w={AW[lang]}"))
    print(fmt(pair(default, aw), "default64 → AW"))
    bd = pair(base, default)
    ba = pair(base, aw)
    if lang in ("bn", "te") and ba.get("n"):
        # close = AutoWindow back near baseline, and better than default
        if ba["d_pp"] <= -8 or (bd.get("d_pp", 0) <= -8 and ba["d_pp"] <= bd["d_pp"] + 3):
            d_kill = True
            print("  >> does NOT close vs baseline (kill-shaped)")
        elif ba["d_pp"] > -3 and (bd.get("d_pp", 0) <= -5):
            print("  >> closes (pred match)")
        elif abs(ba["d_pp"]) <= 3 and abs(bd.get("d_pp", 0)) <= 3:
            print("  >> no default damage to close")
    if lang == "en" and ba.get("n") and abs(ba["d_pp"]) > 3:
        print("  >> en not flat (|Δ|>3pp vs baseline)")

# ---------------------------------------------------------------------------
# B — cliff_multi
# ---------------------------------------------------------------------------
print("\n## B  cliff_multi   baseline vs w ∈ {32,56,88,120,176}")
print("Pred: BLIND if w<c, SAFE if w>c. Allowed: step at c+ε.\n")
B = maps(load("cliff_multi-final.db"))
for lang in ["en", "th", "sw", "bn", "te"]:
    print(f"{lang}  c={C[lang]}")
    base = B[lang].get("baseline", {})
    for w in (32, 56, 88, 120, 176):
        cfg = f"snapkv@r0.75:w{w}"
        tag = "BLIND" if w < C[lang] else "SAFE"
        print(fmt(pair(base, B[lang].get(cfg, {})), f"base → w{w} [{tag}]"))

# ---------------------------------------------------------------------------
# A — cliff_en pads
# ---------------------------------------------------------------------------
print("\n## A  cliff_en   English pads 48/64/96/128 × w")
print("Pred: pad 48 flat at w=64; pad≥64 damaged at w=64, recovers when w>c.")
print("No baseline in this db — acc and paired vs w144 (largest window).\n")


def a_key(r):
    return r["item_id"]


Arows = load("cliff_en-final.db")
# group by pad
by_pad = defaultdict(lambda: defaultdict(dict))
for r in Arows:
    pad = pad_of(r["item_id"])
    by_pad[pad][r["config"]][r["item_id"]] = score_row(r["output"], r["answer_gold"], "en")

for pad in ["48", "64", "96", "128"]:
    print(f"pad {pad}")
    cfgs = by_pad[pad]
    ref = cfgs.get("snapkv@r0.75:w144", {})
    for w in (32, 56, 80, 104, 144):
        cfg = f"snapkv@r0.75:w{w}"
        m = cfgs.get(cfg, {})
        acc = (sum(m.values()) / len(m) * 100) if m else float("nan")
        print(f"  acc w{w:3d}  {acc:5.1f}%   " + fmt(pair(m, ref), f"w{w} → w144").strip())

# ---------------------------------------------------------------------------
# S — schema
# ---------------------------------------------------------------------------
print("\n## S  schema tail   JSON 60/120/200 × {baseline, w64, AW w=41}")
print("Note: AutoWindow w is unpadded English (41), not schema-adjusted c.")
print("Pred: damage iff schema pushes question past w; AW removes it.\n")
Srows = load("schema-final.db")
by_j = defaultdict(lambda: defaultdict(dict))
for r in Srows:
    pad = pad_of(r["item_id"])
    by_j[pad][r["config"]][r["item_id"]] = score_row(r["output"], r["answer_gold"], "en")

for pad in ["60", "120", "200"]:
    print(f"JSON pad {pad}")
    cfgs = by_j[pad]
    base = cfgs.get("baseline", {})
    d64 = cfgs.get("snapkv@r0.75", {})
    aw = cfgs.get("snapkv@r0.75:w41", {})
    print(fmt(pair(base, d64), "baseline → default64"))
    print(fmt(pair(base, aw), "baseline → AW w=41"))
    print(fmt(pair(d64, aw), "default64 → AW w=41"))

print("\n## Gate")
print("D kill-shaped (bn/te not closed):", d_kill)
print("done")
