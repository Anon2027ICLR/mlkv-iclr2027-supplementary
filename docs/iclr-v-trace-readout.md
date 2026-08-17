# V-trace readout — 2026-08-17

**Author: Fable (Claude).** Readout = the committed
`scripts/v_trace_bins.py` run unedited on `results/v_trace.db` (as
preregistered in `docs/iclr-v-trace-preregister.md`). R2, paired within
this db, n=100/cell. Stack `d7368e8bd94a` (pod reproduced the campaign
environment; the shared cells — te baseline, w183, w247 — are
token-identical to `autowin-final.db`/`autowin_q90.db`: a deterministic
replication, still not pooled).

**Completeness.** te ran in full (600/600). The optional bn block was cut
mid-run (w111/w123 complete, w139 at 43/100; w155 and w183 never ran) —
bn is supporting-only below and must not enter any main table.

## te (primary, complete)

Per-window paired damage (base acc 56):

| w | w−c | median V | Δpp | fix/brk | p |
|---|---|---|---|---|---|
| 171 | **+4** | 0.08 | **−18\*** | 5/23 | .0009 |
| 183 | +16 | 0.31 | −6 | 5/11 | .21 |
| 199 | +32 | 0.62 | −4 | 4/8 | .39 |
| 215 | +48 | 0.92 | −4 | 6/10 | .45 |
| 247 | +80 (\(Q_{90}\)) | 1.00 | **0** | 6/6 | 1.0 |

**Headline: \(c+4\) recovers nothing** (−18 ≈ the w=64 hole's −19). The
step is not at \(c\); the required slack is on the order of \(Q\). This
replaces the vaguer "\(c+\varepsilon\)" narrative with a measured
dose curve, and it is the direct refutation of an English-sized slack.

V bins (pooled over treated cells): V<.25 **−16.1** (n=118, p=9e-4);
.25–.5 −4.8; .5–.75 −2.4; **.75–1 −11.9** (n=59, p=.065); V=1 **+0.7**
(n=135).

Marker-only robustness (stricter scorer, not the headline): base 50 →
w171 35 (−15) → w247 47 (−3). Conclusions unchanged.

## Preregister scorecard (te)

| # | Prediction | Result | |
|---|---|---|---|
| 1 | monotone in dose (±3 slack) | −18→−6→−4→−4→0 | **hold** |
| 2 | bins: V=1 flat, V<.25 ≤ −8, monotone | ends hold (+0.7 / −16.1); **.75–1 band −11.9 breaks monotonicity** | **miss** |
| 3 | within-item: logit + sign test | logit V +0.68, z=3.35, p=8e-4; switchers 21/2, p=1e-4 | **hold** |
| 4 | AIC(V) < AIC(w−c) | 689.8 < 692.1 (< 692.2 for (w−c)+Q) | **hold** |
| 5 | Kill: flat bins AND AIC worse | does not fire | — |

**The pred-2 miss, dissected** (after the fact, labeled as such): the
.75–1 band's damage is 9 distinct items (no double-counting), Q 40–81,
six of them from the single w215 cell. At V=1 (w247) 4 of the 9 recover —
so the band mixes "V≈0.9 is still an underdose for long questions" with a
few items that stay broken at any tested dose. n=59, p=.065 (ns). Report
the band honestly; do not claim per-item bin monotonicity, claim the
window-level dose curve (pred 1) plus the item-level trend (preds 3–4).

## bn (partial, supporting only)

w111 (c+4): **−17\*** (3/20) — same "c+4 recovers nothing" as te.
w123 (c+16): −7 (5/12). w139 (n=43): −2.3. Sign test 13/1 (p=.002);
AIC(V) = AIC(w−c) = 318.4 (tie → pred-4 gate MISS on this partial slice).
Do not quote the n=43 cell as a completed cell.

## Paper consequence (decided in the preregister)

This db **replaces** the old 3,200-pair V-band table in `app:v`. The new
appendix content: the te per-window table above, the two-end bins
(V<.25 −16.1 / V=1 +0.7), the within-item logit + sign test, and the
.75–1 caveat. The abstract's V sentence stays at "tracks the damage";
"monotone per-item dose-response" is allowed only with the band caveat
attached. `c+4` earns one main-text sentence: the slack must be
question-sized, not a constant.
