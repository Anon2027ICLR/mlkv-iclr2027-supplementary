# Qwen3-8B scale slice — preregister

**Author: Grok 4.6.** Written *before* any 8B `mlkv run`. 2026-08-15.

\(\hat w = c + Q_{90}\) measured on the 8B tokenizer (same family as 4B).
en + bn × {baseline, `snapkv@r0.75`, `snapkv@r0.75:w<hat>`}, n=100, cap 384.

1. en |Δ|≤3 pp vs baseline at default 64 and at \(\hat w\).
2. bn default 64 damaged (direction of 4B −16 pp; expect ≤ −8).
3. bn \(\hat w\) |Δ|≤3 pp vs baseline.
4. Slice-kill (not paper-kill): bn flat at 64 → 4B hole may be scale-specific.
5. Soft miss: hole at 64 but \(\hat w\) does not close → do not claim 8B success.

R2 only. Do not pool with 4B.
