# Query-agnostic baseline — readout — 2026-08-18

**Author: Fable (Claude).** R2 from raw output, paired within
`results/agnostic.db`, n=100/cell, McNemar + exact CIs. Preregister:
`docs/iclr-agnostic-baseline-preregister.md` (locked). Stack
`d7368e8bd94a`; the 300 baseline rows are byte-identical to
`autowin-final.db`. The optional TOVA block ran, so the arm carries two
non-window scorers, not one.

## Numbers (Δpp vs baseline, ratio 0.75 throughout)

| lang | base | Expected Attention | TOVA | SnapKV w64 (ref) | SnapKV ŵ (ref) |
|---|---|---|---|---|---|
| en | 93 | **−14\*** (4/18, p=.0043, CI [−19.7,−4.3]) | **−8\*** (1/9, p=.022) | +0 | +2 |
| bn | 73 | **−18\*** (6/24, p=.0014, CI [−25.4,−6.9]) | **−16\*** (4/20, p=.0015) | −16\* | −2 |
| te | 56 | **−20\*** (5/25, p=.0003, CI [−26.6,−9.2]) | **−18\*** (4/22, p=.0005) | −19\* | 0 |

(Reference columns from `autowin-final.db`/`autowin_q90.db`, same stack,
same items.)

## Scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | **Main:** EA does not rescue Bengali (≤ −10) | −18\*, CI entirely below −6.9 | **hold** |
| 2 | th loses at least as much as bn under EA | **unscoreable as written** — a design error in the preregister: the prediction names Thai but the locked arm runs en/bn/te. Flagged, not reinterpreted. The substitute evidence for the same claim ("EA's damage does not follow c") is English: c=25, fully safe for SnapKV at 64, yet EA costs it 14 points. | flagged |
| 3 | en damaged under EA | −14\* | **hold** |
| 4 | risk: EA bn within 5 of baseline → advice changes | −18; does not fire | — |

## Reading

The reviewer's proposed alternative — *switch to a scorer that cannot
be blinded* — makes everything worse. Expected Attention loses as much
as blinded SnapKV on Bengali (−18 vs −16), more on Telugu (−20 vs −19),
and, unlike SnapKV, also loses 14 points on English, where SnapKV at
any tested window loses nothing. TOVA, the optional second non-window
scorer, shows the same shape (−8/−16/−18). Both pay a large,
language-blind tax at the same ratio where sized-window SnapKV pays
+2/−2/0. Blindness is a *fixable* failure; being query-agnostic is a
permanent one.

## Integration memo

- §7's existing sentence about Expected Attention (currently citing the
  old cap-128 direction, "damages Thai rather than Bengali") should be
  replaced by this arm's clean numbers and repointed: it is no longer
  only an honest null, it is the answer to "why not switch scorer".
- New appendix rows/table (can share an appendix with the ratio arm:
  "rival remedies at the same ratio").
- Never write: "query-agnostic scorers fail on low-resource languages"
  (they fail everywhere — that is the point); any claim about Thai
  under EA at cap 384 (not run).
- Must disclose: the pred-2 design error, exactly as the scorecard
  states it.
