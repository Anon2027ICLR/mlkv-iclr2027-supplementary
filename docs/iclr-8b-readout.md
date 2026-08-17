# Qwen3-8B scale slice — readout + Fable decisions

**Author: Grok 4.6.** Written 2026-08-15 after a verified pull.  
**For Fable (2026-08-16):** numbers are locked; wording and whether to
put 8B in the main text are yours. Do not rerun GPU. Do not pool with 4B.
Do not quietly retune \(\hat{w}\) or swap the headline scorer.

Preregister (written *before* generate): `docs/iclr-8b-preregister.md`.  
4B Q90 (same formula, different model / items): `docs/iclr-aw-q90-readout.md`.  
Paper handoff: `docs/fable-paper-handoff-2026-08-15.md`.

---

## 1. What ran

| | |
|---|---|
| Model | `Qwen/Qwen3-8B` |
| Task | mRAG, instr-last, ctx 8k, cap 384, n=100 |
| Langs | **en, bn** (te optional in the preregister; not run) |
| Configs | `baseline`, `snapkv@r0.75` (default window 64), `snapkv@r0.75:w<hat>` |
| \(\hat{w}=c+Q_{90}\) | measured on **this** tokenizer: **en 43, bn 183** (same integers as 4B) |
| Rows | **600 / 600**, 0 failed |
| DB | `results/autowin_8b.db` (Mac pull 2026-08-15 04:58 UTC; `PULL_OK`) |
| Stack | `ad3f5a6b57d9` (RTX A6000, bf16, kvpress 0.5.4, transformers 5.2.0) |
| Driver | `scripts/e_aw_8b.sh` (v2; v1 marked done at 0 rows after a disk-quota HF fetch) |

Scorer = R2 `containment_match_lenient` from raw `output`. On this db,
stored `correct` **agrees with R2 on all 600 rows** (unlike older 4B
cells). Still quote R2, not the column, so the paper rule stays one rule.

McNemar two-sided exact on discordant pairs, n=100.

---

## 2. Headline numbers (R2)

| lang | baseline | SnapKV \(w=64\) | \(\hat{w}=c+Q_{90}\) | \(\hat{w}\)−base | \(\hat{w}\)−64 |
|---|---|---|---|---|---|
| en | 96 | 97 | **96** (w=43) | **0** p=1.00 | −1 |
| bn | 81 | 64 (−17) | **73** (w=183) | **−8** p=.008 | **+9** p=.022 |

en paired: base vs 64 is 0/1; base vs \(\hat{w}\) is 0/0. Ceiling, no
information about the hole or the fix.

bn paired:

| | base only | other only | read |
|---|---|---|---|
| base vs 64 | 18 | 1 | 64 hurts |
| base vs \(\hat{w}\) | 8 | 0 | \(\hat{w}\) never beats base |
| 64 vs \(\hat{w}\) | 2 | 11 | \(\hat{w}\) recovers 11 of 18 iso-breaks |

Buckets bn: all-ok 62, all-fail 18, iso-hurt+recover 11, iso-hurt+still 7,
\(\hat{w}\) new-break 1, iso-only-ok 1.

---

## 3. Preregister scorecard

| # | Prediction | Result | |
|---|---|---|---|
| 1 | en \|Δ\|≤3 pp at default 64 and at \(\hat{w}\) | 96 / 97 / 96 | **hold** |
| 2 | bn default 64 damaged (4B was −16; expect ≤ −8) | 81→64 **−17** p≈.000 | **hold** (deeper than 4B) |
| 3 | bn \(\hat{w}\) \|Δ\|≤3 pp vs baseline | 81→73 **−8** p=.008 | **miss** |
| 4 | Slice-kill: bn *flat* at 64 → 4B hole may be scale-specific | hole exists | **does not fire** |
| 5 | Soft miss: hole at 64 but \(\hat{w}\) does not close → do not claim 8B success | this is the outcome | **fires** |

Paper-kill was pred 4, not pred 3. The phenomenon replicates at 8B. The
shipped *formula closes at this scale* does not.

---

## 4. 4B Q90 next to 8B (do not pool)

Same three columns. 4B from `autowin-final.db` + `autowin_q90.db`, same
`item_id`s, stack `d7368e8bd94a`, R2. 8B is a **different** model and
item pack (shared question *order*, different tokenizer-timed prompts —
here the tokenizer family is the same, but do not stack rows).

| | 4B base → 64 → \(\hat{w}\) | 8B base → 64 → \(\hat{w}\) |
|---|---|---|
| en | 93 → 93 → **95 (+2)** | 96 → 97 → **96 (0)** |
| bn | 73 → 57 (−16) → **71 (−2)** | 81 → 64 (−17) → **73 (−8)** |

4B also has te (8B did not run): 56 → 37 (−19) → **56 (0)**.  
4B \(c+16\) (not run at 8B): en 94, bn 66 (−7), te 50 (−6).

**Same shape:** en flat; bn hole at \(w=64\).  
**Different last step:** 4B-bn closes (\(\|\Delta\|\le 3\)); 8B-bn does not.

