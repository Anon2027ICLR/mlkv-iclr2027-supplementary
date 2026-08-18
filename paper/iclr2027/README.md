# ICLR 2027 submission

Build — **the official artifact is the pdflatex build**:

```bash
export PATH=/Library/TeX/texbin:$PATH    # BasicTeX + tlmgr install helvetic courier
pdflatex iclr2027_conference && bibtex iclr2027_conference \
  && pdflatex iclr2027_conference && pdflatex iclr2027_conference
uv run python scripts/page_budget.py paper/iclr2027/iclr2027_conference.pdf  # must print 0
```

**Font history, learned the expensive way.** Three different builds give
three different page counts, and only one of them is the submission:

| build | fonts | verdict |
|---|---|---|
| `tectonic` | Latin Modern (\`times\` fails silently) | ~1 page long; **never judge anything on it** |
| `newtxtext` substitution | Times clone, CM tt, no Helvetica | flattered us by ~11 lines; retired 2026-08-19 |
| `pdflatex` + `times` (+ helvetic, courier) | NimbusRoman / Helvetica / Courier | **the artifact**; page limit judged here only |

ICLR 2027 desk-rejects main text beyond 9 pages. The Ethics,
Reproducibility and AI-use statements do not count toward the limit and
stay where the template puts them (after the conclusion, before
references) — do not move them to the appendix.

**Figures** are generated from the result stores, never hand-edited:

```bash
uv run --with matplotlib python scripts/paper_figures.py   # both figures
```

The palette and the encoding choices are documented in that script's header
(emphasis colours for the two languages that break, an ordinal ramp for the
ordered pad conditions, a distinct marker per series so identity survives
greyscale). The accent pair was checked with a colour-vision validator, not
by eye.

**After adding any result**, run the claim linter *before* the number audit:

```bash
uv run python scripts/claim_lint.py            # all rules
uv run python scripts/claim_lint.py --rule superlative
```

It prints the sentences whose truth depends on the rest of the paper --
superlatives a later arm can overtake, counts that must match a list
elsewhere, universals one new pod can falsify, staleness markers describing
a state the campaign has moved past. It proves nothing and flags no errors;
it is the re-confirmation list. Every claim-level error this campaign has
shipped ("four of eight blind at w=32" against its own constants table,
"nine generation stores" beside a list of eleven, "largest recovery in this
paper" after a larger one landed, "inflates apparent damage" against an
appendix that declines to claim it) is in a category this catches, and each
was previously found by accident.

**Before submitting**, run the number audit; it recomputes every table cell
in this paper from the generation stores and fails on any drift:

```bash
uv run python scripts/audit_paper_numbers.py    # 434 checks
```

**Preregistration timestamps.** Reviewers asked whether the registrations
are verifiable. They are files in this history, and the table below is the
honest accounting the reproducibility statement refers to: each file was
written before its run, but three entered version control in a later batch,
so their commit time does not precede the run.

| preregister | commit | committed (UTC) | first generation (UTC) | commit precedes run |
|---|---|---|---|---|
| `iclr-autowin-q90-preregister.md` | `f3f635f` | 2026-08-17 07:28 | 2026-08-14 14:24 | no (later batch) |
| `iclr-8b-preregister.md` | `f3f635f` | 2026-08-17 07:28 | 2026-08-15 04:14 | no (later batch) |
| `iclr-schema-fix-preregister.md` | `78c0251` | 2026-08-17 01:29 | 2026-08-17 01:20 | no (later batch) |
| `iclr-gemma-q90-preregister.md` | `78c0251` | 2026-08-17 01:29 | 2026-08-17 05:28 | yes |
| `iclr-v-trace-preregister.md` | `78c0251` | 2026-08-17 01:29 | 2026-08-17 03:13 | yes |
| `iclr-llama-preregister.md` | `d2550b0` | 2026-08-17 09:00 | 2026-08-17 09:50 | yes |
| `iclr-instr-first-preregister.md` | `d2550b0` | 2026-08-17 09:00 | 2026-08-17 10:57 | yes |
| `iclr-agnostic-baseline-preregister.md` | `78c18c5` | 2026-08-17 14:07 | 2026-08-17 15:47 | yes |
| `iclr-ratio-sweep-preregister.md` | `78c18c5` | 2026-08-17 14:07 | 2026-08-17 16:49 | yes |
| `iclr-pyramidkv-preregister.md` | `74840de` | 2026-08-18 01:15 | 2026-08-18 01:27 | yes |
| `iclr-template-survey-preregister.md` | `813bcad` | 2026-08-18 | (no generations; locked before tokenizing) | yes |
| `iclr-constant-and-ranking-preregister.md` | `e287172` | 2026-08-18 13:01 | 2026-08-18 13:54 | yes |

The completed Bengali ladder (`v_trace_bn`, first generation 2026-08-17 14:36)
runs against `iclr-v-trace-preregister.md`, already in the table above, and so
does not add a row.

**Determinism.** The count the provenance appendix quotes is produced by a
script, not by hand:

```bash
uv run python scripts/determinism_ledger.py     # 3,243 same-stack, 300 cross
uv run python scripts/decode_cap_ledger.py      # the appendix on the decode cap
uv run python scripts/template_survey_measure.py  # the layout-in-the-wild appendix
uv run python scripts/measure_c.py --models Qwen/Qwen3-4B --no-marker
```

The determinism ledger separates repeats within one stack descriptor (the
figure the paper quotes) from repeats across descriptors, which the PyramidKV
pod produced by accident and which are reported apart. `decode_cap_ledger.py`
owns Appendix on the decode cap and fails on any drift in the values it
prints; `audit_paper_numbers.py` pins the same cells independently.
