# Constant-at-scale arm — readout — 2026-08-19

**Author: Fable (Claude).** R2 from raw output; McNemar + exact CIs by
`closure_cis.py`'s method. Preregister:
`docs/iclr-constant-depth-preregister.md` (`1690413`, 10:33Z), no
amendments. Store: `results/constant_depth.db`, 1,564 rows, stack
**`d7368e8bd94a` — the campaign stack, reproduced a sixth time.**
Driver guards all passed; **BRANCH=A on both languages** (baselines
byte-identical to `depth.db`, 782/782), so the depth store's $\hat w$
cells pair in-stack, per guard G2.

**The external timestamp is fully clean for the first time.** From the
public events feed: the release carrying this registration was pushed
at **11:07:07Z** (`6819299`); the first generation is **11:55:16Z**.
Every row of this arm postdates its third-party timestamp by at least
48 minutes — the first arm in the campaign for which the external
timestamp precedes all of its data, with no correction needed.

## The cells (full pools; $\hat w$ cells from `depth.db`, in-stack)

| cell | value |
|---|---|
| te baseline (n=669) | 62.6 (byte-identical to depth) |
| te w256 vs baseline | **−6.9\*** (20/66, p=6.7×10⁻⁷, CI [−9.0, −4.2]) — **certified residual** |
| te ŵ=247 vs baseline | −5.7\* (19/57, CI [−7.8, −3.1]) — certified residual (depth) |
| **te PRIMARY: ŵ vs w256** | **+1.2 in ŵ's favour (16/8, p=.15, CI [−0.4, +2.5])** — tie, CI contains 0 |
| bn baseline (n=113) | 71.7 (byte-identical to depth) |
| bn w256 vs baseline | **−3.5** (6/10, ns, CI [−9.9, +4.1]) — **misses the point gate** |
| bn ŵ=183 vs baseline | −1.8 (6/8, CI [−8.0, +5.2]) — meets the gate (depth) |
| bn ŵ vs w256 | +1.8 in ŵ's favour (5/3, ns, CI [−3.6, +5.9]) |

## Scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | baselines byte-identical 782/782 | 669/669 + 113/113 | **hold** |
| 2 | te head-to-head a tie: \|Δ\| ≤ 2, CI ∋ 0 | +1.2, CI [−0.4, +2.5] | **hold** |
| 3 | te w256 residual within 2pp of −5.7, CIs overlap | −6.9, CI [−9.0, −4.2] | **hold** |
| 4 | bn point favours ŵ, interval wide, no certification | +1.8, CI [−3.6, +5.9] | **hold** |
| 5 | binding branch | **(c) the tie fires** | binding |

Branch (a) does not fire: w256's Telugu CI lower bound is −9.0, nowhere
near non-inferior at −3. Branch (b) does not fire: neither head-to-head
excludes 0 — though Telugu's misses it by 0.4 of a point on ŵ's side.

## What branch (c) licenses, exactly

Per the registration: the paper reports the intervals, claims **no
certified separation** at this ratio, and writes the registered
coincidence — on Telugu the constant sits nine tokens above the
computed integer, so no separation there was the expected outcome, and
none was found.

Two facts beyond the minimum are legitimately reportable because they
are **same-stack gate outcomes at the full pools** (not the cross-pod
n=100 comparison the paper brackets):

1. **Bengali gate asymmetry, one stack:** $\hat w$ meets the point gate
   (−1.8) where the constant misses it (−3.5). The head-to-head is
   uncertified (CI [−3.6, +5.9]) and must be printed beside it.
2. **Telugu, both certified, the constant deeper:** w256 leaves
   −6.9 [−9.0, −4.2] against ŵ's −5.7 [−7.8, −3.1]; paired
   head-to-head +1.2 toward ŵ, CI [−0.4, +2.5]. A 256-token protected
   tail costs slightly more than a 247-token one and recovers nothing —
   consistent with the heavy-ratio tax direction, far milder at 0.75.

The n=100 constant arm (`constant.db`, its own pod) stays in the paper
untouched as its own pod's result; nothing here averages with it.

## QC — checked rather than assumed

Cell integrity: item sets equal to depth's, both languages, both
configs. No degeneracy: 0 empty outputs, 0 drift flags, at-cap 9% (te)
and 3% (bn) — inside the healthy 8.5–11% band the depth arm
established, nowhere near the 96–100% collapse signature. Markers
healthy (te 82%, bn 98%). Under the stricter marker-only scorer the
Telugu w256 residual is **−9.3\*** (26/88, p=4.6×10⁻⁹,
CI [−11.8, −6.3]) beside ŵ's −9.4 (25/88) — same shape, both
certified, robustness carries.

Determinism ledger (script, not hand-count): same-stack
**4,625/4,625** (+782), and a bonus — the 200 baseline rows this store
shares with `constant.db` cross a stack boundary and are byte-identical,
lifting the cross-stack count to **800/800**.

## Integration memo (wave 5; every number above binds)

- **app:rivals, "One larger constant"** gains the full-pool paragraph:
  the registered coincidence sentence (te: 256 = ŵ+9), the two same-
  stack facts above with their intervals, and "no certified
  separation" stated plainly. This is appendix text — page-budget
  free.
- **tab:rivals** third block gains a full-pool sub-block or the
  paragraph carries the numbers inline — Opus measures which fits.
- **Contribution (v)** may be strengthened only within branch (c)'s
  license, e.g.: the constant "misses at the full pool the Bengali
  gate the rule meets, and leaves a deeper certified Telugu residual;
  the head-to-head is not certified". If main-text lines are
  unavailable, (v) stays as is — the appendix carries it.
- **Reproducibility statement:** store list +`constant_depth`
  (twenty-one named + e3/e3_384 = twenty-three total); arms
  "nine of the twelve" → **"ten of the thirteen"**; the sentence may
  now also say one arm's external timestamp precedes all its rows.
- **README preregistration table:** row `1690413` | 2026-08-19 10:33 |
  first generation 11:55 | yes — footnote: external push `6819299` at
  11:07Z precedes every row (events-feed reconstruction; first arm
  with full external precedence).
- **Determinism:** 3,843 → **4,625** everywhere it appears (§3 + twice
  in app:provenance); cross-descriptor 600 → **800** with one clause
  for the new 200.
- **Audit:** `constant_depth.db` loader; the eight cells above
  (baseline accs, w256 deltas + pairs + CIs via the closure_cis
  method, both head-to-heads); byte-identity 782/782 as a check;
  marker-only (26/88). `closure_cis.py` gains the two w256 full-pool
  rows if they enter tab:ci or app:rivals quoting intervals.
- **Never write:** "certifies the separation" or "the rule beats the
  constant" (branch (b) did not fire — Telugu's CI contains 0 by 0.4
  of a point and that number gets printed, not rounded away); "the
  constant fails at scale" unqualified (Bengali's head-to-head is
  wide); any pooling or averaging of `constant.db` (own pod, n=100)
  with these cells; "saturation" language for the te tie — the
  registered coincidence is the explanation on record.
