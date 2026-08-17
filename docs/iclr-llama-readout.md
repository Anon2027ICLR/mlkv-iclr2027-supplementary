# Llama family slice — readout — 2026-08-17

**Author: Fable (Claude).** R2 from raw `output`, paired within
`results/llama.db` only, n=100/cell, McNemar + exact-conditional 95% CI
(`scripts/closure_cis.py` vocabulary). Preregister:
`docs/iclr-llama-preregister.md` (locked before generate). Stack
`bc917804cb96` — a third tokenizer family; never pooled with any Qwen or
Gemma cell. The optional te block ran.

On-pod measures (`measure_c.py`, `q_percentiles_llama.json`):
c = 25 / 125 / 190 and \(Q_{90}\) = 18 / 87 / 94 for en/bn/te →
\(\hat w\) = **43 / 212 / 284**. Llama's question fertility on bn/te is
higher than Qwen's (87/94 vs 76/80), and so is its instruction fertility
(c 125/190 vs 107/167).

## Numbers

| lang | base | default 64 | \(\hat w\) | \(\hat w\)−base (CI) | \(\hat w\)−64 |
|---|---|---|---|---|---|
| en (\(\hat w\)=43) | 97 | 98 (+1) | **98** | +1 \([-0.9,+1.0]\) | 0 |
| bn (\(\hat w\)=212) | 76 | 58 (**−18\***, CI \([-21.5,-9.2]\)) | **68** | **−8** (3/11, p=.057, CI \([-12.7,+0.2]\)) | **+10\*** (13/3, p=.021) |
| te (\(\hat w\)=284) | 51 | 46 (−5, ns) | **50** | −1 (3/4, CI \([-5.6,+4.4]\)) | +4 (6/2, ns) |

## Preregister scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | precondition \(c_{bn}>64\) | 125 | **hold** |
| 2 | en \|Δ\|≤3 at both | +1 / +1 (ceiling 97) | hold |
| 3 | bn default ≤ −8 | **−18\***, and the CI \([-21.5,-9.2]\) sits entirely below −8 | **hold** — the first hole in the campaign *confirmed by interval*, not only by test |
| 4 | **Main:** bn \(\hat w\) gate \|Δ\|≤3 | **−8** | **miss** (third soft miss; same −8 as 8B-bn) |
| 5 | slice-kill (bn flat at default) | does not fire | — |
| 6 | soft-miss residual audit | run; see below | — |
| 7 | te (optional) | default −5 (ns — no clear hole); \(\hat w\) −1 meets the gate, CI wide | low-signal cell, see caveat |

**The headline this arm buys:** the hole reproduces on a third tokenizer
family, with an interval that excludes anything milder than −9. That is
the item both reviews asked for. The formula's close does not reproduce
(−8, p=.057, CI touching zero at +0.2) — reported exactly as the
8B/Gemma misses were.

## Residual audit (pred 6 checklist, post hoc)

Eleven items are base-correct and \(\hat w\)-wrong. Nine of the eleven
have questions within \(Q_{90}\) (window covers them fully); the other
two belong to the long decile — the first arm where the registered
percentile leftover is actually visible (10/12 long-Q items correct
under \(\hat w\), vs 12/12 at 8B). 7/11 sit at the middle gold position
(8B: 6/7). Question-echo is weaker than at 8B (4/11 vs 7/8). Of the ten
default-window breaks \(\hat w\) does not recover, 4 ramble to the cap
without a marker (recovered: 2/10). Reading: mostly the same
not-blindness residual as 8B/Gemma, plus a real, small percentile
leftover.

## Data-quality caveats (do not hide)

- **te on Llama barely uses the answer marker: 88–89/100 outputs have no
  `####`** (bn: 24–44; Qwen bn was ~4). Scoring rests on the
  first-sentence rule; the marker-only robustness check that worked for
  Qwen is not available here (marker-only accuracy is 6–7%). The te row
  is a low-confidence cell and its baseline (51%) is weak; do not quote
  te-Llama as a close, quote it as "no clear hole, formula does not
  hurt".
- Llama's format-following on Indic scripts is generally poor; paired
  deltas are still within-model and within-rule, but absolute accuracies
  are even less comparable across models than usual.

## Integration memo (plan §4, branch: *soft miss*)

- §6 scale paragraph becomes scale-and-family: one added sentence — the
  default-window hole reproduces on a third tokenizer family
  (Llama-3.1-8B-Instruct: −18 pp, CI \([-21.5,-9.2]\)), where
  \(\hat w\) recovers +10 pp (p=.021) and leaves −8 (p=.057). We do not
  claim the formula closes there.
- The boundary paragraph gains a third point with a *qualified* version
  of the diagnosis: at Llama the residual is mostly not blindness
  (9/11 within-\(Q_{90}\), middle-position-heavy) but the percentile
  leftover is finally visible (2 long-Q misses).
- Appendix table in the App-H format; extend `closure_cis.py` (done) and
  `audit_paper_numbers.py` if the cells enter tables.
- May write: "the hole is a property of the method family, reproduced on
  three tokenizer families at matched retained KV."
- Never write: "closes at Llama"; anything quoting te-Llama absolute
  accuracy without the marker caveat; pooled family numbers.
