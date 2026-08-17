# ICLR 2027 submission

Build:

```bash
tectonic -X compile iclr2027_conference.tex     # local, fast
pdflatex iclr2027_conference && bibtex iclr2027_conference && pdflatex ... x2
```

**Font caveat.** `tectonic` runs a Unicode engine, where the style file's
`times` package does not resolve, so a local build falls back to Latin
Modern and runs roughly 0.4 page longer than the submission build. Measured
2026-08-17: Latin Modern ends the main text mid-page 9, Times (pdflatex, or
a `newtxtext` test build) ends it at the top of page 9 — about 8.2 pages
against the 9-page limit. Judge the page budget on a Times build.

**Figures** are generated from the result stores, never hand-edited:

```bash
uv run python scripts/iclr_fig_triptych.py      # figs/f2_triptych.pdf
```

**Before submitting**, run the number audit; it recomputes every table cell
in this paper from the generation stores and fails on any drift:

```bash
uv run python scripts/audit_paper_numbers.py    # 227 checks
```
