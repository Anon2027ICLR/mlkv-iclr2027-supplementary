# Instruction-first at cap 384 — readout — 2026-08-17

**Author: Fable (Claude).** R2 from raw `output`, McNemar +
exact-conditional 95% CI. Preregister:
`docs/iclr-instr-first-preregister.md` (locked). Primary comparisons are
within `results/instr_first.db`; the pod reproduced the campaign
environment again (stack `d7368e8bd94a`, token-identical shared
machinery), so the cross-layout comparisons on matched question index
against `autowin-final.db` are within-stack and reported as secondary,
as the preregister allows. The optional th block ran.

## Numbers

Within-layout (instruction-first baseline → instruction-first default
window):

| lang | IF base | IF w64 | Δ (CI) |
|---|---|---|---|
| en | 96 | 95 | −1 \([-2.9,+2.4]\) |
| bn | 74 | 70 | **−4** (3/7, p=.34, CI \([-8.7,+3.0]\)) |
| te | 57 | 51 | **−6** (1/7, p=.070, CI \([-7.9,+0.4]\)) |
| th | 80 | 79 | −1 \([-2.9,+2.4]\) |

Cross-layout, same stack, same question index (secondary):

| lang | last-w64 → IF-w64 | last-base → IF-base |
|---|---|---|
| bn | **+13\*** (16/3, p=.0044) | +1 (ns) |
| te | **+14\*** (22/8, p=.016) | +1 (ns) |
| en | +2 (ns) | +3 (ns) |
| th | −6 (ns) | **−5** (2/7, ns) |

## Preregister scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | **Main:** bn and te at w64 \|Δ\|≤3 vs IF baseline | bn −4, te −6 | **miss on the point gate** (both ns; CIs do not exclude 0) |
| 2 | en flat | −1 | hold |
| 3 | layout main effect small | bn +1, te +1; th −5 (the th cost sits in the *baseline*, not in compression) | hold, with the th caveat |
| 4 | th exploratory | IF adds no compression tax for th (−1); the −5/−6 vs instr-last is a layout effect on the uncompressed model | reported |
| 5 | **Kill: bn or te ≤ −8** | −4 and −6 | **does not fire** |

## Reading (labeled post hoc)

The outcome sits between the preregistered pass and the kill. Putting
the question last removes about three quarters of the hole — Bengali
16 → 4, Telugu 19 → 6 — with recovery over instruction-last confirmed at
+13/+14 pp (both p<.02). What remains, 4–6 pp and not significant, is
the same size as the residual seen everywhere else the question is fully
visible: Gemma-bn −6, 8B-bn −8, Llama-bn −8, all at V≈1. This arm
measures that residual *directly on the primary 4B model*, with V=1 by
construction rather than by percentile: the press has a small cost that
visibility does not explain, and the paper's boundary paragraph now has
an in-model measurement behind it instead of only two cross-model
diagnoses. That strengthening was not predicted — the preregister
expected ≈0 — and is reported as a reading, not a confirmed prediction.

Scoring caveat: th under instruction-first drops the marker in 43/100
outputs (lenient and marker-only agree the compression delta is ~0, so
the th conclusion stands, but the IF-vs-last baseline shift for th
partly tracks format behaviour).

## Integration memo (plan §4 — the branch between the two written ones)

Pred 1 did not hold as written, and the kill did not fire, so neither
§4 branch applies verbatim. Recommendation for the writer:

- Build the two-remedies table anyway — it is more honest than the
  predicted version, not less: per language at matched retained KV,
  instr-last w64 (blind), instr-last \(\hat w\), instr-first w64. It
  shows the layout remedy and the measurement remedy landing at the same
  place, both leaving the same small non-visibility residual.
- Rewrite the §6 boundary paragraph to cite this arm: the residual now
  has a direct V=1-by-construction measurement on the primary model.
- May write: "moving the question to the end of the prompt removes most
  of the hole (+13/+14 pp over instruction-last) and leaves 4–6 pp (ns)
  that visibility cannot explain — the same residual the formula leaves."
- Never write: "the layout remedy costs nothing" (th baseline −5);
  "visibility explains the entire hole" (it explains ~3/4 of it);
  "prediction confirmed" for pred 1 (it missed the point gate).
- App K's cap-128 numbers can now be demoted to a historical note, as
  the preregister planned — the clean +13/+14 replaces the old +14/+22.
