# ICLR follow-up plan — 2026-08-17

**Author: Fable (Claude), after a full independent verification of the
campaign. For: the agent (Grok / Opus) that runs the experiments.**
**Deadline:** ICLR 2027 abstract **18 Sep 2026 AOE**, full paper
**25 Sep 2026 AOE**. Writing is the critical path; everything below fits in
1–2 pod-days total.

---

## 0. Where we stand (verified 2026-08-17)

Every number in `fable-paper-handoff-2026-08-15.md` §4 and in the draft TeX
was independently recomputed from the raw dbs on this machine: **all match**
(arms A/B/D/Q90/8B/Gemma/S, §7 stats, McNemar counts, the 8B residual
audit, and the cap-128-era E1/E2/w32 claims via
`scripts/_verify_opus_audit.py`). Additional robustness computed and
available for the appendix: under a stricter marker-only scorer the story
is unchanged (bn: hole −14, Q90-close −1; te: hole −22, close −3).

Defects found (fix list in §4):

1. The 3,200-pair **V-band appendix table is not regenerable** from any
   committed script; best-effort reconstruction gives a different
   composition. It must be replaced (the v_trace arm) or dropped.
2. Bib: `mohtashami2024finch` has the wrong authors — FINCH (TACL 2024) is
   **Corallo & Papotti**; Mohtashami & Jaggi wrote Landmark Attention.
3. Bib: `nawrot2026findings` venue is suspect ("Findings of ACL 2026",
   anthology id `2026.findings-acl.1926` — same number as Chen's
   `2026.acl-long.1926`; The Sparse Frontier is likely NeurIPS 2025).
   Verify against the primary PDF.
4. Draft TeX (Analysis): "Swahili and Bengali come from TyDiQA" — **Telugu
   is also TyDiQA**; fix the sentence.
5. `iclr-8b-readout.md` errata: ramble among still-wrong is **3/7** (item
   40 ends with a marker at 309 tokens), not 4/7; question-echo among the
   8 residuals is **7/8** (item 48 overlaps 2/6 question tokens), not 8/8.
6. `results/autowin_8b-final.db` is **empty (0 rows)** — a trap because
   every other arm reads `-final`. Delete it; the 8B data is
   `autowin_8b.db`.

## 1. The three GPU arms

Preregisters are **locked**. Run as written; do not edit predictions; do
not retune \(c\), \(Q_{90}\), offsets, or the scorer after seeing accuracy.

| arm | driver block | db | ~gens | preregister | priority |
|---|---|---|---|---|---|
| Schema fix (\(\hat w\) with schema-adjusted c) | `e_iclr2.sh schema_fix` | `schema_fix.db` | 900 | `iclr-schema-fix-preregister.md` | 1 |
| Gemma \(\hat w = c+Q_{90}\) (cross-tokenizer close) | `e_iclr2.sh gemma_q90` | `gemma_q90.db` | 900 | `iclr-gemma-q90-preregister.md` | 2 |
| V-trace (te window ladder; committed analysis) | `e_iclr2.sh v_trace` | `v_trace.db` | 600 | `iclr-v-trace-preregister.md` | 3 |
| V-trace bn (optional, pod-time permitting) | `e_iclr2.sh v_trace_bn` | `v_trace.db` | 600 | same | 4 |

Standing rules (unchanged from the campaign):

- A fresh pod is a **new stack**: every block re-runs its own baseline and
  pairs only inside its own db. Never pool with `d7368e8bd94a`,
  `a2011e0bd133`, `ad3f5a6b57d9`, or `485513693f0a`.
- All windows are measured **on-pod** by `measure_c.py` /
  `measure_c_schema.py` / `measure_q.py`; the dev-box numbers in the
  preregisters are expectations, not inputs.
- Greedy, ctx 8k, cap 384, n=100, R2 scoring offline from raw `output`.
  Never stored `correct`. No LLM judges.
- Gemma \(Q_{90}\) goes to `results/q_percentiles_gemma.json` (new `--out`
  flag) so the locked Qwen `q_percentiles.json` is never overwritten.

## 2. Pod runbook

1. Qwen pod (A6000-class, same template as before —
   `docs/runpod-api-guide.md`, mind §7 UV_NO_SYNC / CUDA pinning):
   `bash scripts/e_iclr2.sh chain_qwen` (= schema_fix then v_trace,
   ~1500 gens). If the pod is still healthy afterwards, optionally
   `bash scripts/e_iclr2.sh v_trace_bn`.
