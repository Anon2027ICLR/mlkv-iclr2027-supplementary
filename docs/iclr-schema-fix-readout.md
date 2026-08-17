# Schema-fix readout — 2026-08-17

**Author: Fable (Claude).** R2 = `containment_match_lenient`, recomputed
from raw `output`. Paired on `item_id` within `results/schema_fix.db` only,
n=100/cell, McNemar two-sided. Preregister:
`docs/iclr-schema-fix-preregister.md` (predictions locked before generate).

**Stack note.** The pod reproduced the original environment exactly
(A6000, driver 580.159.03, torch 2.13.0+cu130, kvpress 0.5.4), so the
stack hash is the campaign's `d7368e8bd94a` and the re-run baselines are
token-identical to `schema-final.db` (greedy determinism, verified). All
comparisons below still stay inside this db.

On-pod `measure_c_schema.py`: c_schema = 72 / 166 / 213 for JSON pads
60/120/200 → \(\hat w\) = **90 / 184 / 231** (matches the dev-box lock).

## Numbers

| pad | base | def 64 | \(\hat w_{\text{schema}}\) | \(\hat w\)−base | \(\hat w\)−def64 |
|---|---|---|---|---|---|
| JSON-60 (\(\hat w\)=90) | 94 | 88 (−6, p=.11) | **96** | **+2** p=.63 | **+8\*** (8/0, p=.008) |
| JSON-120 (\(\hat w\)=184) | 95 | 89 (−6\*, p=.03) | **96** | **+1** p=1.0 | **+7\*** (7/0, p=.016) |
| JSON-200 (\(\hat w\)=231) | 94 | 89 (−5, p=.13) | **96** | **+2** p=.50 | **+7\*** (7/0, p=.016) |

\(\hat w\) breaks **zero** items that default-64 got right (f/b 8/0, 7/0,
7/0). For contrast, the old S arm's mis-sized \(w{=}41\) was −23 pp at
JSON-120 on the same items and stack.

## Preregister scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | baseline ≈ 94 ± 4 | 94 / 95 / 94 | hold |
| 2 | def64 damaged everywhere (c_schema > 64 at all pads) | −6 / −6\* / −5 | hold |
| 3 | **Main:** \(\hat w\) \|Δ\| ≤ 3 pp at all pads | +2 / +1 / +2 | **hold** |
| 4 | \(\hat w\) vs def64 ≥ +3 at 120/200 | +8\* / +7\* / +7\* (all three) | hold |
| 5 | Kill: any pad ≤ −8 | does not fire | — |

## What we may now write

- *The same formula, fed the schema-adjusted \(c\), closes the JSON tails
  it previously broke.* The S arm moves from "construction miss" to a
  generalization result: the remedy is about trailing blocks, not
  languages.
- JSON-120 (c_schema=166) is within one token of Telugu's \(c{=}167\) —
  same blindness dose, different cause, same fix.

## What we may not write

- That the old S run tested AutoWindow (it tested a mis-sized \(w\); keep
  that sentence in the appendix for honesty).
- Any pooling with `schema-final.db` rows in a single test (identical
  stack or not, the paper's rule stays within-db).

Paper consequence (plan §3 branch "close"): update `app:schema`, add one
main-text sentence in §"It is not about language".
