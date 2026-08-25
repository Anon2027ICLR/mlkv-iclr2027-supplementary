# Qwen3-32B slice (B3) — preregister DRAFT

**Author: Fable (Claude).** Drafted 2026-08-25, *before* any generation
of this arm exists; DRAFT until the lock commit. Driver:
`scripts/e_iclr10.sh b3` on its own 80GB pod. Store:
`results/qwen32b.db`, self-contained (own stack — the Llama
precedent: quoted beside the campaign cells, never pooled).

Answers reviewer-5 W3: no model ≥ 30B anywhere in the paper. The
mechanism is a property of the scoring rule and must transfer; the
damage magnitude and whether $\hat w$ closes at scale are open — and
the 8B slice (recovers +9, leaves −8) predicts caution, not victory.

Honesty pinned in advance: Qwen3-32B shares the Qwen3 tokenizer, so
this is a SCALE test, not an independent-tokenizer sample — the same
caveat the paper already prints for 8B, and it will be printed here.

## Arm

Qwen3-32B, mRAG instr-last, ctx 8k, cap 384, n=100 per language:

- bn: `baseline`, `snapkv@r0.75` (w=64), `snapkv@r0.75:w183` ($\hat w$)
- te: `baseline`, `snapkv@r0.75` (w=64), `snapkv@r0.75:w247` ($\hat w$)

= 600 generations. $c$ (107/167) and $Q_{90}$ (76/80) are tokenizer
properties and should be identical to 4B/8B; the driver re-derives
both on-pod and aborts on mismatch (if the 32B chat template differs
and moves $c$, the abort is the right outcome and the arm is
re-registered with the measured integers).

## Registered readings (fixed at lock)

1. **Phenomenon:** the default-window hole reproduces (Δ at w=64 vs
   own baseline, CI; prediction: certified loss on both languages, as
   at every Qwen scale so far).
2. **Recovery:** $\hat w$ vs w=64, paired, with CI (prediction:
   significant recovery on both).
3. **Gate:** |Δ| ≤ 3pp at $\hat w$ vs own baseline, per language, the
   standard closure vocabulary. A miss joins the residual table as a
   fifth/sixth missed cell with the item audit in proportion-test
   form; it does not retro-edit anything. Given 8B (−8), a bn miss is
   the EXPECTED branch and is written here in advance so the paper
   cannot be accused of hoping otherwise.
4. If baselines are at ceiling anywhere (the 8B English lesson), the
   cell is reported as carrying no information rather than as a pass.
5. No pooling with any other store; comparisons within this stack
   only.

## Kill conditions

None for the paper's core. The arm can add gate misses (accepted in
reading 3) but cannot weaken the phenomenon; a failure to reproduce
the hole at 32B would itself be a reportable scale finding, stated
with its interval.

Scoring: offline lenient + marker-only; audit section `qwen32b` added
before any number enters the tex.
