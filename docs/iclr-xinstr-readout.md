# English instruction × non-English questions (B2) — readout — 2026-08-24

**Author: Fable (Claude).** R2 from raw output; exact CIs by
`closure_cis.py`'s method; enrichment in proportion-test form (Fisher
exact). Script: `scripts/iclr9_readout.py`. Preregister:
`docs/iclr-xinstr-preregister.md` (`96bd5e2`, 2026-08-23 15:42Z), no
amendments. Store: `results/xinstr.db`, 600 rows, stack
`d7368e8bd94a`. On-pod guards passed: c_en = 25 for the cross prompt
(abort threshold 32 not approached), Q90 re-derived 76/80, match.

## The cells (n=100 per language, en instruction, c=25)

| cell | value |
|---|---|
| bn baseline | 79.0 |
| bn w64 vs baseline | −3.0 (3/6, ns, CI [−7.7, +3.6]) |
| bn ŵ=101 vs baseline | −2.0 (3/5, ns, CI [−6.6, +4.1]) |
| te baseline | 62.0 |
| te w64 vs baseline | −4.0 (2/6, ns, CI [−7.5, +2.4]) |
| te ŵ=105 vs baseline | −4.0 (0/4, ns, CI [−4.0, +0.8]) |

V<1 composition at w=64 (slack 39): bn 70/100 items, te 93/100 items.
Broken-by-w64 counts are 6 and 6; V<1 share among broken = 5/6 (bn),
6/6 (te) vs pool shares 70% / 93% — Fisher p = .67 / 1.00. With 93% of
the Telugu pool already V<1, the enrichment test has no discriminating
power at this damage level; it is reported, as registered, without a
claim on top.

## Scorecard against the registered predictions

| # | Prediction | Result | |
|---|---|---|---|
| 1 | report V<1 split as a proportion test | done (no signal, n too small) | reported |
| 2 | scope WIDENS if ≥ 5pp loss with enrichment | no cell loses ≥ 5pp | does not fire |
| 3 | scope NARROWS if both within ±3pp | bn −3.0 yes; te −4.0 point misses by 1pp, CI ∋ 0 | fires with a caveat |
| 4 | readout format locked | this file | — |
| 5 | ŵ rows ≈ baseline, V=1 for ≥ 90% | Δ −2.0/−4.0 ns; V=1: bn 88/100, te 93/100 | holds (bn 88 < 90, noted) |
| 6 | no cross-language accuracy comparison | none made | — |

**Binding reading: the near-production cell shows no detectable
damage.** With an English instruction, neither Bengali nor Telugu shows
a significant loss at the default window (points −3.0/−4.0, both CIs
containing 0), against −13/−21-point certified holes when the
instruction is in-language. The scope narrows honestly: the blind mode
requires a trailing block long enough to hide the whole question, and
partial visibility with an English-sized tail is benign on these items
— consistent with the English and Gemma partial-visibility
observations. Limitations gains the registered sentence, stating the
point estimates and that the n=100 intervals cannot rule out losses up
to ~7pp.

Prediction 3's letter ("both within ±3pp") is met by bn only; te's
point is −4.0. The registered format forbids re-framing: the readout
states "no significant damage, points −3/−4, CIs include 0" rather
than "both within ±3pp".

One observation outside the registered readings, flagged as such:
under marker-only scoring te loses −12.0\* (1/13) at w64 and −15.0\*
(0/15) at ŵ from a 58.0 baseline — compression under the English
instruction damages Telugu's `####` marker formatting while the answer
content largely survives (lenient −4.0 ns). Formatting fragility, not
content loss; noted for the robustness appendix, not the main text.
