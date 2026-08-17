# ICLR 2027 submission

Build:

```bash
tectonic -X compile iclr2027_conference.tex     # local, fast
pdflatex iclr2027_conference && bibtex iclr2027_conference && pdflatex ... x2
```

**Font caveat — judge the page budget on a Times build.** `tectonic` runs a
Unicode engine where the style file's `times` package does not resolve, so a
local build falls back to Latin Modern, which is wider. Measured 2026-08-17:
in a Times build (pdflatex, or the `newtxtext` substitution used for testing)
the main text ends about 72% of the way down page 9 — roughly 8.7 pages
against the 9-page limit, with a usable margin. The same source in Latin
Modern spills the conclusion onto page 10. Do not cut content to satisfy the
Latin Modern build.

To measure: copy the .tex, swap
`\usepackage{iclr2027_conference,times}` for
`\usepackage{iclr2027_conference}` plus `\usepackage{newtxtext,newtxmath}`,
and compile that copy.

**Bold does not render under `tectonic`.** The same missing Times shape
that costs the font fallback also silently drops `\textbf`, so emphasis in
tables and figure captions looks absent locally and appears correctly in a
Times build. Judge emphasis, like page count, on a Times build.

**Figures** are generated from the result stores, never hand-edited:

```bash
uv run --with matplotlib python scripts/paper_figures.py   # both figures
```

The palette and the encoding choices are documented in that script's header
(emphasis colours for the two languages that break, an ordinal ramp for the
ordered pad conditions, a distinct marker per series so identity survives
greyscale). The accent pair was checked with a colour-vision validator, not
by eye.

**Before submitting**, run the number audit; it recomputes every table cell
in this paper from the generation stores and fails on any drift:

```bash
uv run python scripts/audit_paper_numbers.py    # 227 checks
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
