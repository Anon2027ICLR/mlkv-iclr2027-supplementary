# Llama family slice — preregister

**Author: Fable (Claude).** Written 2026-08-17, *before* any Llama
`mlkv run` at decode cap 384. Driver: `scripts/e_iclr3.sh llama`
(optional `llama_te`). DB: `results/llama.db`.

## Why

Two independent reviews of the finished draft converge on the same
objection: the two genuinely out-of-sample tests of \(\hat w = c+Q_{90}\)
(Gemma-bn, 8B-bn) both miss the registered bound, and 8B shares Qwen's
tokenizer while Gemma is a single contrast. A third tokenizer family is
the highest-value remaining experiment — named as the top score-raiser by
both reviewers. The signal already on disk: at decode cap 128 (stack
`485513693f0a`), `meta-llama/Llama-3.1-8B-Instruct` Bengali lost
**14.0 pp** at the default window (70.0 → 56.0, n=200, R2) — but that era's
cap truncates high-fertility answers, so the number is direction, not a
comparator.

## Arm

`meta-llama/Llama-3.1-8B-Instruct` (gated — the pod needs a HF token with
Llama access), mRAG instr-last, ctx 8k, cap 384, n=100.
Langs **en, bn** primary; **te** optional block if pod time remains.
Configs per lang: `baseline`, `snapkv@r0.75` (default 64),
`snapkv@r0.75:w<hat>`. 600 (+300) generations.

\(c\) and \(Q_{90}\) are measured **on-pod on the Llama tokenizer**
(`measure_c.py`; `measure_q.py --out results/q_percentiles_llama.json` so
the locked Qwen file is untouched). We have not measured them on the dev
box (gated weights); the structural expectation, stated before measuring,
is that Bengali's trailing block lands well above 64 tokens, as it does on
Qwen (107). New stack, third family: own baselines, never pooled with any
Qwen or Gemma cell.

## Statistics discipline (new, and part of the preregister)

Closure is reported with BOTH the registered point gate and the
exact-conditional 95% CI from `scripts/closure_cis.py`, using the fixed
vocabulary: *meets the registered gate* (point \(|\Delta|\le 3\)),
*non-inferior at −3 pp* (CI lower bound \(\ge -3\)), *confirmed residual*
(CI entirely below 0). "Closes" without qualification is never written
about a cell whose CI does not support non-inferiority.

## Predictions (fixed)

1. Precondition: on-pod \(c_{\text{bn}} > 64\). If this fails, the arm
   becomes a negative control (no blindness at the default → predict no
   hole) and predictions 3–4 are void; report it as such.
2. en: \(|\Delta| \le 3\) pp vs baseline at the default window and at
   \(\hat w\).
3. bn at the default window: damaged, \(\le -8\) pp (direction of the
   cap-128 −14).
4. **Main:** bn at \(\hat w\) meets the registered gate
   (\(|\Delta| \le 3\)); CI reported per the discipline above.
5. Slice-kill (kills the Llama signal, not the paper): bn flat at the
   default window → the cap-128 −14 was a decode-cap artifact; report and
   stop.
6. Soft miss (the 8B/Gemma shape): hole at the default, \(\hat w\) does
   not close → run the same residual audit as 8B, unedited checklist:
   per-item \(V\) at \(\hat w\), question-echo, gold position, marker/cap
   behaviour. Report as a third boundary point; do not retune \(c\),
   \(Q_{90}\), or the scorer.
7. te (optional block only): same structure as bn; its miss or close is
   reported identically.

Scoring: R2 from raw `output`. Paired McNemar with discordant counts.
Never stored `correct`. No LLM judges.
