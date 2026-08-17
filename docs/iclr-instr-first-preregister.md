# Instruction-first at cap 384 — preregister

**Author: Fable (Claude).** Written 2026-08-17, *before* any cap-384
instruction-first `mlkv run`. Driver: `scripts/e_iclr3.sh instr_first`
(optional `instr_first_th`). DB: `results/instr_first.db`.

## Why

Both reviews ask for a head-to-head between AutoWindow and the obvious
layout remedy at the same retained budget. The instruction-first numbers
the paper has (+14/+22 pp on Bengali) are from the decode-cap-128 era on
an earlier stack — deliberately quarantined in Appendix K with a
provenance flag, because mixing them into a cap-384 table would be exactly
the era-mixing this paper otherwise avoids. This arm produces the clean
version: same task, same items, same ratio, cap 384, own baselines.

It is also the sharpest remaining test of the mechanism itself. Under
\texttt{instruction + passages + question} the question ends the prompt,
so \(V{=}1\) at every window by construction. If the paper's account is
right, the same press and ratio that cost Bengali 16 and Telugu 19 points
under instruction-last should cost approximately nothing here.

## Arm

Qwen3-4B, mRAG **`--mrag-layout instr-first`**, ctx 8k, cap 384, n=100.
Langs **en, bn, te** primary (one invocation); **th** optional block —
the cap-128 era suggested a real layout tax for Thai (−6.5 pp), worth a
clean measurement. Configs: `baseline`, `snapkv@r0.75` (default 64) —
\(\hat w\) is pointless here since \(V{=}1\) already. 600 (+200)
generations. Item ids take the `mragIF-` prefix; they never collide with
instr-last rows.

Pairing: primary comparisons are within this db (instr-first compressed
vs instr-first baseline). If the pod reproduces the campaign environment
(recent pods have, token-identically), cross-layout comparisons on
matched `qid` against `autowin-final.db` are within-stack and may be
reported as secondary; if the stack hash differs, skip them.

## Predictions (fixed)

1. **Main (mechanism):** bn and te at the default window under
   instruction-first are \(|\Delta| \le 3\) pp vs the instruction-first
   baseline. CI reported per the `closure_cis.py` discipline.
2. en at the default window: flat (\(|\Delta| \le 3\)).
3. Layout main effect on uncompressed baselines (instr-first vs
   instr-last accuracy): small; the cap-128 era showed bn −3 (ns). Not a
   gate — report only. Cross-layout, so only if the stack matches.
4. th (optional block): exploratory. The cap-128 signal was a −6.5 pp
   layout cost; direction is preregistered as *uncertain* and whatever
   appears is reported.
5. **Kill (kills the mechanism claim, not just an arm):** bn or te at
   the default window \(\le -8\) pp vs the instruction-first baseline.
   A window that sees the whole question and still produces the hole
   means the damage is not (only) visibility. If this fires: stop, do
   not wordsmith around it, and escalate to the author — the paper's
   §4–§6 account would need genuine revision.

## Paper consequence (decided now)

If prediction 1 holds, §6 gains the two-remedies table: per language, at
the same retained KV — default window instr-last (blind), \(\hat w\)
instr-last (the measurement remedy), default window instr-first (the
layout remedy) — each against its own baseline. Appendix K's cap-128
numbers are then demoted to a historical note. If prediction 5 fires, no
table: revise instead.

Scoring: R2 from raw `output`. Paired McNemar with discordant counts.
Never stored `correct`.
