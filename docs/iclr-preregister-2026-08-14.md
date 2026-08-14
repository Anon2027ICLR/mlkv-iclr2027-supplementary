# ICLR slot preregister — 2026-08-14

**Author: Grok 4.6.** Written *before* any `mlkv run` of arms A–D or S.
Predictions are fixed here. Deviations get reported, not edited in.

Scoring for every mRAG number: `containment_match_lenient` (R2). Stored
`correct` is never quoted. Comparisons stay inside one `stack_id`
(`docs/runpod-api-guide.md` §7: a hand-pinned wheel is a different stack).

`c` is measured by `scripts/measure_c.py` from the run tokenizer + chat
template, not copied from a table. AutoWindow uses language-level
`w = c_lang + 16`, not a per-item `w_i`.

Locked 2026-08-14 on this machine (Qwen3-4B: fallback *I*+5-token
suffix; Gemma-3-4b-it: after-question):

| | en | zh | es | vi | th | sw | bn | te |
|---|---|---|---|---|---|---|---|---|
| Qwen *I* / *c* / *w* | 20/25/41 | 24/29/45 | 30/35/51 | 34/39/55 | 40/45/61 | 42/47/63 | 102/107/123 | 162/167/183 |
| Gemma *I* / *c* / *w* | 21/27/43 | — | — | — | — | — | **26/32/48** | 38/44/60 |

---

## Arms

**A — Identification** (EN pads, Qwen3-4B, ctx 8k, cap 384, n=100).
Reuse `mragPAD{48,64,96,128}` items. Sweep `snapkv@r0.75:w{32,56,80,104,144}`.
No new baselines — those already live in `pad384.db`. New rows go to
`cliff_en.db`.

**B — External validity** (Qwen3-4B, en/th/sw/bn/te, ctx 8k, cap 384, n=100).
`baseline` + `snapkv@r0.75:w{32,56,88,120,176}` → `cliff_multi.db`.
bn and te are mandatory: without them the `c` range cannot beat language FE.

**C — Cross-tokenizer** (`google/gemma-3-4b-it`, en/bn/te, ctx 8k, cap 384,
n=100). `baseline` + `snapkv@r0.75:w{16,24,32,48,64}` → `cliff_gemma.db`.
Do not pool with Qwen cells.

**D — AutoWindow** (Qwen3-4B, en/zh/es/vi/th/sw/bn/te, ctx 8k, cap 384, n=100).
`{baseline, snapkv@r0.75, snapkv@r0.75:w<c+16>}` → `autowin.db`.
Same `r0.75` ⇒ iso-retained-KV (SnapKV keeps the window inside the budget).

**S — Schema tail** (EN, Qwen3-4B, ctx 8k, cap 384, n=100).
`--mrag-tail json` at pad 60/120/200 × `{baseline, snapkv@r0.75,
snapkv@r0.75:w<c+16>}` → `schema.db`.

---

## Registered predictions

1. Mixed-effects: `correct ~ compressed * 1[w < c_i] + (1|item)`.
   The interaction is the headline.
2. AIC on arm B: `(w − c)` vs raw `w` vs language fixed effects.
   Language FE is mandatory because `(w − c)` is collinear with language.
3. Allowed refinement, not a failure: the step sits at `c + ε` (a handful
   of visible question tokens). Remedy stays `w = c + 16`.
4. Arm D: bn/te damage at default w=64 closes under `w = c+16`; en stays
   flat (|Δ| ≤ 3pp).
5. Arm C: Gemma bn breaks at w ∈ {16, 24} and is flat by w=48. Qwen bn on
   the same items is still broken at w=64.
6. Arm S: damage appears iff the schema pushes the question past w;
   AutoWindow removes it.
7. Arm A: pad 48 (c < 64) is flat at w=64; pad 64+ is damaged at w=64
   and recovers once w > c.

**Kills the ICLR submission:** arm D fails to close bn/te. Diagnosis
without a settable remedy is the Chen 2026 profile. Park and go ICML.

**Does not kill:** S null (keep pad-English); C null (keep the observational
Gemma table); B cannot separate `c` from language (weaken the threshold
sentence, keep D + G2b + w32).
