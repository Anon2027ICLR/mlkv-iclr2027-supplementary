# Constant-vs-rule and the ranking control — readout — 2026-08-19

**Author: Fable (Claude).** R2 from raw output, paired within
`results/constant.db`, n=100/cell, McNemar + exact CIs. Preregister:
`docs/iclr-constant-and-ranking-preregister.md` (`e287172`, 13:01 UTC —
53 minutes before the first generation at 13:54 UTC; the
commit-precedes-run column gains a row). Stack: **a fifth descriptor**,
`82b8ad33f530` (campaign driver, different host kernel). All pairing is
within-store; ŵ and default-window numbers beside the cells are
cross-stack context in brackets. The 300 uncompressed baselines shared
with the AutoWindow store are **byte-identical across this boundary
too** — cross-stack determinism is now 600/600 over two independent
drifted pods, and the ledger prints it separately from the 3,243.

**Pool check (W4 scoping), resolved 2026-08-19** — the pod log never
carried it home, so it was re-run locally (pure `datasets`, no GPU):
TyDiQA-GoldP validation pools are **bn 113, te 669, sw 499**. The
reviewer's n=500 request is therefore **feasible for Telugu and
structurally impossible for Bengali**: bn is capped at 113 evaluation
items, and reaching past the validation split would consume the train
split that Q90 is estimated on, breaking the held-out discipline. The
clean extension design, if run: final n = the *entire* validation pool
(bn 113, te 669) — a stopping rule with no free parameter, which kills
the optional-stopping objection outright. At n=669 the Telugu closure
interval scales to roughly ±2.7 pp — inside the ±3 gate for the first
time — so the extension could convert one of the two headline cells from
gate-met to certified, while Bengali's cap is stated as the honest
constraint it is.

## Numbers (Δpp vs own baseline; context in brackets)

| lang | base | w256 @ r0.75 | random @ r0.75 | [snapkv w64 / ŵ] |
|---|---|---|---|---|
| en | 93 | +1 (1/0, CI [−0.9,+1.0]) | **−87\*** (0/87) | [+0 / +2] |
| bn | 73 | **−5** (5/10, p=.30, CI [−11.5,+3.5]) | **−72\*** (0/72) | [−16\* / −2] |
| te | 56 | −3 (4/7, CI [−8.6,+4.2]) | **−56\*** (0/56) | [−19\* / 0] |

## Scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | bn and te at w256 within ±3 | te −3 meets (at the boundary); **bn −5 misses the point gate** (ns, CI [−11.5,+3.5]) | **half-miss** |
| 2 | en at w256 within ±3 | +1 | **hold** |
| 3 | random loses double digits everywhere, more than blind SnapKV | −87/−72/−56, all far beyond the blind cells | **hold — but see the mechanism note** |
| 4 | value-of-ranking ordered en > bn > te | 87/56/37 matches, **but trivially**: random sits at the floor (6/1/0%), so the ordering is the baseline ordering, not a differential measurement | technically holds, evidentially empty |
| 5 | binding rewrite if pred 1 holds | pred 1 did not hold on Bengali → **the rewrite does not fire** | — |
| 6 | w256 opens a significant tax at 0.75 | bn −5 is ns → does not fire | — |

## Reading

**The pincer, measured, lands between its jaws — on the paper's side.**
The reviewer expected the constant to suffice at the headline ratio.
Judged exactly as the rule was judged — the preregistered ±3 point gate,
each config against its own baseline in its own store — **w256 misses on
Bengali (−5) where ŵ met (−2), meets at the boundary on Telugu (−3 vs
0), and matches on English (+1 vs +2)**. The honest symmetric caveat:
the Bengali interval `[−11.5,+3.5]` cannot certify the miss any more
than ŵ's `[−9.1,+5.9]` certified the close; what is preregistered and
point-estimated is that the rule met all three gates and the constant
met two. Combined with the heavy-ratio tax (en −9\* at 0.9375), the
constant's ledger reads: never beats the rule's cells anywhere, misses
one gate at the ratio the reviewer chose, taxes English at the other.
Contribution (v) survives without the forced rewrite — but its wording
must change from "worse at the same ratio" to gate language.

**The ranking control worked too well to be a differential.** Random
eviction at r=0.75 doesn't lose answers — it **collapses generation**:
96–100% of outputs run to the decode cap and 55–61% are pure repetition
loops ("The The The…", "সসসস…"). So pred 3's headline holds (even a
blinded ranking beats no ranking by 50–87 points), but the per-language
"value of the ranking" the preregister hoped for is dominated by
coherence collapse, not answer retention — random is at the floor
everywhere and discriminates nothing. The Gemma blind-English anomaly
therefore stays an *observation*: the app:gemma sentence gets the
measured statement and loses the post-hoc explanation.

## Integration memo (Opus wave 2 — `docs/opus-wave2-2026-08-19.md`)

- Contribution (v): "worse at the same ratio" → gate language,
  length-neutral (page 2 is at an exact boundary).
- app:rivals: the r=0.75 block (random / w256 / bracketed ŵ) + the
  gate-vs-gate paragraph + the pred-1 half-miss disclosed.
- app:gemma: replace "only where the scorer's ranking was carrying the
  answer" with the measured-but-bounded statement.
- Provenance: fifth descriptor; cross-stack 300→600; ledger wording.
- Audit: six new cells; README prereg row (`e287172`, yes).
- **Never write:** a per-language value-of-ranking differential (floor
  effect); "the constant fails significantly at 0.75" (ns); "the
  constant suffices at 0.75" (bn missed the point gate); any ŵ-vs-w256
  paired claim across stacks — gate-vs-gate on own baselines only.
