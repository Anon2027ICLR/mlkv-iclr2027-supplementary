# 16k prefill slice (B4) — readout — 2026-08-25

**Author: Fable (Claude).** R2 from raw output; exact CIs by
`closure_cis.py`'s method; script `scripts/iclr10_readout.py`.
Preregister: `docs/iclr-ctx16k-preregister.md`, locked and pushed at
`88ac260` (01:21:12Z); the arm ran last in the chain (done 08:10Z).
Store: `results/ctx16k.db`, 300 rows, stack `32e553f1ae77`. The 100
eval qids are exactly the 8k eval set's first hundred (overlap
100/100, the registered reporting).

## The cells (n=100, te, ctx 16k, own baseline)

| cell | value |
|---|---|
| 16k baseline | 54.0 (8k full-pool baseline is 62.6; longer prompts are harder — descriptive only, not item-paired across lengths) |
| **w64 vs baseline (blind)** | **−15.0\* (3/18, CI [−19.7, −5.7], p=.0015) — certified** |
| **ŵ=247 vs baseline (GATE)** | **−2.0 (3/5, CI [−6.6, +4.1]) — gate MET, interval wide** |
| **ŵ vs w64 (recovery)** | **+13.0\* (15/2, CI [+4.6, +16.5], p=.0023)** |

Marker-only: same shape (hole −14\* certified, recovery +10\*
p=.021; gate point −4, one point outside — the lenient scorer is the
registered primary and the ordering is unchanged).

## Scorecard against the registered readings

| # | Registered reading | Result | |
|---|---|---|---|
| 1 | blind mode persists at 16k (prediction: certified loss) | −15.0 [−19.7, −5.7] | **holds** |
| 2 | the SAME integer ŵ=247 meets the gate and recovers | gate met (−2.0); recovery +13.0\* | **holds** |
| 3 | magnitude vs 8k reported descriptively, no cross-length test | −15 vs −19/−20 at 8k; stated, untested | done |
| 4 | mitigation branch (hole < 10pp) | does not fire | — |
| 5 | no pooling with 8k stores | none | — |

**Binding reading: both registered predictions hold.** The blind mode
is prefill-independent, exactly as the threshold account requires
($c{=}167 > 64$ does not move with prompt length), and the SAME
integer computed from the tokenizer and template — no re-measurement,
no re-tuning — meets the gate at twice the prefill with a significant
recovery. Reviewer-5 Q2 is answered: the effect and the remedy both
survive 16k, and the remedy's inputs being prefill-free is now a
measured fact rather than an observation about the formula.
