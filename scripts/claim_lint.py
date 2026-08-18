#!/usr/bin/env python3
"""Surface the sentences in the paper whose truth depends on the rest of it.

`audit_paper_numbers.py` checks values against the stores. It cannot check
claims *about* those values: a count that has to match a list elsewhere, a
superlative that a later arm can overtake, a universal that one new pod can
falsify, or two sentences in different sections that contradict each other.
Every such error this campaign has shipped was of that kind, and each was
caught by accident rather than by a step.

This script does not decide correctness. It prints the sentences that carry
that risk, grouped by why, so the reader re-confirms them against the current
state of the paper. Run it after adding any result, before committing.

  UV_NO_SYNC=1 uv run python scripts/claim_lint.py [--section SUBSTR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "iclr2027" / "iclr2027_conference.tex"

# Each rule is (label, regex, why it is dangerous).
RULES = [
    ("superlative", r"\b(largest|smallest|biggest|deepest|longest|shortest|"
                    r"best|worst|strongest|weakest|highest|lowest|most|least)\b",
     "a later arm can overtake it"),
    ("uniqueness", r"\b(only|sole|solely|unique|first time|for the first time|"
                   r"no other|nothing else)\b",
     "one new cell can falsify it"),
    ("universal", r"\b(every|all|always|never|none|throughout|anywhere|"
                  r"everywhere|in every|at any)\b",
     "holds over a set that grows"),
    ("written count", r"\b(one|two|three|four|five|six|seven|eight|nine|ten|"
                      r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
                      r"seventeen|eighteen|nineteen|twenty)\s+"
                      r"(of the|of our|generation|arm|store|language|cell|"
                      r"model|item|prediction|remed|scorer|famil|token)",
     "must match a list or a set computed elsewhere"),
    ("scope of paper", r"\bin this paper\b|\bthis paper('s)? (subject|thesis|claim)\b|"
                       r"\bwe never\b|\bnowhere\b",
     "a claim about the whole document"),
    ("capability denial", r"\b(cannot|can not|do not claim|does not claim|"
                          r"is not able|impossible)\b",
     "a later result may make it possible, or another section may assert it"),
    ("staleness marker", r"\b(partial|cut short|earlier run|not yet|was not run|"
                         r"an earlier|so far|to date|currently)\b",
     "describes a state the campaign may have moved past"),
]

SKIP_ENV = re.compile(r"\\begin\{(tabular|table|figure|abstract)\}.*?"
                      r"\\end\{\1\}", re.S)


def sentences(text: str):
    """(line number, sentence) pairs, comments and floats removed."""
    lines = text.splitlines()
    out, buf, start = [], [], 1
    for n, raw in enumerate(lines, 1):
        line = re.sub(r"(?<!\\)%.*$", "", raw)
        if not line.strip():
            if buf:
                out.append((start, " ".join(buf)))
                buf = []
            continue
        if not buf:
            start = n
        buf.append(line.strip())
    if buf:
        out.append((start, " ".join(buf)))
    # split paragraphs into sentences, keeping the paragraph's first line number
    result = []
    for n, para in out:
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(\\])", para):
            if s.strip():
                result.append((n, s.strip()))
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", help="only sentences whose text matches this")
    ap.add_argument("--rule", help="only this rule label")
    args = ap.parse_args()

    text = TEX.read_text()
    hits: dict[str, list] = {label: [] for label, _, _ in RULES}
    for n, sent in sentences(text):
        if args.section and args.section.lower() not in sent.lower():
            continue
        for label, pattern, _ in RULES:
            if args.rule and label != args.rule:
                continue
            if re.search(pattern, sent, re.I):
                hits[label].append((n, sent))

    total = 0
    for label, _, why in RULES:
        rows = hits[label]
        if not rows:
            continue
        print(f"\n=== {label} ({len(rows)}) — {why}")
        for n, sent in rows:
            flat = re.sub(r"\s+", " ", sent)
            print(f"  L{n:<5} {flat[:150]}{'...' if len(flat) > 150 else ''}")
        total += len(rows)

    print(f"\n{total} sentences to re-confirm. This script proves nothing; it "
          f"lists what a new result can silently invalidate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
