"""Language-drift detection: does a response slide out of the prompt language?

Primary detector: GlotLID (fastText model, optional dependency) applied to
line-level segments, char-weighted. Fallback: Unicode-script analysis, which
can only separate languages of *different* scripts (plus Vietnamese among
Latin-script languages, via its unique diacritics). The fallback returns None
when it cannot decide, rather than guessing.

Deterministic by construction — no LLM judges (QuantiBias: judge choice moves
measured effect sizes).
"""

from __future__ import annotations

import functools
import logging
import re
import unicodedata

from mlkv.languages import LANGUAGES, VIETNAMESE_MARKS, Language

logger = logging.getLogger(__name__)

_SCRIPT_PREFIXES = [
    ("LATIN", "Latin"),
    ("CYRILLIC", "Cyrillic"),
    ("CJK", "Han"),
    ("HIRAGANA", "Han"),   # counted with Han for ja
    ("KATAKANA", "Han"),
    ("THAI", "Thai"),
    ("BENGALI", "Bengali"),
    ("TELUGU", "Telugu"),
    ("HANGUL", "Hangul"),
    ("ARABIC", "Arabic"),
    ("DEVANAGARI", "Devanagari"),
]


def _char_script(ch: str) -> str | None:
    """Script of a letter char; None for digits/punct/space/symbols."""
    if not ch.isalpha():
        return None
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    for prefix, script in _SCRIPT_PREFIXES:
        if name.startswith(prefix):
            return script
    return "Other"


def script_profile(text: str) -> dict[str, int]:
    """Letter counts per script."""
    profile: dict[str, int] = {}
    for ch in text:
        script = _char_script(ch)
        if script:
            profile[script] = profile.get(script, 0) + 1
    return profile


@functools.lru_cache(maxsize=1)
def _glotlid_model():
    try:
        import fasttext
        from huggingface_hub import hf_hub_download

        path = hf_hub_download("cis-lmu/glotlid", "model.bin")
        return fasttext.load_model(path)
    except Exception as exc:  # missing dep or offline
        logger.warning("GlotLID unavailable (%s); using script-only fallback", exc)
        return None


# Markup and math that confuse line-level LID: LaTeX commands, markdown
# emphasis/heading/code chars, operators, digits. Reasoning models emit a lot
# of this; classifying it as-is manufactures fake drift (observed: 0.44 "drift"
# on perfectly English Qwen3 CoT full of \text{...} lines).
_MARKUP_RE = re.compile(r"\\[a-zA-Z]+|[\\${}^_*#`|~=+\-×÷/<>()\[\]]|\d")


def _lid_text(segment: str) -> str:
    """Strip markup/math before language ID; keeps letters and spacing."""
    return " ".join(_MARKUP_RE.sub(" ", segment).split())


# Line-level LID thresholds, tuned on the 2026-08-09 Mac mini-pilot outputs
# (150 generations, sweep in docs/pilot-results.md): GlotLID is unreliable on
# short header/label fragments ("Final Answer:", "Total bolts" → random Latin
# languages). Requiring >=30 alphabetic chars and >=0.7 confidence drops
# English false drift from 0.171 to 0.025 while VI (incl. the NFD arm) goes
# to 0.000. Cost: genuinely code-switched SHORT fragments are not counted —
# acceptable, P3b claims are about sustained language sliding.
MIN_SEGMENT_ALPHA = 30
MIN_LID_CONFIDENCE = 0.7


def _predict(model, text: str) -> tuple[str, float]:
    """Predict (label, confidence). fasttext's Python wrapper breaks under
    NumPy 2 (np.array(..., copy=False)); call the underlying binding directly
    and fall back to the wrapper for other fasttext builds."""
    try:
        pred = model.f.predict(text, 1, 0.0, "strict")  # [(prob, label), ...]
        return (pred[0][1], pred[0][0]) if pred else ("", 0.0)
    except AttributeError:
        labels, probs = model.predict(text)
        return (labels[0], float(probs[0])) if labels else ("", 0.0)


def drift_score(text: str, expected: Language) -> float | None:
    """Fraction of letter mass written in a language other than `expected`.

    Returns None when undecidable (script fallback + same-script languages).
    """
    # Canonicalize to NFC: the NFD experiment arm (and models echoing NFD
    # input) would otherwise break the Vietnamese-diacritic fallback, which
    # tests for precomposed characters.
    text = unicodedata.normalize("NFC", text).strip()
    if not text:
        return None

    model = _glotlid_model()
    if model is not None:
        segments = [s.strip() for s in text.splitlines() if s.strip()]
        if not segments:
            segments = [text]
        drifted = total = 0
        for seg in segments:
            cleaned = _lid_text(seg)
            weight = sum(1 for ch in cleaned if ch.isalpha())
            if weight < MIN_SEGMENT_ALPHA:
                continue  # headers/math fragments — LID unreliable
            label, confidence = _predict(model, cleaned.replace("\n", " "))
            if confidence < MIN_LID_CONFIDENCE:
                continue
            label = label.removeprefix("__label__")
            total += weight
            if label != expected.glotlid:
                drifted += weight
        return drifted / total if total else None

    # Script-only fallback.
    profile = script_profile(text)
    total = sum(profile.values())
    if total == 0:
        return None
    in_script = profile.get(expected.script, 0)
    if expected.script != "Latin":
        return 1.0 - in_script / total
    # Latin-script languages: only Vietnamese is separable (unique diacritics).
    if expected.code == "vi":
        vi_marks = sum(1 for ch in text if ch in VIETNAMESE_MARKS)
        non_latin = total - in_script
        # Heuristic: real Vietnamese prose has diacritics on a sizable share
        # of letters; a response with almost none has likely drifted to English.
        if vi_marks / max(in_script, 1) < 0.02:
            return min(1.0, (non_latin + in_script) / total)
        return non_latin / total
    return None  # EN/ES/FR/DE/SW mutually inseparable without GlotLID


def expected_language(code: str) -> Language:
    return LANGUAGES[code]
