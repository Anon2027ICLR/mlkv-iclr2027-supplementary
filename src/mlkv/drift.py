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


def _predict_label(model, text: str) -> str:
    """Predict one language label. fasttext's Python wrapper breaks under
    NumPy 2 (np.array(..., copy=False)); call the underlying binding directly
    and fall back to the wrapper for other fasttext builds."""
    try:
        pred = model.f.predict(text, 1, 0.0, "strict")  # [(prob, label), ...]
        return pred[0][1] if pred else ""
    except AttributeError:
        return model.predict(text)[0][0]


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
        segments = [s.strip() for s in text.splitlines() if len(s.strip()) >= 8]
        if not segments:
            segments = [text]
        drifted = total = 0
        for seg in segments:
            weight = sum(1 for ch in seg if ch.isalpha())
            if weight == 0:
                continue
            label = _predict_label(model, seg.replace("\n", " "))
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
