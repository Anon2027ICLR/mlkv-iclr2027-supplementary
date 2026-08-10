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
# span>308####") — and sometimes wrap their REAL answer in the same angle
# brackets ("#### <308>", mimicking the template). So: delete only the known
# placeholder phrases (they are constants from our own qa_instructions), and
# otherwise keep bracket CONTENT while dropping the brackets themselves.
_PLACEHOLDER_PHRASES = [
    "exact answer span", "fragmento exacto de la respuesta",
    "extrait exact de la réponse", "exakte Antwortpassage",
    "точный фрагмент ответа", "原文中的答案片段", "本文中の正確な答え",
    "ข้อความคำตอบตรงตามต้นฉบับ", "kifungu halisi cha jibu", "সঠিক উত্তরাংশ",
    "ఖచ్చితమైన సమాధాన భాగం", "cụm từ trả lời chính xác",
]
_PLACEHOLDER_RE = re.compile(  # matches "<phrase>" and "</phrase>" echoes
    "<\\s*/?\\s*(?:" + "|".join(re.escape(p) for p in _PLACEHOLDER_PHRASES) + ")\\s*>"
)
_BRACKET_RE = re.compile(r"[<>]")


def extract_span(text: str) -> str:
    """Predicted answer region: after the last '####' marker that still has
    content (models emit trailing/multiple markers), else full text.
    Known placeholder echoes are deleted; other angle brackets are dropped
    but their content survives ("<308>" -> "308")."""
    positions = [m.end() for m in MARKER_RE.finditer(text)]
    candidates = [text[p:] for p in reversed(positions)] + [text]
    for region in candidates:
        region = _PLACEHOLDER_RE.sub(" ", region)
        region = _BRACKET_RE.sub(" ", region)
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
    """Strict span equality after normalization."""
    pred_norm = normalize(pred, lang)
    return any(pred_norm == normalize(g, lang) for g in golds)


def containment_match(pred: str, golds: list[str], lang: str) -> bool:
    """Normalized substring containment (Benchmark Illusion, 2606.17609):
    correct if the gold span appears verbatim inside the prediction after
    normalization. Robust to sentence-wrapped answers ("The defense gave up
    308 points"), whose rate of occurrence differs BY LANGUAGE — strict EM
    would convert that format-compliance difference into fake per-language
    damage. Token-boundary guard for whitespace languages so gold "24" does
    not match inside "245"."""
    pred_norm = normalize(pred, lang)
    if not pred_norm:
        return False
    for g in golds:
        g_norm = normalize(g, lang)
        if not g_norm:
            continue
        if lang in CHAR_TOKEN_LANGS:
            if g_norm.replace(" ", "") in pred_norm.replace(" ", ""):
                return True
        elif re.search(rf"(?<![^\W_]){re.escape(g_norm)}(?![^\W_])", pred_norm):
            return True
    return False


def f1(pred: str, golds: list[str], lang: str) -> float:
    pred_tokens = tokenize(pred, lang)
    return max(_f1_single(pred_tokens, tokenize(g, lang)) for g in golds)


def span_scores(output: str, golds: list[str], lang: str) -> dict:
    """Score a raw model output against gold answer spans.

    `correct` (headline) = containment match — strict EM measures format
    compliance, which varies by language and would manufacture fake gaps.
    Strict EM and F1 are reported alongside."""
    span = extract_span(output)
    return {
        "em": containment_match(span, golds, lang),
        "em_strict": exact_match(span, golds, lang),
        "f1": f1(span, golds, lang),
    }
