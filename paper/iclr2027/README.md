# ICLR 2027 submission

Build:

```bash
tectonic -X compile iclr2027_conference.tex     # local, fast
pdflatex iclr2027_conference && bibtex iclr2027_conference && pdflatex ... x2
```

**Font caveat.** `tectonic` runs a Unicode engine, where the style file's
`times` package does not resolve, so a local build falls back to Latin
Modern and runs roughly 0.4 page longer than the submission build. Measured
2026-08-17 after the review fixes: Latin Modern ends the main text low on
page 9, Times (pdflatex, or a `newtxtext` test build) ends it mid-page 9 —
about 8.7 pages against the 9-page limit. Judge the page budget on a Times
build, and note the margin is now thin: anything added to the body needs a
compensating cut.

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
