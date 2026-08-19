# Preregistration: the constant at scale — w=256 on the full validation pools

**Status: REGISTERED at commit. The timestamp protocol below must
complete before any generation exists.**
Author: Fable (Claude), reviewed and committed by the author.
Date: 2026-08-19. Driver: `scripts/e_iclr8.sh`, committed alongside.

## Motivation, stated before the data

The paper's remaining contested claim is contribution (v)'s competitive
half: that one larger constant misses gates the computed rule meets. At
$n{=}100$ the constant's one clear miss (Bengali, $-5$) carries CI
$[-11.5, +3.5]$ — an interval containing the rule's own $-2$ — and the
paper concedes it "certifies neither the miss nor a close". Meanwhile
the depth arm certified the rule's own Telugu residual at $n{=}669$.
The comparison the paper does not contain is rule versus constant at
the sample size that decides things. This arm runs it, and binds us to
publish the answer whichever way it falls.

One structural fact is registered here so the readout cannot discover
it opportunistically: **on Telugu the constant nearly is the rule.**
$\hat w_{te} = 247$ and $256 = c_{te} + 89$, nine tokens above it. The
two windows should behave almost identically there — if the constant
"suffices" on Telugu, it does so by sitting 9 tokens above the computed
integer. On Bengali they genuinely differ ($\hat w_{bn} = 183$;
$256 = c_{bn} + 149$), so Bengali is where a real separation could
appear, on a pool capped at 113. We state this asymmetry now, as part
of the design, not later as an explanation.

## Design

- Model `Qwen/Qwen3-4B`, task `mrag`, ctx `8k`, eviction ratio 0.75.
- Languages: te and bn. English excluded: at this ratio no tested
  window costs English anything ($+1$ at $n{=}100$), so an English cell
  cannot separate the arms and would be spent tokens.
- Items: the **entire** TyDiQA-GoldP validation pools — te 669, bn 113
  — constructed identically to the depth arm (same seed formula
  `{SEED}:{lang}:{ctx}:{i}`, gold position `i % 3`, `max_items` set to
  the pool size). The stopping rule is everything-there-is: final $n$
  is the whole pool, no free parameter, nothing to stop early on.
- Configs generated in this arm: `baseline` and `snapkv@r0.75:w256`,
  both languages. The baseline is re-generated deliberately — see G2.
- Store: `results/constant_depth.db`. Driver: `scripts/e_iclr8.sh`
  (`set -euo pipefail`; guards abort before generation).

**Standard cost: 1,564 generations** (2 configs × 782 items).
**Fallback cost (branch G2-B): 2,346** — the depth arm's size.

## Guards, checked before and during the run

- **G1 (pre-run, aborts):** eval ∩ Q90-source = ∅ under the corrected
  invariant, with the three known duplicate Bengali ids (val idx
  38/51/68) pinned as the only allowed overlap, exactly as in the depth
  preregister's Amendment 1.
- **G2 (pairing license):** comparisons pair within one stack.
  - **Branch A (expected):** the pod reproduces stack `d7368e8bd94a`
    AND the re-generated baselines are byte-identical to `depth.db`'s
    (782/782). Then the depth store's $\hat w$ cells are in-stack and
    pairable, and the head-to-head below uses them directly.
  - **Branch B:** stack differs, or any baseline row differs. Then
    $\hat w$ (te 247, bn 183) is also generated on this pod (+782),
    every comparison pairs within `constant_depth.db` only, and all
    depth-store numbers become bracketed context. No mixed pairing
    under any wording. The driver also takes branch B when it cannot
    verify byte-identity on-pod (`depth.db` absent) — a conservative
    superset: extra $\hat w$ rows only add checks and can never weaken
    the registration.
- **G3 (degeneracy kill):** if any cell shows ≥50% at-cap generations
  or ≥30% repetition loops, stop; the cell is generation collapse (the
  random-control signature) and supports no accuracy claim.

## Predictions

- **P1.** Baselines reproduce byte-identically against `depth.db`
  (782/782) — the campaign stack's sixth reproduction.
- **P2 (primary endpoint, te).** Paired $\hat w$ vs $w{=}256$ on the
  669 shared items: $|\Delta| \le 2$\,pp with a CI containing 0 — a
  tie, per the nine-token argument above.
- **P3 (te vs baseline).** $w{=}256$ leaves a residual within 2\,pp of
  $\hat w$'s $-5.7$, interval overlapping $[-7.8, -3.1]$.
- **P4 (bn, secondary).** Paired $\hat w$ vs $w{=}256$ at $n{=}113$:
  point estimate favours $\hat w$ ($\Delta \ge 0$ in $\hat w$'s
  favour); the interval is expected wide, and we do not expect
  certification either way on a 113-item pool.
- **P5 (binding branches — the readout must take exactly one):**
  - **(a) The constant wins:** $w{=}256$ vs baseline on the full te
    pool is non-inferior at $-3$\,pp (CI lower bound $\ge -3$) while
    $\hat w$'s residual stays certified. Then contribution (v)'s
    competitive half is **rewritten, not defended**: the claim "one
    larger constant misses gates the rule meets" is withdrawn for this
    ratio, and the paper states that a large constant matches the rule
    at the cost of a per-family justification it cannot give. The
    transfer half (PyramidKV) is unaffected and remains the
    contribution.
  - **(b) The rule wins:** the paired head-to-head excludes 0 in
    $\hat w$'s favour on either language. Then and only then may the
    paper claim the rule beats the constant at scale, quoting the
    interval.
  - **(c) The tie (expected):** neither (a) nor (b). The paper reports
    the interval, claims no separation at this ratio, and writes the
    registered coincidence: the constant passes on Telugu where it
    sits nine tokens above the computed integer, and the $n{=}100$
    Bengali miss stays what it was — uncertified either way. The
    reviewer-facing sentence becomes "we ran the constant at the full
    pool and report the interval", which is the honest ceiling.
- No outcome is reported as an average with, or a replacement of, any
  $n{=}100$ cell; the $n{=}100$ constant arm stays in the paper as its
  own pod's result.

## Statistics

R2 scoring (`containment_match_lenient`), recomputed offline; McNemar
two-sided exact with discordant counts printed; exact-conditional
Clopper–Pearson intervals via `closure_cis.py`'s method; deltas as
`round(100*(f-b)/n)` at one decimal for full-pool cells. The marker-only
robustness variant (`containment_match_marker_only`) is run over every
new cell and reported in the readout.

## Timestamp protocol (ordered, no step optional)

1. This file is committed.
2. `bash scripts/build_release.sh`; the four gates pass.
3. The release is force-pushed to the anonymous remote (fresh
   fine-grained token, private terminal; the token is revoked after).
   The push timestamp then precedes every row of this arm.
4. Only then does the pod start.

## Amendment policy

Dated amendments in this file only, before the rows they govern, for
harness mis-specification or guard corrections — never for predictions
after data exists. The depth arm's two amendments are the precedent.
