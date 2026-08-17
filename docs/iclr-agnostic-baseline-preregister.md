# Query-agnostic baseline — preregister

**Author: Fable (Claude).** Written 2026-08-17 (late), *before* any
cap-384 Expected Attention `mlkv run`. Driver: `scripts/e_iclr4.sh
agnostic` (optional `agnostic_tova`). DB: `results/agnostic.db`.

## Why

The second clean-reader review's sharpest experimental ask (W4/Q1): the
paper's practical conclusion — size the window — is never compared with
the obvious alternative, *switch to a scorer that cannot be blinded*.
Expected Attention estimates future-query attention and never reads the
question, so blindness is impossible for it by construction. If it loses
less than blinded SnapKV on Bengali/Telugu at the same ratio, the paper's
advice changes to "switch scorer" and we must say so.

Prior signal, decode-cap-128 era (`pressgen.db`, stack `485513693f0a`,
paired against the same-stack baselines): `expected@r0.75` scored
en $-14$, th $-35$, bn $-18$ vs baseline — worse than blinded SnapKV on
Bengali and catastrophic on Thai. That era's cap truncates high-fertility
outputs, so these are direction, not comparators; this arm is the clean
measurement.

## Arm

Qwen3-4B, mRAG instr-last, ctx 8k, cap 384, n=100, langs **en, bn, te**.
Configs: `baseline`, `expected@r0.75` (ExpectedAttentionPress via
kvpress, same eviction ratio as every headline table). 600 generations,
self-contained (own baseline, own stack). Optional block: `tova@r0.75`
(+300) — a second non-window scorer, same design.

## Predictions (fixed)

1. **Main:** Expected Attention does not rescue Bengali: bn
   `expected@r0.75` vs baseline ≤ $-10$\,pp (cap-128 direction: $-18$).
2. Its damage does not follow $c$: Thai (c=45, safe for SnapKV at 64)
   loses at least as much as Bengali under Expected Attention (cap-128
   direction: th $-35$ vs bn $-18$). The failure mode is different in
   kind, not milder in degree.
3. en: damaged too (cap-128 direction: $-14$) — the scorer that cannot
   be blinded pays everywhere instead.
4. **Changes-the-paper outcome (genuine risk):** bn under Expected
   Attention within 5\,pp of baseline → switching scorer beats sizing
   the window for Bengali, and §6/Limitations must say so. Do not
   wordsmith around it.

Reporting: R2 from raw output, McNemar with discordant counts,
`closure_cis.py`-style CI where a gate-like statement is made. Never
pool with any other stack.

## Paper consequence (decided now)

If preds 1–3 hold: one short paragraph (§6 or Limitations) and a row in
the appendix — *the scorer that cannot be blinded is not a remedy: it
pays a larger, language-independent tax at the same ratio.* If pred 4
fires: the practical-guidance paragraph is rewritten around scorer
choice, and the abstract's remedy sentence is qualified.
