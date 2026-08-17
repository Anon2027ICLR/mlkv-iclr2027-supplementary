#!/usr/bin/env python3
"""Figure 2: the identification triptych.

(a) sweep w across five languages   [cliff_multi-final.db]
(b) sweep the English tail          [cliff_en-final.db]
(c) sweep the slack on Telugu       [v_trace.db]

R2 only, recomputed from raw outputs; paired within each store.
  UV_NO_SYNC=1 uv run python scripts/iclr_fig_triptych.py
"""
from __future__ import annotations

import ast
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "iclr2027" / "figs"
OUT.mkdir(parents=True, exist_ok=True)

C = {"en": 25, "th": 45, "sw": 47, "bn": 107, "te": 167}
PAD_C = {"48": 57, "64": 73, "96": 105, "128": 137}  # measure_c_schema.py, prose tail
COL = {"en": "#1c2430", "th": "#5a6570", "sw": "#8a93a0",
       "bn": "#0c6a86", "te": "#a1332c"}
PAD_COL = {"48": "#8a93a0", "64": "#5a6570", "96": "#0c6a86", "128": "#a1332c"}

mpl.rcParams.update({
    "font.family": "serif", "font.size": 7.5,
    "axes.linewidth": 0.6, "axes.titlesize": 7,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "pdf.fonttype": 42,
})


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


def load(db, key=lambda r: r[0]):
    """-> lang -> config -> key -> bool"""
    con = sqlite3.connect(f"file:{ROOT / 'results' / db}?mode=ro", uri=True)
    out = defaultdict(lambda: defaultdict(dict))
    for iid, lang, cfg, o, g in con.execute(
        "SELECT item_id, lang, config, output, answer_gold FROM generations"
    ):
        out[lang][cfg][key((iid, lang))] = bool(containment_match_lenient(o or "", golds(g), lang))
    con.close()
    return out


def delta(base, comp):
    common = set(base) & set(comp)
    return 100.0 * sum(comp[i] - base[i] for i in common) / len(common)


def acc(m):
    return 100.0 * sum(m.values()) / len(m)


fig, axes = plt.subplots(1, 3, figsize=(5.5, 1.95))

# ---- (a) five languages ---------------------------------------------------
ax = axes[0]
S = load("cliff_multi-final.db")
ws = [32, 56, 88, 120, 176]
for lang in ["en", "th", "sw", "bn", "te"]:
    base = S[lang]["baseline"]
    ys = [delta(base, S[lang][f"snapkv@r0.75:w{w}"]) for w in ws]
    ax.plot(ws, ys, "-o", color=COL[lang], ms=2.6, lw=1.0, label=lang)
    ax.axvline(C[lang], color=COL[lang], ls=":", lw=0.6, alpha=0.75)
ax.axhline(0, color="#b4c0c9", lw=0.6)
ax.set_title("(a) sweep $w$: 5 languages")
ax.set_xlabel("window $w$ (tokens)")
ax.set_ylabel(r"$\Delta$pp vs. baseline")
ax.set_xticks(ws)
ax.set_ylim(-24, 7)
ax.legend(frameon=False, ncol=5, loc="lower center", fontsize=5.8,
          handlelength=0.9, columnspacing=0.6, handletextpad=0.3,
          borderpad=0.1)

# ---- (b) English pads -----------------------------------------------------
ax = axes[1]
con = sqlite3.connect(f"file:{ROOT / 'results' / 'cliff_en-final.db'}?mode=ro", uri=True)
by_pad = defaultdict(lambda: defaultdict(dict))
for iid, cfg, o, g in con.execute(
    "SELECT item_id, config, output, answer_gold FROM generations"
):
    pad = re.search(r"PAD(\d+)", iid).group(1)
    by_pad[pad][cfg][iid] = bool(containment_match_lenient(o or "", golds(g), "en"))
con.close()
ws_b = [32, 56, 80, 104, 144]
for pad in ["48", "64", "96", "128"]:
    ys = [acc(by_pad[pad][f"snapkv@r0.75:w{w}"]) for w in ws_b]
    ax.plot(ws_b, ys, "-o", color=PAD_COL[pad], ms=2.6, lw=1.0,
            label=f"$c{{=}}{PAD_C[pad]}$")
    ax.axvline(PAD_C[pad], color=PAD_COL[pad], ls=":", lw=0.6, alpha=0.75)
ax.set_title("(b) sweep the tail: English")
ax.set_xlabel("window $w$ (tokens)")
ax.set_ylabel("accuracy (\\%)")
ax.set_xticks(ws_b)
ax.set_ylim(74, 97)
ax.legend(frameon=False, ncol=1, loc="lower right", fontsize=5.8,
          handlelength=1.2, labelspacing=0.25, handletextpad=0.4)

# ---- (c) Telugu dose ladder ----------------------------------------------
ax = axes[2]
V = load("v_trace.db")
c_te = C["te"]
offs = [4, 16, 32, 48, 80]
base = V["te"]["baseline"]
ys = [delta(base, V["te"][f"snapkv@r0.75:w{c_te + o}"]) for o in offs]
medV = [0.08, 0.31, 0.62, 0.92, 1.00]  # medians from scripts/v_trace_bins.py
ax.plot(offs, ys, "-o", color=COL["te"], ms=2.8, lw=1.1)
ax.axhline(0, color="#b4c0c9", lw=0.6)
label_off = [(7, 3), (0, 5), (0, 5), (0, -10), (-8, 4)]
for x, y, v, off in zip(offs, ys, medV, label_off):
    ax.annotate(f"{v:.2f}", (x, y), textcoords="offset points",
                xytext=off, fontsize=6.0, color="#1c2430", ha="center")
ax.set_title("(c) sweep the slack: Telugu")
ax.set_xlabel("slack $w-c$ (tokens)")
ax.set_ylabel(r"$\Delta$pp vs. baseline")
ax.set_xticks(offs)
ax.set_ylim(-24, 7)

fig.tight_layout(pad=0.4, w_pad=1.0)
fig.savefig(OUT / "f2_triptych.pdf", bbox_inches="tight", pad_inches=0.01)
plt.close()
print("wrote", OUT / "f2_triptych.pdf")
print("(a) te/bn:", [round(delta(S['te']['baseline'], S['te'][f'snapkv@r0.75:w{w}']), 1) for w in ws])
print("(c) te   :", [round(y, 1) for y in ys])
