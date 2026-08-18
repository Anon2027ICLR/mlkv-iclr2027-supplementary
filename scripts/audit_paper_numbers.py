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
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

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


def load(db, key=None):
    con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
    out = defaultdict(lambda: defaultdict(dict))
    for iid, lang, cfg, o, g in con.execute(
        "SELECT item_id, lang, config, output, answer_gold FROM generations"
    ):
        k = key(iid) if key else lang
        out[k][cfg][iid] = bool(containment_match_lenient(o or "", golds(g), lang))
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
except Exception as exc:  # tokenizer or model files unavailable
    print(f"  SKIPPED (no tokenizer available: {type(exc).__name__})")

# --------------------------------------------------------------------------
print(f"\n{CHECKS[0]} checks run, {len(FAILS)} mismatches")
if FAILS:
    print("\n".join(FAILS))
    sys.exit(1)
print("all paper table cells reproduce from the stores")
