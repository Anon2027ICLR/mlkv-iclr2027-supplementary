# ICLR slot readout — 2026-08-14

**Author: Grok 4.6.** R2 = `containment_match_lenient`. Never stored
`correct`. Paired on `item_id`, n=100, McNemar two-sided. Stack
`d7368e8bd94a`. DBs: `results/{autowin,cliff_en,cliff_multi,schema}-final.db`
pulled from `r948gmdyb92lxo` at 13:49 UTC; `SYNCED` touched after
`PRAGMA quick_check=ok`.

Locked *c* (Qwen3-4B): en 25, zh 29, es 35, vi 39, th 45, sw 47, bn 107,
te 167. AutoWindow *w* = *c*+16.

---

## D — AutoWindow (gate)

| lang | *c* / *w* | base | def 64 | AW | def−base | AW−base | AW−def |
|---|---|---|---|---|---|---|---|
| en | 25 / 41 | 93 | 93 | 94 | +0.0 | **+1.0** | +1.0 |
| zh | 29 / 45 | 83 | 83 | 85 | +0.0 | +2.0 | +2.0 |
| es | 35 / 51 | 88 | 86 | 88 | −2.0 | +0.0 | +2.0 |
| vi | 39 / 55 | 83 | 78 | 81 | −5.0 p=.06 | −2.0 | +3.0 |
| th | 45 / 61 | 85 | 85 | 84 | +0.0 | −1.0 | −1.0 |
| sw | 47 / 63 | 56 | 53 | 56 | −3.0 | +0.0 | +3.0 |
| **bn** | 107 / 123 | 73 | 57 | 66 | **−16.0 p&lt;.001** | **−7.0 p=.14** | **+9.0 p=.012** (10/1) |
| **te** | 167 / 183 | 56 | 37 | 50 | **−19.0 p=.001** | **−6.0 p=.21** | **+13.0 p=.002** (15/2) |

en |Δ| ≤ 3pp vs baseline: **holds**.

bn/te vs default 64: real recovery. vs baseline: **not closed** (−7 / −6 pp).
Not the registered clean pass. Not a hard kill either — the *c*+ε
refinement is the honest reading, and arm B says the remaining gap is
dose: bn almost flat at *w*=176 (*c*+69, −3 pp); te still −13 pp at
*w*=176 (*c*+9).

**Gate call:** do not write “AutoWindow *c*+16 closes bn/te.” Write
“recovers most of the *w*=64 hole; residual sits past *c*+16.” Follow-up
if submitting ICLR: *w* = *c* + α*Q* or score/protect split (type A/B in
the fail brainstorm).

---

## B — cliff_multi

en: flat at every *w* (SAFE). **Match.**

th *w*32 −6.0 p=.07; *w*56 still −4; *w*88 0. Delayed heal.

sw *w*32 −7.0 p=.04; later −2…−4 on a 56% baseline. Direction only; do
not headline.

bn: *w*32/56/88 −13/−15/−21 (all p≤.007); *w*120 −8 p=.10; *w*176 −3.
Blind cells match; heal after *c*, not at *c*.

te: −19/−21/−18/−14/−13 at *w*32…176. Still broken at *w*=176 (*c*+9,
p=.019). Strongest evidence that +16 is an underdose for Telugu.

---

## A — English pad sweep (no baseline in this db)

Accuracy vs *w*144 (largest window):

| pad | w32 | w56 | w80 | w104 | w144 |
|---|---|---|---|---|---|
| 48 | 81 (+11 pp to 144, p=.001) | 87 | 92 | 92 | 92 |
| 64 | 86 (+7, p=.04) | 90 | 94 | 93 | 93 |
| 96 | 82 (+11, p=.001) | 90 | 89 | 90 | 93 |
| 128 | 78 (+13, p=.001) | 85 | 89 | 89 | 91 |

Cliff is real on English. Longer tail → worse *w*32. Saturation ~*w*80.
Pred “pad 48 flat at *w*=64”: *w*56 still 5 pp below *w*144 (p=.06) —
soft miss if *w*56 is the proxy; flat by *w*80.

---

## S — schema tail (does not kill)

AutoWindow here used **unpadded** English *w*=41, not schema-adjusted
*c*. That is smaller than the default 64, so AW cannot remove a
schema-induced blind.

| JSON | base | def 64 | AW 41 |
|---|---|---|---|
| 60 | 94 | 88 (−6 p=.11) | 88 (−6 p=.07) |
| 120 | 95 | 89 (−6 p=.03) | **72 (−23 p&lt;.001)** |
| 200 | 94 | 89 (−5 p=.13) | **75 (−19 p&lt;.001)** |

Default 64: mild ~5–6 pp hole. AW 41 on long schema: **hurts**, as
predicted by *w* &lt; *c*. Pred “AW removes it” fails because *w* was
not recomputed. Keep G2b / arm A as the English constructed instance.
If S is rerun: set *w* = *c*_schema+16.

---

## What to claim

- *w* vs *c* tracks damage directionally. en SAFE. bn/te BLIND at 64.
- Three levers still stand: widen *w* (E2 + D partial), move
  instruction (E1, disk), lengthen English tail (A).
- Do not claim a one-integer *c*+16 close. Residual on bn/te is the
  registered third outcome, sized by B’s *w*176 cell.
- S is a construction miss, not a mechanism miss.
