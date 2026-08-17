# V-trace arm — preregister

**Author: Fable (Claude).** Written 2026-08-17, *before* any `mlkv run` of
this arm. Driver: `scripts/e_iclr2.sh v_trace` (optional second block
`v_trace_bn`). DB: `results/v_trace.db`.
Analysis script committed WITH this preregister: `scripts/v_trace_bins.py`
— run it unedited on the finished db; that script (not a notebook, not an
ad-hoc REPL) is the arm's readout. This is the reproducibility fix for the
old 3,200-pair V-band table, whose exact cell composition was never pinned
by a committed script and which is language-confounded in the intermediate
bands (te/th-heavy).

## Why

\(V=\mathrm{clamp}((w-c)/Q,0,1)\) is the paper's contribution (ii), but no
experiment has traced it *within one language on parallel items*, where
tokenizer identity and item difficulty cannot masquerade as a V effect.
Because \(Q_i\) varies per item (te: \(Q_{50}=54\), \(Q_{90}=80\), range
~14–170), a single window already spreads V across items, and a ladder of
windows moves the SAME item through several V values — item fixed effects
then absorb difficulty.

## Design

Qwen3-4B, mRAG **te** (largest `c`, deepest hole, widest Q spread),
instr-last, ctx 8k, cap 384, n=100.

Configs: `baseline` + `snapkv@r0.75:w{c+4, c+16, c+32, c+48, c+80}`.
The OFFSETS {4, 16, 32, 48, 80} are locked; `c` is re-measured on-pod
(expected 167 → windows 171/183/199/215/247). 600 generations.

Expected median V per cell (dev-box numbers, \(Q_{50}=54\)):
≈ 0.07 / 0.30 / 0.59 / 0.89 / 1.0. The thinnest band of the old table
(0 < V < 0.25, n=4) is exactly where `c+4` and `c+16` put their mass.

`w=183` and `w=247` replicate the D-arm `c+16` and Q90-arm cells on a new
stack — a free replication check. **Do not pool** them with
`autowin-final.db` / `autowin_q90.db` (stack `d7368e8bd94a`); own baseline
lives in this db.

Optional secondary block (only if pod time remains): **bn** with locked
offsets {4, 16, 32, 48, 76} (76 = \(Q_{90}\)(bn); expected windows
111/123/139/155/183). Same predictions, same script.

## Per-item V

\(V_i = \mathrm{clamp}((w - c)/Q_i,\, 0,\, 1)\), with \(Q_i\) =
`len(tokenizer.encode(question))` of the eval item (run tokenizer, question
recovered via `meta.qid` from TyDiQA validation). Computed by
`v_trace_bins.py`, never by hand.

## Predictions (fixed)

1. Monotone in dose: mean paired damage vs baseline is non-increasing as
   `w` rises, with ±3 pp slack between adjacent cells.
2. Binned by \(V_i\) (bins 0–.25, .25–.5, .5–.75, .75–1, =1, pooling all
   five treated cells): the V=1 bin is |Δ| ≤ 3 pp; the V < 0.25 bin is
   ≤ −8 pp; bin means are monotone.
3. Within-item: cluster-robust logit of treated correctness on \(V_i\)
   across the five cells (items as clusters) has a positive coefficient,
   p < .05; among items whose correctness switches across cells, more
   items flip correct-at-high-V than the reverse (sign test p < .05).
4. Model comparison on treated rows (logit, AIC): `y ~ V` beats
   `y ~ (w−c)` (both 2 params). If `y ~ (w−c) + Q` matches `y ~ V`,
   report that honestly: V is then a convenient one-number
   reparametrization — still input-side, still zero-inference — not a
   deeper law.
5. Kill (kills the *dose-response claim for V*, not the threshold story):
   bin means flat (all within 4 pp of each other) AND AIC(V) worse than
   AIC(w−c) by > 2 → drop the V gradient claim; V stays as notation.
   Also possible and reportable, not hideable: a sharp step already flat
   at `c+4` — "a few visible question tokens suffice" is a finding, not a
   failure.

## Paper consequence (decided now)

Whatever this arm returns REPLACES the old V-band appendix table
(`app:v` in the draft). The old table is not regenerable from a committed
script and must not ship as-is.

Scoring: R2 from raw `output`. Never stored `correct`. Analysis:
`scripts/v_trace_bins.py` only.
