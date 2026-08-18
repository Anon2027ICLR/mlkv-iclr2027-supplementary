# PyramidKV transfer — preregister

**Author: Fable (Claude).** Written 2026-08-18, *before* any pyramidkv
`mlkv run` anywhere in this project. Driver: `scripts/e_iclr5.sh core`
(optional `te`). DB: `results/pyramidkv.db`.

## Why

The one form of the "obvious remedy" objection still standing after the
rival-remedies arms: *AutoWindow is hyperparameter tuning dressed up as a
formula — one number, fitted to one method.* The only clean refutation is
transfer: the same integer, derived offline from the prompt and never
re-tuned, must fix a **second** method of the windowed family. You cannot
tune one number on one method and have it work on another unless it
measures a property of the prompt rather than of the method.

PyramidKV is the right second member: a separately published eviction
strategy (pyramid-shaped per-layer budgets) whose kvpress implementation
`PyramidKVPress` **subclasses `SnapKVPress` and inherits the shipped
`window_size=64` verbatim**. Same scorer inputs, different allocation
policy, same inherited constant — exactly the paper's phrase "SnapKV and
its descendants", instantiated. The codebase anticipated this sweep: the
registry comment already designates knorm/random as its negative
controls.

No prior pyramidkv data exists in any store; every number below is a
genuine prediction.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384, n=100/cell, self-contained
(own baselines, own stack, pairs only within `pyramidkv.db`).

Core (600 generations):
- bn: `baseline`, `pyramidkv@r0.75`, `pyramidkv@r0.75:w183`
- en: `baseline`, `pyramidkv@r0.75`, `pyramidkv@r0.75:w43`

Optional block `te` (+300): `baseline`, `pyramidkv@r0.75`,
`pyramidkv@r0.75:w247`.

The windows 183/43/247 are **the shipped AutoWindow integers, unchanged**
— that is the treatment. The driver re-measures $c$ and $Q_{90}$ on-pod
and **aborts on any mismatch** with 107+76/25+18/167+80: a differing
value means environment drift, not a new $\hat w$. All other
PyramidKVPress parameters stay at library defaults; the driver logs the
dataclass fields so the defaults are on record. Reference SnapKV numbers
(same stack `d7368e8bd94a` if the pod reproduces it, else quoted as
cross-stack context only): bn $-16^{*}$/$-2$, en $+0$/$+2$, te
$-19^{*}$/$0$ at default/$\hat w$.

## Predictions (fixed)

1. **Hole reproduces on the second method:** bn `pyramidkv@r0.75`
   (inherited $w{=}64$) vs own baseline ≤ $-10$\,pp, McNemar $p<.05$.
   Same scorer inputs must be blinded identically; per-layer allocation
   may modulate the size, hence $-10$ rather than SnapKV's $-16$.
2. **Main — the integer transfers:** bn `pyramidkv@r0.75:w183` is within
   $\pm 3$\,pp of its own baseline (point gate), and recovers ≥ $+8$\,pp
   over the default cell ($p<.05$).
3. **Safe-language control:** both en pyramidkv cells within $\pm 3$\,pp
   of baseline (en is never blind at 64, and the rule must not hurt).
4. Only if the optional block runs — te: default ≤ $-10$\,pp; $\hat
   w{=}247$ within $\pm 3$\,pp.
5. **Kill:** bn at the default > $-5$\,pp → the blindness account is
   SnapKV-specific; the paper's "and its descendants" framing and the
   class-level reading of the title are overclaims and must be narrowed.
   Report it; do not soften it.
6. **Genuine risk short of the kill:** hole reproduces but $\hat w$
   leaves bn ≤ $-10$ → the window is necessary but not sufficient under
   pyramid allocation; contribution (iii) must be qualified as
   per-method, and §6 must say the transfer failed.

Reporting: R2 from raw output, paired McNemar with discordant counts,
`closure_cis.py`-style exact CI wherever a gate statement is made. Never
pool across stacks; cross-store comparison only if the stack hash
matches.

## Paper consequence (decided now)

If preds 1–3 hold: one sentence in §6 — *the integer is a property of
the prompt, not of the method: dropped unchanged into PyramidKV, which
inherits the same shipped window, it removes the same hole* — plus rows
beside the SnapKV cells in Appendix `app:rivals` (which becomes "rival
remedies, and a second member of the family"). If pred 5 fires, the
class claim is withdrawn in §7's honest-nulls paragraph. If pred 6
fires, the transfer failure is reported in the same sentence slot that
success would have used.
