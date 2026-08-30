#!/usr/bin/env python3
"""Paper figures, generated from the result stores. Never hand-edit the PDFs.

  figs/f1_layout.pdf    the instruction-last layout, drawn to token scale
  figs/f2_triptych.pdf  three sweeps of the same mechanism

  UV_NO_SYNC=1 uv run --with matplotlib python scripts/paper_figures.py

Design notes, so a later edit does not undo them:

* Colour does identity work only where identity matters. In panel (a) the
  story is that two languages break and three do not, so Bengali and Telugu
  take the two accent hues and the rest are context grey (the "emphasis"
  pattern). Bengali violet / Telugu orange clear the colour-vision checks
  with a wide margin (OKLab dE 29.5 under protanopia, 37.6 unsimulated).
* Instruction pad length is *ordered*, so the pad conditions take a
  single-hue ramp, light to dark, not four unrelated hues.
* Identity is never colour alone: every series also carries a distinct
  marker, so the figure survives greyscale printing and colour blindness.
* Panels (b) and (c) share an x-axis (slack, w - c) and its scale, which is
  what makes "English saturates a few tokens past c, Telugu needs eighty"
  legible as a distance on the page.
* Median visibility is labelled only at the two endpoints of (c); the full
  column is in the dose table. A number on every point is noise.
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
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "iclr2027" / "figs"
OUT.mkdir(parents=True, exist_ok=True)

# --- palette (validated; see the module docstring) --------------------------
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, RULE = "#e1e0d9", "#c3c2b7"
BN, TE = "#4a3aa7", "#eb6834"
QUESTION = "#2a78d6"
PAD_RAMP = ["#86b6ef", "#5598e7", "#256abf", "#104281"]

C = {"en": 25, "th": 45, "sw": 47, "bn": 107, "te": 167}
PAD_C = {"48": 57, "64": 73, "96": 105, "128": 137}  # measure_c_schema.py, prose tail
# median question length on the scored items (Qwen3-4B tokenizer)
Q_MED = {"en": 13, "bn": 47}

mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "STIX Two Text", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 7.5,
    "axes.linewidth": 0.5,
    "axes.edgecolor": RULE,
    "axes.labelcolor": INK_2,
    "axes.labelsize": 7,
    "axes.titlesize": 7.5,
    "axes.titlecolor": INK,
    "text.color": INK_2,
    "xtick.color": RULE, "ytick.color": RULE,
    "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2,
    "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "legend.fontsize": 6.3,
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


def load(db, key=None):
    con = sqlite3.connect(f"file:{ROOT / 'results' / db}?mode=ro", uri=True)
    out = defaultdict(lambda: defaultdict(dict))
    for iid, lang, cfg, o, g in con.execute(
        "SELECT item_id, lang, config, output, answer_gold FROM generations"
    ):
        out[key(iid) if key else lang][cfg][iid] = bool(
            containment_match_lenient(o or "", golds(g), lang))
    con.close()
    return out


def delta(base, comp):
    common = set(base) & set(comp)
    return 100.0 * sum(comp[i] - base[i] for i in common) / len(common)


def acc(m):
    return 100.0 * sum(m.values()) / len(m)


def tidy(ax, grid_axis="y"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, lw=0.5, zorder=0)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
def fig_layout():
    """Figure 1: where the window falls, to token scale."""
    S, W, XMIN = 5, 64, -262
    rows = [
        ("English",               C["en"], Q_MED["en"], "$V = 1$"),
        ("Bengali",               C["bn"], Q_MED["bn"], "$V = 0$"),
        ("English + JSON schema", 166,     Q_MED["en"], "$V = 0$"),
    ]
    fig, ax = plt.subplots(figsize=(5.5, 1.42))
    h = 0.32
    for i, (name, c, q, vlab) in enumerate(rows):
        y = len(rows) - 1 - i
        q0 = -(c + q)
        ax.add_patch(Rectangle((XMIN, y - h / 2), q0 - XMIN, h, fc=GRID, ec="none"))
        ax.add_patch(Rectangle((q0, y - h / 2), q, h, fc=QUESTION, ec="none"))
        ax.add_patch(Rectangle((-c, y - h / 2), c - S, h, fc=MUTED, ec="none"))
        ax.add_patch(Rectangle((-S, y - h / 2), S, h, fc=INK_2, ec="none"))
        ax.text(XMIN, y + 0.30, f"{name}   $c = {c}$", ha="left", va="bottom",
                fontsize=6.8, color=INK)
        ax.text(6, y, vlab, ha="left", va="center", fontsize=6.8, color=INK)

    ax.add_patch(Rectangle((-W, -0.52), W, 3.02, fc="#f4f2ec", ec=INK, lw=0.8,
                           zorder=0))
    ax.annotate("last $w = 64$ tokens: what the scorer sees",
                xy=(-W / 2, 2.50), xytext=(-W / 2, 2.74), ha="center",
                fontsize=6.8, color=INK,
                arrowprops=dict(arrowstyle="-", lw=0.5, color=INK))

    handles = [Rectangle((0, 0), 1, 1, fc=c, ec="none") for c in
               (GRID, QUESTION, MUTED, INK_2)]
    ax.legend(handles, ["passages (8k tokens, truncated)", "question",
                        "instruction", "chat suffix"],
              loc="lower center", bbox_to_anchor=(0.5, -0.66), ncol=4,
              frameon=False, handlelength=1.0, handleheight=0.8,
              columnspacing=1.3, handletextpad=0.4)

    ax.set_xlim(XMIN, 46)
    ax.set_ylim(-0.70, 2.98)
    ax.set_xticks([-256, -192, -128, -64, 0])
    ax.set_xticklabels(["256", "192", "128", "64", "0"])
    ax.set_xlabel("tokens before the end of the prompt", labelpad=2)
    ax.set_yticks([])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    fig.savefig(OUT / "f1_layout.pdf", bbox_inches="tight", pad_inches=0.01)
    plt.close()
    print("wrote", OUT / "f1_layout.pdf")


# ---------------------------------------------------------------------------
def fig_triptych():
    # Panel (b) carries the causal claim, so it gets twice the width of
    # (a) and (c); the figure height is unchanged.
    fig, axes = plt.subplots(1, 3, figsize=(5.5, 1.98),
                             gridspec_kw={"width_ratios": [1, 2, 1]})

    # (a) five languages against the window ---------------------------------
    ax = axes[0]
    S = load("cliff_multi-final.db")
    ws = [32, 56, 88, 120, 176]
    series = [("en", MUTED, "o", 0.9), ("th", MUTED, "s", 0.9),
              ("sw", MUTED, "^", 0.9), ("bn", BN, "D", 1.3), ("te", TE, "v", 1.3)]
    for lang, col, mk, lw in series:
        base = S[lang]["baseline"]
        ys = [delta(base, S[lang][f"snapkv@r0.75:w{w}"]) for w in ws]
        ax.plot(ws, ys, "-", marker=mk, color=col, ms=2.6, lw=lw, label=lang,
                mew=0, zorder=3 if col == MUTED else 4)
    ax.axhline(0, color=RULE, lw=0.6, zorder=1)
    for lang, col, *_ in series:
        ax.plot([C[lang]], [-24], marker="|", ms=4.5, mew=1.0, color=col,
                clip_on=False, zorder=5)
    ax.annotate("$c$", xy=(C["te"], -24), xytext=(C["te"] + 5, -23.2),
                fontsize=6.3, color=TE)
    tidy(ax)
    ax.set_title("(a) across languages")
    ax.set_xlabel("observation window $w$")
    ax.set_ylabel(r"$\Delta$pp vs. baseline")
    ax.set_xticks(ws)
    ax.set_ylim(-24, 9)
    ax.set_yticks([-20, -15, -10, -5, 0, 5])
    ax.legend(loc="upper center", ncol=5, frameon=False, handlelength=0.8,
              columnspacing=0.55, handletextpad=0.25, borderpad=0.1,
              bbox_to_anchor=(0.5, 1.02))

    # (b) English pads against the slack ------------------------------------
    ax = axes[1]
    P = load("cliff_en-final.db", key=lambda i: re.search(r"PAD(\d+)", i).group(1))
    ws_b = [32, 56, 80, 104, 144]
    for (pad, col, mk) in zip(["48", "64", "96", "128"], PAD_RAMP,
                              ["o", "s", "^", "D"]):
        xs = [w - PAD_C[pad] for w in ws_b]
        ys = [acc(P[pad][f"snapkv@r0.75:w{w}"]) for w in ws_b]
        ax.plot(xs, ys, "-", marker=mk, color=col, ms=2.6, lw=1.0, mew=0,
                label=pad, zorder=3)
    ax.axvline(0, color=RULE, lw=0.6, zorder=1)
    ax.text(4, 75.2, "$w = c$", fontsize=6.3, color=MUTED, ha="left")
    tidy(ax)
    ax.set_title("(b) English, four pads")
    ax.set_xlabel("slack $w - c$")
    ax.set_ylabel("accuracy (\\%)")
    ax.set_xlim(-112, 95)
    ax.set_ylim(74, 97)
    ax.set_yticks([75, 80, 85, 90, 95])
    leg = ax.legend(loc="upper left", ncol=2, frameon=False, handlelength=0.8,
                    columnspacing=0.55, handletextpad=0.25, borderpad=0.1,
                    title="pad (tokens)")
    leg.get_title().set_fontsize(6.0)
    leg.get_title().set_color(MUTED)

    # (c) Telugu against the slack ------------------------------------------
    ax = axes[2]
    V = load("v_trace.db")
    offs = [4, 16, 32, 48, 80]
    base = V["te"]["baseline"]
    ys = [delta(base, V["te"][f"snapkv@r0.75:w{C['te'] + o}"]) for o in offs]
    ax.plot(offs, ys, "-", marker="v", color=TE, ms=3.0, lw=1.3, mew=0, zorder=3)
    ax.axhline(0, color=RULE, lw=0.6, zorder=1)
    ax.axvline(0, color=RULE, lw=0.6, zorder=1)
    ax.annotate("median $V = 0.08$:\nfour visible tokens\nrecover nothing",
                xy=(offs[0], ys[0] + 0.6), xytext=(-104, -14.5),
                fontsize=6.3, color=INK_2, ha="left", va="top", linespacing=1.35,
                arrowprops=dict(arrowstyle="-", lw=0.4, color=MUTED,
                                shrinkA=2, shrinkB=2))
    ax.annotate("$V = 1$", xy=(offs[-1], ys[-1]), xytext=(offs[-1] - 6, 3.4),
                fontsize=6.3, color=INK_2, ha="right",
                arrowprops=dict(arrowstyle="-", lw=0.4, color=MUTED))
    tidy(ax)
    ax.set_title("(c) Telugu, five slacks")
    ax.set_xlabel("slack $w - c$")
    ax.set_ylabel(r"$\Delta$pp vs. baseline")
    ax.set_xlim(-112, 95)
    ax.set_ylim(-24, 9)
    ax.set_yticks([-20, -15, -10, -5, 0, 5])

    fig.tight_layout(pad=0.35, w_pad=1.1)
    fig.savefig(OUT / "f2_triptych.pdf", bbox_inches="tight", pad_inches=0.01)
    plt.close()
    print("wrote", OUT / "f2_triptych.pdf")

    # the collapse claim in panel (b), stated numerically for the caption
    below, above = [], []
    for pad in ["48", "64", "96", "128"]:
        for w in ws_b:
            a = acc(P[pad][f"snapkv@r0.75:w{w}"])
            (above if w > PAD_C[pad] else below).append(a)
    print(f"  panel (b): windows below c reach at most {max(below):.0f}%, "
          f"windows above c at least {min(above):.0f}%")


if __name__ == "__main__":
    fig_layout()
    fig_triptych()