The 4B sentence in the handoff (*\(c+Q_{90}\) closes en/bn/te*) stays
true **of 4B**. It is not true of 8B-bn.

---

## 5. What the outputs actually do

Question strings from TyDiQA-GoldP validation via `meta.qid`. Question
token lengths with the Qwen3-4B tokenizer (same family; 8B \(\hat{w}\)
integers already matched 4B). Visible-question budget of \(\hat{w}\) on
bn is \(w-c=183-107=76=Q_{90}\).

**The residual is not “\(\hat{w}\) still cannot see the question.”**

- **7/8** residual items (base ✓, \(\hat{w}\) ✗) **echo the question**.
  Item 48 overlaps only 2/6 question tokens, so it is not an echo.
- All 12 items with \(Q>76\) are **correct under \(\hat{w}\)** (12/12).
  Residual Q tokens: 38–67, all ≤ \(Q_{90}\).
- Default-64 iso-hurt items that \(\hat{w}\) **fails** to recover: 3/7
  iso outputs **ramble to the 384 cap**, no `####` (loop “birthplace is
  mentioned as the birthplace…”). Item 40 ends with a marker at 309
  tokens, so it is not a cap-ramble. Default-64 items that \(\hat{w}\)
  **does** recover: 0/11 ramble.
- Gold-passage **position:** 6/7 still-wrong residuals are **middle**.
  Front/back recover more often. SnapKV `r0.75` still evicts most
  pre-window KV — seeing the question does not imply the gold span
  survived.

So \(\hat{w}\) turns off the *blind / format-collapse* mode. The leftover
−8 pp is copy-fidelity of the span plus leftover evidence eviction, not
\(w<c\).

### The 8 residual rows (bn)

| item | Q (gloss) | baseline span | \(\hat{w}\) span | class |
|---|---|---|---|---|
| 13 | novelist born where | …কুমিল্লা **অধীনে** ব্রাহ্মণবাড়ীয়া…গোকর্ণঘাট | same place, **drops অধীনে** | near-copy |
| 16 | who invented Chinese script | সাং **চিয়েন** | সাং **চিয়ে** | truncated name |
| 48 | Ganesha’s brother | কার্তিকে**য়** | কার্তিকে**যণ** | 1-char typo (iso was already correct) |
| 91 | MH370 date | ২০১৪ **খ্রিস্টাব্দের** ৮ই মার্চ | ২০১৪ **খ্রিষ্টাব্দের** ৮ই মার্চ | same date, স্ vs ষ্ |
| 79 | first madrasa | সাফা… **যায়েদ-বিন-আরকামের** বাড়িতে | সাফা… **যায়েদ-বাড়িতে** | abbreviated name |
| 2 | Kolkata metro when | ২৪ অক্টোবর ১৯৮৪ | **১৯৮৪** only | incomplete |
| 7 | Masterda’s father | রাজমনি সেন | **সূর্য সেন** (the man himself) | wrong entity |
| 40 | Anas ibn Malik born? | **মদীনায়** | “unknown; came to মদিনা at 10” | wrong fact + ী/ই |

Rough split: **~5/8 near-copy / orthography**, **~3/8 genuinely wrong**.
R2 still scores all eight 0. That is the locked rule.

Recoveries look the same in reverse: iso writes *Mount View* /
*Gorachandra*; \(\hat{w}\) restores *Mountain View* / *Gorachand* to
match gold. Not “iso answered a different question.”

en: 96/97/96; 3 items fail under all three configs. No residual story.

---

## 6. Is the eval fair?

**Fair for the hole. Slightly harsh for “\(\hat{w}\) closes.”**

R2 is verbatim-substring containment (marker span **or** first prose
sentence). It was locked on 2026-08-12 to stop marker-only from
manufacturing language gaps (`docs/mrag-scoring-issue.md`). Design
commitment: **no LLM judges** (`README.md`, `qa_metrics.py`,
`paper/draft.md`).

Same items, paired, same `r`, same cap, McNemar, R2 fixed before the 8B
run — the *within-language* contrast is a clean experiment. `instr-last`
+ \(w=64\) is a **mechanism stress test**, not a SnapKV production
layout. The handoff already forbids “serving default.”

Where it leans:

- Baseline copies gold more often (bn gold-anywhere 86/100 vs \(\hat{w}\)
  78/100). Compression → paraphrase / typo → containment 0. That
  **inflates** any press-vs-baseline gap. Direction of the iso hole is
  not an artifact (ramble / wrong entity). Magnitude of the 8B close
  miss is a bit overstated.
- Absolute en vs bn accuracy is **not** a fair “bn is worse at RAG”
  comparison (morphology, spelling variants, multi-word golds). The
  paper already refuses that sentence.
- n=100: −8 pp is eight items. The \(\|\Delta\|\le 3\) gate is three
  scoring coin-flips.

Robustness *after* seeing the residual (appendix only — do **not**
replace the headline):

