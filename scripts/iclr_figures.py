#!/usr/bin/env python3
"""F2/F3/F4 from locked result stores. R2 only."""
from __future__ import annotations

import ast
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "iclr2027" / "figs"
OUT.mkdir(parents=True, exist_ok=True)
C = {"en": 25, "th": 45, "sw": 47, "bn": 107, "te": 167}

mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "pdf.fonttype": 42,
})


def golds(s):
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


def r2(out, gold, lang):
    return bool(containment_match_lenient(out or "", golds(gold), lang))


def load(db):
    con = sqlite3.connect(f"file:{ROOT / 'results' / db}?mode=ro", uri=True)
    S = defaultdict(lambda: defaultdict(dict))
    for iid, lang, cfg, out, gold in con.execute(
        "SELECT item_id, lang, config, output, answer_gold FROM generations"
    ):
        S[lang][cfg][iid] = r2(out, gold, lang)
    return S


def acc(m):
    return 100.0 * sum(m.values()) / len(m) if m else float("nan")


def pair_d(a, b):
    common = set(a) & set(b)
    if not common:
        return float("nan")
    return 100.0 * (sum(b[i] for i in common) - sum(a[i] for i in common)) / len(common)


def fig2():
    S = load("cliff_multi-final.db")
    fig, ax = plt.subplots(figsize=(5.4, 2.6))
    ws = [32, 56, 88, 120, 176]
    colors = {"en": "#1c2430", "th": "#5a6570", "sw": "#8a93a0", "bn": "#0c6a86", "te": "#a1332c"}
    for lang in ["en", "th", "sw", "bn", "te"]:
        base = S[lang]["baseline"]
        ys = [pair_d(base, S[lang][f"snapkv@r0.75:w{w}"]) for w in ws]
        ax.plot(ws, ys, "-o", color=colors[lang], ms=3.5, lw=1.2, label=lang)
        ax.axvline(C[lang], color=colors[lang], ls=":", lw=0.7, alpha=0.8)
    ax.axhline(0, color="#b4c0c9", lw=0.6)
    ax.set_xlabel("observation window $w$ (tokens)")
    ax.set_ylabel(r"$\Delta$pp vs baseline")
    ax.set_xticks(ws)
    ax.legend(frameon=False, ncol=5, loc="lower right", fontsize=8)
    ax.set_ylim(-24, 6)
    fig.tight_layout()
    fig.savefig(OUT / "f2_cliff.pdf")
    plt.close()


def fig3():
    D = load("autowin-final.db")
    Q = load("autowin_q90.db")
    fig, ax = plt.subplots(figsize=(5.4, 2.5))
    langs = ["en", "bn", "te"]
    x = range(len(langs))
    w16 = {"en": 41, "bn": 123, "te": 183}
    wq = {"en": 43, "bn": 183, "te": 247}
    series = []
    for name, getter in [
        ("$w{=}64$", lambda L: pair_d(D[L]["baseline"], D[L]["snapkv@r0.75"])),
        ("$c{+}16$", lambda L: pair_d(D[L]["baseline"], D[L][f"snapkv@r0.75:w{w16[L]}"])),
        ("$c{+}Q_{90}$", lambda L: pair_d(D[L]["baseline"], Q[L][f"snapkv@r0.75:w{wq[L]}"])),
    ]:
        series.append((name, [getter(L) for L in langs]))
    width = 0.26
    cols = ["#a1332c", "#c4921a", "#0c6a86"]
    for i, ((name, ys), col) in enumerate(zip(series, cols)):
        xs = [xi + (i - 1) * width for xi in x]
        ax.bar(xs, ys, width=width, color=col, label=name, edgecolor="none")
    ax.axhline(0, color="#1c2430", lw=0.6)
    ax.set_xticks(list(x))
    ax.set_xticklabels(langs)
    ax.set_ylabel(r"$\Delta$pp vs baseline")
    ax.legend(frameon=False, fontsize=8)
    ax.set_ylim(-22, 6)
    fig.tight_layout()
    fig.savefig(OUT / "f3_autowin.pdf")
    plt.close()


def fig4():
    con = sqlite3.connect(f"file:{ROOT / 'results' / 'cliff_en-final.db'}?mode=ro", uri=True)
    by = defaultdict(lambda: defaultdict(dict))
    for iid, cfg, out, gold in con.execute(
        "SELECT item_id, config, output, answer_gold FROM generations"
    ):
        pad = iid.split("PAD")[1].split("-")[0]
        by[pad][cfg][iid] = r2(out, gold, "en")
    fig, ax = plt.subplots(figsize=(5.4, 2.5))
    ws = [32, 56, 80, 104, 144]
    cols = {"48": "#8a93a0", "64": "#5a6570", "96": "#0c6a86", "128": "#a1332c"}
    for pad in ["48", "64", "96", "128"]:
        ys = [acc(by[pad][f"snapkv@r0.75:w{w}"]) for w in ws]
        ax.plot(ws, ys, "-o", color=cols[pad], ms=3.5, lw=1.2, label=f"pad {pad}")
    ax.set_xlabel("observation window $w$ (tokens)")
    ax.set_ylabel("English R2 (%)")
    ax.set_xticks(ws)
    ax.set_ylim(74, 96)
    ax.legend(frameon=False, ncol=4, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "f4_pad.pdf")
    plt.close()


if __name__ == "__main__":
    fig2()
    fig3()
    fig4()
    print("wrote", list(OUT.glob("*.pdf")))
