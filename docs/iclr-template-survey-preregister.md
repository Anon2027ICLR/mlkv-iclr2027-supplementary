# Template survey, measurement stage — preregister

**Author: Fable (Claude).** Written 2026-08-18, *after* collection
(`docs/template-survey-report.md`, commit `60d3daf`, spot-verified: T06
rendered trailing block reproduces at exactly 348 characters, T18 at
exactly 1{,}005 from the yaml-parsed template, and the SGLang RFC quote
matches the issue verbatim) and *before* any tokenizer has touched any
template. The record list T01–T22 is **locked as collected**; no record
may be added, dropped, or re-edited at measurement time.

## What gets measured

For every record with a nonzero static trailing block, the **static
trailing-block token count**: the verbatim trailing block from the
report, with every unfilled placeholder (`{...}` / `{{...}}` /
`{% ... %}` Jinja constructs) **deleted** (empty-string instantiation),
tokenized with `add_special_tokens=False`. Deletion makes every number a
*lower bound* — placeholders only add. Blocks that grow at runtime
(`{existing_answer}`, `{context_msg}`, `{agent_scratchpad}`,
observations) are reported as the static lower bound plus the growth
mechanism; the one shipped artifact with a concrete observation
(SWE-agent demonstration trajectory, 112 characters) may be quoted as an
example, nothing invented.

Tokenizer: **Qwen/Qwen3-4B** (primary model of the paper; ungated).
Gemma-3-4b-it and Llama-3.1-8B numbers may be added as secondary columns
only if those tokenizers are locally available; their absence changes
nothing.

Question-last records (trailing block `none`) score 0 by construction
and stay in every table — they are the honest half of the survey.

Thresholds: the two shipped constants, **32** and **64**. "Crosses" =
static lower bound strictly greater than the constant. No chat-template
suffix is added to template blocks (a deployment's suffix only adds, so
crossing claims remain lower bounds).

## Predictions (fixed before tokenizing)

1. Every single-shot RAG default (T01, T04, T05, T08; ≤25 characters)
   measures **< 32** tokens: shipped single-shot RAG defaults are safe
   at both constants.
2. **T06** (LlamaIndex refine default, 348 characters with query first
   and context after) measures **≥ 32** on Qwen3-4B with placeholders
   deleted — a shipped RAG default whose *static* block alone crosses
   the stricter shipped constant, before any runtime content.
3. **T18** (SWE-agent instance template, 1{,}005 characters after the
   problem statement) measures **≥ 64** — an agent scaffold whose static
   block alone exceeds the kvpress default, larger than Telugu's 167
   only at runtime growth, and every observation lands after it.
4. Descriptive, not gated: the modern vendor structured-output pattern
   (T10–T16 minus T12) carries schemas in API fields, not after the
   question — which **falsifies the collection-stage guess** (recorded
   in `docs/contribution-ceiling-2026-08-18.md`) that schema-after-task
   text is where large blocks live in the wild. The biting geometry
   lives instead in refine chains and agentic re-prefill. We report this
   reversal as what the survey found, not as what we expected.

**Kill (changes the paper):** if T06 **and** T18 both measure < 32, the
"the geometry ships today" reframe dies; the survey is then reported as
a Limitations paragraph — single-shot defaults are safe, and the biting
layout arises only from in-language instructions, in-prompt schemas, or
runtime accumulation — with no appendix table and no claim of deployed
exposure.

## Paper consequence (decided now)

If predictions 1–3 hold: one compact appendix table (22 rows: ID,
category, question-last?, static tokens, crosses 32/64) plus at most
**two** main-text sentences, placed under the spill protocol
(`scratchpad/spill.py`, structural cuts only); the deployment-status
paragraph (TensorRT-LLM RocketKV still opt-in at `window_size=32`
default; vLLM dense defaults; SGLang RFC naming SnapKV/PyramidKV
explicit non-goals, default-off) refreshes the Scope paragraph's
citation with access-dated permalinks in the appendix. If the kill
fires: Limitations sentence only, and the contribution list does not
change.

Measurement script: `scripts/template_survey_measure.py`, committed with
its output; every number that reaches the TeX gets pinned in
`audit_paper_numbers.py` under the same tokenizer-gated guard as the
constants-table checks.
