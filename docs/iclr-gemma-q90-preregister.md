# Gemma AutoWindow-Q90 arm — preregister

**Author: Fable (Claude).** Written 2026-08-17, *before* any `mlkv run` of
this arm. Driver: `scripts/e_iclr2.sh gemma_q90`. DB: `results/gemma_q90.db`.

## Why

The Gemma sweep (arm C) showed the cliff MOVES with the tokenizer (bn
`c` 107→32; hole at Gemma-blind `w=16/24`), but the remedy
\(\hat{w}=c+Q_{90}\) has only been validated on the Qwen tokenizer. This arm
closes the cross-tokenizer loop: *c moves → hole moves → formula follows c.*

## Locked numbers (dev box 2026-08-17; re-measure on-pod before generate)

`measure_c.py` (gemma-3-4b-it, `after_question`, s=6) and `measure_q.py`
(same held-out split rule, written to `results/q_percentiles_gemma.json`
via `--out` so the locked Qwen file is untouched):

| | c | \(Q_{50}\) | \(Q_{90}\) | \(\hat{w}=c+Q_{90}\) | old grid cells |
|---|---|---|---|---|---|
| en | 27 | 12 | 18 | **45** | 16/24/32/48/64 |
| bn | 32 | 11 | **18** | **50** | w48 was −5 (ns) |
| te | 44 | 14 | **20** | **64** | w64 was −3 (ns) |

Two remarks fixed before any accuracy is seen:

- Gemma's question fertility on bn/te is ~4× lower than Qwen's
  (\(Q_{90}\) 18/20 vs 76/80). The formula therefore lands near the
  shipped default instead of far above it.
- \(\hat{w}_{\text{te}} = 64\) **equals the kvpress default**: the formula
  predicts the default is already adequate for Gemma-te. That prediction is
  itself testable (pred 4). For bn, \(\hat{w}=50\) sits inside the 48–64
  range where the old stack measured −5 (ns) — the close must beat that.

## Arm

gemma-3-4b-it, mRAG instr-last, ctx 8k, cap 384, n=100, langs **en, bn, te**.
Configs per lang: `baseline`, `snapkv@r0.75` (default 64),
`snapkv@r0.75:w<hat_w>`. 900 generations. For te, \(\hat{w}\) and the
default coincide if the on-pod measure returns 64 — then run the config
string `snapkv@r0.75:w64` anyway (it is the same treatment; keeping the
explicit config makes the table read uniformly).

A fresh pod is a NEW stack: own baselines. **Never pool with
`cliff_gemma.db` (stack `a2011e0bd133`) or with any Qwen cell.**

## Predictions (fixed)

1. en |Δ| ≤ 3 pp vs baseline at default 64 and at \(\hat{w}=45\).
2. bn default 64: mild damage, direction of the old stack (−5); expect
   −9 … 0.
3. **Main:** bn \(\hat{w}=50\) |Δ| ≤ 3 pp vs baseline.
4. te: \(\hat{w}=64\) ≡ default within noise, and both ≥ −4 pp vs
   baseline — "the formula returns the default when the default suffices."
5. Kill (kills the formula on this tokenizer, not the slot): bn
   \(\hat{w} \le -8\) pp vs baseline → treat exactly like the 8B soft miss
   (report; do not retune \(Q_{90}\); do not swap scorer).

Scoring: R2 (`containment_match_lenient`) from raw `output`. Never stored
`correct`. Paired McNemar, n=100, within this db only. Baseline accuracy
may differ from the old Gemma stack (75/62/37) — that is stack drift, not a
gate; deltas are the readout.
