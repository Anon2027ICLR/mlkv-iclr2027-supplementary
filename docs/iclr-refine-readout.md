# Refine layout: a shipped template, measured (B1) — readout — 2026-08-25

**Author: Fable (Claude).** R2 from raw output; exact CIs by
`closure_cis.py`'s method; script `scripts/iclr10_readout.py`.
Preregister: `docs/iclr-refine-preregister.md`, locked and pushed at
`88ac260` (01:21:12Z); first generation 02:38:36Z. Store:
`results/refine.db`, 400 rows, stack `32e553f1ae77`. On-pod guard
asserted the T06 geometry on a probe item (query-first, T06 suffix
last) before any generation.

## The cells (n=100 per language, T06 layout, own baselines)

| cell | value |
|---|---|
| en refine baseline | 87.0 (instr-last baseline was 93 — a layout effect, absorbed by within-store pairing) |
| **en w64 vs baseline** | **−3.0 (1/4, CI [−4.9, +2.2], ns)** |
| bn refine baseline | 80.0 |
| **bn w64 vs baseline** | **−8.0 (3/11, CI [−12.7, +0.2], p=.057)** |

Marker-only scoring is structurally absent here — the T06 template
asks for "Refined Answer:", never for the `####` convention, so the
marker-only column is 0 by construction and carries no information;
the lenient scorer's first-sentence branch does all scoring, as the
layout dictates.

## Scorecard against the registered readings

| # | Registered reading | Result | |
|---|---|---|---|
| 1 | primary paired Δ + CI per language | above | run as registered |
| 2 | blind-mode branch: en ≥ 5pp loss, CI ∌ 0 → main-text result | en −3.0, CI ∋ 0 | **does not fire** |
| 3 | benign branch: \|Δ\| ≤ 3pp | en −3.0, at the boundary | fires for en |
| 4 | intermediate, reported with intervals | bn −8.0, CI [−12.7, +0.2] | bn is this |
| 5 | the rule's output here is a refusal (ŵ ≈ whole prompt) | reported as registered | — |
| 6 | no cross-language comparison | none made | — |
| 7 | scope honesty (our items, not an agent loop) | pre-written, applies | — |

**Binding reading: the hoped-for headline did not materialize, and the
preregistration makes that easy to say.** Total blindness in the
shipped refine layout — V=0 for every item, every language — costs
English a non-significant −3.0 at n=100, consistent with Gemma's
undamaged blind-English cells: blindness is necessary for the failure,
not sufficient. Bengali's −8.0 at p=.057 is suggestive and
uncertified; it is reported as exactly that, with no claim on top.
What the arm buys the paper is still real: the survey's strongest
static-geometry example now carries a damage measurement instead of an
inference, and the honest sentence in the wild-layout appendix changes
from "not tested" to "tested; benign on our items at n=100, with the
Bengali interval leaving room for a real effect."
