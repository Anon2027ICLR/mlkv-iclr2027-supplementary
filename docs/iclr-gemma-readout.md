# Gemma arm C readout — 2026-08-15

**Author: Grok 4.6.** R2, paired on Gemma `item_id`, n=100.
`cliff_gemma.db` pulled 17:11 UTC; pod EXITED after SYNCED.
Stack `a2011e0bd133` / `google/gemma-3-4b-it`. **Do not pool with Qwen.**

On-pod `measure_c.py` (after_question): en *c*=27, **bn *c*=32**, te *c*=44.

| lang | *c* | w16 | w24 | w32 | w48 | w64 |
|---|---|---|---|---|---|---|
| en | 27 | +2.0 | +1.0 | +3.0 | +4.0 | +3.0 |
| **bn** | **32** | **−13.0*** | **−10.0*** | −9.0* | −5.0 | −5.0 |
| te | 44 | −3.0 | −4.0 | −3.0 | −1.0 | −3.0 |

\* McNemar *p*<.05. Baseline acc: en 75, bn 62, te 37.

**Preds (preregister / plan)**

1. en |Δ|≤3 at *w*≥32: **soft**. *w*32/64 hold; *w*48 is +4 (help, *p*=.13). No English damage.
2. bn breaks at 16/24, flat by 48/64: **partial**. Blind cells match (−13 / −10). *w*=32 (=*c*) still −9 (*c*+ε). *w*48/64 −5, ns, not ≤3.
3. te cliff near *c*≈44, not Qwen 167: **direction**. No Qwen-scale hole at *w*=64 (−3 vs Qwen te −19). No sharp Gemma-te step either (baseline 37% is noisy).

**What we may write.** Same-language Bengali *c* moves 107→32; the *w*=16/24 hole appears where Gemma is blind and is much smaller at *w*=64 than Qwen’s *w*=64 hole. Tokenizer, not language identity.

**What we may not write.** “Gemma bn is flat by 48.” “Gemma te has a clean step at 44.” Pooled Qwen+Gemma percentages.
