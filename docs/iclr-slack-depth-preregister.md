# Slack ablation at depth (B1) — preregister

**Author: Fable (Claude).** Written 2026-08-24, *before* any generation
of this arm exists. Driver: `scripts/e_iclr9.sh b1` (chain block 1).
Store: `results/slack_depth.db`, self-contained (own baselines, own
stack, pairs only within itself).

Answers reviewer-4 W1/Q1: the central component of the rule (Q90) has
never been separated from a trivial constant slack at the paper's most
powerful sample. The n=100 dose ladder shows the big step between c+4
and c+16; from c+16 on, the curve is flat within noise; the direct
c+16→ŵ comparison is +5/+6pp, each ns, pooled p=.027 — and that pooling
was not preregistered. At the full pool, ŵ leaves −5.7 (certified) while
c+16 was never run there. This arm runs it.

## Stopping rule, fixed first

Final n = the entire TyDiQA-GoldP Telugu validation pool, 669 items —
the depth arm's everything-there-is rule, reused verbatim. No free
parameter. Bengali is NOT extended: its pool caps at 113 and adds no
power beyond the existing n=100 c+16 cell.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384:

- te × 669: `baseline`, `snapkv@r0.75:w183` (c+16),
  `snapkv@r0.75:w199` (c+32), `snapkv@r0.75:w247` (ŵ = c+Q90).

= 2,676 generations. w247 is re-run here although `depth.db` certifies
it, because the decisive head-to-head (w183 vs w247) must pair within
one store. The driver re-derives c (167), Q90 (80) and ŵ (247) on-pod
and aborts on mismatch; the held-out/eval disjointness guard from the
depth arm runs unchanged.

## Registered readings (fixed now, before any row)

1. **Primary comparison:** paired McNemar + exact conditional 95% CI,
   w183 vs w247, 669 items, offline scoring
   (`containment_match_lenient`; marker-only as robustness).
2. **Q90 survives** iff the head-to-head CI excludes 0 in ŵ's favour
   AND the point gap is ≥ 3pp. Then Section 5 keeps its shape and the
   paper gains its strongest pro-Q90 number.
3. **Q90 has no demonstrated advantage** if the head-to-head CI lies
   within ±2pp. Committed consequence: contribution (iii) is rewritten
   from "the slack must be question-sized" to "the window must clear c
   with adequate slack; Q90 is a principled, measurement-only choice
   that never underperformed"; the FINCH and protection-budget
   comparisons are softened to match. No re-tuning, no new percentile,
   no substitute comparison.
4. Intermediate outcomes (CI excludes 0 but gap < 3pp, or CI spans
   [−2, +something]) are reported as what they are: a real but small
   Q90 advantage, stated with its interval, and the abstract does not
   round it up.
5. c+32 vs ŵ is reported the same way wherever c+16 is. If c+32 ≈ ŵ
   but c+16 < ŵ, the honest sentence is "slack of roughly Q50, not
   Q90, suffices on this pool" and the paper says it.
6. Each window's Δ vs its own baseline is reported with the same
   exact CI as the depth arm (fixed/broken counts shown).
7. The baseline and w247 cells overlap `depth.db`;
   `determinism_ledger.py` counts cross-stack byte-identity after the
   pull. Informational, not a gate: within-store pairing carries every
   claim.

## Kill conditions

None for the phenomenon: the −20.2pp default hole stands regardless.
Reading 3 is the pre-accepted loss branch for the rule's Q90 component.
If the baseline accuracy drifts by more than 3pp from depth.db's 56%
(non-byte-identical stack), we still pair within-store and say so.

Scoring: never the stored `correct`; every number recomputed offline by
the audit script, which gains a `slack_depth` section before any number
enters the tex.
