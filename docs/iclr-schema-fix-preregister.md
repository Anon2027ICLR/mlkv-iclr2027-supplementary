# Schema-fix arm — preregister

**Author: Fable (Claude).** Written 2026-08-17, *before* any `mlkv run` of
this arm. Driver: `scripts/e_iclr2.sh schema_fix`. DB: `results/schema_fix.db`.

## Why

The S arm was a construction miss: AutoWindow ran with unpadded English
`w=41` while the JSON tail pushed the true trailing count far past 64
(JSON-120 at `w=41`: **−23 pp**). The paper currently explains this away in
prose. This arm tests the SAME shipped formula with the schema-adjusted `c`:

\[
\hat{w}_{\text{schema}} = c_{\text{schema}} + Q_{90}(\text{en}),
\qquad c_{\text{schema}} = I_{\text{padded}} + s .
\]

If it closes, the remedy generalizes from language-induced to
schema-induced trailing blocks — the "not about language" thesis applied to
the fix itself. If it fails, that is a limitation to report, not to hide.

## Locked numbers (dev box 2026-08-17; re-measure on-pod before generate)

`scripts/measure_c_schema.py` builds the padded instruction with the same
`_pad_instruction` the mRAG builder uses (single source of truth), Qwen3-4B,
`s=5`, `Q90(en)=18` from `measure_q.py`:

| pad target | `I_padded` | `c_schema` | old AW (S arm) | \(\hat{w}_{\text{schema}}\) |
|---|---|---|---|---|
| 60 | 67 | **72** | 41 | **90** |
| 120 | 161 | **166** | 41 | **184** |
| 200 | 208 | **213** | 41 | **231** |

Note before seeing any accuracy: JSON-120's `c_schema=166` is within one
token of Telugu's `c=167` — same blindness dose, different cause. Also
`c_schema > 64` at ALL pads including JSON-60, so default-64 is predicted
blind everywhere on this grid (consistent with the old S readout −6/−6/−5).

## Arm

Qwen3-4B, mRAG **en**, instr-last, ctx 8k, cap 384, n=100,
`--mrag-instr-pad {60,120,200} --mrag-tail json`.
Configs per pad: `baseline`, `snapkv@r0.75` (default 64),
`snapkv@r0.75:w<hat_w_schema>`. 900 generations.

A fresh pod is a NEW stack: baseline and default-64 are re-run in this db.
**Never pair against `schema-final.db` (stack `d7368e8bd94a`).** All
comparisons stay inside `schema_fix.db`.

## Predictions (fixed)

1. Sanity, not a gate: baseline ≈ 94 ± 4 per pad (old stack was 94/95/94).
2. Default 64 damaged at every pad (direction of the old −6/−6/−5;
   expect ≤ −4 pp somewhere on the grid).
3. **Main:** \(\hat{w}_{\text{schema}}\) |Δ| ≤ 3 pp vs baseline at all
   three pads.
4. Recovery: \(\hat{w}_{\text{schema}}\) vs default 64 ≥ +3 pp at
   JSON-120 and JSON-200; JSON-60 may be within noise.
5. Kill (kills the *generalization*, not the slot): any pad with
   \(\hat{w}_{\text{schema}} \le -8\) pp vs baseline → schema tails break
   the remedy. Report as a limitation. Do not retune \(Q_{90}\) or `c`.

Scoring: `containment_match_lenient` (R2) recomputed from raw `output`.
Never stored `correct`. Paired McNemar, n=100, within this db only.
