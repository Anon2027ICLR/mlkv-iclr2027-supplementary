"""Span EM/F1 scoring for mRAG-QA (SQuAD/MLQA-style, multilingual-aware).

Deliberately separate from metrics.py (numeric MGSM scoring): span scoring has
its own normalization pitfalls. Language-aware choices, mirroring the MLQA
official evaluation:
- Article stripping ONLY for languages with articles in our matrix (en/es/de);
  stripping "the"-lookalikes in other languages would corrupt answers.
- Token-level F1 uses whitespace tokens, EXCEPT for languages written without
  word separators (zh/ja/th) which use character-level tokens.
- NFKC normalization unifies full-width digits/punctuation (common in zh/ja).

No LLM judges — deterministic by construction (design commitment).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

MARKER_RE = re.compile(r"####")

# Languages in our matrix written without whitespace word boundaries.
CHAR_TOKEN_LANGS = {"zh", "ja", "th"}

# Article sets per language (only languages that have articles); lowercase.
ARTICLES: dict[str, set[str]] = {
    "en": {"a", "an", "the"},
    "es": {"el", "la", "los", "las", "un", "una", "unos", "unas"},
    "de": {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
           "einem", "einer", "eines"},
}


# Models echo the instruction's placeholder verbatim ("#### <exact answer
# span>308####"). Angle-bracketed segments are placeholder debris — gold spans
# in XQuAD/MLQA/TyDiQA never contain '<...>'.
_PLACEHOLDER_RE = re.compile(r"<[^>]*>")


def extract_span(text: str) -> str:
    """Predicted answer region: after the last '####' marker that still has
    content (models emit trailing/multiple markers), else full text.
    Placeholder echoes in angle brackets are stripped before scoring."""
    positions = [m.end() for m in MARKER_RE.finditer(text)]
    candidates = [text[p:] for p in reversed(positions)] + [text]
    for region in candidates:
        region = _PLACEHOLDER_RE.sub(" ", region)
        region = re.sub(r"[#\s]+$", "", region).strip()
        if re.search(r"\w", region):  # needs actual content, not marker debris
            return region
    return ""


def normalize(text: str, lang: str) -> str:
    """Lowercase, strip punctuation/symbols, drop articles, collapse spaces."""
    text = unicodedata.normalize("NFKC", text).lower()
    chars = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("P") or cat.startswith("S"):
            chars.append(" ")  # punctuation acts as a token boundary
        else:
            chars.append(ch)
    words = "".join(chars).split()
    articles = ARTICLES.get(lang, set())
    words = [w for w in words if w not in articles]
    return " ".join(words)


def tokenize(text: str, lang: str) -> list[str]:
    normalized = normalize(text, lang)
    if lang in CHAR_TOKEN_LANGS:
        return [ch for ch in normalized if not ch.isspace()]
    return normalized.split()


def _f1_single(pred_tokens: list[str], gold_tokens: list[str]) -> float:
    if not pred_tokens or not gold_tokens:
        return float(pred_tokens == gold_tokens)
    common = Counter(pred_tokens) & Counter(gold_tokens)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def exact_match(pred: str, golds: list[str], lang: str) -> bool:
    pred_norm = normalize(pred, lang)
    return any(pred_norm == normalize(g, lang) for g in golds)


def f1(pred: str, golds: list[str], lang: str) -> float:
    pred_tokens = tokenize(pred, lang)
    return max(_f1_single(pred_tokens, tokenize(g, lang)) for g in golds)


def span_scores(output: str, golds: list[str], lang: str) -> dict:
    """Score a raw model output against gold answer spans."""
    span = extract_span(output)
    return {
        "em": exact_match(span, golds, lang),
        "f1": f1(span, golds, lang),
    }
