# Oracle per-item window at depth (B2) — preregister DRAFT

**Author: Fable (Claude).** Drafted 2026-08-25, *before* any generation
of this arm exists; DRAFT until the lock commit. Driver:
`scripts/e_iclr10.sh b2`. Store: `results/oracle_depth.db`,
self-contained.

Answers reviewer-5 Q1: the per-item window $w_i = c + |Q_i|$ is the
natural upper bound of the remedy — $V_i{=}1$ for every item by
construction, no percentile leftover. The paper declines to deploy it
(serving-path parser); science still wants its number. If the oracle
closes the Telugu residual, the $\hat w$ residual is per-item
visibility after all and contribution (iv) must be revised; if it does
not, (iv) is reinforced by the strongest visibility treatment that
exists. The instruction-first arm (−3.4 certified at V=1) predicts the
second branch; this arm tests it in the ORIGINAL layout.

## Mechanism (before the lock)

New config `snapkv@r0.75:wq` (+ unit tests, committed before the
lock): per-item observation window $w_i = c + |Q_i|$, emulated
per-item by the same machinery as the `@b` budget family; $|Q_i|$
computed from the run tokenizer on the item's question, $c$ the
locked measured constant (re-derived on pod, FATAL on mismatch).

## Stopping rule

The entire Telugu validation pool, 669 items (the depth rule,
verbatim). No free parameter.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384:

- te × 669: `baseline`, `snapkv@r0.75:w247` ($\hat w$),
  `snapkv@r0.75:wq` (oracle).

= 2,007 generations. $\hat w$ is re-run so the decisive head-to-head
(oracle vs $\hat w$) pairs within one store; baseline and w247 double
as a determinism measurement against `depth.db`/`slack_depth.db`
(expected byte-identical; informational).

## Registered readings (fixed at lock)

1. **Primary:** paired Δpp of oracle vs own baseline, exact
   conditional 95% CI, offline scoring; oracle-vs-$\hat w$ head-to-head
   (McNemar + CI) beside it.
2. **(iv) reinforced** if the oracle's CI excludes 0 and its point sits
   within ±3pp of −5.7, AND the oracle-vs-$\hat w$ CI includes 0: full
   per-item visibility does not remove the residual — it is eviction
   cost, now certified against the strongest visibility treatment.
   Expected branch.
3. **(iv) revised** if the oracle meets the ±3pp gate vs baseline with
   the head-to-head CI excluding 0 in the oracle's favour: the
   language-level percentile, not visibility per se, was leaving the
   residual, and the paper must say the per-item refinement closes
   what $\hat w$ does not — contribution (iv) is rewritten and the
   per-item window is promoted from "natural refinement" to the
   measured remedy. Pre-accepted branch.
4. Intermediate outcomes reported as what they are, with intervals.
5. Item audit in proportion-test form (gold position, |Q| decile) on
   whichever branch.
6. The long decile is the interesting stratum: the ~58 items with
   $|Q| > Q_{90}$ are where oracle and $\hat w$ genuinely differ
   ($V<1$ under $\hat w$, $V=1$ under oracle). Their paired
   oracle-vs-$\hat w$ contrast is registered as a secondary reading
   with its own count, not folded into the pool.

## Kill conditions

None beyond reading 3's committed rewrite. The phenomenon and the
recovery numbers are untouched by any outcome.

Scoring: offline lenient + marker-only; audit section `oracle_depth`
added before any number enters the tex.
