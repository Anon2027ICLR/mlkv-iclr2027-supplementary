# AutoWindow-Q90 readout — 2026-08-15

**Author: Grok 4.6.** R2 = `containment_match_lenient`. Paired on
`item_id` with `autowin-final.db` (same 100 items, stack `d7368e8bd94a`).
`autowin_q90.db` pulled 15:09 UTC; `SYNCED` touched.

Formula locked before generate: \(\hat{w}=c+Q_{90}\) → en 43 / bn 183 / te 247.

| lang | base | def 64 | *c*+16 | *Q*₉₀ | *Q*₉₀−base | vs pred \|Δ\|≤3pp |
|---|---|---|---|---|---|---|
| en | 93 | 93 | 94 | 95 | **+2.0** p=.50 | hold |
| bn | 73 | 57 (−16) | 66 (−7) | 71 | **−2.0** p=.79 | hold |
| te | 56 | 37 (−19) | 50 (−6) | 56 | **+0.0** p=1.00 | hold |

bn vs default 64: +14 pp (16/2, p=.001). te vs default 64: +19 pp
(21/2, p<.001). Incremental vs *c*+16: bn +5 (p=.27), te +6 (p=.07).

**Predictions 1–2 from `iclr-autowin-q90-preregister.md`: match.** Formula
kill (bn/te still ≤ −8 pp) does not fire.

Do not write that *c*+16 closes. Write: English-calibrated slack underdoses
long questions; \(c+Q_{90}\) closes en/bn/te at matched retained KV.
