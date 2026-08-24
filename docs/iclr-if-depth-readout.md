# Instruction-first Telugu at depth (B4) — readout — 2026-08-24

**Author: Fable (Claude).** R2 from raw output; exact CIs by
`closure_cis.py`'s method; item audit in proportion-test form (Fisher
exact). Script: `scripts/iclr9_readout.py`. Preregister:
`docs/iclr-if-depth-preregister.md` (`96bd5e2`, 2026-08-23 15:42Z), no
amendments. Store: `results/if_depth.db`, 1,338 rows, stack
`d7368e8bd94a`. The n=100 `instr_first.db` cells are a subset:
**byte-identical on all 200 shared rows** (100 baseline + 100 w64),
same stack.

## The cells (n=669, te, instr-first layout, own baseline)

| cell | value |
|---|---|
| IF baseline | 59.8 |
| **IF w64 vs IF baseline** | **−3.4\* (16/39, p=.0027, CI [−5.3, −1.2])** — confirmed residual |
| reference: ŵ residual, instr-last full pool (depth.db) | −5.7\* (CI [−7.8, −3.1]) |

Item audit (broken n=39 vs pool n=669, Fisher exact): gold position
front/middle/back = 25.6/43.6/30.8% of broken vs 33.3% each in the
pool (p = .38/.17/.86); |Q| > median(52) = 59.0% vs 49.2% (p=.25);
|Q| > Q90(79) = 15.4% vs 9.6% (p=.25). **No significant concentration
by position or question length** — the damage looks like ordinary
eviction cost, not a hidden visibility mode. The 51/57 raw-fraction
style is retired as registered.

Marker-only scoring is uninformative here and is reported only as a
caveat: the IF layout collapses `####` compliance (baseline 5.5%),
the known layout-marker behaviour of Appendix `app:levers`; the
marker-only Δ (+1.0, ns) measures marker emission, not answers.

## Scorecard against the registered readings

| # | Registered reading | Result | |
|---|---|---|---|
| 1 | primary paired Δ + exact CI, offline | −3.4, CI [−5.3, −1.2] | run as registered |
| 2 | **(iv) confirmed** iff CI excludes 0 AND point within ±3pp of −5.7 | CI ∌ 0; \|−3.4 − (−5.7)\| = 2.3 ≤ 3 | **FIRES** |
| 3 | retraction branch (CI ∋ 0, \|point\| ≤ 2) | does not fire | — |
| 4 | intermediate | does not fire | — |
| 5 | item audit as proportion tests | table above, no signal | reported |
| 6 | byte-identity vs instr_first.db | 200/200 | informational |

**Binding branch: reading 2 — contribution (iv) is confirmed at
power.** With the question fully visible by construction (V=1), the
default window still costs Telugu −3.4pp with a CI excluding 0, within
2.3pp of the ŵ residual on the instr-last pool. The residual is
layout-independent ordinary eviction cost; the n=100 ns cell
(−6, CI [−7.9, +0.4]) is superseded by this certified one. The paper
may now say "confirmed", not "consistent with", and the item audit
backs it in the registered format.

Note the point ordering for honest wording: the IF residual (−3.4
[−5.3, −1.2]) is nominally *smaller* than the ŵ residual (−5.7
[−7.8, −3.1]); the intervals overlap and the registered ±3pp
equivalence is met, but the paper should not describe them as "the
same number" — "statistically indistinguishable, both certified below
zero, gap 2.3pp inside the registered band" is the accurate sentence.
