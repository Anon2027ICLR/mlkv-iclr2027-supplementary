# Bengali dose ladder, completed — readout — 2026-08-18

**Author: Fable (Claude).** Analysis = `scripts/v_trace_bins.py --db
results/v_trace_bn.db`, unedited, as the preregister requires.
Predictions inherit from `docs/iclr-v-trace-preregister.md` (offsets
4/16/32/48/76, locked). Stack `d7368e8bd94a` — the pod reproduced the
campaign environment a fourth time; the 343 generations shared with
`v_trace.db` are byte-identical.

## Numbers (base 73, n=100/cell)

| w | w−c | med V | Δpp | f/b | p |
|---|---|---|---|---|---|
| 111 | 4 | 0.09 | **−17\*** | 3/20 | .0005 |
| 123 | 16 | 0.34 | −7 | 5/12 | .14 |
| 139 | 32 | 0.68 | −3 | 4/7 | .55 |
| 155 | 48 | 1.00 | −5 | 3/8 | .23 |
| 183 | 76 (=Q₉₀) | 1.00 | −2 | 6/8 | .79 |

Bins: V<.25 **−14.0** (5/23, p=9×10⁻⁴); .25–.5 −7.4; .5–.75 −5.7;
.75–1 −8.5 (ns); V=1 **0.0** (9/9). Within-item: sign test **18/1**
(p=10⁻⁴); cluster logit on V +0.648 (z=2.95, p=.0032); AIC: V 637.7 <
(w−c) 639.7 < (w−c)+|Q| 641.5.

## Scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | monotone in dose (±3 slack) | −17→−7→−3→−5→−2 | **hold** |
| 2 | per-item bins monotone, ends anchored | ends hold (V<.25 −14, V=1 exactly 0); .75–1 band −8.5 ns breaks the middle — the same shape as Telugu | **miss**, same as te |
| 3 | within-item trend | 18/1, logit p=.0032 | **hold** |
| 4 | AIC(V) < AIC(w−c) | 637.7 < 639.7 — the partial block's tie resolves in V's favour with full data | **hold** |
| 5 | kill | does not fire | — |

**The paper's dose story is now two-language.** Bengali mirrors Telugu
rung for rung: four visible question tokens buy nothing (−17 vs te's
−18, both ≈ their w=64 holes), and the curve is flat only at V=1.
Reviewer Q3 ("why was the Bengali block cut at 43/100?") is answered by
completion: the block was an optional pod-schedule casualty and is now a
full, preregistered replication. The partial-cell caveats in §5 and
Appendix F are superseded.

## Integration memo

- §5: replace the partial-replication sentence with the completed one
  (two-language symmetry; cite both c+4 cells).
- Appendix F: replace the partial-block paragraph with the full ladder
  (table or inline numbers), note the AIC tie resolving to V, and keep
  the .75–1 caveat with its two-language shape.
- Add `v_trace_bn` to the reproducibility store list and the audit.
- Never write: per-item bin monotonicity (still misses in the same band
  on both languages).
