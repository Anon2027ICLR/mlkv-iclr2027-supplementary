# Thai and Swahili at their own ŵ (B3) — preregister

**Author: Fable (Claude).** Written 2026-08-24, *before* any generation
of this arm exists. Driver: `scripts/e_iclr9.sh b3`. Store:
`results/thsw.db`, self-contained.

Answers reviewer-4 W7/Q6: the paper computes ŵ_th = 91 and ŵ_sw = 67
(Table constants) and uses Thai and Swahili to widen the problem's
scope (the w=64→32 flip costs them 4.5 and 6.5pp), but never runs a
single accuracy cell at either ŵ. "The rule cannot produce this flip"
is arithmetic, not measurement. This arm measures it — on the two
languages where the rule was never tested, including one (sw) where ŵ
sits just 3 tokens above the shipped default.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384, n=100 per language:

- th: `baseline`, `snapkv@r0.75` (w=64), `snapkv@r0.75:w91`
  (= c 45 + Q90 46)
- sw: `baseline`, `snapkv@r0.75` (w=64), `snapkv@r0.75:w67`
  (= c 47 + Q90 20)

= 600 generations. The w=64 cells make the ŵ-vs-default contrast pair
within-store. On-pod guards: `measure_c.py` must return c = 45/47,
`measure_q.py` must return Q90 = 46/20 (th from XQuAD val[100:], sw
from TyDiQA train minus eval ids — the usual disjointness guard runs
for sw; th's split disjointness holds by construction and is asserted
anyway).

## Registered gate and readings (fixed now)

1. **Gate:** |Δ| ≤ 3pp at ŵ vs own baseline, per language — the same
   preregistered closure gate every other AutoWindow cell was judged
   by, with the same exact conditional CI reported beside it.
2. A pass on both adds two languages to the rule's evaluated set
   (3/8 → 5/8) and closes the reviewer's "tested only where it wins"
   hole.
3. A miss on either is reported as a fifth (sixth) gate miss and joins
   the residual table with the same item-level audit in
   proportion-test form. It does not retro-edit the existing four
   misses and no alternative window is tried.
4. ŵ vs w=64 within-store is reported as context (both languages sit
   above threshold at the default, so no recovery is predicted; the
   prediction is "no damage at either window, gate met at ŵ").
5. Baselines are expected near the campaign values (th 85, sw 56);
   a drift > 5pp is reported as stack drift and the cells still pair
   within-store only.

## Kill conditions

None for the paper's core: these are coverage cells. Reading 3 is the
pre-accepted unfavourable branch.

Scoring: offline, audit section `thsw` added before any number enters
the tex.

## Amendment, 2026-08-24 — after the guard fired, before any generation

The chain's first pod run aborted in `run_guards()` after 31 seconds,
with zero generations produced (log preserved at
`docs/iclr9-guards-failed-2026-08-24.md`);
no accuracy of any arm has been seen, so this amendment is written from
the same epistemic position as the original. What the guard found:
TyDiQA-GoldP Swahili's raw train and validation splits share **two
exact duplicate examples** (identical id, question and context):
`swahili--1339720473726915592-0` and `swahili-1422153578110398972-3`,
at validation positions 133 and 300. Unlike Bengali's three documented
duplicates — which sit inside `validation[:100]` and are therefore
removed from the Q90 source by construction — these two sit outside
`[:100]`, so they remain inside the Q90 estimation set. The full-pool
invariant `eval(full pool) ∩ Q90-source = ∅` is genuinely violated for
Swahili: the guard caught what it was built to catch.

Decision, taken at this level and not in the script: **the arm keeps
Swahili and the guard is keyed to the eval set each arm registers.**
The invariant this preregistration depends on is that no *evaluated*
item contributes to the Q90 estimation set. This arm evaluates
`validation[:100]` (`--max-items 100`, registered above), and
`val[:100] ∩ Q90-source = ∅` holds — re-verified locally on 2026-08-24.
The guard therefore asserts, per language: full-pool disjointness for
Telugu and Bengali (unchanged in strength — both hold), and
first-100 disjointness for Swahili (the registered eval set). The two
Swahili ids are recorded as documented raw-split duplicates so that any
*new* overlap still aborts; they are **not** an allowlist for full-pool
use. Any future arm that evaluates the Swahili pool beyond
`validation[:100]` must re-register and either exclude these two ids
from its Q90 source or disclose them.

Consequences accepted with the decision:

- Shipped `Q90[sw]=20` is unchanged and untouched. Recomputed on
  2026-08-24 with the two duplicate ids removed from the source, the
  percentile is identical (20, n=2753 vs n=2755): the wart cannot move
  the constant, and the constant is not re-tuned. `ŵ_sw = 67` stands
  as registered.
- The paper's measurement appendix discloses the Swahili raw-split
  duplicates next to the Bengali ones (the depth-arm amendment
  precedent), stating that no evaluated item sits in any Q90 source
  and that the sw eval set is `validation[:100]`.
- The Swahili validation pool size (499) is now pinned in the guard,
  as the other pools are.
