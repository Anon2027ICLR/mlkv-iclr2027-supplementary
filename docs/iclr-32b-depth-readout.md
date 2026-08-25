# Qwen3-32B Telugu at depth (B5, the closing arm) — readout — 2026-08-26

**Author: Fable (Claude).** R2 from raw output; exact CIs by
`closure_cis.py`'s method; script `scripts/iclr10_readout.py`.
Preregister: `docs/iclr-32b-depth-preregister.md`, locked and pushed
at `c7431a8` (2026-08-25 09:26:06Z, GitHub server timestamp); first
generation 10:27:46Z — every row postdates its registration by at
least 61 minutes. Store: `results/qwen32b_depth.db`, 2,007 rows,
stack `7fe1bcd86629` (own 80GB pod, self-contained). On-pod guards:
c=167 and Q90=80 reproduce on the 32B checkpoint; the Telugu
full-pool disjointness guard held. The B3 n=100 cells reproduce
**byte-identically across the pod boundary, 300/300** — the
cross-stack ledger moves to 2,438, all identical.

## The cells (n=669, te, own baseline; baseline acc 62.9)

| cell | value |
|---|---|
| **w64 (PRIMARY hole)** | **−10.2\* (35/103, CI [−13.1, −6.8], p=5.8×10⁻⁹) — certified** |
| **ŵ=247 (GATE)** | **−1.6 (16/27, CI [−3.5, +0.4]) — gate MET**; the CI misses non-inferiority at −3 by 0.5 |
| **recovery ŵ vs w64** | **+8.5\* (86/29, CI [+5.4, +11.1], p≈10⁻⁷)** |

Item audit (broken n=103, Fisher): middle gold position **46.6% vs
33.3% (p=.003)** — the position fingerprint of the oracle arm,
replicated on an independent model, scale and pod; front/back ns;
|Q| > median ns (p=.83). Marker-only: uninformative exactly as
registered before the data (baseline 1.2%, the placeholder
behaviour).

## Scorecard against the registered readings

| # | Registered reading | Result | |
|---|---|---|---|
| 1 | primary paired Δ + exact CI | −10.2 [−13.1, −6.8] | run as registered |
| 2 | **hole-persists branch** (CI entirely below 0) | **FIRES** | the n=100 −4.0 was sampling noise (35/103 discordance at depth) |
| 3 | attenuation branch | does not fire | — |
| 4 | intermediate | does not fire | — |
| 5 | gate at ŵ, recovery beside it | gate MET (−1.6); recovery +8.5\* | no new miss row |
| 6 | item audit, proportion form | middle p=.003, \|Q\| ns | reported |
| 7 | B3's te numbers superseded; no pooling | applied | — |

**Binding branch: reading 2, and it lands better than either
registered branch promised.** The phenomenon is certified at 32B
(−10.2, against −20.2 at 4B — softened but unambiguous), and the
remedy is *stronger* at scale: where the 4B full pool leaves a
certified −5.7 residual at ŵ, the 32B full pool leaves −1.6 with the
interval containing zero and its lower bound half a point from the
non-inferiority line. The scale story the paper can now tell is not
"effects soften into noise" but: the hole persists, certified, at
every Qwen scale tested, and the computed integer recovers more of it
the larger the model. The B3 Telugu slice is superseded (kept as the
record that n=100 misled, which the depth arm's own history already
demonstrated once at 4B); Bengali-at-32B (certified hole, missed
gate, n=100) remains B3's standing contribution.