2. Gemma block on a second pod, or on the same pod after the chain:
   `bash scripts/e_iclr2.sh gemma_q90` (~900 gens).
3. Pull `results/{schema_fix,gemma_q90,v_trace}.db` (+ `-snapshot`) the
   same way earlier arms were pulled (`pull_*_when_done.sh` pattern);
   check the `ALL_ICLR2_*_DONE` markers and row counts
   (schema_fix 900, gemma_q90 900, v_trace 600 or 1200).

## 3. After the data — readouts and paper consequences

Write one readout per arm in the house format (numbers locked, author
line, R2, within-db pairing). Decision branches are fixed now:

**Schema fix.**
- Close (pred 3 holds): move S from "construction miss" to "the remedy
  generalizes to schema-induced trailing blocks". Update `app:schema` and
  add one main-text sentence in §"It is not about language". Allowed
  sentence: *the same formula, fed the schema-adjusted c, closes the JSON
  tails it previously broke.* JSON-120 (c_schema≈166 ≈ Telugu's 167) is
  the cleanest parallel — one row in the appendix table.
- Miss (kill fires): keep the construction-miss framing, add an explicit
  limitation: schema tails are not closed by c+Q90. Never write that S
  "does not matter".

**Gemma Q90.**
- Close (pred 3): the cross-tokenizer story completes — *c moves, the hole
  moves, the formula follows c*. Add the \(\hat w\) column/row next to
  `tab:gemma`. If pred 4 also holds, the allowed sentence is: *for
  Gemma-te the formula returns the shipped default (64) — it also knows
  when the default suffices.* Do not write that sentence if pred 4 fails.
- Miss: treat exactly like the 8B soft miss (report; formula partial on
  this tokenizer; identification unaffected).

**V-trace.**
- Readout = `scripts/v_trace_bins.py` output, unedited. Whatever it says
  **replaces** the old V-band table in `app:v` (that table is
  unreproducible and must not ship as-is). If preds 2–4 hold, V gets a
  small dose-response figure/table computed from this db; if the kill
  fires, V stays as notation and `app:v` is deleted, and the abstract's V
  sentence is softened to the definition + Luo-slot claim only.
- The `w=183` / `w=247` cells double as a new-stack replication of the
  D/Q90 cells — quote as a stability check, never pooled.

## 4. No-GPU must-dos (parallel with the runs)

1. Fix `mohtashami2024finch` → Corallo & Papotti, FINCH, TACL 2024.
2. Verify `nawrot2026findings` venue/authors from the primary PDF; fix the
   anthology-id collision with `chen2026instruction`.
3. TeX: "Swahili and Bengali come from TyDiQA" → add Telugu.
4. Apply the two errata to `iclr-8b-readout.md` (3/7 ramble; 7/8 echo) and
   soften the §10 caption seed accordingly.
5. `rm results/autowin_8b-final.db` (empty file, trap).
6. Add the appendix robustness table for 8B-bn (already verified: R2
   81/64/73; fold 81/65/75; recall≥0.7 85/70/79 — ranking unchanged).
7. D1/D2/D3 remain as in `iclr-8b-readout.md` §8; default = Grok's
   (8B one paragraph + appendix row; keep R2; §1 stays a 4B sentence).
8. Cap-128 provenance: E1 (+14/+22), E2 (+10.5) and the w32 flip come from
   the cap-128 era (verified, untruncated controls exist). Add one
   appendix sentence stating the cap difference so a reviewer discovers it
   from us, not from the logs.

## 5. Do not

- Pool any new-stack cell with any old stack, or 4B with 8B, or Qwen with
  Gemma.
- Rerun old arms "to refresh numbers".
- Touch `c`, `Q_{90}`, the offsets, or R2 after seeing any accuracy.
- Add models (14B, Llama) unless all three arms land early AND the writer
  asks — a Llama slice is the only justified extension (generality), and
  it needs its own preregister first.
- Put an LLM judge anywhere near a reported number.

## 6. Timeline

- By ~Aug 24: pods run, dbs pulled, row counts checked.
- By ~Aug 26: three readouts written; `v_trace_bins.py` output archived.
- Aug 27 – Sep 10: paper integration (Fable) — tables/figures updated per
  §3 branches; V appendix replaced; bib finished from primary PDFs.
- Sep 10–18: polish, page budget, anonymization pass, abstract in.
