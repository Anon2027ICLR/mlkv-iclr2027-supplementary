# Refine layout: a shipped template, measured (B1) — preregister

**Author: Fable (Claude).** Written 2026-08-25, *before* any generation
of this arm exists; locked at the F19 commit, which also carries the
harness changes and their tests.
Driver: `scripts/e_iclr10.sh b1`. Store: `results/refine.db`,
self-contained.

Answers reviewer-5 W2 (the sharpest form: "the layouts with the
longest trailing blocks — refine loops, agent scaffolds — are only
measured statically"). Appendix Q found that LlamaIndex's shipped
refine default (T06) puts the query first and, at its
empty-placeholder floor, exactly 64 static tokens after it — before
the existing answer or the new context adds anything. In that layout
the question sits at the far LEFT of the prompt: at any small $w$ the
observation window holds none of it, for every language including
English. This arm measures, rather than asserts, what the default
window does there.

## Mechanism (before the lock)

New harness flag `--mrag-layout refine` (+ unit tests, committed
before the lock): item layout

```
<question>
<T06 refine template text, verbatim from the frozen survey record>
<existing answer stub>
[gold + distractor passages packed to 8k as "new context"]
<chat suffix>
```

The existing-answer slot is a FIXED neutral English sentence, identical
across items and languages, so it contributes a constant token count
and no information about the gold answer; its exact text is pinned in
the unit test. Item ids `mragRF-…` so run keys cannot collide with
frozen families. PROMPT_VERSION unchanged (new family, not a mutation).

## Arm

Qwen3-4B, ctx 8k, cap 384, n=100 per language:

- en: `baseline`, `snapkv@r0.75` (w=64)
- bn: `baseline`, `snapkv@r0.75` (w=64)

= 400 generations. V=0 by construction for every item at w=64 (the
question is ~8k tokens from the prompt end); the driver asserts the
question-first geometry on a probe item and aborts if the template
render moves it.

## Registered readings (fixed now, before any row)

1. **Primary:** paired Δpp of w=64 vs this layout's own uncompressed
   baseline, per language, exact conditional 95% CI, offline scoring.
2. **Blind-mode branch:** if English loses ≥ 5pp with the CI excluding
   0, the paper gains a main-text result: the failure reaches English
   through a shipped template — the language axis was only ever the
   common route to a long trailing block, exactly as Section 4 argues.
3. **Benign branch:** if |Δ| ≤ 3pp, the honest reading is that total
   blindness in this layout does not damage these items — consistent
   with Gemma's undamaged blind English cells, and a real bound on the
   paper's scope. Limitations gains the sentence; the static survey
   stays a geometry claim. Pre-accepted.
4. Intermediate outcomes reported with their intervals, no rounding.
5. What the rule says here is reported as a finding, not hidden:
   $c$ in this layout is the entire post-question suffix (~8k), so
   $\hat w = c + Q_{90}$ prescribes no eviction at any practical
   window — AutoWindow's output for a question-first layout is a
   refusal, which is the correct diagnosis (protect or reorder, do
   not window). No alternative window is tried.
6. No cross-language comparison; en and bn read against their own
   baselines only.
7. Scope honesty, pre-written: this measures OUR items in the shipped
   layout, not an agent loop mid-trajectory; the claim licensed is
   about the layout geometry, not about agent task success.

## Kill conditions

None for the paper's core; both branches are publishable. The arm
exists to replace an inference from static geometry with a
measurement.

Scoring: offline lenient + marker-only beside it; audit section
`refine` added before any number enters the tex.
