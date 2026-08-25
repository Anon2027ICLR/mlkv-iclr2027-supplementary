# 16k prefill slice (B4) — preregister

**Author: Fable (Claude).** Written 2026-08-25, *before* any generation
of this arm exists; locked at the F19 commit, which also carries the
harness changes and their tests. Driver:
`scripts/e_iclr10.sh b4`. Store: `results/ctx16k.db`, self-contained.

Answers reviewer-5 Q2: every headline number sits at one prefill
(8k). The blind mode is a hard threshold in $c$ and $w$, neither of
which moves with prefill length — the prediction is that blindness
persists unchanged at 16k — but at $r{=}0.75$ a 16k prefill retains
twice the absolute cache, so the damage magnitude and the residual
may move. One slice measures instead of asserting.

## Arm

Qwen3-4B, mRAG instr-last, ctx 16k (the harness's existing 16k
packing), cap 384, n=100:

- te: `baseline`, `snapkv@r0.75` (w=64), `snapkv@r0.75:w247` ($\hat w$)

= 300 generations. Telugu because it is the headline language and the
only one with a certified 8k residual to compare against. Same items
where the 16k packing permits (the packer refills distractors; qids
are recorded and the overlap with the 8k eval set is reported).

## Registered readings (fixed now, before any row)

1. **Blind mode:** Δ at w=64 vs own 16k baseline, exact CI.
   Prediction: certified loss — $V{=}0$ is decided by $c{=}167 > 64$,
   which prefill length cannot change.
2. **Recovery and gate:** $\hat w{=}247$ vs baseline, |Δ| ≤ 3pp gate
   with CI, and $\hat w$ vs w=64 recovery. $\hat w$'s inputs ($c$,
   $Q_{90}$) are prefill-independent, so the SAME integer is used —
   that invariance is itself the point being tested.
3. **Magnitude comparison to 8k** is reported descriptively (the two
   context lengths change the items' distractor composition, so this
   is not an item-paired contrast and no significance claim is made
   across lengths).
4. If the w=64 hole shrinks materially at 16k (point < 10pp against
   ~20 at 8k), the honest sentence is that absolute retained cache
   buys partial mitigation even when blind, and the paper says so;
   the threshold claim is untouched either way.
5. No pooling with the 8k stores; within-store pairs only.

## Kill conditions

None for the paper's core; this is a robustness slice. Reading 4's
branch is the pre-accepted unfavourable one.

Scoring: offline lenient + marker-only; audit section `ctx16k` added
before any number enters the tex.
