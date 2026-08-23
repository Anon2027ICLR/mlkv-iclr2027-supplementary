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
