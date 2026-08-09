"""Answer extraction and scoring.

The extraction must be number-format aware: Vietnamese/Spanish/German write
1.234 for one thousand two hundred thirty-four and 12,5 for twelve and a half,
while English writes 1,234 and 12.5. A naive English-biased extractor would
manufacture spurious per-language "damage" — so ambiguous strings yield ALL
consistent interpretations and a prediction counts as correct if ANY matches
the gold answer. GSM8K gold answers are integers, which keeps this safe.
"""

from __future__ import annotations

import re

MARKER_RE = re.compile(r"####")
# A number: digits possibly with , or . group/decimal separators inside.
NUMBER_RE = re.compile(r"-?\d[\d.,]*")


def _interpretations(token: str) -> set[float]:
    """All plausible numeric readings of a raw number token."""
    token = token.strip().rstrip(".,")  # trailing sentence punctuation
    if not token or not re.search(r"\d", token):
        return set()
    out: set[float] = set()
    has_dot, has_comma = "." in token, "," in token

    def _try(s: str) -> None:
        try:
            out.add(float(s))
        except ValueError:
            pass

    if has_dot and has_comma:
        # Rightmost separator is the decimal one; the other is grouping.
        if token.rfind(".") > token.rfind(","):
            _try(token.replace(",", ""))                     # 1,234.5
        else:
            _try(token.replace(".", "").replace(",", "."))   # 1.234,5
    elif has_dot or has_comma:
        sep = "." if has_dot else ","
        parts = token.lstrip("-").split(sep)
        # Grouping reading: every group after the first has exactly 3 digits.
        if all(len(p) == 3 for p in parts[1:]) and parts[0] and len(parts[0]) <= 3:
            _try(token.replace(sep, ""))
        # Decimal reading: only valid with a single separator.
        if len(parts) == 2:
            _try(token.replace(",", "."))
    else:
        _try(token)
    return out


def extract_candidates(text: str) -> set[float]:
    """Numeric interpretations of the model's final answer.

    Prefer the region after the last '####' marker; fall back to the full text.
    Within the region, the last number token is the answer.
    """
    marker_positions = [m.end() for m in MARKER_RE.finditer(text)]
    zones = [text[marker_positions[-1]:]] if marker_positions else []
    zones.append(text)
    for zone in zones:
        tokens = NUMBER_RE.findall(zone)
        if tokens:
            return _interpretations(tokens[-1])
    return set()


def parse_gold(gold: str | int | float) -> float:
    """GSM8K-style gold answers: integers, possibly with ',' grouping."""
    if isinstance(gold, (int, float)):
        return float(gold)
    return float(str(gold).strip().replace(",", ""))


def is_correct(response: str, gold: str | int | float, tol: float = 1e-6) -> bool:
    gold_value = parse_gold(gold)
    return any(abs(c - gold_value) <= tol for c in extract_candidates(response))


def output_stats(response: str, n_tokens: int) -> dict:
    """Length accounting in tokens AND bytes (fertility-corrected axis)."""
    return {
        "n_output_tokens": n_tokens,
        "output_bytes": len(response.encode("utf-8")),
        "output_chars": len(response),
    }
