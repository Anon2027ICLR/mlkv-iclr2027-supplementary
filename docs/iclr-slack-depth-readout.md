# Slack ablation at depth (B1) — readout — 2026-08-24

**Author: Fable (Claude).** R2 from raw output; McNemar + exact CIs by
`closure_cis.py`'s method (script: `scripts/iclr9_readout.py`).
Preregister: `docs/iclr-slack-depth-preregister.md` (`96bd5e2`,
2026-08-23 15:42Z), no amendments. Store: `results/slack_depth.db`,
2,676 rows, stack **`d7368e8bd94a` — the campaign stack again.** All
driver guards passed (c=167, Q90=80, ŵ=247 re-derived on-pod, match);
first generation 2026-08-24 01:25:37Z, ≥ 9.7 h after the registration's
commit. Baseline and w247 cells are **byte-identical to `depth.db` on
all 1,338 shared rows** — the cleanest cross-arm determinism result of
the campaign, and it settles the prereg's drift clause: the "56%"
quoted there was the marker-only baseline (55.0); the lenient depth
baseline is 62.6 in both stores, drift exactly 0.

## The cells (n=669, te, own baselines)

| cell | value |
|---|---|
| baseline | 62.6 |
| c+16 (w183) vs baseline | **−10.3\*** (24/93, CI [−12.7, −7.4]) — certified residual |
| c+32 (w199) vs baseline | **−7.8\*** (18/70, CI [−9.8, −5.2]) — certified residual |
| ŵ=247 vs baseline | **−5.7\*** (19/57, CI [−7.8, −3.1]) — certified residual, = depth.db exactly |
| **PRIMARY: ŵ vs c+16** | **+4.6 in ŵ's favour (55/24, p=.0006, CI [+1.9, +7.0])** |
| ŵ vs c+32 | +2.1 in ŵ's favour (36/22, p=.087, CI [−0.3, +4.2]) |

Accuracies: 52.3 (c+16) → 54.9 (c+32) → 57.0 (ŵ): the dose curve that
was flat within noise at n=100 is monotone and separated at n=669.

Marker-only robustness: same ordering (43.9 → 45.1 → 45.6), h2h ŵ vs
c+16 = +1.6 (46/35, CI [−1.1, +4.3]) — direction agrees, not
certified. The lenient scorer is the registered primary; the paper
prints both, per the depth-arm precedent.

## Scorecard against the registered readings

| # | Registered reading | Result | |
|---|---|---|---|
| 1 | primary = paired McNemar + exact CI, w183 vs w247 | +4.6, p=.0006 | run as registered |
| 2 | **Q90 survives** iff CI excludes 0 in ŵ's favour AND gap ≥ 3pp | CI [+1.9, +7.0] ∌ 0, gap 4.6 ≥ 3 | **FIRES** |
| 3 | no-advantage branch (CI within ±2pp) | does not fire | — |
| 4 | intermediate | does not fire (reading 2 met in full) | — |
| 5 | c+32 vs ŵ reported alongside | +2.1, CI [−0.3, +4.2], ns | reported |
| 6 | per-window Δ vs own baseline, exact CIs | table above | reported |
| 7 | determinism ledger on the depth.db overlap | 1,338/1,338 byte-identical | informational |

**Binding branch: reading 2 — the Q90 component survives its
separation test at the paper's most powerful sample.** Section 5 keeps
its shape; contribution (iii) stands as written, now backed by a
preregistered head-to-head instead of the unregistered pooled p=.027,
which is retired.

On reading 5's wording: c+16 is certifiably worse than ŵ, c+32 is not
separated from ŵ (point +2.1 toward ŵ, CI spans 0). The honest
sentence is therefore *not* "Q50 suffices" — c+32 ≈ c+Q50−22 was never
a Q50 arm — but: the advantage of question-sized slack over c+16 is
certified (+4.6 [+1.9, +7.0]); over c+32 the point estimate still
favours ŵ but the interval includes 0. Every window below ŵ leaves a
strictly larger certified residual. No re-tuning, no new percentile.
