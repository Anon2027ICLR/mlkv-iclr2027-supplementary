# Thai and Swahili at their own ŵ (B3) — readout — 2026-08-24

**Author: Fable (Claude).** R2 from raw output; exact CIs by
`closure_cis.py`'s method. Script: `scripts/iclr9_readout.py`.
Preregister: `docs/iclr-thsw-preregister.md` (`96bd5e2`, 2026-08-23
15:42Z) **plus the 2026-08-24 amendment** (`1a7959c`, 16:21Z, still
before any generation): the Swahili raw-split duplicate decision —
guard keyed to the registered eval set (val[:100]), Q90_sw=20
unchanged with or without the two duplicate ids, full-pool use would
require re-registration. Store: `results/thsw.db`, 600 rows, stack
`d7368e8bd94a`. On-pod guards passed: c = 45/47, Q90 = 46/20,
val[:100] ∩ Q90-source = ∅ for sw; th disjoint by split.

## The cells (n=100 per language, own baselines)

| cell | value |
|---|---|
| th baseline | 85.0 (campaign 85, drift 0.0) |
| **th ŵ=91 vs baseline (GATE)** | **−1.0 (1/2, CI [−2.9, +2.4]) — gate MET, non-inferior at −3pp** |
| th w64 vs baseline | +0.0 (1/1, CI [−1.9, +1.9]) |
| sw baseline | 56.0 (campaign 56, drift 0.0) |
| **sw ŵ=67 vs baseline (GATE)** | **−3.0 (2/5, CI [−6.5, +2.9]) — gate MET at the boundary; interval too wide for ±3pp** |
| sw w64 vs baseline | −3.0 (2/5, CI [−6.5, +2.9]) |

sw's ŵ sits 3 tokens above the default; the two windows change 33/100
outputs but land on the same aggregate Δ. Both languages sit above
threshold at the default, as predicted — no recovery was predicted and
none was needed.

Marker-only scoring is uninformative for both languages (baselines
collapse to 13/9% — the known th/sw marker behaviour) and is not part
of the gate.

## Scorecard against the registered readings

| # | Registered reading | Result | |
|---|---|---|---|
| 1 | gate \|Δ\| ≤ 3pp at ŵ, exact CI beside it | th −1.0 MET; sw −3.0 MET (boundary) | **both gates met** |
| 2 | a double pass adds th+sw: evaluated set 3/8 → 5/8 | fires | **counts** |
| 3 | miss branch | does not fire | — |
| 4 | ŵ vs w64 context | th 0.0 / −1.0; sw −3.0 / −3.0 | reported |
| 5 | baseline drift check (> 5pp) | 0.0 / 0.0 | clean |

**Binding reading: both closure gates are met at the languages the
rule was never run on.** Thai is additionally non-inferior at −3pp by
interval (lower bound −2.9); Swahili meets the registered point gate
exactly at the boundary and its n=100 interval is wide
([−6.5, +2.9]) — the paper prints the vocabulary distinction, as with
the other n=100 closure rows. The reviewer's "tested only where it
wins" hole is closed: the evaluated set is now en, bn, te, th, sw
(5/8), with no gate miss added.
