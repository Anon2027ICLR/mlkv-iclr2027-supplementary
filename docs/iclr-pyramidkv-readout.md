# PyramidKV transfer — readout — 2026-08-18

**Author: Fable (Claude).** R2 from raw output, paired within
`results/pyramidkv.db`, n=100/cell, McNemar + exact CIs. Preregister:
`docs/iclr-pyramidkv-preregister.md`, committed 01:15 UTC — twelve
minutes before the first generation (01:27 UTC), so this arm joins the
commit-precedes-run column. The optional te block ran, so the arm
carries both blind languages.

**Stack note, first of its kind.** The pod did *not* reproduce the
campaign stack: `c8fd7773c51a` vs `d7368e8bd94a` (driver 580.159.04 vs
.03, different host kernel; same GPU model, torch, kvpress,
transformers). All pairing below is within-store, and the SnapKV numbers
quoted beside it are cross-stack context, not comparators. The drift
bought an unplanned measurement: the 300 baseline generations this store
shares with `autowin-final.db` are **byte-identical across the stack
boundary** — the campaign's first cross-stack determinism evidence.
`determinism_ledger.py` is now stack-aware and tallies it separately
(same stack: 3,243/3,243, the paper's number, unchanged; cross stack:
300/300, quoted apart, never pooled).

## Numbers (Δpp vs own baseline; SnapKV context in brackets)

| lang | base | pyramidkv w=64 | pyramidkv ŵ | recovery w64→ŵ | [snapkv w64 / ŵ] |
|---|---|---|---|---|---|
| bn | 73 | **−28\*** (3/31, CI [−32.7,−17.9]) | −2 (6/8, CI [−9.1,+5.9]) | **+26\*** (29/3) | [−16\* / −2] |
| en | 93 | +2 (3/1) | +0 (1/1, CI [−1.9,+1.9]) | −2 | [+0 / +2] |
| te | 56 | **−32\*** (3/35, CI [−36.7,−21.8]) | −1 (5/6, CI [−7.3,+5.9]) | **+31\*** (32/1) | [−19\* / 0] |

ŵ = 183/43/247 — the shipped AutoWindow integers, unchanged; the driver's
on-pod re-measurement matched them (the config names are the proof).

## Scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | hole reproduces on the second method (bn ≤ −10, sig.) | **−28\***, CI entirely below −17.9 | **hold** |
| 2 | **main — the integer transfers** (bn ŵ within ±3; recovery ≥ +8, sig.) | −2 on the point gate; **+26\*** (29/3, p<10⁻⁴) | **hold** |
| 3 | safe-language control (both en cells within ±3) | +2 / +0 | **hold** |
| 4 | te optional (default ≤ −10; ŵ within ±3) | **−32\*** / −1 | **hold** |
| 5 | kill (no hole at default) | does not fire | — |
| 6 | risk (hole but no transfer) | does not fire | — |

## Reading

The strongest possible outcome for the "obvious remedy" objection. The
same three integers, derived offline from the prompt and never re-tuned,
dropped into a second published method of the family, remove holes that
are **deeper than SnapKV's** (−28/−32 vs −16/−19) and land at −2/+0/−1 —
the same gate SnapKV met. The recoveries (+26, +31) are the two largest
in the campaign. One number that fixes two methods is not a tuned
hyperparameter; it is a measurement of the prompt.

The deeper holes deserve one honest clause: the preregister's prose
guessed the pyramid allocation would *shallow* the hole (hence the −10
floor) and it deepened it instead — plausibly because the tighter
upper-layer budgets amplify a blind scorer's mistakes, but we did not
preregister that mechanism and should state it as observation, not
explanation. The gate was ≤ −10, so the prediction holds either way.

Sanity, checked rather than assumed: pyramidkv@w64 outputs differ from
snapkv@w64 on 73/100 bn items (it really is a different allocation; the
27 identical are items where both presses survive), zero empty or
degenerate outputs, and the blind cells' at-cap rate rises modestly
(bn 11%, te 21% vs 6/11% at baseline) — rambling on broken items, in
line with every earlier arm, not the driver of a 28-point hole.

## Integration memo (for the next Opus round; do not act before then)

- §6, after the scale/third-family paragraph or inside "The rule": the
  preregistered sentence — *the integer is a property of the prompt, not
  of the method: dropped unchanged into PyramidKV, which inherits the
  same shipped window, it removes the same hole* — with the two deltas
  and Appendix ref.
- `app:rivals` gains a third block (or the agnostic table gains a
  pyramidkv column pair) and its title extends: rival remedies, *and a
  second member of the family*.
- Reproducibility: store list 15→16 (`pyramidkv`); prereg count 6→7 of
  ten; README table gains the row (commit `74840de` 01:15 UTC, first
  generation 01:27 UTC, yes).
- Provenance appendix: one sentence for the cross-stack 300/300, quoted
  separately from the same-stack 3,243 (ledger now prints both).
- Audit: six new deltas + two recoveries + stars; the `tab:rivals`
  loader pattern extends directly.
- Never write: "closes on the second method" (bn/te ŵ CIs span ±7–9, the
  same width as SnapKV's — gate vocabulary only); "pyramid allocation is
  worse under blindness" as a general claim (two languages, one model,
  unregistered mechanism); never pool any pyramidkv cell with a
  `d7368e8bd94a` cell — context brackets only.
