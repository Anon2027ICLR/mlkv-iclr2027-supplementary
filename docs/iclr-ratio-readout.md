# Heavy-ratio sweep — readout — 2026-08-18

**Author: Fable (Claude).** R2, paired within `results/ratio.db`,
n=100/cell, McNemar + exact CIs. Preregister:
`docs/iclr-ratio-sweep-preregister.md` (locked). Stack `d7368e8bd94a`;
the 200 baseline rows are byte-identical to `autowin-final.db`. Retained
budget at r=0.9375 on the 8k prompts is ≈512 tokens, so w=256 protects
half the surviving cache.

## Numbers (r = 0.9375, Δpp vs uncompressed baseline)

| | en (base 93) | bn (base 73) |
|---|---|---|
| default w=64 | 91 (−2, ns) | 29 (**−44\***, CI [−47.5,−34.3]) |
| ŵ (43 / 183) | 92 (−1, ns) | 49 (**−24\***, CI [−27.5,−14.8]) |
| w=256 | 84 (**−9\***, p=.049, CI [−14.7,−0.0]) | 45 (**−28\***, CI [−33.8,−17.2]) |

Pairwise: bn w64→ŵ **+20\*** (22/2, p<10⁻⁴, CI [+11.0,+23.5]);
bn w64→256 +16\* (p=.0025); bn 256→ŵ +4 (ns).
en w64→256 −7 (ns, CI [−13.5,+2.0]); en 256→ŵ +8 (p=.077);
en w64→ŵ +1.

## Scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | bn ŵ recovers vs default at 0.9375 | **+20\*** — the largest single recovery in the campaign | **hold** |
| 2 | the tax is real: en w256 ≤ −4 vs w64 | −7 (point gate met; ns vs w64 at p=.14, and −9\* vs baseline at p=.049) | **hold on the point gate; significance is vs baseline, not vs w64 — say both** |
| 3 | en ŵ within 3 of w64 | +1 | **hold** |
| 4 | ŵ weakly dominates 256 (no cell where 256 wins by >3; ≥1 where ŵ wins by >3) | 256 never beats ŵ (en −8, bn −4 for 256); ŵ beats 256 by 8 on en | **hold** |
| 5 | negative branch (en 256 flat) | does not fire | — |

## Reading

Three facts, one per audience. For the deployer: at heavy eviction the
rule still buys the largest recovery measured anywhere in this paper
(+20 on Bengali) — but nothing rescues Bengali fully at r=0.9375 (−24
residual under ŵ), which is exactly what the deployer-guidance sentence
("lower the ratio") predicts. For the "just use a big window" reader:
the window tax our Limitations predicted is now measured — w=256 costs
English 9 points against baseline at this ratio while ŵ_en=43 costs
one — and the big constant never beats the measured one anywhere. For
the Limitations section: its prediction gets a citation instead of a
promise.

Honest cavils: the en tax is significant against baseline (p=.049,
interval touching 0.0) but not against w64 (p=.14) at n=100; and the bn
dominance margin over 256 is +4 (ns) — the dominance claim is carried
by English, and the readout says so.

## Integration memo

- Limitations: the "at heavier ratios that separation may become
  necessary" clause now cites measured numbers instead of predicting.
- §6 (or Limitations): the one-big-constant paragraph — a bigger
  constant is still a constant, and now also measurably worse: −9\* on
  English at r=0.9375 where ŵ costs −1, and never better than ŵ.
- Appendix table (shared with the agnostic arm).
- Never write: "the tax is significant vs the default window" (it is
  significant vs baseline); "ŵ dominates 256 on Bengali" (+4, ns);
  "ŵ closes at heavy ratio" (−24\*).
