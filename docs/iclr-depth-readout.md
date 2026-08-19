# Depth arm — readout — 2026-08-19

**Author: Fable (Claude).** R2 from raw output, paired within
`results/depth.db`, McNemar + exact CIs. Preregister:
`docs/iclr-depth-preregister.md` (`43049d1`) with two dated amendments
(guard mis-specification `8f3adf5`; mid-run harness-cap fix `cfc95ce`).
Stack: **`d7368e8bd94a` — the campaign stack, reproduced a fifth time.**
The 400 rows shared with `autowin-final` (te/bn baselines and default
windows) are byte-identical; same-stack determinism rises to
**3,843/3,843** and the ledger now counts `depth.db`.

## The headline: the changes-the-paper branch fired, as preregistered

| cell | full pool | n=100 history |
|---|---|---|
| te baseline (n=669) | 62.6 | 56 |
| te w64 | **−20.2\*** (19/154, CI [−22.4,−17.3]) | −19\* |
| te ŵ=247 | **−5.7\*** (19/57, p=1.5×10⁻⁵, **CI [−7.8,−3.1]**) | 0 |
| te recovery w64→ŵ | **+14.5\*** (117/20, p=7×10⁻¹⁸) | +19\* |
| bn baseline (n=113) | 71.7 | 73 |
| bn w64 | −15.0\* (3/20, CI [−19.2,−6.7]) | −16\* |
| bn ŵ=183 | **−1.8** (6/8, CI [−8.0,+5.2]) — gate met | −2 |
| bn recovery | +13.3\* (18/3, p=.0015) | +14\* |

**Prediction 5 fires.** Telugu at ŵ on the full pool is −5.7 with an
interval entirely below −3: the full pool does not merely miss the
gate, it **certifies the residual**. The decomposition is exact: the
original 100 items reproduce byte-identically and still sit at 0.0
(6/6); the 569 new items sit at −6.7\* (13/51). The n=100 gate-met was
sampling luck, and the preregister's own words apply: the full-pool
number becomes the headline, the abstract's gate sentence is
requalified, and we do not wordsmith around it.

## Scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | te ŵ within ±3 on the full pool | −5.7\* | **miss** |
| 2 | blind hole replicates on the new items alone | [100:669] at w64: −20.4\* | **hold** |
| 3 | te interval non-inferior at −3 | interval [−7.8,−3.1] — certifies the *miss* instead | **inverted** |
| 4 | bn full-pool within 2pp of n=100 | 71.7/−15.0/−1.8 vs 73/−16/−2 | **hold** |
| 5 | changes-the-paper | **fires** | binding |

## Why this makes the paper more coherent, not less

The certified Telugu residual is **not a visibility failure**: of its 57
residual items, **51 have the entire question inside the window**
(|Q| ≤ Q₉₀ = 80), and coverage on the full pool is 611/669 (bn: 98/113;
bn residual 7/8 fully visible). That is the same diagnosis as every
other missing cell — Gemma-bn (plateau), 8B-bn (8/8), Llama-bn (9/11) —
now measured on the primary model at 6.7× the sample. The paper's
residual story stops having an exception: **the rule removes the blind
mode everywhere (te recovery +14.5\* at p=7×10⁻¹⁸, the strongest
significance in the campaign) and leaves a few-point eviction residual
that visibility cannot explain.** Bengali still meets the gate on its
full (capped) pool; its interval stays wide, as always stated.

## An honesty correction to our own external-timestamp claim

The push record (`6e833be`) said the depth registration was externally
timestamped "before any of its data". Too strong: pod generation began
at 23:54Z on the 18th (Grok reran immediately after the guard amendment
at 23:30Z, before the push-first plan existed at 00:10Z — no instruction
was violated), and the GitHub push landed at 01:18Z on the 19th. What is
true and stays valuable: the preregister **commit** (16:32Z) precedes
all generation by 7.4 hours in author-controlled history, and the
**external** timestamp precedes every Bengali row (01:43Z onward), the
entire [300:669] Telugu extension (post-02:21Z) on which predictions 2
and 5 rest, and amendment 2 — 1,446 of 2,346 rows. The release-plan
status line carries the same correction, and the paper may claim only
this form.

## QC — checked rather than assumed (2026-08-19, second pass)

