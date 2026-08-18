#!/usr/bin/env python3
"""Count main-text lines spilling past the ICLR page limit.

Measures the lines between the top of the page carrying the Ethics
Statement heading and the heading itself -- i.e. main text that overflowed
page 9. Run it on the OFFICIAL build only (pdflatex + times):

  pdflatex iclr2027_conference && bibtex iclr2027_conference \
    && pdflatex ... x2
  uv run python scripts/page_budget.py paper/iclr2027/iclr2027_conference.pdf

Never trust a tectonic or newtxtext build for this number: Latin Modern
overstates by ~a page, and the newtxtext substitution understates by
about eleven lines against real Times + Helvetica + Courier (measured
2026-08-19, the day it nearly shipped a violation).
"""
import re,subprocess,sys
pdf=sys.argv[1] if len(sys.argv)>1 else "times_build.pdf"
txt=subprocess.run(["pdftotext","-layout",pdf,"-"],capture_output=True,text=True).stdout
pages=txt.split("\f")
tgt=None
for i,p in enumerate(pages):
    if re.search(r"E\s*THICS\s+STATEMENT",p,re.I): tgt=i; break
if tgt is None:
    print("ETHICS heading not found"); sys.exit(1)
p=pages[tgt].strip().splitlines()
n=0
for l in p[1:]:
    if re.search(r"E\s*THICS\s+STATEMENT",l,re.I): break
    t=re.sub(r"^\s*\d+\s*","",l).strip()
    if t: n+=1
print(f"main text spilling onto page {tgt+1}: {n} lines   (total pages {len(pages)})")
