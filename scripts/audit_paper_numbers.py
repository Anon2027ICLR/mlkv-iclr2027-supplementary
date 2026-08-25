#!/usr/bin/env python3
"""Recompute every table cell in the paper from the generation stores and
compare it against the value currently written in the TeX source.

The expected values below are transcribed from
paper/iclr2027/iclr2027_conference.tex. Run before every submission:

  UV_NO_SYNC=1 uv run python scripts/audit_paper_numbers.py

Any MISMATCH is a bug in the paper, in this file, or in the data — stop
and find out which before shipping.
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
from mlkv.qa_metrics import (  # noqa: E402
    containment_match_lenient,
    containment_match_marker_only,
)

RES = ROOT / "results"
FAILS: list[str] = []
CHECKS = [0]


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
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


def load(db, key=None, scorer=containment_match_lenient):
    con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
    out = defaultdict(lambda: defaultdict(dict))
    for iid, lang, cfg, o, g in con.execute(
        "SELECT item_id, lang, config, output, answer_gold FROM generations"
    ):
        k = key(iid) if key else lang
        out[k][cfg][iid] = bool(scorer(o or "", golds(g), lang))
    con.close()
    return out


def cmp_pair(base, comp):
    common = sorted(set(base) & set(comp))
    n = len(common)
    fixed = sum(1 for i in common if not base[i] and comp[i])
    broken = sum(1 for i in common if base[i] and not comp[i])
    return dict(
        n=n,
        base=round(100 * sum(base[i] for i in common) / n),
        acc=round(100 * sum(comp[i] for i in common) / n),
        d=round(100 * (sum(comp[i] for i in common) - sum(base[i] for i in common)) / n),
        star=mcnemar_p(fixed, broken) < 0.05,
        fb=(fixed, broken),
    )


def check(label, got, want):
    CHECKS[0] += 1
    if got != want:
        FAILS.append(f"{label}: TeX says {want!r}, data says {got!r}")
        print(f"  MISMATCH  {label}: TeX {want!r} vs data {got!r}")


# --------------------------------------------------------------------------
print("## Table 1 (window sweep) — tab:cliff")
S = load("cliff_multi-final.db")
TEX_CLIFF = {  # lang: (base, [(delta, star) per w in 32,56,88,120,176])
    "en": (93, [(2, False), (1, False), (1, False), (-1, False), (1, False)]),
    "th": (85, [(-6, False), (-4, False), (0, False), (-2, False), (-3, False)]),
    "sw": (56, [(-7, True), (-4, False), (-2, False), (-4, False), (-3, False)]),
    "bn": (73, [(-13, True), (-15, True), (-21, True), (-8, False), (-3, False)]),
    "te": (56, [(-19, True), (-21, True), (-18, True), (-14, True), (-13, True)]),
}
# The scope paragraph claims an English-validated benchmark cannot tell the
# two shipped constants apart. That is a direct paired comparison the tables
# never make: w=32 lives in this store and w=64 (the implicit default) in the
# AutoWindow store. Both are English, same items, same stack, so the
# comparison is legal -- but it has to be computed, not inferred from two
# rows that each sit beside a different baseline.
_D_EN = load("autowin-final.db")["en"]
check("scope en w32-vs-w64 delta",
      cmp_pair(S["en"]["snapkv@r0.75:w32"], _D_EN["snapkv@r0.75"])["d"], -2)
check("scope en w32-vs-w64 not significant",
      cmp_pair(S["en"]["snapkv@r0.75:w32"], _D_EN["snapkv@r0.75"])["star"], False)
# and the two stores must agree on the English baseline they share, or the
# comparison above is crossing an item boundary rather than a window one
check("scope en baselines agree across the two stores",
      cmp_pair(S["en"]["baseline"], _D_EN["baseline"])["fb"], (0, 0))

for lang, (base_tex, cells) in TEX_CLIFF.items():
    base = S[lang]["baseline"]
    check(f"cliff {lang} baseline", round(100 * sum(base.values()) / len(base)), base_tex)
    for w, (d_tex, star_tex) in zip((32, 56, 88, 120, 176), cells):
        r = cmp_pair(base, S[lang][f"snapkv@r0.75:w{w}"])
        check(f"cliff {lang} w{w} delta", r["d"], d_tex)
        check(f"cliff {lang} w{w} star", r["star"], star_tex)

# --------------------------------------------------------------------------
print("## Table 2 (dose ladder) — tab:dose")
V = load("v_trace.db")
TEX_DOSE = [  # w, acc, delta, fixed/broken
    (171, 38, -18, (5, 23)), (183, 50, -6, (5, 11)), (199, 52, -4, (4, 8)),
    (215, 52, -4, (6, 10)), (247, 56, 0, (6, 6)),
]
base_te = V["te"]["baseline"]
check("dose te baseline", round(100 * sum(base_te.values()) / len(base_te)), 56)
for w, acc_tex, d_tex, fb_tex in TEX_DOSE:
    r = cmp_pair(base_te, V["te"][f"snapkv@r0.75:w{w}"])
    check(f"dose te w{w} acc", r["acc"], acc_tex)
    check(f"dose te w{w} delta", r["d"], d_tex)
    check(f"dose te w{w} fixed/broken", r["fb"], fb_tex)

# The Bengali block of the same table, run to completion on its own grid.
VB = load("v_trace_bn.db")
TEX_DOSE_BN = [
    (111, 56, -17, (3, 20), True), (123, 66, -7, (5, 12), False),
    (139, 70, -3, (4, 7), False), (155, 68, -5, (3, 8), False),
    (183, 71, -2, (6, 8), False),
]
base_bn = VB["bn"]["baseline"]
check("dose bn baseline", round(100 * sum(base_bn.values()) / len(base_bn)), 73)
for w, acc_tex, d_tex, fb_tex, star_tex in TEX_DOSE_BN:
    r = cmp_pair(base_bn, VB["bn"][f"snapkv@r0.75:w{w}"])
    check(f"dose bn w{w} acc", r["acc"], acc_tex)
    check(f"dose bn w{w} delta", r["d"], d_tex)
    check(f"dose bn w{w} fixed/broken", r["fb"], fb_tex)
    check(f"dose bn w{w} star", r["star"], star_tex)
# The completed block supersedes a run that stopped on its third rung; the
# appendix quotes how many generations the two runs share.
shared = sum(
    1
    for cfg in set(V["bn"]) & set(VB["bn"])
    for iid in set(V["bn"][cfg]) & set(VB["bn"][cfg])
)
check("dose bn generations shared with the earlier run", shared, 343)

# --------------------------------------------------------------------------
print("## Table 3A (AutoWindow, languages) — tab:aw")
D = load("autowin-final.db")
Q = load("autowin_q90.db")
TEX_AWA = {  # lang: (base, (w64_acc, d, star), (c16_acc, d), (q90_acc, d), w_hat)
    "en": (93, (93, 0, False), (94, 1), (95, 2), 43),
    "bn": (73, (57, -16, True), (66, -7), (71, -2), 183),
    "te": (56, (37, -19, True), (50, -6), (56, 0), 247),
}
C16 = {"en": 41, "bn": 123, "te": 183}
for lang, (b_tex, w64, c16, q90, what) in TEX_AWA.items():
    base = D[lang]["baseline"]
    check(f"aw {lang} baseline", round(100 * sum(base.values()) / len(base)), b_tex)
    r = cmp_pair(base, D[lang]["snapkv@r0.75"])
    check(f"aw {lang} w64 acc", r["acc"], w64[0])
    check(f"aw {lang} w64 delta", r["d"], w64[1])
    check(f"aw {lang} w64 star", r["star"], w64[2])
    r = cmp_pair(base, D[lang][f"snapkv@r0.75:w{C16[lang]}"])
    check(f"aw {lang} c+16 acc", r["acc"], c16[0])
    check(f"aw {lang} c+16 delta", r["d"], c16[1])
    r = cmp_pair(base, Q[lang][f"snapkv@r0.75:w{what}"])
    check(f"aw {lang} q90 acc", r["acc"], q90[0])
    check(f"aw {lang} q90 delta", r["d"], q90[1])

# main-text claims: gains vs the default window
for lang, want_d, want_fb in [("bn", 14, (16, 2)), ("te", 19, (21, 2))]:
    r = cmp_pair(D[lang]["snapkv@r0.75"], Q[lang][f"snapkv@r0.75:w{TEX_AWA[lang][4]}"])
    check(f"aw {lang} q90-vs-w64 delta", r["d"], want_d)
    check(f"aw {lang} q90-vs-w64 fixed/broken", r["fb"], want_fb)

# --------------------------------------------------------------------------
print("## Table 3B (AutoWindow, schema tails) — tab:aw")
SF = load("schema_fix.db", key=lambda i: re.search(r"JSON(\d+)", i).group(1))
TEX_AWB = {  # pad: (base, (w64_acc, d, star), (hat_acc, d), hat_w, (fixed,broken) vs w64)
    "60": (94, (88, -6, False), (96, 2), 90, (8, 0)),
    "120": (95, (89, -6, True), (96, 1), 184, (7, 0)),
    "200": (94, (89, -5, False), (96, 2), 231, (7, 0)),
}
for pad, (b_tex, w64, hat, hw, fb_tex) in TEX_AWB.items():
    base = SF[pad]["baseline"]
    check(f"schema {pad} baseline", round(100 * sum(base.values()) / len(base)), b_tex)
    r = cmp_pair(base, SF[pad]["snapkv@r0.75"])
    check(f"schema {pad} w64 acc", r["acc"], w64[0])
    check(f"schema {pad} w64 delta", r["d"], w64[1])
    check(f"schema {pad} w64 star", r["star"], w64[2])
    r = cmp_pair(base, SF[pad][f"snapkv@r0.75:w{hw}"])
    check(f"schema {pad} hat acc", r["acc"], hat[0])
    check(f"schema {pad} hat delta", r["d"], hat[1])
    r = cmp_pair(SF[pad]["snapkv@r0.75"], SF[pad][f"snapkv@r0.75:w{hw}"])
    check(f"schema {pad} hat-vs-w64 fixed/broken", r["fb"], fb_tex)

# --------------------------------------------------------------------------
print("## Appendix: c+16 eight-language grid — tab:aw16")
TEX_AW16 = {
    "en": (93, 93, 94), "zh": (83, 83, 85), "es": (88, 86, 88), "vi": (83, 78, 81),
    "th": (85, 85, 84), "sw": (56, 53, 56), "bn": (73, 57, 66), "te": (56, 37, 50),
}
C16_ALL = {"en": 41, "zh": 45, "es": 51, "vi": 55, "th": 61, "sw": 63, "bn": 123, "te": 183}
for lang, (b_tex, w64_tex, c16_tex) in TEX_AW16.items():
    base = D[lang]["baseline"]
    check(f"aw16 {lang} base", round(100 * sum(base.values()) / len(base)), b_tex)
    check(f"aw16 {lang} w64", cmp_pair(base, D[lang]["snapkv@r0.75"])["acc"], w64_tex)
    check(f"aw16 {lang} c+16",
          cmp_pair(base, D[lang][f"snapkv@r0.75:w{C16_ALL[lang]}"])["acc"], c16_tex)

# --------------------------------------------------------------------------
print("## Appendix: English pad grid — tab:padgrid")
P = load("cliff_en-final.db", key=lambda i: re.search(r"PAD(\d+)", i).group(1))
TEX_PAD = {
    "48": [81, 87, 92, 92, 92], "64": [86, 90, 94, 93, 93],
    "96": [82, 90, 89, 90, 93], "128": [78, 85, 89, 89, 91],
}
for pad, accs in TEX_PAD.items():
    for w, a_tex in zip((32, 56, 80, 104, 144), accs):
        m = P[pad][f"snapkv@r0.75:w{w}"]
        check(f"pad {pad} w{w}", round(100 * sum(m.values()) / len(m)), a_tex)

# --------------------------------------------------------------------------
print("## Appendix: Gemma sweep — tab:gemmasweep")
G = load("cliff_gemma.db")
TEX_GEM = {
    "en": (75, [(2, False), (1, False), (3, False), (4, False), (3, False)]),
    "bn": (62, [(-13, True), (-10, True), (-9, True), (-5, False), (-5, False)]),
    "te": (37, [(-3, False), (-4, False), (-3, False), (-1, False), (-3, False)]),
}
for lang, (b_tex, cells) in TEX_GEM.items():
    base = G[lang]["baseline"]
    check(f"gemma {lang} base", round(100 * sum(base.values()) / len(base)), b_tex)
    for w, (d_tex, star_tex) in zip((16, 24, 32, 48, 64), cells):
        r = cmp_pair(base, G[lang][f"snapkv@r0.75:w{w}"])
        check(f"gemma {lang} w{w} delta", r["d"], d_tex)
        check(f"gemma {lang} w{w} star", r["star"], star_tex)

# --------------------------------------------------------------------------
print("## Appendix: Gemma AutoWindow arm")
GQ = load("gemma_q90.db")
TEX_GQ = {"en": (75, 78, 78, 45), "bn": (62, 57, 56, 50), "te": (37, 34, 34, 64)}
for lang, (b_tex, w64_tex, hat_tex, hw) in TEX_GQ.items():
    base = GQ[lang]["baseline"]
    check(f"gemmaq {lang} base", round(100 * sum(base.values()) / len(base)), b_tex)
    check(f"gemmaq {lang} w64", cmp_pair(base, GQ[lang]["snapkv@r0.75"])["acc"], w64_tex)
    check(f"gemmaq {lang} hat",
          cmp_pair(base, GQ[lang][f"snapkv@r0.75:w{hw}"])["acc"], hat_tex)

# --------------------------------------------------------------------------
print("## Appendix: 8B cells — tab:8brobust and app:8b")
E = load("autowin_8b.db")
TEX_8B = {"en": (96, 97, 96, 43), "bn": (81, 64, 73, 183)}
for lang, (b_tex, w64_tex, hat_tex, hw) in TEX_8B.items():
    base = E[lang]["baseline"]
    check(f"8b {lang} base", round(100 * sum(base.values()) / len(base)), b_tex)
    r64 = cmp_pair(base, E[lang]["snapkv@r0.75"])
    check(f"8b {lang} w64", r64["acc"], w64_tex)
    rh = cmp_pair(base, E[lang][f"snapkv@r0.75:w{hw}"])
    check(f"8b {lang} hat", rh["acc"], hat_tex)
check("8b bn w64 delta", cmp_pair(E["bn"]["baseline"], E["bn"]["snapkv@r0.75"])["d"], -17)
check("8b bn w64 fixed/broken",
      cmp_pair(E["bn"]["baseline"], E["bn"]["snapkv@r0.75"])["fb"], (1, 18))
check("8b bn hat delta",
      cmp_pair(E["bn"]["baseline"], E["bn"]["snapkv@r0.75:w183"])["d"], -8)
check("8b bn hat fixed/broken",
      cmp_pair(E["bn"]["baseline"], E["bn"]["snapkv@r0.75:w183"])["fb"], (0, 8))
r = cmp_pair(E["bn"]["snapkv@r0.75"], E["bn"]["snapkv@r0.75:w183"])
check("8b bn hat-vs-w64 delta", r["d"], 9)
check("8b bn hat-vs-w64 fixed/broken", r["fb"], (11, 2))

# --------------------------------------------------------------------------
print("## Appendix: old (mis-sized) schema run — app:schema")
SO = load("schema-final.db", key=lambda i: re.search(r"JSON(\d+)", i).group(1))
TEX_SO = {"60": (94, 88, 88), "120": (95, 89, 72), "200": (94, 89, 75)}
for pad, (b_tex, w64_tex, w41_tex) in TEX_SO.items():
    base = SO[pad]["baseline"]
    check(f"schema-old {pad} base", round(100 * sum(base.values()) / len(base)), b_tex)
    check(f"schema-old {pad} w64", cmp_pair(base, SO[pad]["snapkv@r0.75"])["acc"], w64_tex)
    check(f"schema-old {pad} w41",
          cmp_pair(base, SO[pad]["snapkv@r0.75:w41"])["acc"], w41_tex)

# --------------------------------------------------------------------------
print("## Appendix: Llama third family — tab:llama and the section prose")
LL = load("llama.db")
TEX_LL = {  # lang: (baseline, w64, hat, hat_w, hat_delta)
    "en": (97, 98, 98, 43, 1),
    "bn": (76, 58, 68, 212, -8),
    "te": (51, 46, 50, 284, -1),
}
for lang, (b_tex, w64_tex, hat_tex, hw, hd_tex) in TEX_LL.items():
    base = LL[lang]["baseline"]
    check(f"llama {lang} base", round(100 * sum(base.values()) / len(base)), b_tex)
    check(f"llama {lang} w64", cmp_pair(base, LL[lang]["snapkv@r0.75"])["acc"], w64_tex)
    rh = cmp_pair(base, LL[lang][f"snapkv@r0.75:w{hw}"])
    check(f"llama {lang} hat", rh["acc"], hat_tex)
    check(f"llama {lang} hat delta", rh["d"], hd_tex)
# prose in app:llama and in the scale paragraph
r = cmp_pair(LL["bn"]["baseline"], LL["bn"]["snapkv@r0.75"])
check("llama bn w64 delta", r["d"], -18)
check("llama bn w64 fixed/broken", r["fb"], (2, 20))
check("llama bn w64 star", r["star"], True)
r = cmp_pair(LL["bn"]["snapkv@r0.75"], LL["bn"]["snapkv@r0.75:w212"])
check("llama bn hat-vs-w64 delta", r["d"], 10)
check("llama bn hat-vs-w64 fixed/broken", r["fb"], (13, 3))
check("llama te w64 delta", cmp_pair(LL["te"]["baseline"], LL["te"]["snapkv@r0.75"])["d"], -5)

# --------------------------------------------------------------------------
print("## Main text: two remedies — tab:remedies")
IF = load("instr_first.db")
# columns 1-2 are the existing instruction-last cells (D and Q90 stores);
# column 3 pairs within instr_first.db against its own baseline.
TEX_REM = {  # lang: (last_w64, last_hat, question_last_w64)
    "en": (0, 2, -1),
    "bn": (-16, -2, -4),
    "te": (-19, 0, -6),
}
for lang, (c1, c2, c3) in TEX_REM.items():
    check(f"remedies {lang} last-w64",
          cmp_pair(D[lang]["baseline"], D[lang]["snapkv@r0.75"])["d"], c1)
    check(f"remedies {lang} last-hat",
          cmp_pair(D[lang]["baseline"], Q[lang][f"snapkv@r0.75:w{TEX_AWA[lang][4]}"])["d"], c2)
    check(f"remedies {lang} question-last",
          cmp_pair(IF[lang]["baseline"], IF[lang]["snapkv@r0.75"])["d"], c3)
    # Table 2's layout column now prints the accuracy beside the difference,
    # so the recoveries quoted in section 6 can be reconstructed from it.
    check(f"remedies {lang} question-last accuracy",
          cmp_pair(IF[lang]["baseline"], IF[lang]["snapkv@r0.75"])["acc"],
          {"en": 95, "bn": 70, "te": 51}[lang])
check("remedies bn last-w64 star",
      cmp_pair(D["bn"]["baseline"], D["bn"]["snapkv@r0.75"])["star"], True)
check("remedies te last-w64 star",
      cmp_pair(D["te"]["baseline"], D["te"]["snapkv@r0.75"])["star"], True)
# cross-layout recoveries quoted in section 4 and the boundary paragraph
for lang, want_d in [("bn", 13), ("te", 14)]:
    def by_idx(m):
        return {k.rsplit("-", 1)[-1]: v for k, v in m.items()}
    r = cmp_pair(by_idx(D[lang]["snapkv@r0.75"]), by_idx(IF[lang]["snapkv@r0.75"]))
    check(f"cross-layout {lang} recovery", r["d"], want_d)
    check(f"cross-layout {lang} star", r["star"], True)

# --------------------------------------------------------------------------
print("## Appendix: rival remedies — tab:rivals")
AG = load("agnostic.db")
RA = load("ratio.db")
# Top block: two query-agnostic scorers at the ratio used throughout, beside
# the windowed cells they would replace (those come from D and Q, checked
# above, so only the two new columns are new data).
TEX_RIVALS_AG = {  # lang: ((expected d, star), (tova d, star))
    "en": ((-14, True), (-8, True)),
    "bn": ((-18, True), (-16, True)),
    "te": ((-20, True), (-18, True)),
}
for lang, (ea, tova) in TEX_RIVALS_AG.items():
    base = AG[lang]["baseline"]
    for cfg, (d_tex, star_tex) in (("expected@r0.75", ea), ("tova@r0.75", tova)):
        r = cmp_pair(base, AG[lang][cfg])
        check(f"rivals {lang} {cfg} delta", r["d"], d_tex)
        check(f"rivals {lang} {cfg} star", r["star"], star_tex)
    # the windowed reference columns are the same cells as tab:aw
    check(f"rivals {lang} baseline matches autowin",
          round(100 * sum(base.values()) / len(base)), TEX_AWA[lang][0])

# Bottom block: the heavy-ratio sweep.
W_HAT = {"en": 43, "bn": 183}
TEX_RIVALS_RA = {  # lang: ((w64 d, star), (w256 d, star), (hat d, star))
    "en": ((-2, False), (-9, True), (-1, False)),
    "bn": ((-44, True), (-28, True), (-24, True)),
}
for lang, (w64, w256, hat) in TEX_RIVALS_RA.items():
    base = RA[lang]["baseline"]
    cells = (
        ("snapkv@r0.9375", w64),
        ("snapkv@r0.9375:w256", w256),
        (f"snapkv@r0.9375:w{W_HAT[lang]}", hat),
    )
    for cfg, (d_tex, star_tex) in cells:
        r = cmp_pair(base, RA[lang][cfg])
        check(f"rivals {lang} r0.9375 {cfg} delta", r["d"], d_tex)
        check(f"rivals {lang} r0.9375 {cfg} star", r["star"], star_tex)

# Prose in the same appendix and in the limitations: w=256 against the
# default window and against w-hat, and the Bengali recovery.
r = cmp_pair(RA["en"]["snapkv@r0.9375"], RA["en"]["snapkv@r0.9375:w256"])
check("rivals en w256 vs default delta", r["d"], -7)
check("rivals en w256 vs default not significant", r["star"], False)
for lang, want_d in (("en", 8), ("bn", 4)):
    r = cmp_pair(RA[lang]["snapkv@r0.9375:w256"],
                 RA[lang][f"snapkv@r0.9375:w{W_HAT[lang]}"])
    check(f"rivals {lang} hat beats w256 by", r["d"], want_d)
    check(f"rivals {lang} hat-vs-w256 not significant", r["star"], False)
r = cmp_pair(RA["bn"]["snapkv@r0.9375"], RA["bn"][f"snapkv@r0.9375:w183"])
check("rivals bn hat recovery over default", r["d"], 20)
check("rivals bn hat recovery fixed/broken", r["fb"], (22, 2))
check("rivals bn hat recovery star", r["star"], True)
# The limitations quote a range for how much sizing the window recovers over
# the default across model families. Only cells the default actually blinds
# count: at Gemma c=32 < 64, so its default window already sees the question.
# The heavy-ratio Bengali recovery is a different ratio, not a family, and is
# deliberately outside this range.
family_recoveries = [
    cmp_pair(D["bn"]["snapkv@r0.75"], Q["bn"]["snapkv@r0.75:w183"])["d"],
    cmp_pair(D["te"]["snapkv@r0.75"], Q["te"]["snapkv@r0.75:w247"])["d"],
    cmp_pair(E["bn"]["snapkv@r0.75"], E["bn"]["snapkv@r0.75:w183"])["d"],
    cmp_pair(LL["bn"]["snapkv@r0.75"], LL["bn"]["snapkv@r0.75:w212"])["d"],
]
check("limitations family recovery range low", min(family_recoveries), 9)
check("limitations family recovery range high", max(family_recoveries), 19)

# --------------------------------------------------------------------------
print("## Appendix: interval rows added for the new arms — tab:ci")
# The CI bounds themselves are owned by closure_cis.py; here we only check the
# point estimates and discordant counts the table prints beside them.
for label, base, comp, d_tex, fb_tex in [
    ("ci llama en", LL["en"]["baseline"], LL["en"]["snapkv@r0.75:w43"], 1, (1, 0)),
    ("ci llama bn", LL["bn"]["baseline"], LL["bn"]["snapkv@r0.75:w212"], -8, (3, 11)),
    ("ci llama te", LL["te"]["baseline"], LL["te"]["snapkv@r0.75:w284"], -1, (3, 4)),
    ("ci IF bn", IF["bn"]["baseline"], IF["bn"]["snapkv@r0.75"], -4, (3, 7)),
    ("ci IF te", IF["te"]["baseline"], IF["te"]["snapkv@r0.75"], -6, (1, 7)),
]:
    r = cmp_pair(base, comp)
    check(f"{label} delta", r["d"], d_tex)
    check(f"{label} fixed/broken", r["fb"], fb_tex)

# --------------------------------------------------------------------------
print("## Section 6 and tab:ci: the depth arm on the full validation pools")
# The two headline closure cells re-run on the entire TyDiQA validation pools
# under the preregistered everything-there-is stopping rule. Self-contained:
# own baselines, own stack, pairs only within depth.db. These cells print one
# decimal in the paper, so they are checked to one decimal rather than through
# cmp_pair's integer rounding.
DP = load("depth.db")


def depth_pair(base, comp):
    common = sorted(set(base) & set(comp))
    n = len(common)
    f = sum(1 for i in common if not base[i] and comp[i])
    b = sum(1 for i in common if base[i] and not comp[i])
    return dict(n=n, fb=(f, b), d=round(100 * (f - b) / n, 1),
                acc=round(100 * sum(comp[i] for i in common) / n, 1),
                p=mcnemar_p(f, b))


TEX_DEPTH = {  # lang: (w-hat, n, baseline acc, (w64 d, fb), (hat d, fb), (rec d, fb))
    "te": (247, 669, 62.6, (-20.2, (19, 154)), (-5.7, (19, 57)), (14.5, (117, 20))),
    "bn": (183, 113, 71.7, (-15.0, (3, 20)), (-1.8, (6, 8)), (13.3, (18, 3))),
}
for lang, (what, n_tex, base_tex, w64, hat, rec) in TEX_DEPTH.items():
    base = DP[lang]["baseline"]
    d64 = DP[lang]["snapkv@r0.75"]
    dw = DP[lang][f"snapkv@r0.75:w{what}"]
    check(f"depth {lang} pool size", len(base), n_tex)
    check(f"depth {lang} baseline accuracy",
          round(100 * sum(base.values()) / len(base), 1), base_tex)
    for label, comp_base, comp, (d_tex, fb_tex) in [
        ("default window", base, d64, w64),
        ("w-hat", base, dw, hat),
        ("recovery", d64, dw, rec),
    ]:
        r = depth_pair(comp_base, comp)
        check(f"depth {lang} {label} delta", r["d"], d_tex)
        check(f"depth {lang} {label} fixed/broken", r["fb"], fb_tex)
# The abstract and section 1 quote the default's cost at the full pools,
# rounded to whole points: the triple -20/+14/-5.7 has to be the same sample
# size end to end or it does not sum, which is what E1 repaired.
check("abstract depth hole bn", round(depth_pair(
    DP["bn"]["baseline"], DP["bn"]["snapkv@r0.75"])["d"]), -15)
check("abstract depth hole te", round(depth_pair(
    DP["te"]["baseline"], DP["te"]["snapkv@r0.75"])["d"]), -20)
# The abstract and section 1 round the two recoveries to whole points.
check("abstract depth recovery te", round(depth_pair(
    DP["te"]["snapkv@r0.75"], DP["te"]["snapkv@r0.75:w247"])["d"]), 14)
check("abstract depth recovery bn", round(depth_pair(
    DP["bn"]["snapkv@r0.75"], DP["bn"]["snapkv@r0.75:w183"])["d"]), 13)
# The strongest significance the paper quotes, as printed: p = 7e-18.
_p = depth_pair(DP["te"]["snapkv@r0.75"], DP["te"]["snapkv@r0.75:w247"])["p"]
check("depth te recovery p exponent", math.floor(math.log10(_p)), -18)
check("depth te recovery p mantissa", round(_p / 10 ** math.floor(math.log10(_p))), 7)

# The decomposition section 6 and app:ci both print: the original hundred
# items reproduce byte-identically and still sit at zero, the 569 new ones at
# -6.7. Item index comes from the id suffix, which mrag assigns from the
# question-pool position.
_idx = lambda i: int(i.rsplit("-", 1)[1])
for label, keep, d_tex in [("original 100", lambda i: _idx(i) < 100, 0.0),
                           ("new 569", lambda i: _idx(i) >= 100, -6.7)]:
    r = depth_pair({k: v for k, v in DP["te"]["baseline"].items() if keep(k)},
                   {k: v for k, v in DP["te"]["snapkv@r0.75:w247"].items() if keep(k)})
    check(f"depth te decomposition, {label}", r["d"], d_tex)

# --------------------------------------------------------------------------
print("## Section 6: coverage and the residual visibility audit, full pools")
# "The window covers the entire question for 98 of 113 Bengali and 611 of 669
# Telugu items" and "on the full Telugu pool 51 of 57 do" are properties of
# the questions, not of any store, so they are recomputed from the TyDiQA
# validation split and the run tokenizer. Skipped loudly where either is
# missing -- the same rule as the constants block above.
try:
    import json as _json

    from datasets import load_dataset  # noqa: E402
    from transformers import AutoTokenizer  # noqa: E402

    _tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-4B")
    _q90 = {r["lang"]: r["Q90"] for r in _json.loads(
        (RES / "q_percentiles.json").read_text()) if r["model"] == "Qwen/Qwen3-4B"}
    check("Q90 used for the Telugu window", _q90["te"], 80)
    check("Q90 used for the Bengali window", _q90["bn"], 76)
    _tydi = load_dataset("google-research-datasets/tydiqa", "secondary_task")
    TEX_COVER = {  # lang: (w-hat, coverage, residual fully visible)
        "te": (247, (611, 669), (51, 57)),
        "bn": (183, (98, 113), (7, 8)),
    }
    for lang, (what, cover_tex, resid_tex) in TEX_COVER.items():
        name = {"te": "telugu", "bn": "bengali"}[lang]
        rows = [r for r in _tydi["validation"] if r["id"].startswith(name + "-")]
        qlen = [len(_tok(r["question"], add_special_tokens=False)["input_ids"])
                for r in rows]
        base, dw = DP[lang]["baseline"], DP[lang][f"snapkv@r0.75:w{what}"]
        # The store's own qid must agree with the split position, or indexing
        # by the item-id suffix would silently score the wrong question.
        con = sqlite3.connect(f"file:{RES / 'depth.db'}?mode=ro", uri=True)
        mism = sum(1 for iid, meta in con.execute(
            "SELECT item_id, meta FROM generations WHERE lang=? AND config='baseline'",
            (lang,)) if _json.loads(meta)["qid"] != rows[_idx(iid)]["id"])
        con.close()
        check(f"depth {lang} qid alignment with the validation split", mism, 0)
        visible = [i for i in range(len(rows)) if qlen[i] <= _q90[lang]]
        check(f"depth {lang} coverage at w-hat",
              (len(visible), len(rows)), cover_tex)
        residual = [i for i in range(len(rows))
                    if base[f"mrag-{lang}-8k-{i}"] and not dw[f"mrag-{lang}-8k-{i}"]]
        check(f"depth {lang} residual items fully visible",
              (sum(1 for i in residual if qlen[i] <= _q90[lang]), len(residual)),
              resid_tex)
except Exception as exc:  # tokenizer or dataset unavailable
    print(f"  SKIPPED (no tokenizer or dataset: {type(exc).__name__})")

# --------------------------------------------------------------------------
print("## Appendix app:r2: the stricter marker-only rule, both places it is quoted")
# app:r2 quotes one stricter rule twice -- the Telugu dose ladder and the
# depth arm's residual -- and both must come from the same scorer, pinned in
# qa_metrics.containment_match_marker_only. The 2026-08-19 depth readout
# briefly carried a 24/87 pair from a leaky hybrid (marker present, then
# extract_span, whose whole-text fallback credits marker-debris rows); that
# hybrid agrees with the strict rule on the ladder and diverges on depth,
# which is why this block pins the pair and not just the delta.
VT_MO = load("v_trace.db", scorer=containment_match_marker_only)
for cfg, want in [("baseline", 50), ("snapkv@r0.75:w171", 35),
                  ("snapkv@r0.75:w247", 47)]:
    cell = VT_MO["te"][cfg]
    check(f"app:r2 marker-only ladder, te {cfg}",
          round(100 * sum(cell.values()) / len(cell)), want)
DP_MO = load("depth.db", scorer=containment_match_marker_only)
r = depth_pair(DP_MO["te"]["baseline"], DP_MO["te"]["snapkv@r0.75:w247"])
check("app:r2 marker-only depth residual delta", r["d"], -9.4)
check("app:r2 marker-only depth residual fixed/broken", r["fb"], (25, 88))
check("app:r2 marker-only depth p exponent", math.floor(math.log10(r["p"])), -9)
check("app:r2 marker-only depth p mantissa",
      round(r["p"] / 10 ** math.floor(math.log10(r["p"])), 1), 2.1)


def _binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def _clopper_pearson(k, n, alpha=0.05):
    # Same method as closure_cis.py, which owns the CI vocabulary; kept here
    # only so the app:r2 interval is recomputed rather than transcribed.
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


_f, _b = r["fb"]
_N, _n = _f + _b, 669
_lo, _hi = _clopper_pearson(_f, _N)
check("app:r2 marker-only depth CI",
      (round(100 * (2 * _lo - 1) * _N / _n, 1), round(100 * (2 * _hi - 1) * _N / _n, 1)),
      (-11.9, -6.5))

# --------------------------------------------------------------------------
print("## app:rivals: the constant at scale — store constant_depth")
# The ninth arm store and the last one the campaign produces. Everything
# app:rivals prints about it is recomputed here, including the guard that
# makes two of the four comparisons legal at all.


def _ci(fb, n):
    """The interval, to the one decimal app:rivals prints."""
    f, b = fb
    N = f + b
    lo, hi = _clopper_pearson(f, N)
    return (round(100 * (2 * lo - 1) * N / n, 1),
            round(100 * (2 * hi - 1) * N / n, 1))


CDP = load("constant_depth.db")
# The guard first: the head-to-heads below pair w=256 cells from this store
# against w-hat cells from depth.db, which is only sound because the two
# stores ran the same items on the same stack and their baselines agree byte
# for byte. Compared as raw output, not as scored booleans -- a scoring
# agreement would survive two different generations that both happen to be
# right.
_c1 = sqlite3.connect(f"file:{RES / 'constant_depth.db'}?mode=ro", uri=True)
_c2 = sqlite3.connect(f"file:{RES / 'depth.db'}?mode=ro", uri=True)
_q = "SELECT item_id, lang, output FROM generations WHERE config='baseline'"
_a = {(l, i): o for i, l, o in _c1.execute(_q)}
_b2 = {(l, i): o for i, l, o in _c2.execute(_q)}
_c1.close()
_c2.close()
_shared = sorted(set(_a) & set(_b2))
check("constant_depth shares every baseline row with depth", len(_shared), 782)
check("constant_depth baselines byte-identical to depth",
      sum(1 for k in _shared if _a[k] == _b2[k]), 782)

for _lang, _acc in (("te", 62.6), ("bn", 71.7)):
    _bl = CDP[_lang]["baseline"]
    check(f"constant_depth {_lang} baseline accuracy",
          round(100 * sum(_bl.values()) / len(_bl), 1), _acc)

# w=256 against its own baseline: a closure cell, one per pool.
TEX_W256 = {"te": (-6.9, (20, 66), (-9.0, -4.2)),
            "bn": (-3.5, (6, 10), (-9.9, 4.1))}
for _lang, (_d, _fb, _ci_tex) in TEX_W256.items():
    _r = depth_pair(CDP[_lang]["baseline"], CDP[_lang]["snapkv@r0.75:w256"])
    check(f"w256 {_lang} full-pool delta", _r["d"], _d)
    check(f"w256 {_lang} full-pool fixed/broken", _r["fb"], _fb)
    check(f"w256 {_lang} full-pool CI", _ci(_r["fb"], _r["n"]), _ci_tex)
# The Telugu residual is the one app:rivals calls certified, so its
# significance is pinned as printed: p = 6.7e-7.
_pte = depth_pair(CDP["te"]["baseline"], CDP["te"]["snapkv@r0.75:w256"])["p"]
check("w256 te p exponent", math.floor(math.log10(_pte)), -7)
check("w256 te p mantissa", round(_pte / 10 ** math.floor(math.log10(_pte)), 1), 6.7)

# The head-to-heads. base = w256, comp = w-hat, so a positive delta favours
# the computed integer. This is the pairing the byte-identity above licenses.
TEX_H2H = {"te": (247, 1.2, (16, 8), (-0.4, 2.5)),
           "bn": (183, 1.8, (5, 3), (-3.6, 5.9))}
for _lang, (_w, _d, _fb, _ci_tex) in TEX_H2H.items():
    _r = depth_pair(CDP[_lang]["snapkv@r0.75:w256"],
                    DP[_lang][f"snapkv@r0.75:w{_w}"])
    check(f"head-to-head {_lang} delta", _r["d"], _d)
    check(f"head-to-head {_lang} fixed/broken", _r["fb"], _fb)
    check(f"head-to-head {_lang} CI", _ci(_r["fb"], _r["n"]), _ci_tex)
# The tie rests on zero being inside the Telugu interval by four tenths of a
# point, which is the number app:rivals is required to print rather than
# round. Pin the sign of the bound, not just its value.
check("head-to-head te interval contains zero",
      _ci(depth_pair(CDP["te"]["snapkv@r0.75:w256"],
                     DP["te"]["snapkv@r0.75:w247"])["fb"], 669)[0] < 0, True)

# Robustness: the same residual under the stricter marker-only scorer.
CDP_MO = load("constant_depth.db", scorer=containment_match_marker_only)
_rmo = depth_pair(CDP_MO["te"]["baseline"], CDP_MO["te"]["snapkv@r0.75:w256"])
check("w256 te marker-only delta", _rmo["d"], -9.3)
check("w256 te marker-only fixed/broken", _rmo["fb"], (26, 88))
check("w256 te marker-only p exponent", math.floor(math.log10(_rmo["p"])), -9)

# --------------------------------------------------------------------------
print("## Section 7: the stuffed control — store stuffed")
# The disconfirmation paragraph had no backing anywhere. This is the one of
# its three claims that a shipped store can carry: mgsm-stuffed, scored live
# by the numeric MGSM extractor, so the stored `correct` column is the rule
# and R2 does not apply to it.
_st = sqlite3.connect(f"file:{RES / 'stuffed.db'}?mode=ro", uri=True)
_rows = defaultdict(lambda: defaultdict(dict))
for _iid, _lang, _cfg, _corr in _st.execute(
        "SELECT item_id, lang, config, correct FROM generations"):
    _rows[_lang][_cfg][_iid] = bool(_corr)
_st.close()
_stuffed = cmp_pair(_rows["bn"]["baseline"], _rows["bn"]["snapkv@r0.75"])
check("stuffed control bn delta", _stuffed["d"], -3)
check("stuffed control bn fixed/broken", _stuffed["fb"], (7, 10))
check("stuffed control bn not significant", _stuffed["star"], False)

# --------------------------------------------------------------------------
print("## Appendix: the 0.75<=V<1 band's per-rung membership — app:dose")
# app:dose used to say the band "contains nine distinct items". It contains
# 59: visibility rises with the window, so each item crosses into the band at
# exactly one rung and the 59 observations cannot be fewer than 59 items.
# Nine is the broken count. The rung histogram is pinned so the corrected
# sentence cannot drift back.
try:
    from datasets import load_dataset  # noqa: E402
    from transformers import AutoTokenizer  # noqa: E402

    _tk = AutoTokenizer.from_pretrained("Qwen/Qwen3-4B")
    _te_rows = [r for r in load_dataset(
        "google-research-datasets/tydiqa", "secondary_task")["validation"]
        if r["id"].startswith("telugu-")]
    VT = load("v_trace.db")["te"]
    _C_TE = 167
    _ql = {}

    def _qlen(i):
        if i not in _ql:
            _ql[i] = len(_tk(_te_rows[i]["question"],
                             add_special_tokens=False)["input_ids"])
        return _ql[i]

    _base = {int(k.rsplit("-", 1)[1]): v for k, v in VT["baseline"].items()}
    _rungs, _broken = {}, set()
    for _cfg in sorted(c for c in VT if c != "baseline"):
        _slack = int(_cfg.rsplit("w", 1)[1]) - _C_TE
        _cells = {int(k.rsplit("-", 1)[1]): v for k, v in VT[_cfg].items()}
        _mem = [i for i in _cells if 0.75 <= min(_slack, _qlen(i)) / _qlen(i) < 1.0]
        _rungs[_slack] = len(_mem)
        _broken |= {i for i in _mem if _base[i] and not _cells[i]}
    check("dose band size equals its distinct item count", sum(_rungs.values()), 59)
    check("dose band membership by rung",
          {k: v for k, v in _rungs.items() if v}, {32: 14, 48: 40, 80: 5})
    check("dose band distinct broken items", len(_broken), 9)
    check("dose band broken items recovered at V=1",
          sum(1 for i in _broken
              if {int(k.rsplit("-", 1)[1]): v
                  for k, v in VT["snapkv@r0.75:w247"].items()}[i]), 4)
except Exception as exc:
    print(f"  SKIPPED (no tokenizer or dataset: {type(exc).__name__})")

# --------------------------------------------------------------------------
print("## Appendix: the Gemma Telugu closure row, and Bengali's exhausted pool")
# Gemma te is the cell Section 6 uses to say the shipped constant can already
# pass, so tab:ci now carries it; the CI itself is closure_cis.py's.
_GT = load("gemma_q90.db")
_gt = cmp_pair(_GT["te"]["baseline"], _GT["te"]["snapkv@r0.75:w64"])
check("gemma te closure delta", _gt["d"], -3)
check("gemma te closure fixed/broken", _gt["fb"], (4, 7))
# app:ci says Bengali's full-pool row adds no discordant item beyond the
# original hundred -- the reason its interval cannot narrow however the pool
# is read. Checked as: the pair on the first 100 equals the pair on all 113,
# and the 13 new items contribute (0, 0).
_bn_idx = lambda i: int(i.rsplit("-", 1)[1])
_bn_base, _bn_hat = DP["bn"]["baseline"], DP["bn"]["snapkv@r0.75:w183"]
_first = depth_pair({k: v for k, v in _bn_base.items() if _bn_idx(k) < 100},
                    {k: v for k, v in _bn_hat.items() if _bn_idx(k) < 100})
_new = depth_pair({k: v for k, v in _bn_base.items() if _bn_idx(k) >= 100},
                  {k: v for k, v in _bn_hat.items() if _bn_idx(k) >= 100})
check("bn full pool pair equals the n=100 pair",
      depth_pair(_bn_base, _bn_hat)["fb"], _first["fb"])
check("bn items beyond the original hundred are all concordant", _new["fb"], (0, 0))
check("bn items beyond the original hundred", _new["n"], 13)

# --------------------------------------------------------------------------
print("## Section 4: the shipped-constant flip — store w32")
# The store behind "moving from w=64 to w=32 costs Thai 4.5 and Swahili 6.5"
# was in neither the store list nor this audit until wave 4. It is its own
# pod (stack 485513693f0a), decode cap 384, n=200 per language as the same
# 100 questions at two context budgets, so every pairing here is within the
# store and within a language.
W32 = load("w32.db")
# The text prints one decimal here (4.5, 6.5), so the check carries one:
# cmp_pair rounds to whole points and -4.5 rounds to -4, which is a real
# disagreement with the page rather than a tolerance to widen.
# English on this second pod replicates the Scope sentence's point rather
# than contradicting it. The sentence's -2 pp is a within-stack pairing of
# w=32 (cliff_multi) against w=64 (autowin) on stack d7368e8bd94a, whose
# English baselines are byte-identical across the two stores -- pinned
# above, with the baseline-agreement guard that makes it legal. w32.db is a
# different pod (485513693f0a), and there the same contrast is 0.0 pp
# (2/2, n=200): two pods, neither able to tell the shipped constants apart.
_w32_en = depth_pair(W32["en"]["snapkv@r0.75"], W32["en"]["snapkv@r0.75:w32"])
check("w32 second-pod replication, en w32-vs-w64 delta", _w32_en["d"], 0.0)
check("w32 second-pod replication, en pair", _w32_en["fb"], (2, 2))
check("w32 second-pod replication, en not significant",
      mcnemar_p(*_w32_en["fb"]) < 0.05, False)

for lang, (d_tex, fb_tex) in {"th": (-4.5, (2, 11)), "sw": (-6.5, (1, 14))}.items():
    r = depth_pair(W32[lang]["snapkv@r0.75"], W32[lang]["snapkv@r0.75:w32"])
    check(f"w32 flip {lang} delta", r["d"], d_tex)
    check(f"w32 flip {lang} fixed/broken", r["fb"], fb_tex)
    check(f"w32 flip {lang} n", r["n"], 200)

# --------------------------------------------------------------------------
print("## Appendix: PyramidKV, the second member of the family — tab:rivals")
# Its pod did not reproduce the campaign stack, so every comparison here is
# within this store; the SnapKV values printed beside it in the table are
# checked above against their own stores and are never paired with these.
PK = load("pyramidkv.db")
TEX_PK = {  # lang: (baseline, w-hat, (default d, star), (hat d, star),
            #        (recovery d, star, fixed/broken))
    "bn": (73, 183, (-28, True), (-2, False), (26, True, (29, 3))),
    "en": (93, 43, (2, False), (0, False), (-2, False, (0, 2))),
    "te": (56, 247, (-32, True), (-1, False), (31, True, (32, 1))),
}
for lang, (b_tex, what, dflt, hat, rec) in TEX_PK.items():
    base = PK[lang]["baseline"]
    check(f"pyramidkv {lang} baseline",
          round(100 * sum(base.values()) / len(base)), b_tex)
    r = cmp_pair(base, PK[lang]["pyramidkv@r0.75"])
    check(f"pyramidkv {lang} default delta", r["d"], dflt[0])
    check(f"pyramidkv {lang} default star", r["star"], dflt[1])
    r = cmp_pair(base, PK[lang][f"pyramidkv@r0.75:w{what}"])
    check(f"pyramidkv {lang} hat delta", r["d"], hat[0])
    check(f"pyramidkv {lang} hat star", r["star"], hat[1])
    r = cmp_pair(PK[lang]["pyramidkv@r0.75"], PK[lang][f"pyramidkv@r0.75:w{what}"])
    check(f"pyramidkv {lang} recovery delta", r["d"], rec[0])
    check(f"pyramidkv {lang} recovery star", r["star"], rec[1])
    check(f"pyramidkv {lang} recovery fixed/broken", r["fb"], rec[2])
# The abstract prints the two recoveries as a pair.
check("abstract transfer recoveries",
      sorted(cmp_pair(PK[l]["pyramidkv@r0.75"],
                      PK[l][f"pyramidkv@r0.75:w{TEX_PK[l][1]}"])["d"]
             for l in ("bn", "te")), [26, 31])

# --------------------------------------------------------------------------
# The abstract, the introduction and contribution (i) all rest on one pair of
# constants: the Telugu trailing block and the trailing block of an English
# prompt carrying a 120-token JSON schema, which differ by a single token.
# Those come from the tokenizer rather than from any store, so they are
# recomputed here from the same code the runs used. Skipped, loudly, where
# the tokenizer is not available -- this must not turn the audit red on a
# machine that only has the stores.
print("## Abstract: the two trailing blocks that land one token apart")
try:
    from transformers import AutoTokenizer  # noqa: E402

    from mlkv.languages import LANGUAGES  # noqa: E402
    from mlkv.tasks.mrag import _pad_instruction  # noqa: E402

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-4B")
    suffix = 5  # assistant header, as measured by measure_c.py

    def trailing(instruction):
        return len(tok(instruction, add_special_tokens=False)["input_ids"]) + suffix

    check("abstract c for Telugu", trailing(LANGUAGES["te"].qa_instruction), 167)
    check("abstract c for English with a 120-token JSON schema",
          trailing(_pad_instruction(LANGUAGES["en"].qa_instruction, "en", tok,
                                    120, tail="json")), 166)

    # The constants table, and the two counts the scope paragraph and the
    # abstract draw from it. A blinded language is one whose trailing block
    # exceeds the constant, so the counts follow from these eight numbers and
    # nothing else -- which is how "four" survived here for a while: it was
    # the count over the five swept languages, quoted in a sentence about all
    # eight.
    # The two template-survey numbers the paper prints. The trailing-block
    # strings are locked in template_survey_measure.py (which checks its own
    # transcription against the collected report), so they are imported
    # rather than copied -- one source of truth for the locked text.
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "tsm", ROOT / "scripts" / "template_survey_measure.py")
    _tsm = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_tsm)

    def survey_tokens(tid):
        block = next(r[3] for r in _tsm.RECORDS if r[0] == tid)
        cleaned = _tsm.PLACEHOLDER.sub("", block)
        return len(tok(cleaned, add_special_tokens=False)["input_ids"])

    check("survey T06 LlamaIndex refine default", survey_tokens("T06"), 64)
    check("survey T18 SWE-agent instance template", survey_tokens("T18"), 221)
    # The scope sentence says the refine block equals the library default and
    # the agent block exceeds the longest trailing block among our languages.
    check("survey T06 equals the library default", survey_tokens("T06") == 64, True)

    TEX_C = {"en": 25, "zh": 29, "es": 35, "vi": 39,
             "th": 45, "sw": 47, "bn": 107, "te": 167}
    measured = {}
    for lang, want in TEX_C.items():
        measured[lang] = trailing(LANGUAGES[lang].qa_instruction)
        check(f"constants table c for {lang}", measured[lang], want)
    check("languages blinded at the research default of 64",
          sum(1 for c in measured.values() if c > 64), 2)
    # The appendix reports c with the answer-format sentence removed. Import
    # the cutting rule from measure_c.py rather than restating it -- Thai has
    # no separable format sentence and must stay absent, not be guessed at.
    _spec_c = importlib.util.spec_from_file_location(
        "mc", ROOT / "scripts" / "measure_c.py")
    _mc = importlib.util.module_from_spec(_spec_c)
    _spec_c.loader.exec_module(_mc)
    TEX_C_MIN = {"en": 14, "zh": 16, "es": 19, "vi": 21,
                 "sw": 26, "bn": 69, "te": 98}
    c_min = {}
    for lang in TEX_C:
        stripped = _mc.strip_marker_sentence(LANGUAGES[lang].qa_instruction)
        if stripped is None:
            check(f"no-marker c for {lang} is not separable", lang, "th")
            continue
        c_min[lang] = trailing(stripped)
    for lang, want in TEX_C_MIN.items():
        check(f"no-marker c for {lang}", c_min[lang], want)
    check("languages still blinded at 64 without the format sentence",
          sum(1 for c in c_min.values() if c > 64), 2)
    check("languages still blinded at 32 without the format sentence",
          sum(1 for c in c_min.values() if c > 32), 2)
    # Scope and app:measure say THREE languages stay blind at 32 under
    # minimal instructions. That is the count over all eight, using the
    # minimal form where one exists and the full trailing block where none
    # does: Thai has no separable answer-format sentence, so cutting is not
    # available to it and its c=45 stands. The check above counts only the
    # separable languages, which is why the two numbers differ and why both
    # are pinned.
    check("languages blinded at 32 under minimal instructions",
          sum(1 for lang in TEX_C
              if c_min.get(lang, measured[lang]) > 32), 3)
    check("languages blinded at the shipped constant of 32",
          sum(1 for c in measured.values() if c > 32), 6)
    # The appendix says the agent template's static block is longer than the
    # longest trailing block among our eight languages. Derive that bound
    # from the same measured constants rather than pinning Telugu's 167.
    check("survey T18 exceeds the longest language trailing block",
          survey_tokens("T18") > max(measured.values()), True)
except Exception as exc:  # tokenizer or model files unavailable
    print(f"  SKIPPED (no tokenizer available: {type(exc).__name__})")

# --------------------------------------------------------------------------
print("## Appendix: the constant and the no-ranking control — tab:rivals")
# Its pod is a fifth stack descriptor, so every comparison is within this
# store; the bracketed SnapKV values printed beside it are checked above
# against their own stores and are never paired with these.
CO = load("constant.db")
TEX_CO = {  # lang: (baseline, (w256 d, star), (random d, star, fixed/broken))
    "en": (93, (1, False), (-87, True, (0, 87))),
    "bn": (73, (-5, False), (-72, True, (0, 72))),
    "te": (56, (-3, False), (-56, True, (0, 56))),
}
for lang, (b_tex, w256, rnd) in TEX_CO.items():
    base = CO[lang]["baseline"]
    check(f"constant {lang} baseline",
          round(100 * sum(base.values()) / len(base)), b_tex)
    r = cmp_pair(base, CO[lang]["snapkv@r0.75:w256"])
    check(f"constant {lang} w256 delta", r["d"], w256[0])
    check(f"constant {lang} w256 star", r["star"], w256[1])
    r = cmp_pair(base, CO[lang]["random@r0.75"])
    check(f"constant {lang} random delta", r["d"], rnd[0])
    check(f"constant {lang} random star", r["star"], rnd[1])
    check(f"constant {lang} random fixed/broken", r["fb"], rnd[2])
# The Bengali miss is what the appendix hangs its argument on, so pin its
# discordant counts too.
check("constant bn w256 fixed/broken",
      cmp_pair(CO["bn"]["baseline"], CO["bn"]["snapkv@r0.75:w256"])["fb"], (5, 10))
# Derived: the appendix says the constant meets the gate on two of three
# languages. Recompute that count rather than trusting the sentence.
_gate = sum(
    1 for lang in TEX_CO
    if abs(cmp_pair(CO[lang]["baseline"], CO[lang]["snapkv@r0.75:w256"])["d"]) <= 3
)
check("constant meets the +-3 gate on this many languages", _gate, 2)
# and the no-ranking accuracies the appendix prints as 6/1/0
for lang, want in (("en", 6), ("bn", 1), ("te", 0)):
    check(f"constant {lang} random accuracy",
          cmp_pair(CO[lang]["baseline"], CO[lang]["random@r0.75"])["acc"], want)

# --------------------------------------------------------------------------
print("## Appendix: the decode cap — tab:cap")
# Full derivation, including the within-item causal comparison, lives in
# scripts/decode_cap_ledger.py; the cells the appendix prints are pinned here
# too, so one script still fails on any drift in the paper.
_cap_rows = {}
for _db in ("e3-final.db", "e3_384.db"):
    _con = sqlite3.connect(f"file:{RES / _db}?mode=ro", uri=True)
    _cap = _con.execute("SELECT MAX(n_output_tokens) FROM generations").fetchone()[0]
    for _lang, _out, _ntok in _con.execute(
        "SELECT lang, output, n_output_tokens FROM generations WHERE config='baseline'"
    ):
        _d = _cap_rows.setdefault((_cap, _lang), {"n": 0, "trunc": 0, "mark": 0})
        _d["n"] += 1
        _d["trunc"] += _ntok >= _cap
        _d["mark"] += "####" in (_out or "")
    _con.close()
TEX_CAP = {  # (cap, lang): (truncated %, marker %)
    (128, "el"): (65, 45), (128, "hi"): (50, 59), (128, "ru"): (30, 71),
    (128, "th"): (14, 58), (128, "de"): (12, 74), (128, "en"): (6, 95),
    (128, "vi"): (4, 94), (128, "es"): (4, 96), (128, "zh"): (1, 98),
    (384, "el"): (17, 90), (384, "hi"): (4, 97), (384, "ru"): (2, 92),
}
for (cap, lang), (t_tex, m_tex) in TEX_CAP.items():
    d = _cap_rows[(cap, lang)]
    check(f"cap{cap} {lang} truncated", round(100 * d["trunc"] / d["n"]), t_tex)
    check(f"cap{cap} {lang} marker", round(100 * d["mark"] / d["n"]), m_tex)

# --------------------------------------------------------------------------
print("## ICLR9 B1: the slack ablation at depth — slack_depth.db")
# Self-contained store; every pair inside it. One decimal, like depth.
SL = load("slack_depth.db")


def _dpair(base, comp):
    common = sorted(set(base) & set(comp))
    n = len(common)
    f = sum(1 for i in common if not base[i] and comp[i])
    b = sum(1 for i in common if base[i] and not comp[i])
    return dict(n=n, fb=(f, b), d=round(100 * (f - b) / n, 1),
                acc=round(100 * sum(comp[i] for i in common) / n, 1),
                p=mcnemar_p(f, b))


check("slack te pool size", len(SL["te"]["baseline"]), 669)
check("slack te baseline accuracy",
      round(100 * sum(SL["te"]["baseline"].values()) / 669, 1), 62.6)
for w, d_tex, fb_tex in [(183, -10.3, (24, 93)), (199, -7.8, (18, 70)),
                         (247, -5.7, (19, 57))]:
    r = _dpair(SL["te"]["baseline"], SL["te"][f"snapkv@r0.75:w{w}"])
    check(f"slack te w{w} delta", r["d"], d_tex)
    check(f"slack te w{w} fixed/broken", r["fb"], fb_tex)
r = _dpair(SL["te"]["snapkv@r0.75:w183"], SL["te"]["snapkv@r0.75:w247"])
check("slack h2h what-vs-c+16 delta", r["d"], 4.6)
check("slack h2h what-vs-c+16 fixed/broken", r["fb"], (55, 24))
check("slack h2h what-vs-c+16 p", round(r["p"], 4), 0.0006)
r = _dpair(SL["te"]["snapkv@r0.75:w199"], SL["te"]["snapkv@r0.75:w247"])
check("slack h2h what-vs-c+32 delta", r["d"], 2.1)
check("slack h2h what-vs-c+32 fixed/broken", r["fb"], (36, 22))
# byte-identity with the depth arm, quoted in section 5 and app:provenance
_c1 = sqlite3.connect(f"file:{RES / 'depth.db'}?mode=ro", uri=True)
_c2 = sqlite3.connect(f"file:{RES / 'slack_depth.db'}?mode=ro", uri=True)
_same = 0
for cfg in ("baseline", "snapkv@r0.75:w247"):
    a = dict(_c1.execute(
        "SELECT item_id, output FROM generations WHERE lang='te' AND config=?",
        (cfg,)))
    b = dict(_c2.execute(
        "SELECT item_id, output FROM generations WHERE lang='te' AND config=?",
        (cfg,)))
    _same += sum(1 for i in set(a) & set(b) if a[i] == b[i])
_c1.close(); _c2.close()
check("slack/depth shared generations byte-identical", _same, 1338)
# marker-only robustness quoted in app:ci
SLM = load("slack_depth.db", scorer=containment_match_marker_only)
check("slack marker-only baseline",
      round(100 * sum(SLM["te"]["baseline"].values()) / 669, 1), 55.0)
for w, acc_tex in [(183, 43.9), (199, 45.1), (247, 45.6)]:
    check(f"slack marker-only acc w{w}",
          round(100 * sum(SLM["te"][f"snapkv@r0.75:w{w}"].values()) / 669, 1),
          acc_tex)
r = _dpair(SLM["te"]["snapkv@r0.75:w183"], SLM["te"]["snapkv@r0.75:w247"])
check("slack marker-only h2h delta", r["d"], 1.6)
check("slack marker-only h2h fixed/broken", r["fb"], (46, 35))

# --------------------------------------------------------------------------
print("## ICLR9 B4: instruction-first at depth — if_depth.db")
IFD = load("if_depth.db")
check("if_depth pool size", len(IFD["te"]["baseline"]), 669)
check("if_depth baseline accuracy",
      round(100 * sum(IFD["te"]["baseline"].values()) / 669, 1), 59.8)
r = _dpair(IFD["te"]["baseline"], IFD["te"]["snapkv@r0.75"])
check("if_depth w64 delta", r["d"], -3.4)
check("if_depth w64 fixed/broken", r["fb"], (16, 39))
check("if_depth w64 p", round(r["p"], 4), 0.0027)
_c1 = sqlite3.connect(f"file:{RES / 'instr_first.db'}?mode=ro", uri=True)
_c2 = sqlite3.connect(f"file:{RES / 'if_depth.db'}?mode=ro", uri=True)
_same = 0
for cfg in ("baseline", "snapkv@r0.75"):
    a = dict(_c1.execute(
        "SELECT item_id, output FROM generations WHERE lang='te' AND config=?",
        (cfg,)))
    b = dict(_c2.execute(
        "SELECT item_id, output FROM generations WHERE lang='te' AND config=?",
        (cfg,)))
    _same += sum(1 for i in set(a) & set(b) if a[i] == b[i])
_c1.close(); _c2.close()
check("if_depth/instr_first shared generations byte-identical", _same, 200)

# --------------------------------------------------------------------------
print("## ICLR9 B3: Thai and Swahili at their own w-hat — thsw.db")
TS = load("thsw.db")
for lang, what, b_tex, hat, w64 in [
    ("th", 91, 85, (-1, (1, 2)), (0, (1, 1))),
    ("sw", 67, 56, (-3, (2, 5)), (-3, (2, 5))),
]:
    base = TS[lang]["baseline"]
    check(f"thsw {lang} baseline",
          round(100 * sum(base.values()) / len(base)), b_tex)
    r = cmp_pair(base, TS[lang][f"snapkv@r0.75:w{what}"])
    check(f"thsw {lang} w-hat delta", r["d"], hat[0])
    check(f"thsw {lang} w-hat fixed/broken", r["fb"], hat[1])
    check(f"thsw {lang} gate met", abs(r["d"]) <= 3, True)
    r = cmp_pair(base, TS[lang]["snapkv@r0.75"])
    check(f"thsw {lang} w64 delta", r["d"], w64[0])
    check(f"thsw {lang} w64 fixed/broken", r["fb"], w64[1])

# --------------------------------------------------------------------------
print("## ICLR9 B2: English instruction, non-English questions — xinstr.db")
XI = load("xinstr.db")
for lang, what, b_tex, w64, hat in [
    ("bn", 101, 79, (-3, (3, 6)), (-2, (3, 5))),
    ("te", 105, 62, (-4, (2, 6)), (-4, (0, 4))),
]:
    base = XI[lang]["baseline"]
    check(f"xinstr {lang} baseline",
          round(100 * sum(base.values()) / len(base)), b_tex)
    r = cmp_pair(base, XI[lang]["snapkv@r0.75"])
    check(f"xinstr {lang} w64 delta", r["d"], w64[0])
    check(f"xinstr {lang} w64 fixed/broken", r["fb"], w64[1])
    check(f"xinstr {lang} w64 not significant", r["star"], False)
    r = cmp_pair(base, XI[lang][f"snapkv@r0.75:w{what}"])
    check(f"xinstr {lang} w-hat delta", r["d"], hat[0])
    check(f"xinstr {lang} w-hat fixed/broken", r["fb"], hat[1])

# --------------------------------------------------------------------------
print("## Table 1: the w=64 column (AutoWindow store, same stack)")
# The default-window column added to tab:cliff comes from autowin-final,
# whose baselines are byte-identical to the sweep's; each cell pairs
# against its own store's baseline.
AWD = load("autowin-final.db")
for lang, d_tex, star_tex in [("en", 0, False), ("th", 0, False),
                              ("sw", -3, False), ("bn", -16, True),
                              ("te", -19, True)]:
    r = cmp_pair(AWD[lang]["baseline"], AWD[lang]["snapkv@r0.75"])
    check(f"cliff w64 column {lang} delta", r["d"], d_tex)
    check(f"cliff w64 column {lang} star", r["star"], star_tex)

# --------------------------------------------------------------------------
print("## Fourth-review prose: proportion-form residual audits (tokenizer)")
# The 8B / Llama / Gemma / IF-depth / xinstr / Vietnamese sentences that
# need a tokenizer and the raw datasets. Skipped loudly if unavailable.
try:
    import json as _json

    from datasets import load_dataset as _ld  # noqa: E402
    from transformers import AutoTokenizer as _AT  # noqa: E402

    def _qlens(model, lang):
        tok = _AT.from_pretrained(model)
        if lang in ("bn", "te", "sw"):
            name = {"bn": "bengali", "te": "telugu", "sw": "swahili"}[lang]
            ds = _ld("google-research-datasets/tydiqa", "secondary_task")
            rows = [r for r in ds["validation"] if r["id"].startswith(name + "-")]
        else:
            rows = list(_ld("google/xquad", f"xquad.{lang}", split="validation"))
        return {r["id"]: len(tok.encode(r["question"], add_special_tokens=False))
                for r in rows}

    def _qid_map(db, lang):
        con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
        m = {iid: _json.loads(meta)["qid"] for iid, meta in con.execute(
            "SELECT item_id, meta FROM generations WHERE lang=? "
            "AND config='baseline'", (lang,))}
        con.close()
        return m

    # 8B bn: 8 of 8 broken fully visible, pool 88 of 100 (Q90=76)
    E8 = load("autowin_8b.db")
    _ql = _qlens("Qwen/Qwen3-8B", "bn")
    _qm = _qid_map("autowin_8b.db", "bn")
    base, comp = E8["bn"]["baseline"], E8["bn"]["snapkv@r0.75:w183"]
    broken = [i for i in base if base[i] and not comp[i]]
    check("8B residual fully visible",
          (sum(1 for i in broken if _ql[_qm[i]] <= 76), len(broken)), (8, 8))
    check("8B pool fully visible",
          sum(1 for i in base if _ql[_qm[i]] <= 76), 88)

    # Llama bn: 10 of 11 within Q90=87, one beyond
    _ql = _qlens("meta-llama/Llama-3.1-8B-Instruct", "bn")
    _qm = _qid_map("llama.db", "bn")
    base, comp = LL["bn"]["baseline"], LL["bn"]["snapkv@r0.75:w212"]
    broken = [i for i in base if base[i] and not comp[i]]
    check("llama residual fully visible",
          (sum(1 for i in broken if _ql[_qm[i]] <= 87), len(broken)), (10, 11))
    check("llama pool fully visible",
          sum(1 for i in base if _ql[_qm[i]] <= 87), 88)

    # Gemma bn: 7 of 9 broken fully visible, pool 86 of 100 (Q90=18)
    _ql = _qlens("google/gemma-3-4b-it", "bn")
    _qm = _qid_map("gemma_q90.db", "bn")
    base, comp = GQ["bn"]["baseline"], GQ["bn"]["snapkv@r0.75:w50"]
    broken = [i for i in base if base[i] and not comp[i]]
    check("gemma residual fully visible",
          (sum(1 for i in broken if _ql[_qm[i]] <= 18), len(broken)), (7, 9))
    check("gemma pool fully visible",
          sum(1 for i in base if _ql[_qm[i]] <= 18), 86)

    # xinstr V<1 composition at w=64 (c=25, slack 39) and the broken counts
    _ql_qwen = {lang: _qlens("Qwen/Qwen3-4B", lang) for lang in ("bn", "te", "vi")}
    for lang, v_tex, brk_tex in [("bn", 70, 6), ("te", 93, 6)]:
        _qm = _qid_map("xinstr.db", lang)
        base, comp = XI[lang]["baseline"], XI[lang]["snapkv@r0.75"]
        check(f"xinstr {lang} items with V<1 at w64",
              sum(1 for i in base if _ql_qwen[lang][_qm[i]] > 39), v_tex)
        check(f"xinstr {lang} broken count",
              sum(1 for i in base if base[i] and not comp[i]), brk_tex)

    # Vietnamese: held-out percentiles and the w=64 cell composition
    _tok = _AT.from_pretrained("Qwen/Qwen3-4B")
    _rows = list(_ld("google/xquad", "xquad.vi", split="validation"))[100:]
    _ls = sorted(len(_tok.encode(r["question"], add_special_tokens=False))
                 for r in _rows)
    check("vi held-out Q50/Q90/Qmax",
          (_ls[len(_ls) // 2], _ls[int(0.9 * len(_ls))], _ls[-1]), (17, 26, 46))
    _qm = _qid_map("autowin-final.db", "vi")
    base, comp = AWD["vi"]["baseline"], AWD["vi"]["snapkv@r0.75"]
    check("vi items with V<1 at w64",
          sum(1 for i in base if _ql_qwen["vi"][_qm[i]] > 25), 3)
    _brk = [i for i in base if base[i] and not comp[i]]
    check("vi broken at w64, all fully visible",
          (sum(1 for i in _brk if _ql_qwen["vi"][_qm[i]] <= 25), len(_brk)),
          (5, 5))

    # if_depth item audit: broken shares by gold position (no enrichment)
    _pos = {}
    _c = sqlite3.connect(f"file:{RES / 'if_depth.db'}?mode=ro", uri=True)
    for iid, meta in _c.execute(
            "SELECT item_id, meta FROM generations WHERE config='baseline'"):
        _pos[iid] = _json.loads(meta)["position"]
    _c.close()
    base, comp = IFD["te"]["baseline"], IFD["te"]["snapkv@r0.75"]
    broken = [i for i in base if base[i] and not comp[i]]
    check("if_depth broken by position (front/middle/back)",
          tuple(sum(1 for i in broken if _pos[i] == p)
                for p in ("front", "middle", "back")), (10, 17, 12))
except Exception as exc:  # tokenizer or dataset unavailable
    print(f"  SKIPPED (no tokenizer or dataset: {type(exc).__name__})")

# --------------------------------------------------------------------------
print("## ICLR10: refine layout — refine.db")
RFD = load("refine.db")
for lang, b_tex, d_tex, fb_tex in [("en", 87, -3, (1, 4)),
                                   ("bn", 80, -8, (3, 11))]:
    base = RFD[lang]["baseline"]
    check(f"refine {lang} baseline",
          round(100 * sum(base.values()) / len(base)), b_tex)
    r = cmp_pair(base, RFD[lang]["snapkv@r0.75"])
    check(f"refine {lang} w64 delta", r["d"], d_tex)
    check(f"refine {lang} w64 fixed/broken", r["fb"], fb_tex)
    check(f"refine {lang} w64 not significant", r["star"], False)
check("refine bn p as printed",
      round(mcnemar_p(3, 11), 3), 0.057)

# --------------------------------------------------------------------------
print("## ICLR10: the per-item oracle window at depth — oracle_depth.db")
ORD = load("oracle_depth.db")
check("oracle pool size", len(ORD["te"]["baseline"]), 669)
check("oracle baseline accuracy",
      round(100 * sum(ORD["te"]["baseline"].values()) / 669, 1), 62.6)
r = _dpair(ORD["te"]["baseline"], ORD["te"]["snapkv@r0.75:w247"])
check("oracle-arm w247 delta", r["d"], -5.7)
check("oracle-arm w247 fixed/broken", r["fb"], (19, 57))
r = _dpair(ORD["te"]["baseline"], ORD["te"]["snapkv@r0.75:wq167"])
check("oracle w_i delta", r["d"], -5.1)
check("oracle w_i fixed/broken", r["fb"], (22, 56))
r = _dpair(ORD["te"]["snapkv@r0.75:w247"], ORD["te"]["snapkv@r0.75:wq167"])
check("oracle h2h delta", r["d"], 0.6)
check("oracle h2h fixed/broken", r["fb"], (19, 15))
# the position fingerprint quoted in section 5 and the readout
_c = sqlite3.connect(f"file:{RES / 'oracle_depth.db'}?mode=ro", uri=True)
_pos, _qt = {}, {}
import json as _json2
for iid, meta in _c.execute(
        "SELECT item_id, meta FROM generations WHERE config='baseline'"):
    m = _json2.loads(meta)
    _pos[iid], _qt[iid] = m["position"], m["q_tokens"]
_c.close()
base, comp = ORD["te"]["baseline"], ORD["te"]["snapkv@r0.75:wq167"]
_brk = [i for i in base if base[i] and not comp[i]]
check("oracle residual by position (front/middle/back)",
      tuple(sum(1 for i in _brk if _pos[i] == p)
            for p in ("front", "middle", "back")), (6, 26, 24))
check("oracle pool front count",
      sum(1 for i in base if _pos[i] == "front"), 223)
check("oracle long decile size (|Q|>80)",
      sum(1 for i in base if _qt[i] > 80), 58)
# cross-stack byte-identity with the depth arm (app:provenance)
_c1 = sqlite3.connect(f"file:{RES / 'depth.db'}?mode=ro", uri=True)
_c2 = sqlite3.connect(f"file:{RES / 'oracle_depth.db'}?mode=ro", uri=True)
_same = 0
for cfg in ("baseline", "snapkv@r0.75:w247"):
    a = dict(_c1.execute("SELECT item_id, output FROM generations "
                         "WHERE lang='te' AND config=?", (cfg,)))
    b = dict(_c2.execute("SELECT item_id, output FROM generations "
                         "WHERE lang='te' AND config=?", (cfg,)))
    _same += sum(1 for i in set(a) & set(b) if a[i] == b[i])
_st = {r[0] for r in _c1.execute("SELECT DISTINCT stack_id FROM generations")} \
    & {r[0] for r in _c2.execute("SELECT DISTINCT stack_id FROM generations")}
_c1.close(); _c2.close()
check("oracle/depth shared generations byte-identical", _same, 1338)
check("oracle and depth stacks are distinct", len(_st), 0)

# --------------------------------------------------------------------------
print("## ICLR10: the 16k prefill slice — ctx16k.db")
CKD = load("ctx16k.db")
base = CKD["te"]["baseline"]
check("ctx16k baseline", round(100 * sum(base.values()) / len(base)), 54)
r = cmp_pair(base, CKD["te"]["snapkv@r0.75"])
check("ctx16k w64 delta", r["d"], -15)
check("ctx16k w64 fixed/broken", r["fb"], (3, 18))
r = cmp_pair(base, CKD["te"]["snapkv@r0.75:w247"])
check("ctx16k w-hat delta", r["d"], -2)
check("ctx16k w-hat fixed/broken", r["fb"], (3, 5))
r = cmp_pair(CKD["te"]["snapkv@r0.75"], CKD["te"]["snapkv@r0.75:w247"])
check("ctx16k recovery delta", r["d"], 13)
check("ctx16k recovery fixed/broken", r["fb"], (15, 2))
check("ctx16k recovery p as printed", round(mcnemar_p(15, 2), 4), 0.0023)

# --------------------------------------------------------------------------
print("## ICLR10: the Qwen3-32B slice — qwen32b.db")
QBD = load("qwen32b.db")
for lang, what, b_tex, hole, gate, rec in [
    ("bn", 183, 80, (-12, (1, 13)), (-5, (2, 7)), (7, (9, 2))),
    ("te", 247, 56, (-4, (8, 12)), (-1, (2, 3)), (3, (9, 6))),
]:
    base = QBD[lang]["baseline"]
    check(f"32B {lang} baseline",
          round(100 * sum(base.values()) / len(base)), b_tex)
    r = cmp_pair(base, QBD[lang]["snapkv@r0.75"])
    check(f"32B {lang} hole delta", r["d"], hole[0])
    check(f"32B {lang} hole fixed/broken", r["fb"], hole[1])
    r = cmp_pair(base, QBD[lang][f"snapkv@r0.75:w{what}"])
    check(f"32B {lang} gate delta", r["d"], gate[0])
    check(f"32B {lang} gate fixed/broken", r["fb"], gate[1])
    r = cmp_pair(QBD[lang]["snapkv@r0.75"],
                 QBD[lang][f"snapkv@r0.75:w{what}"])
    check(f"32B {lang} recovery delta", r["d"], rec[0])
check("32B bn hole significant",
      cmp_pair(QBD["bn"]["baseline"], QBD["bn"]["snapkv@r0.75"])["star"], True)
check("32B te hole not significant",
      cmp_pair(QBD["te"]["baseline"], QBD["te"]["snapkv@r0.75"])["star"], False)
# the marker-collapse caveat quoted in app:scale16k (0--1% compliance)
QBM = load("qwen32b.db", scorer=containment_match_marker_only)
for lang, want in (("bn", 0), ("te", 1)):
    check(f"32B {lang} marker-only baseline",
          round(100 * sum(QBM[lang]["baseline"].values()) / 100), want)

# --------------------------------------------------------------------------
print(f"\n{CHECKS[0]} checks run, {len(FAILS)} mismatches")
if FAILS:
    print("\n".join(FAILS))
    sys.exit(1)
print("all paper table cells reproduce from the stores")
