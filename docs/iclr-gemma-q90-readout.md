# Gemma AutoWindow-Q90 readout — 2026-08-17

**Author: Fable (Claude).** R2 from raw `output`, paired within
`results/gemma_q90.db` only, n=100, McNemar two-sided. Preregister:
`docs/iclr-gemma-q90-preregister.md` (locked before generate).

**Stack note.** Pod reproduced the original Gemma environment exactly →
stack hash `a2011e0bd133` (same as arm C); re-run baselines are
token-identical to `cliff_gemma.db` (greedy determinism). Comparisons stay
within this db.

On-pod measures matched the dev-box lock: c = 27/32/44,
\(Q_{90}\) = 18/18/20 (`results/q_percentiles_gemma.json`) →
\(\hat w\) = **45 / 50 / 64** for en/bn/te.

## Numbers

| lang | base | def 64 | \(\hat w\) | \(\hat w\)−base | \(\hat w\)−def64 |
|---|---|---|---|---|---|
| en (\(\hat w\)=45) | 75 | 78 (+3) | **78** | **+3** p=.25 | 0 |
| bn (\(\hat w\)=50) | 62 | 57 (−5, p=.23) | **56** | **−6** (3/9, p=.15) | −1 |
| te (\(\hat w\)=64) | 37 | 34 (−3) | **34** | **−3** p=.55 | 0 (identical outputs) |

## Preregister scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | en \|Δ\| ≤ 3 at def64 and \(\hat w\) | +3 / +3 | hold (at the boundary) |
| 2 | bn def64 in −9…0 | −5 | hold |
| 3 | **Main:** bn \(\hat w{=}50\) \|Δ\| ≤ 3 | **−6** | **miss** |
| 4 | te \(\hat w{=}64\) ≡ default, both ≥ −4 | identical (w64 explicit = default), −3 | **hold** |
| 5 | Kill: bn \(\hat w \le -8\) | does not fire | — |

Pred 3 is a **soft miss**, same shape as 8B-bn: the formula does not close,
the kill does not fire.

## Reading (after the fact, labeled as such)

At \(\hat w{=}50\) with \(Q_{50}^{bn}{=}11\), the question is fully inside
the window for most items (\(V{\approx}1\)), yet bn still loses ~5–6 pp —
the same plateau the old stack showed at every \(w \ge 48\) (−5 ns at
48 and 64). The Gemma-bn residual is therefore **not blindness**; it is
the same not-window damage family as the 8B-bn residual. Consistent story
across both misses: \(c+Q_{90}\) removes the blind mode; it does not
remove a ~5 pp press tax that exists at every window Gemma was tested at.

## What we may / may not write

- **May** (pred 4 held): *for Gemma-te the formula returns the shipped
  default (64) — it also knows when the default suffices.*
- **May**: hole follows \(c\) (arm C) and \(\hat w\) avoids the deep
  \(w{=}16/24\) hole (−13/−10 on the old stack) by construction.
- **May not**: "\(c+Q_{90}\) closes on Gemma" (pred 3 missed); pooled
  Gemma/Qwen numbers; en "+3 confirms anything" (75% baseline, help ns).
- Do not retune \(Q_{90}\) or swap the scorer (design lock).

Paper consequence (plan §3 branch "miss"): one paragraph + appendix row,
treated exactly like the 8B soft miss; the identification story is
unaffected.
