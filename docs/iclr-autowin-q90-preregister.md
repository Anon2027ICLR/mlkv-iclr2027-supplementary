# AutoWindow-Q90 follow-up — preregister

**Author: Grok 4.6.** Written *before* any `mlkv run` of this arm.
D (`w = c+16`) recovered bn/te vs default 64 but did not close vs
baseline. This run tests one locked formula. Do not retune \(\hat{q}\)
after seeing accuracy.

## Formula (shipped)

\[
\hat{w}(\text{lang}) = c(\text{lang}) + Q_{90}(\text{lang})
\]

- \(c\): `scripts/measure_c.py` on the run tokenizer + chat template
  (same lock as 2026-08-14: Qwen3-4B en 25 / bn 107 / te 167).
- \(Q_{90}\): 90th percentile of question-token length
  `len(tokenizer.encode(question, add_special_tokens=False))`.
- **Held-out:** not the 100 eval items (`questions[:100]` after the mRAG
  pool order). XQuAD: `validation[100:]`. TyDiQA-GoldP (bn/te): `train`,
  dropping any `qid` that appears in `validation[:100]`.
- Language-level, not per-item \(w_i\). Same `r0.75` (iso-retained-KV).

Locked 2026-08-14 on this machine (`scripts/measure_q.py`, Qwen3-4B):

| | n held-out | \(Q_{50}\) | \(Q_{90}\) | \(c\) | \(\hat{w}=c+Q_{90}\) | old \(c+16\) |
|---|---|---|---|---|---|---|
| en | 1090 XQuAD val[100:] | 12 | 18 | 25 | **43** | 41 |
| bn | 2387 TyDi train | 46 | 76 | 107 | **183** | 123 |
| te | 5563 TyDi train | 54 | 80 | 167 | **247** | 183 |

`c+16` stays in the paper as the English-calibrated ablation already run.

## Arm

Qwen3-4B, mRAG, instr-last, ctx 8k, cap 384, n=100, langs **en, bn, te**.

`snapkv@r0.75:w<hat_w>` → `results/autowin_q90.db`.

Pair against **the same `item_id`s** in `autowin-final.db` (baseline and
`c+16` already paid). Do not regenerate baselines unless `item_id`s
diverge.

## Predictions (fixed)

1. en: |Δ| vs baseline ≤ 3pp (already \(V \approx 1\) at \(c+16\)).
2. bn and te: |Δ| vs baseline ≤ 3pp (headline close).
3. Allowed leftover: items with \(Q_i > Q_{90}\) may stay damaged;
   the rest should be flat. Report that split.
4. Does not kill: en overshoots slightly. Kills the *formula*, not the
   ICLR slot: bn or te still ≤ −8pp vs baseline after \(Q_{90}\). Then
   stop raising \(w\); next lever is score/protect, not a bigger
   percentile.

Scoring: `containment_match_lenient` (R2). Never stored `correct`.
