# Qwen3-32B slice (B3) — readout — 2026-08-25

**Author: Fable (Claude).** R2 from raw output; exact CIs by
`closure_cis.py`'s method; script `scripts/iclr10_readout.py`.
Preregister: `docs/iclr-32b-preregister.md`, locked and pushed at
`88ac260` (01:21:12Z); first generation 03:26:47Z on its own 80GB pod.
Store: `results/qwen32b.db`, 600 rows, stack `4493ddfae662`
(self-contained, the Llama precedent — never pooled with any other
stack). On-pod guards: c = 25/107/167 and Q90 = 76/80 reproduce on the
32B checkpoint (shared Qwen3 tokenizer and template), as registered.

## The cells (n=100 per language, own baselines)

| cell | value |
|---|---|
| bn baseline | 80 |
| **bn w64 (hole)** | **−12.0\* (1/13, CI [−13.9, −4.5], p=.0018) — certified** |
| bn ŵ=183 (GATE) | −5.0 (2/7, CI [−8.5, +1.8]) — **point gate MISSED**, interval wide |
| bn recovery ŵ vs w64 | +7.0 (9/2, CI [−0.4, +10.5], p=.065) — ns |
| te baseline | 56 |
| **te w64 (hole)** | **−4.0 (8/12, CI [−12.4, +5.6], ns)** — no certified hole at n=100 |
| te ŵ=247 (GATE) | −1.0 (2/3, CI [−4.5, +3.5]) — point gate met, interval wide |
| te recovery | +3.0 (9/6, ns) |

**Marker-only is uninformative for this arm and is reported only as a
caveat** (the Llama-Telugu precedent): 32B answers in prose and then
copies the instruction's placeholder verbatim after the marker
(`#### <সঠিক উত্তরাংশ>`), so marker compliance is 0–1% at baseline
and every 32B number rides the first-sentence branch of the registered
lenient scorer. A model-scale formatting behaviour, documented, not a
harness artefact.

## Scorecard against the registered readings

| # | Registered reading | Result | |
|---|---|---|---|
| 1 | phenomenon: certified w64 loss on both languages | bn **certified −12.0**; te **ns** | bn holds; te takes the registered "reportable scale finding" branch, stated with its interval |
| 2 | recovery significant on both | bn +7.0 p=.065; te +3.0 ns | **does not certify** — reported as-is |
| 3 | gate; a bn miss is the EXPECTED branch | bn missed (−5.0); te met (−1.0, wide) | as pre-written; bn joins the residual table |
| 4 | ceiling cells carry no information | neither at ceiling | — |
| 5 | no pooling | own stack only | — |

**Binding reading: scale softens everything, and the preregistration
said to expect caution.** The Bengali hole persists and is certified
at 32B (−12, against −16/−17 at 4B/8B); its ŵ misses the point gate at
−5, the now-familiar Bengali residual at every scale above 4B. The
Telugu cell cannot distinguish a hole from noise at n=100 (−4.0,
[−12.4, +5.6]) — an honest scale finding, not a refutation: the
threshold arithmetic (c=167 > 64) is unchanged, and what n=100 lacks
is power, not direction (f/b 8/12). If GPU budget allows before the
deadline, the decisive follow-up is the full-pool 32B Telugu arm; it
would resolve this cell the way depth resolved the n=100 gate.
