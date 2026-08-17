# Heavy-ratio sweep — preregister

**Author: Fable (Claude).** Written 2026-08-17 (late), *before* any
r=0.9375 `mlkv run` at cap 384. Driver: `scripts/e_iclr4.sh ratio`.
DB: `results/ratio.db`.

## Why

Two asks from the second review collapse into one arm. (W5/Q2) The
Limitations section predicts a failure regime — at heavy eviction the
protected window starts taxing the content budget — that the paper never
measures. (W4-iv, implicit) The cheapest rival remedy is not a scorer
but a *bigger constant*: at iso-ratio, why not set $w{=}256$ for
everyone, as a task-average sweep would? Both questions are about the
same quantity: what a large window costs when the cache is small.

Prior signal, decode-cap-128 era (`e2-final.db`): at $r{=}0.9375$,
widening $w$ from 64 to 256 cost **English $-6$\,pp and Thai $-8$\,pp**
while recovering Bengali $+15$ — the tax is real for languages that were
never blind, exactly where the per-language rule keeps $w$ small
($\hat w_{\text{en}}{=}43$). Cap-128 era: direction only; this arm is
the clean measurement.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384, n=100, langs **en, bn**.
Configs: `baseline`, `snapkv@r0.9375` (default window),
`snapkv@r0.9375:w<hat>` ($\hat w$ measured on-pod: expected 43 / 183),
`snapkv@r0.9375:w256` (the one-big-constant rival). 800 generations,
self-contained. The retained budget at 0.9375 on an 8k prompt is ~512
tokens, so $w{=}256$ is half the surviving cache.

## Predictions (fixed)

1. bn: $\hat w$ recovers vs the default window at 0.9375 (cap-128
   direction: $+15$); the hole exists at the default (bn blind at 64
   regardless of ratio).
2. **The tax is real:** en at $w{=}256$ loses vs en at $w{=}64$ at this
   ratio (cap-128 direction: $-6$); gate: ≤ $-4$\,pp.
3. **The rule avoids it:** en at $\hat w{=}43$ within 3\,pp of en at
   $w{=}64$.
4. **The point (why not one big constant):** on the same two languages,
   per-language $\hat w$ weakly dominates $w{=}256$ — no cell where 256
   beats $\hat w$ by more than 3\,pp, and at least one (en) where
   $\hat w$ beats 256 by more than 3.
5. Negative outcome (report, do not hide): if en at 256 is flat at this
   ratio, the window tax did not reproduce at cap 384; the "why not a
   big constant" argument then rests only on the constant-inherits-the-
   tokenizer point, and the Limitations sentence is weakened
   accordingly. This is a bounding experiment either way.

Reporting: R2, McNemar with discordant counts, CIs via
`closure_cis.py` conventions. Own stack, own baselines, never pooled.

## Paper consequence (decided now)

Preds 2–4 hold → §6 gains the "why not a bigger constant" paragraph
with measured numbers, and the Limitations window-tax sentence gets its
citation. Pred 5 fires → the Limitations sentence is rewritten to say
the tax was not detectable at 8k/0.9375/cap-384, and no
dominance claim is made.
