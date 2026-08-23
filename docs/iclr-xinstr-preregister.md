# English instruction × non-English questions (B2) — preregister

**Author: Fable (Claude).** Written 2026-08-24, *before* any generation
of this arm exists. Driver: `scripts/e_iclr9.sh b2`. Store:
`results/xinstr.db`, self-contained.

Answers reviewer-4 W3/Q2: every language-dependent number in the paper
comes from translated instructions. If a deployment ships one English
instruction for all languages (the common case — every template in the
Appendix P survey is English), c ≈ 25 for every language and the blind
mode vanishes. But the framework still predicts language dependence
through a second path: at w=64 with c=25 the slack is 39 tokens, while
held-out Q50 is 46 (bn) and 54 (te) — so more than half the items of
either language see only part of their question. This is the nearest
cell to production, and it is missing.

## Mechanism

New harness flag `--mrag-instr-lang en` (committed with its unit tests
before this file): items keep their language's questions and passages,
the instruction is English's frozen one, layout instr-last, item ids
prefixed `mragXen-` so run keys cannot collide with frozen rows.
PROMPT_VERSION unchanged — this is a new item family, not a mutation of
an old one.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384, n=100 per language,
`--mrag-instr-lang en`:

- bn: `baseline`, `snapkv@r0.75` (w=64), `snapkv@r0.75:w101`
  (= c_en 25 + Q90_bn 76 — what the rule prescribes in this layout)
- te: `baseline`, `snapkv@r0.75` (w=64), `snapkv@r0.75:w105`
  (= 25 + Q90_te 80)

= 600 generations. On-pod guard: `measure_c.py` for en must return
c=25 (the cross prompt's trailing block is the English instruction plus
the chat suffix; abort if > 32, meaning the instruction did not
transplant cleanly). Q90 values re-derived by `measure_q.py` and must
match 76/80.

## Registered predictions (fixed now)

1. **Framework prediction:** at w=64, damage concentrates on items with
   |Q| > 39 (V < 1). Report the split as a proportion test (share of
   V<1 items among broken vs among all), not a raw fraction.
2. If bn or te at w=64 loses ≥ 5pp with V<1 enrichment: the paper's
   scope WIDENS (an English instruction does not save a long-question
   language) — main-text result, and V earns its keep as the quantity
   that predicted it.
3. If both languages sit within ±3pp at w=64: the scope NARROWS — the
   failure requires a trailing block long enough to hide the whole
   question, and partial visibility with an English-sized tail is
   benign on these items, consistent with the English/Gemma
   partial-visibility observations. Limitations gains one sentence
   saying exactly that.
4. Both outcomes are publishable; this cell has no gate to miss and no
   kill condition. What is registered is the readout format, so the
   result cannot be re-framed after the fact.
5. The w101/w105 rows document the rule's prescription in this layout;
   predicted ≈ baseline (V=1 for ≥90% of items by construction).
6. No cross-language accuracy comparison: bn and te are read against
   their own baselines only, as always.

Scoring: offline `containment_match_lenient`; the audit script gains an
`xinstr` section. Note for the readout: the English instruction's ####
marker convention is unchanged, so the marker path applies as usual.
