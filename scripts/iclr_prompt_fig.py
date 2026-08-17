#!/usr/bin/env python3
"""Appendix figure: frozen qa_instruction strings (en / bn / te)."""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT = Path(__file__).resolve().parents[1] / "paper" / "iclr2027" / "figs"
OUT.mkdir(parents=True, exist_ok=True)

EN = "Answer the question using only the passages above. End your reply with '#### <exact answer span>'."
BN = "শুধুমাত্র উপরের অনুচ্ছেদগুলি ব্যবহার করে প্রশ্নের উত্তর দাও। উত্তরের শেষে লেখো '#### <সঠিক উত্তরাংশ>'।"
TE = "పై పేరాగ్రాఫ్‌లను మాత్రమే ఉపయోగించి ప్రశ్నకు సమాధానం ఇవ్వండి. సమాధానం చివర '#### <ఖచ్చితమైన సమాధాన భాగం>' రాయండి."

def pick(*names):
    avail = {f.name: f.fname for f in font_manager.fontManager.ttflist}
    for n in names:
        if n in avail:
            return n
    return "DejaVu Sans"

latin = pick("Times New Roman", "Nimbus Roman", "DejaVu Serif")
bn_f = pick("Kohinoor Bangla", "Bangla MN", "Arial Unicode MS")
te_f = pick("Kohinoor Telugu", "Telugu MN", "Arial Unicode MS")

fig, axes = plt.subplots(3, 1, figsize=(5.5, 3.6))
rows = [
    (axes[0], "en  $I{=}20$ on Qwen3-4B", EN, latin),
    (axes[1], "bn  $I{=}102$ on Qwen3-4B  (same meaning)", BN, bn_f),
    (axes[2], "te  $I{=}162$ on Qwen3-4B  (same meaning)", TE, te_f),
]
for ax, title, text, font in rows:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=9, pad=4, fontname=latin)
    ax.text(0.0, 0.55, text, fontsize=8.5, va="center", ha="left",
            fontname=font, wrap=True)
    ax.add_patch(plt.Rectangle((0, 0.15), 1, 0.7, fill=False, lw=0.5,
                               edgecolor="#888888", transform=ax.transAxes))

fig.tight_layout()
fig.savefig(OUT / "app_instructions.pdf")
print("wrote", OUT / "app_instructions.pdf", "fonts", latin, bn_f, te_f)
