#!/usr/bin/env python3
"""Rewrite PDF date strings to UTC, in place, without moving a single byte.

WHY.  A PDF written by pdfTeX or matplotlib carries the builder's UTC offset:

    /CreationDate (D:20260819085835+HH'MM')

Nothing in a double-blind submission is supposed to say where the author sits,
and this says it on every build, in the artifact reviewers actually open --
including inside the figure dictionaries that pdflatex copies into the paper.
`pdfinfo` hides it by rendering the date in the *reader's* timezone, which is
why it survives: it looks local to whoever checks.

HOW.  Any offset and `+00'00'` are the same seven bytes, so converting the
instant to UTC and writing the zero offset leaves every xref offset in the
file valid. Rebuilding the xref table is the thing that would go wrong, and
this never has to. Idempotent: a date already at `+00'00'` or `Z` is left
alone.

The permanent fix for future builds is to set the environment, which pdfTeX and
matplotlib both honour, and which this script exists to backstop:

    FORCE_SOURCE_DATE=1 SOURCE_DATE_EPOCH=$(date -u +%s) pdflatex ...

    python scripts/utc_pdf_dates.py paper/iclr2027/figs/*.pdf   # in place
    python scripts/utc_pdf_dates.py --check paper/iclr2027/*.pdf
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys

# D:YYYYMMDDHHmmSS+HH'mm'  -- the offset form is the only one that leaks.
PDF_DATE = re.compile(rb"D:(\d{14})([+-])(\d{2})'(\d{2})'")


def to_utc(m):
    stamp, sign, hh, mm = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
    delta = dt.timedelta(hours=hh, minutes=mm)
    if sign == b"+":
        delta = -delta
    t = dt.datetime.strptime(stamp.decode("ascii"), "%Y%m%d%H%M%S") + delta
    out = b"D:" + t.strftime("%Y%m%d%H%M%S").encode("ascii") + b"+00'00'"
    assert len(out) == len(m.group(0)), "byte length must not change"
    return out


def normalize(data: bytes):
    """Return (new_bytes, n_rewritten).  Zero offsets are already fine."""
    hits = [m for m in PDF_DATE.finditer(data)
            if (m.group(2), m.group(3), m.group(4)) != (b"+", b"00", b"00")]
    if not hits:
        return data, 0
    return PDF_DATE.sub(to_utc, data), len(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--check", action="store_true",
                    help="report and exit 1 instead of rewriting")
    a = ap.parse_args()
    bad = 0
    for path in a.pdfs:
        with open(path, "rb") as f:
            data = f.read()
        new, n = normalize(data)
        if not n:
            print(f"  ok    {path}")
            continue
        bad += n
        if a.check:
            offs = sorted({m.group(0).decode() for m in PDF_DATE.finditer(data)})
            print(f"  LEAK  {path}: {n} non-UTC date(s): {', '.join(offs)}")
        else:
            assert len(new) == len(data)
            with open(path, "wb") as f:
                f.write(new)
            print(f"  fixed {path}: {n} date(s) -> +00'00'")
    if a.check and bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
