# Template survey — readout — 2026-08-18

**Author: Fable (Claude).** Collection: Grok, `docs/template-survey-report.md`
(`60d3daf`), 22 records selected by popularity before layout was read;
spot-verified against primary sources (T06 reproduces at exactly 348
characters, T18 at exactly 1{,}005, SGLang RFC quote verbatim).
Preregister: `docs/iclr-template-survey-preregister.md` (`813bcad`),
committed before any tokenizer ran. Measurement:
`scripts/template_survey_measure.py`, Qwen3-4B tokenizer, placeholders
deleted so every number is a lower bound.

## Numbers (static trailing block, tokens)

| group | records | tokens |
|---|---|---|
| single-shot RAG defaults | T01–T05, T08, T09 | **0–5** |
| vendor structured output | T10–T16 (minus T12) | **0** (schema in API fields) |
| OpenAI JSON-mode example | T12 | 6 |
| eval harness QA | T20, T21 | 3–5 |
| Belebele MCQ | T22 | 15–19 (+ choice strings at runtime) |
| **LlamaIndex refine default** | **T06** | **64** — the kvpress constant exactly, before `{existing_answer}` or `{context_msg}` add a token |
| LangChain ReAct | T17 | 3 static; grows per step by `Observation: … Thought:` |
| **SWE-agent instance template** | **T18** | **221** — larger than Telugu's 167, before any observation |
| OpenHands | T19 | no static form; every tool message lands after the user's task |

## Scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | single-shot RAG defaults all < 32 | 4–5 | **hold** |
| 2 | T06 ≥ 32 | **64** | **hold** |
| 3 | T18 ≥ 64 | **221** | **hold** |
| 4 | (descriptive) vendor APIs moved schemas out of the prompt | confirmed — falsifies the collection-stage guess, recorded as found | — |
| kill | T06 and T18 both < 32 | does not fire | — |

## Reading

The survey splits the world cleanly, and both halves serve the paper.
The safe half: shipped single-shot RAG defaults leave 4–5 tokens after
the question, modern vendor structured-output APIs carry schemas in API
fields rather than prompt text, and harness QA templates are
question-adjacent — **the paper's failure mode does not indict everyday
single-shot RAG**, and saying so plainly costs nothing and buys
credibility. The biting half: the geometry the paper studies is the
*default shape of iteration*. LlamaIndex's shipped refine template puts
the query first and — at its empty-placeholder floor — exactly **64
tokens** after it, the kvpress constant to the token, before any actual
answer or context arrives; SWE-agent's instance template puts **221**
static tokens after the problem statement, more than Telugu's 167, and
then every observation lands after that; ReAct and OpenHands append
every tool result after the already-rendered question by construction.

One honest boundary, stated before anyone asks: these are geometry
measurements, not damage measurements. Whether windowed eviction hurts
agent loops the way it hurts instruction-last QA is not tested here —
the relevant query for an agent's next step is partly the recent
observations the window does see. The claim the survey supports is
scope: the layout in which the constant can blind the scorer is not an
artifact of our construction; it ships today, in defaults an order of
magnitude more popular than the evictors themselves.

Deployment re-check (permalinked in the report): RocketKV remains
opt-in with `window_size=32` as the config default; vLLM's default
backends are dense; the open SGLang sparsity RFC is default-off and
names H2O, SnapKV and PyramidKV as explicit non-goals. The Scope
paragraph's state-of-the-world is current as of 2026-08-18.

## Integration memo (one Opus round, budget-gated)

- New appendix (outside the page budget): the 22-row table + the
  reading above compressed + the deployment paragraph with access-dated
  permalinks. Label suggestion `app:wild`.
- At most two main-text sentences under the spill protocol; the natural
  home is the Scope paragraph (after "such prompts are non-English"):
  the geometry also ships language-independently — a refine default
  whose static floor is the kvpress constant exactly, an agent template
  that out-lengths Telugu before its first observation.
- Audit: pin T06=64 and T18=221 under the tokenizer-gated guard
  (the trailing strings are already data in the measure script).
- Never write: any damage claim for agent loops (not measured); any
  "most templates are unsafe" claim (most are safe — that is the
  finding); T06 crossing 64 (it *equals* 64 — crossing starts at the
  first runtime token, say it that way).
