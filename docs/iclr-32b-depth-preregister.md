# Qwen3-32B Telugu at depth (B5, the closing arm) — preregister

**Author: Fable (Claude).** Written 2026-08-25, *before* any generation
of this arm exists; locked at the F23 commit. Driver:
`scripts/e_iclr10.sh b5` on its own 80GB pod. Store:
`results/qwen32b_depth.db`, self-contained (own baselines, own stack;
never pooled with any other store).

Motivation. The B3 slice left exactly one ambiguous cell in the paper:
Telugu at 32B, where $n{=}100$ cannot distinguish a hole from noise
($-4.0$, 8/12, CI $[-12.4,+5.6]$). Every other load-bearing cell is
either certified or closed on a registered branch. This arm applies
the campaign's standard resolution — the everything-there-is stopping
rule — to that cell. It is the last preregistered arm before the
deadline; if its pod has not started by 2026-09-10, the arm is
dropped and the paper keeps the honest inconclusive sentence.

## Stopping rule

The entire TyDiQA-GoldP Telugu validation pool, 669 items (the depth
rule, verbatim). No free parameter. Bengali is NOT extended: its pool
caps at 113 and adds no power (the ICLR9 precedent).

## Arm

Qwen3-32B, mRAG instr-last, ctx 8k, cap 384:

- te × 669: `baseline`, `snapkv@r0.75` (w=64),
  `snapkv@r0.75:w247` ($\hat w$).

= 2,007 generations. The driver re-derives $c{=}167$ and $Q_{90}{=}80$
on the 32B checkpoint and aborts on mismatch; the Telugu full-pool
disjointness guard runs unchanged. The B3 $n{=}100$ cells are a
subset; byte-identity of the shared 300 generations is counted by the
determinism ledger (informational — a new pod is a new stack, so this
is expected to be a cross-stack measurement).

## Scoring caveat, registered up front

32B emits the answer in prose and copies the instruction's placeholder
after the `####` marker (the B3 readout), so the marker-only scorer is
uninformative for this model and every number rides the registered
lenient scorer's first-sentence branch. This is stated here, before
the data, so it cannot read as a post-hoc excuse on either branch.

## Registered readings (fixed now, before any row)

1. **Primary:** paired Δpp of w=64 vs own baseline on 669 items,
   exact conditional 95% CI, offline lenient scoring.
2. **Hole-persists branch:** the CI lies entirely below 0. The
   phenomenon holds at 32B on both blinded languages; the magnitude
   is compared to 4B's $-20.2$ descriptively (different model, no
   paired test), and "scale softens the magnitudes" stays as written.
3. **Attenuation branch (pre-accepted):** the point estimate has
   $|\Delta| \le 3$\,pp AND the CI lies within $[-5, +5]$. The paper
   then states a real scale finding in the main text: at 32B the
   Telugu default-window damage is bounded near zero while Bengali's
   persists (certified at $-12$) — the blind mode's cost, not its
   geometry, depends on model size, and the threshold arithmetic
   ($c{=}167>64$) is untouched. No re-tuning follows.
4. Intermediate outcomes reported with their intervals, no rounding
   toward either branch.
5. **Gate:** $|\Delta| \le 3$\,pp at $\hat w$ vs own baseline, the
   standard closure vocabulary; a miss joins the residual table (no
   retro-editing), and the $\hat w$-vs-w64 recovery is reported with
   its CI beside it.
6. Item audit in proportion-test form (gold position and |Q| via
   `meta.q_tokens`) on whichever branch carries broken items.
7. No pooling with `qwen32b.db` or any 4B store; within-store pairs
   only. The B3 slice's numbers are superseded for Telugu by this
   arm's and remain the record for Bengali.

## Kill conditions

None for the paper's core: the phenomenon rests on the 4B pools and
Bengali-at-32B either way. Reading 3 is the pre-accepted branch that
changes a sentence, not a contribution.

Scoring: offline; audit section `qwen32b_depth` added before any
number enters the tex.
