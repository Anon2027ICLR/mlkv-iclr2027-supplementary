# Oracle per-item window at depth (B2) — readout — 2026-08-25

**Author: Fable (Claude).** R2 from raw output; exact CIs by
`closure_cis.py`'s method; script `scripts/iclr10_readout.py`.
Preregister: `docs/iclr-oracle-preregister.md`, locked and pushed at
`88ac260` (2026-08-25 01:21:12Z, GitHub server timestamp); first
generation of the arm 02:38Z+ — every row postdates its registration.
Store: `results/oracle_depth.db`, 2,007 rows, stack `32e553f1ae77`
(new pod). **Cross-stack determinism, the strongest yet: the baseline
and w247 cells reproduce `depth.db` byte-for-byte, 1,338/1,338, across
a stack boundary** — the campaign's cross-stack ledger moves from 800
to 2,138, all identical.

## The cells (n=669, te, own baseline; baseline acc 62.6)

| cell | value |
|---|---|
| ŵ=247 vs baseline | −5.7\* (19/57, CI [−7.8, −3.1]) — certified residual, = depth.db exactly |
| **oracle wᵢ=c+\|Qᵢ\| vs baseline** | **−5.1\* (22/56, CI [−7.3, −2.4], p=.0001) — confirmed residual** |
| **PRIMARY h2h: oracle vs ŵ** | **+0.6 (19/15, CI [−1.2, +2.3], p=.61) — indistinguishable** |
| long decile \|Q\|>80 (n=58): oracle vs ŵ | +1.7 (3/2, CI [−6.1, +7.7]) — no gain even where the rules differ |

Marker-only robustness: same picture (−9.4/−8.5 vs baseline, h2h +0.9
[−1.3, +3.0] ns).

Item audit of the oracle residual (broken n=56 vs pool n=669, Fisher):
gold position front **10.7% vs 33.3% (p=.0001)**, middle **46.4% vs
33.3% (p=.038)**, back 42.9% (p=.14); |Q| > median 60.7% vs 49.2%
(p=.093, ns). The residual patterns by gold POSITION — depleted at
front, concentrated mid/back — and not significantly by question
length. This is the first position enrichment in the campaign to reach
significance (the instruction-first audit pointed the same way at
p=.17); it is what ordinary retrieval-difficulty eviction cost looks
like, and what a visibility failure could not produce (visibility does
not vary with gold position).

## Scorecard against the registered readings

| # | Registered reading | Result | |
|---|---|---|---|
| 1 | primary Δ + h2h with CIs | above | run as registered |
| 2 | **(iv) reinforced** iff oracle CI ∌ 0 AND point within ±3pp of −5.7 AND h2h CI ∋ 0 | −5.1 ∌ 0; \|−5.1+5.7\|=0.6; h2h [−1.2,+2.3] ∋ 0 | **FIRES** |
| 3 | (iv) revised branch | does not fire | — |
| 4 | intermediate | does not fire | — |
| 5 | item audit, proportion form | above (position signal reported) | done |
| 6 | long-decile secondary | +1.7 ns (n=58) | reported |

**Binding branch: reading 2 — contribution (iv) is reinforced by the
strongest visibility treatment that exists.** Per-item Vᵢ=1 with no
percentile leftover removes 0.6pp of a 5.7pp residual, with the
head-to-head interval containing zero. Reviewer-5 Q1 is answered by
measurement: the oracle upper bound of the remedy does not close the
residual, so the residual is not visibility at any granularity — and
the paper may now say so with the position-enrichment mechanism
sketch beside it. The percentile's honesty note stands: the oracle's
CI upper bound (−2.4) sits above the −3 gate line, so the oracle cell
reads "confirmed", not "certified"; the difference between the two
windows is smaller than the vocabulary distinction.
