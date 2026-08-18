# Depth on the closure cells — preregister

**Author: Fable (Claude).** Written 2026-08-19, *before* any generation
beyond item index 100 exists for bn/te on the main task. Driver:
`scripts/e_iclr7.sh chain`. DB: `results/depth.db`. Answers reviewer-3
W4: the two headline closure cells carry intervals 2–5× wider than the
±3 gate judging them, and the reviewer values depth here above any
additional model family.

## The stopping rule, fixed first

Final n = **the entire TyDiQA-GoldP validation pool**: 669 items for
Telugu, 113 for Bengali (measured 2026-08-19; the pool sizes are the
constraint, not a choice). This rule has no free parameter, which is the
point: extending n after seeing n=100 invites an optional-stopping
objection, and "we used everything there is" is the one stopping rule
that cannot be gamed. Consequences, accepted in advance:

- The **full-pool estimates become the paper's numbers** for these cells
  regardless of direction; the n=100 cells remain as the preregistered
  history they are, in their own stores.
- Bengali's cap is reported as the structural constraint it is: 113
  validation items exist, and the train split cannot be used because it
  is the Q₉₀ estimation source. Bengali's interval will stay wide and
  the paper will keep saying so.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384, self-contained (own
baselines, own stack, pairs only within `depth.db`):

- te: `baseline`, `snapkv@r0.75`, `snapkv@r0.75:w247` × 669 items
- bn: `baseline`, `snapkv@r0.75`, `snapkv@r0.75:w183` × 113 items

≈ 2,350 generations, one session. The windows are the shipped AutoWindow
integers, unchanged; the driver re-derives them on-pod and **aborts on
mismatch** (environment drift, not a new ŵ). Two further guards, both
FATAL: the held-out/eval separation check (no evaluation item id may
appear in the Q₉₀ estimation split — the split is `train`, eval is
`validation`, and the driver asserts the id sets are disjoint rather
than assuming it), and the usual stack preflight.

## Amendment, 2026-08-19 — before any generation exists

The guard fired on its first run, which is what guards are for, and what
it found was a mis-specification in the guard itself, not in the
discipline it protects. TyDiQA-GoldP's Bengali train and validation
splits share **three exact duplicate examples** (same id, same question,
same context: indices 38, 51 and 68 of the validation pool). The guard
as written demanded the *raw HF splits* be disjoint — a property of the
dataset we do not control. The invariant the preregistration actually
depends on is ours: **no evaluation item may contribute to the Q₉₀
estimation set**, and that set has always been `train` minus the ids of
`validation[:100]` (`measure_q.py`), which excludes all three duplicates.
Re-verified independently on 2026-08-19: eval(full pool) ∩ Q₉₀-source =
∅ for both languages, and the item builder is inert to the wart as well
(distractor pools deduplicate by context string and exclude the gold by
string equality, so a train copy of an eval item's context can neither
duplicate the gold nor enter its own prompt).

The guard is therefore corrected to assert the true invariant, the three
duplicate ids are reported here rather than silently tolerated, and
nothing else changes: predictions, stopping rule and paper consequences
below stand as written. The run also exposed a driver bug — `| tee`
swallowed the FATAL exit code — fixed in `533ca26` (`set -uo pipefail`)
before any generation; the same latent pattern exists in the earlier
drivers `e_iclr4–6`, where it never bit because their guards passed.

## Predictions (fixed)

1. **Main:** Telugu at $\hat w{=}247$ meets the ±3 point gate on the
   full pool (n=100 value: 0).
2. The Telugu blind hole replicates **on the new items alone** (items
   [100:669] at the default window: ≤ −10, significant) — the guard
   against the extension block differing systematically from the
   original hundred.
3. The Telugu closure interval at n=669 is non-inferior at −3 — the
   first certifiable close on a headline language. This is the
   prediction most at risk: interval width depends on the discordant
   count, not n alone, and ±2.7 is an extrapolation. If the interval
   lands wide of −3, the paper reports gate-met-not-certified exactly as
   it does today, at triple the sample.
4. Bengali full-pool (n=113) values sit within 2\,pp of the n=100
   values — stability, not a new claim.
5. **Changes-the-paper risk:** Telugu at $\hat w$ on the full pool ≤ −4
   → the n=100 gate-met was sampling luck; the full-pool number becomes
   the headline, the abstract's gate sentence is requalified, and we do
   not wordsmith around it.

Reporting: R2 from raw output, McNemar with discordant counts,
`closure_cis.py` extended with the full-pool rows; never pool across
stacks; the n=100 and full-pool estimates are never averaged — the
full-pool number supersedes by preregistered rule.

## Paper consequence (decided now)

If preds 1–3 hold: app:ci gains the full-pool rows; the §6 gate
paragraph's interval sentence upgrades for Telugu ("certified
non-inferior at n=669") and keeps Bengali's honest cap; one sentence in
Limitations replaces "each cell rests on 100 items" with the split
picture. If pred 3 alone fails: same edits minus the word "certified".
If pred 5 fires: the abstract and §6 requalify, and the reviewer was
right that the gate was a coin-flip — reported in those words.