| 8B bn | base | 64 | \(\hat{w}\) | \(\hat{w}\)−base |
|---|---|---|---|---|
| R2 (locked) | 81 | 64 | 73 | **−8** |
| fold ী/ষ্ → ি/স্ | 81 | 65 | 75 | −6 |
| gold-token recall ≥ 0.7 | 85 | 70 | 79 | −6 |

Ranking unchanged. Soft miss remains a soft miss. Iso hole stays ~−15.

---

## 7. LLM-as-judge — Grok recommendation

**Do not put an LLM judge in the headline metric.**

Why, for *this* paper:

1. Headline scorer is a written invariant. Swapping it after pred 3
   misses looks like metric shopping.
2. The thesis is *token-window visibility*. R2 is aligned with “did the
   model surface the gold span.” A semantic judge mixes in a second
   question.
3. `drift.py` already cites QuantiBias: judge choice moves effect sizes.
   A bn judge is worse than an en judge — the exact fake-gap shape R2
   was adopted to avoid.
4. Reproducibility: vendor, date, prompt, same-family circularity if
   the judge is Qwen.
5. The only thing a judge would settle is the ~5 near-copy residuals.
   That is a 20-minute **author audit** (table in §5), already done.

Allowed without breaking the lock:

- Appendix table: fold / token-F1 / rec≥0.7, “ranking unchanged.”
- Author classification of the 8 residuals (near-copy vs wrong).
- QC-style LLM *audit* of those 8 rows as review candidates — never a
  verdict, never a reported accuracy. Same posture as
  `src/mlkv/qc_llm_audit.py` on MGSM-VI.

Not allowed without an explicit Fable override written into the paper’s
limitations: replace R2; report a judge accuracy as the 8B result; claim
8B “closes” under a post-hoc judge.

Gold spans exist (XQuAD / TyDi). That is the setting deterministic span
metrics were built for.

---

## 8. What Fable decides tomorrow

Three independent choices. Default = Grok’s recommendation if you do
not want to reopen science.

### D1 — How to write 8B (main vs appendix)

| Option | Meaning | Grok |
|---|---|---|
| **A** | One paragraph + one row in the scale/appendix table. Hole replicates; \(\hat{w}\) recovers part; residual −8 pp. 4B remains the close. | **default** |
| B | Promote 8B into the main “does the formula ship?” sentence. Then you must *weaken* the ship claim (closes at 4B; partial at 8B). Costs main-text space. | only if you want honesty-in-the-lead over a clean 4B ship |
| C | Omit 8B from the PDF. Honest but wasteful: pred 4 (not a 4B artifact) is the reason the slice was run. | no |

**Never write:** “8B success”; “\(c+Q_{90}\) closes at 8B”; pooled 4B+8B
%; “8B-en confirms the fix” (ceiling); “residual = Q90 underdose”
(contradicted by \(Q>76\) = 12/12 correct).

### D2 — Headline scorer

| Option | Grok |
|---|---|
| **Keep R2 everywhere** | **default** |
| R2 headline + appendix robustness (fold / rec≥0.7 / author residual table) | recommended companion to A |
| LLM judge as a reported accuracy | **no** |
| Change R2 after the fact to make 8B-bn \(\|\Delta\|\le 3\) | **no** |

### D3 — Does 8B change the one-sentence paper?

Handoff §1 currently: *\(w=c+Q_{90}\) closes en/bn/te*. That sentence is
**4B**. Options:

| Option | Grok |
|---|---|
| **Keep §1 as 4B.** 8B is a scale check with a soft miss, one sentence. | **default** |
| Qualify §1: *closes en/bn/te at 4B; at 8B the hole replicates and \(\hat{w}\) is a partial recover.* | if D1=B |
| Retreat the ship to “better than default 64, not a close.” | too weak — 4B did close; \(c+16\) is already the underdose ablation |

The identification story (English pad, layout-first, Gemma \(c\) move)
does not depend on 8B closing. 8B’s load-bearing gift is **pred 4 did
not fire**.

---

## 9. Do not do

- Pool 4B and 8B rows or stack ids.
- Run 14B / te-8B / Llama just to hunt a close.
- Bump storage or restore Llama weights.
- Rewrite F2–F4 around 8B.
- Touch `c` or \(Q_{90}\) after seeing 8B accuracy.
- Quote stored `correct` as a different rule (here it matches; still don’t).

---

## 10. Suggested sentences (if D1=A, D2=R2)

Main (one breath):

> A Qwen3-8B slice (en/bn, same formula, n=100) reproduces the Bengali
> default-window hole (−17 pp) and recovers part of it at
> \(w=c+Q_{90}\) (+9 pp vs \(w=64\); −8 pp vs baseline). We do not claim
> the formula closes at 8B.

Appendix caption seed:

> Residual 8B-bn errors are not unseen questions: seven of eight echo
> the question (item 48 does not), and all twelve items with
> \(Q>Q_{90}\) are correct under \(\hat{w}\). Several residuals are
> near-copy / orthography under verbatim containment (R2). Three of
> the seven default-\(w=64\) failures that \(\hat{w}\) does not recover
> are generation collapse (cap 384, no marker); item 40 is not.