Cell integrity: ids contiguous 0..668/0..112, no duplicates, all six
cells full. No degeneracy: zero empty outputs, one repetition loop in
2,346 rows, at-cap 8.5–11% on te (vs 96–100% when generation actually
collapses — the random control's signature); prompt-token medians are
identical across the pre-fix and post-fix blocks (8185/8187/8186), the
resume invariant visible in the data itself. Markers healthy (te
83–87%, bn 96%; the Llama-te pathology does not appear on Qwen). Drift
flags: 2 rows, both in te w64.

**The certified residual is genuine, not a scoring artifact.** Of the
57 residual items, the gold string appears anywhere in the ŵ output for
only 5; the rest are true content misses or fidelity degradations the
frozen metric counts by design (sampled: a partial answer listing one
crop of three; a city-name variant "విశాఖపురం" for "విశాఖపట్నం"; a
paraphrase that drops the exact span). Only 10/57 ran to the decode
cap and 19/57 lack the marker — neither failure mode dominates. And
under the stricter marker-only scorer the residual is **−9.4\***
(24/87, p=1.4×10⁻⁹): same sign, still certified — Appendix C's
every-conclusion-unchanged claim extends to this arm.

## A correction to the marker-only pair (2026-08-19, wave-3 adjudication)

The QC paragraph above quotes the marker-only residual as −9.4\* at
24/87 with p=1.4×10⁻⁹. The delta is right and the pair is not. The
24/87 came from a leaky hybrid definition — "marker present, then
`extract_span`" — and `extract_span`, on an output whose marker is
followed only by debris, silently falls back to scoring the **whole
text**, which is the exact leak marker-only scoring exists to close.
The strict rule (span after the last marker that still has content;
no marker scores wrong) is the rule the paper's Appendix C already
uses — it reproduces the printed dose-ladder accuracies 50/35/47 —
and under it the depth residual is **−9.4\* at 25/88, p=2.1×10⁻⁹,
CI [−11.9, −6.5]**: same delta, same sign, still entirely below the
gate. Every conclusion drawn from the QC paragraph stands; only the
discordant pair and the p change. Found by the wave-3 executor's
independent reproduction (it could produce −9.4 under every clean
definition but never the 24/87 pair), adjudicated by re-deriving both
numbers from `depth.db`; the scorer is now pinned as
`qa_metrics.containment_match_marker_only` with unit tests, and the
audit pins the ladder trio, the pair, the p and the interval. The
paper quotes only the corrected pair.

## Integration memo (Opus wave 3; every number above binds)

- **Abstract**: `meets its $\pm 3$\,pp gate on English, Bengali and
  Telugu ($+2/{-}2/0$\,pp)` and the `+14/+19` recovery clause are
  requalified: gate at n=100, full-pool Telugu certifies −5.7
  [−7.8,−3.1] beside +14.5 recovery (p<10⁻¹⁷); "Where the gate is
  missed, the residual is not a visibility failure" now carries Telugu
  too. Page-1 budget protocol applies.
- **§6 gate paragraph**: full-pool sentence; recoveries +14/+19 →
  +13/+14 (full-pool values); coverage `88 of 100 … 93 of 100` →
  `98 of 113 … 611 of 669`.
- **§6 residuals paragraph**: `The three cells that miss the closure
  gate are all Bengali` is now false — four cells, one of them the
  primary model's Telugu at n=669; add its 51/57 audit; drop "also the
  only cell where a miss could appear".
- **Limitations**: `each cell rests on 100 items` → the headline cells
  now rest on the full validation pools (669/113); Telugu's interval
  certifies its residual; Bengali's pool is structurally capped.
- **app:ci**: full-pool rows (te ŵ [−7.8,−3.1] *certified residual*;
  bn ŵ [−8.0,+5.2] gate met); 8B-bn's "confirmed residual" has company.
- **Bookkeeping**: store list +`depth` (eighteen main + two cap-era);
  prereg table row (`43049d1`, first generation 23:54Z, yes) + both
  amendments noted; determinism 3,843; external-timestamp claim in its
  corrected form only.
- **Audit**: depth loader; the eight table cells above; coverage counts
  via the tokenizer-gated block; recovery f/b pairs.
- **Never write**: "closes" for bn full pool (CI wide); any use of the
  n=100 Telugu 0 as current (history only, labelled); any averaging of
  n=100 with full-pool numbers; the uncorrected external-timestamp
  claim.
