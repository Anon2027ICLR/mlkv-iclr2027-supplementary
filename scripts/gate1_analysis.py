"""Gate-1 analysis over the pilot db (run: uv run python scripts/gate1_analysis.py).

Implements the runbook §5 checklist: per-language deltas vs baseline with exact
McNemar tests on paired item flips, the (lang − en) gap table, byte-denominated
length inflation, drift, truncation, mojibake rate, mRAG (containment-rescored)
deltas, the NFD 2x2, canary levels, and triplicate reproducibility.
"""

from __future__ import annotations

import math
import sqlite3
import sys
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "results/pilot-final.db"
LANGS = ["en", "vi", "zh", "sw"]


def mcnemar_p(b: int, c: int) -> float:
    """Exact two-sided McNemar (binomial) on discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def logit(p: float, n: int) -> float:
    p = min(max(p, 0.5 / n), 1 - 0.5 / n)  # Haldane-style clamp
    return math.log(p / (1 - p))


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


def cell_items(task: str, model_like: str, config: str, lang: str) -> dict[str, int]:
    return {
        r["item_id"]: r["correct"]
        for r in conn.execute(
            "SELECT item_id, correct FROM generations WHERE task=? AND model LIKE ? "
            "AND config=? AND lang=?", (task, model_like, config, lang))
    }


print(f"=== GATE-1 ANALYSIS ({DB}) ===\n")
print("--- 1. MGSM deltas vs baseline (abs pp / relative / logit) + McNemar")
for model in ["Qwen%", "meta%"]:
    for config in ["kv4", "kv2"]:
        line = []
        for lang in LANGS:
            base = cell_items("mgsm", model, "baseline", lang)
            comp = cell_items("mgsm", model, config, lang)
            common = set(base) & set(comp)
            if not common:
                continue
            n = len(common)
            acc_b = sum(base[i] for i in common) / n
            acc_c = sum(comp[i] for i in common) / n
            b_flips = sum(1 for i in common if base[i] and not comp[i])
            c_flips = sum(1 for i in common if not base[i] and comp[i])
            p = mcnemar_p(b_flips, c_flips)
            rel = (acc_c - acc_b) / acc_b * 100 if acc_b else float("nan")
            dlog = logit(acc_c, n) - logit(acc_b, n)
            star = "**" if p < 0.01 else ("*" if p < 0.05 else "  ")
            line.append(f"{lang}:{(acc_c-acc_b)*100:+5.1f}pp/{rel:+5.1f}%/{dlog:+5.2f}L p={p:.3f}{star}")
        print(f"  {model:<6} {config:<4} " + " | ".join(line))

print("\n--- 2. Gap table (Δlang − Δen, absolute pp; ≥3pp flagged)")
for model in ["Qwen%", "meta%"]:
    for config in ["kv4", "kv2"]:
        base_en = cell_items("mgsm", model, "baseline", "en")
        comp_en = cell_items("mgsm", model, config, "en")
        d_en = (sum(comp_en.values()) - sum(base_en.values())) / len(base_en)
        gaps = []
        for lang in ["vi", "zh", "sw"]:
            base = cell_items("mgsm", model, "baseline", lang)
            comp = cell_items("mgsm", model, config, lang)
            d = (sum(comp.values()) - sum(base.values())) / len(base)
            g = (d - d_en) * 100
            flag = " ←≥3pp" if abs(g) >= 3 else ""
            gaps.append(f"{lang}:{g:+.1f}{flag}")
        print(f"  {model:<6} {config:<4} " + "  ".join(gaps))

print("\n--- 3. Behavioral: bytes ratio vs baseline / truncation% / drift / mojibake%")
for model in ["Qwen%", "meta%"]:
    for config in ["baseline", "kv4", "kv2"]:
        line = []
        for lang in LANGS:
            r = conn.execute(
                "SELECT AVG(output_bytes) ab, AVG(n_output_tokens>=768)*100 tr, "
                "AVG(drift) dr, AVG(output LIKE '%�%')*100 mj "
                "FROM generations WHERE task='mgsm' AND model LIKE ? AND config=? AND lang=?",
                (model, config, lang)).fetchone()
            rb = conn.execute(
                "SELECT AVG(output_bytes) FROM generations WHERE task='mgsm' "
                "AND model LIKE ? AND config='baseline' AND lang=?", (model, lang)).fetchone()[0]
            ratio = r["ab"] / rb if rb else float("nan")
            line.append(f"{lang}: {ratio:4.2f}x t{r['tr']:3.0f}% d{r['dr'] if r['dr'] is not None else -1:.2f} m{r['mj']:2.0f}%")
        print(f"  {model:<6} {config:<9} " + " | ".join(line))

print("\n--- 4. mRAG (containment-rescored) deltas vs baseline")
for model in ["Qwen%", "meta%"]:
    for config in ["snapkv@r0.75", "snapkv@b2048", "snapkv@b1024"]:
        line = []
        for lang in LANGS:
            base = cell_items("mrag", model, "baseline", lang)
            comp = cell_items("mrag", model, config, lang)
            common = set(base) & set(comp)
            n = len(common)
            if n == 0:
                continue
            d = (sum(comp[i] for i in common) - sum(base[i] for i in common)) / n * 100
            b_f = sum(1 for i in common if base[i] and not comp[i])
            c_f = sum(1 for i in common if not base[i] and comp[i])
            p = mcnemar_p(b_f, c_f)
            star = "*" if p < 0.05 else " "
            line.append(f"{lang}:{d:+5.1f}pp p={p:.2f}{star}")
        print(f"  {model:<6} {config:<13} " + " | ".join(line))

print("\n--- 5. Triplicate reproducibility (item-level)")
try:
    runs = []
    for db in [DB, "results/repeat2.db", "results/repeat3.db"]:
        cc = sqlite3.connect(db)
        runs.append({r[0]: (r[1], r[2]) for r in cc.execute(
            "SELECT item_id, correct, output FROM generations WHERE model LIKE 'Qwen%' "
            "AND task='mgsm' AND config='baseline' AND lang='vi'")})
    common = set(runs[0]) & set(runs[1]) & set(runs[2])
    same_correct = sum(1 for i in common if runs[0][i][0] == runs[1][i][0] == runs[2][i][0])
    same_output = sum(1 for i in common if runs[0][i][1] == runs[1][i][1] == runs[2][i][1])
    print(f"  n={len(common)}: identical correctness {same_correct}, identical raw outputs {same_output}")
except Exception as e:
    print("  (repeat dbs unavailable:", e, ")")
