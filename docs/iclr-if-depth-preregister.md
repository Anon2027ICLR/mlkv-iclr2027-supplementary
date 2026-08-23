# Instruction-first Telugu at depth (B4) — preregister

**Author: Fable (Claude).** Written 2026-08-24, *before* any generation
of this arm exists. Driver: `scripts/e_iclr9.sh b4`. Store:
`results/if_depth.db`, self-contained.

Answers reviewer-4 W5/Q8: contribution (iv) — "the residual is not a
visibility failure" — currently rests on an n=100 ns cell:
instruction-first (question-last, V=1 by construction) at w=64 costs
Telugu −6pp with CI [−7.9, +0.4]. The certified ŵ residual on the full
pool is −5.7 [−7.8, −3.1]. Whether those two are the same number is
exactly what n=100 cannot say and n=669 can.

## Stopping rule

Final n = the entire Telugu validation pool, 669 items (the depth
arm's rule, verbatim). No free parameter.

## Arm

Qwen3-4B, mRAG **instr-first** (`--mrag-layout instr-first`, item ids
`mragIF-te-`), ctx 8k, cap 384:

- te × 669: `baseline` (IF layout's own baseline),
  `snapkv@r0.75` (w=64).

= 1,338 generations. Every window sees the whole question by
construction (V=1), so w=64 needs no companion window here; what is
being measured is eviction cost with visibility removed from the
picture. The IF baseline is the comparator — layout effects on the
uncompressed model (the Thai marker behaviour of Appendix
`app:levers`) stay out of the compression difference by construction.

## Registered readings (fixed now)

1. **Primary:** paired Δpp of w=64-IF vs IF baseline on 669 items,
   exact conditional 95% CI, offline scoring; marker-only robustness
   beside it (the depth-arm precedent).
2. **Contribution (iv) confirmed** if the CI excludes 0 and the point
   estimate sits within ±3pp of the ŵ residual (−5.7): the residual is
   layout-independent ordinary eviction cost, now certified at power.
   Expected branch.
3. **Contribution (iv) retracted to its n=100 cells** if the CI
   includes 0 with |point| ≤ 2pp: full visibility removes the
   residual, so the ŵ residual is NOT plain eviction cost and the
   paper must say the diagnosis failed at depth. Pre-accepted loss
   branch — the four gate-miss cells then carry an open question, not
   a diagnosis.
4. Intermediate outcomes reported with their intervals, no rounding
   toward either branch.
5. Item-level audit in proportion-test form (per the new residual
   readout format): among items broken by w=64-IF, the shares by gold
   position and by |Q| decile, against the pool's shares. The 51/57
   raw-fraction style is retired.
6. The IF n=100 items are a subset of this pool; byte-identity of the
   shared generations is counted by `determinism_ledger.py`
   (informational — `instr_first.db` sits on the campaign stack).

## Kill conditions

None beyond reading 3's committed retraction. The arm cannot hurt the
phenomenon or the recovery numbers; it can only settle what the
residual is.

Scoring: offline, audit section `if_depth` added before any number
enters the tex.
