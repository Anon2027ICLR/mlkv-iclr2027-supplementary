# Constant-vs-rule at the headline ratio, and the value of the ranking — preregister

**Author: Fable (Claude).** Written 2026-08-18, *before* any cap-384
`snapkv@r0.75:w256` or `random@r0.75` generation exists anywhere in this
project. Driver: `scripts/e_iclr6.sh chain`. DB: `results/constant.db`.
Answers reviewer-3 W1/Q1 (the missing constant cell) and W6/Q5 (the
random-eviction control the registry comment always intended —
`compression.py` has carried `random` as a negative control since the
press-generality sweep was designed).

## Why

W1 is a pincer built from our own appendices: the largest $\hat w$ in
the paper is 247, so a single constant $w{=}256$ dominates every value
the rule produces; Appendix O (cap-128 era) shows Bengali saturating
between 128 and 256 at this ratio; and the paper only ever races the
constant at $r{=}0.9375$, the regime engineered to make it lose. The
cap-128 prior, recomputed tonight: bn $w128{\to}w256$ at $r{=}0.75$ is
$0.0$\,pp (17/16, $n{=}200$). The decisive cap-384 cell has never run.

W6: on Gemma, blind English gains $+2/+1$; on padded Qwen, blind English
loses ${\sim}10$. "Damage appears where the ranking was carrying the
answer" is currently post-hoc. `random@r0.75` per language turns the
value of the ranking into a measured quantity: value-of-ranking(lang) =
acc(blind SnapKV) − acc(random) on the same items.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384, n=100/cell, self-contained
(own baselines, own stack; pairs only within `constant.db`):

- en, bn, te × {`baseline`, `snapkv@r0.75:w256`, `random@r0.75`} — 900
  generations.
- `pool_check` block (zero generations): print the TyDiQA-GoldP
  validation pool sizes for bn/te, to scope the W4 depth extension
  honestly before any promise is made about it.

Reference cells (same-stack cross-store context only if the stack hash
matches; otherwise brackets): ŵ cells (bn −2, te 0, en +2), default
cells (bn −16*, te −19*, en +0).

## Predictions (fixed)

1. **The pincer closes on us, and we take it:** bn and te at
   `snapkv@r0.75:w256` are within $\pm 3$\,pp of their own baselines
   (256 > every measured $c+Q_{90}$, so $V{=}1$ for ≥93/100 items by
   construction; the saturation prior points the same way).
2. en at w256, $r{=}0.75$: within $\pm 3$ (retained cache ≈2{,}048
   tokens; the heavy-ratio tax should not appear here).
3. `random@r0.75` loses double digits on every language (uniform
   retention shreds the gold passage), and loses **more than blind
   SnapKV** on en/bn/te — i.e. even a blinded ranking beats no ranking.
4. Value-of-ranking is language-ordered: (blind − random) is largest for
   English and smallest for Telugu — blind SnapKV retains more of its
   value where the surviving prompt structure is cheaper to rank.
   (Directional; not gated.)
5. **Kill for the rule's moderate-ratio necessity (expected to fire,
   and binding):** if pred 1 holds, contribution (v) and §6's
   larger-constant sentence are **rewritten, not defended**: at moderate
   ratios one certified constant suffices, and what the paper sells is
   the certification — max-over-languages $\hat w$ is the rule's own
   output for mixed traffic; 256 works because the measurement says 247
   suffices; the shipped 64 and 32 fail because nobody measured. The
   per-language form stays load-bearing only at heavy ratio (Appendix
   K), and the paper says exactly that.
6. Genuine risk in the other direction: w256 opens a tax at $r{=}0.75$
   on any language (≤ −4 vs baseline, significant) → the constant is
   not free even at moderate ratio; report it and contribution (v)
   stands with the ratio scoped.

Reporting: R2 from raw output, McNemar with discordant counts, exact
CIs on any gate statement, never pool across stacks, within-store
pairing only.

## Paper consequence (decided now)

Branch of pred 5: rewrite contribution (v) + §6 sentence + app:rivals
paragraph around certification-not-per-language-windows; abstract's
transfer clause survives (it is about method-transfer, not
per-language necessity). Branch of pred 6: scope contribution (v) to
"at matched ratios the constant is not free" with the new cell as
evidence. Either way the W6 sentence in app:gemma is replaced by the
measured value-of-ranking, and the honest-nulls paragraph gains the
Gemma anomaly explicitly if pred 4's ordering fails.
