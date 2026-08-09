"""Contamination canary: GSM-Plus-style numeric perturbation of MGSM items.

Design doc §2.2: perturb a number in the question, recompute the answer
symbolically from the GSM8K solution annotations (`<<expr=result>>`) with
sympy, and auto-verify. Contamination inflates memorized baselines but cannot
follow a perturbed number, so a baseline gap between original and canary items
flags contamination. This is a robustness check, not load-bearing.

Auto-verification, per item:
1. Structure check: evaluating the ORIGINAL annotation chain must reproduce
   every annotated intermediate and the final gold answer exactly (sympy
   Rational — no float noise). Items whose rationale we cannot replay are
   dropped.
2. Perturbation check: the perturbed chain must keep intermediates integer
   where the originals were integer, non-negative where the originals were
   non-negative, and must change the final answer (else the canary detects
   nothing).

The perturbation for item i is chosen deterministically from the ENGLISH
question/rationale only, then the same number substitution is applied to every
language's parallel question — canary items stay parallel across languages.

Known limitation (shared with GSM-Plus): a numeric literal in the solution can
coincide with an implicit constant (7 days/week, 2 for "half"...). We only
perturb values that appear exactly once in the question and are not in
CONSTANT_DENYLIST; residual mismatches are a per-item risk, acceptable for a
robustness canary.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import sympy

from mlkv.languages import LANGUAGES

logger = logging.getLogger(__name__)

SEED = "mlkv-canary-v1"
DEFAULT_N_ITEMS = 50

ANNOTATION_RE = re.compile(r"<<([^<>=]+)=([^<>=]+)>>")
# Number token inside an annotation expression (commas already stripped).
EXPR_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
# Number token in question text: optional 3-digit grouping + optional decimals.
QUESTION_NUM_RE = re.compile(r"(?<![\d.,])\d+(?:,\d{3})*(?:\.\d+)?(?!\d)(?![.,]\d)")

# Values likely to appear as implicit constants in solutions (half, dozen,
# days/week, percent base...) — never perturbed.
CONSTANT_DENYLIST = {1, 2, 3, 4, 5, 7, 10, 12, 24, 60, 100, 365, 1000}

# Candidate offsets for the perturbed value, tried in rng order.
OFFSETS = [d for d in range(-9, 10) if d != 0]


class ChainError(ValueError):
    """The annotation chain cannot be (re)played unambiguously."""


def _rat(token: str) -> sympy.Rational:
    return sympy.Rational(str(token).replace(",", "").strip())


def parse_annotations(rationale: str) -> list[tuple[str, sympy.Rational]]:
    """Extract (expression, result) pairs from `<<expr=result>>` annotations."""
    pairs = []
    for expr, result in ANNOTATION_RE.findall(rationale):
        try:
            pairs.append((expr.replace(",", "").strip(), _rat(result)))
        except (ValueError, TypeError, sympy.SympifyError) as exc:
            raise ChainError(f"unparseable annotation result: {result!r}") from exc
    if not pairs:
        raise ChainError("no <<expr=result>> annotations")
    return pairs


def _eval(expr: str) -> sympy.Rational:
    try:
        value = sympy.sympify(expr, rational=True)  # floats become exact Rationals
    except Exception as exc:  # sympy raises many types on malformed input
        raise ChainError(f"unparseable expression: {expr!r}") from exc
    if not value.is_number or not value.is_rational:
        raise ChainError(f"non-numeric expression: {expr!r}")
    return sympy.Rational(value)


def evaluate_chain(
    annotations: list[tuple[str, sympy.Rational]],
    substitutions: dict[sympy.Rational, sympy.Rational] | None = None,
) -> list[sympy.Rational]:
    """Replay the annotation chain, propagating substituted values forward.

    Each expression's numeric literals are looked up in `substitutions`
    (initially the perturbed question number); when an expression's new result
    differs from its annotated original, the original→new mapping is added so
    downstream expressions that reference the intermediate update too.
    """
    subs = dict(substitutions or {})
    results = []
    for expr, orig_result in annotations:
        new_expr = EXPR_NUM_RE.sub(
            lambda m: f"({subs.get(_rat(m.group()), _rat(m.group()))})", expr
        )
        value = _eval(new_expr)
        results.append(value)
        if value != orig_result:
            if orig_result in subs and subs[orig_result] != value:
                raise ChainError(
                    f"ambiguous intermediate {orig_result}: two new values"
                )
            subs[orig_result] = value
    return results


def verify_chain(annotations: list[tuple[str, sympy.Rational]],
                 gold: sympy.Rational) -> bool:
    """Original chain must reproduce every annotated result and the gold."""
    try:
        results = evaluate_chain(annotations)
    except ChainError:
        return False
    return all(r == orig for r, (_, orig) in zip(results, annotations)) and (
        results[-1] == gold
    )


@dataclass(frozen=True)
class Perturbation:
    old: int        # original question number
    new: int        # perturbed question number
    gold_old: int
    gold_new: int


def _question_values(question: str) -> list[sympy.Rational]:
    return [_rat(tok) for tok in QUESTION_NUM_RE.findall(question)]


def choose_perturbation(en_question: str, rationale: str, gold: float,
                        rng) -> Perturbation | None:
    """Deterministically pick a (number, offset) that survives all checks."""
    try:
        annotations = parse_annotations(rationale)
    except ChainError:
        return None
    gold_rat = _rat(gold)
    if not verify_chain(annotations, gold_rat):
        return None
    originals = evaluate_chain(annotations)

    values = _question_values(en_question)
    expr_values = {
        _rat(tok) for expr, _ in annotations for tok in EXPR_NUM_RE.findall(expr)
    }
    candidates = [
        v for v in values
        if v.is_integer and v > 0
        and values.count(v) == 1
        and int(v) not in CONSTANT_DENYLIST
        and v in expr_values
    ]
    rng.shuffle(candidates)

    for value in candidates:
        offsets = list(OFFSETS)
        rng.shuffle(offsets)
        for offset in offsets:
            new_value = int(value) + offset
            if new_value < 1:
                continue
            try:
                results = evaluate_chain(
                    annotations, {value: sympy.Rational(new_value)}
                )
            except ChainError:
                continue
            ok = all(
                (not orig.is_integer or new.is_integer)
                and (orig < 0 or new >= 0)
                for orig, new in zip(originals, results)
            )
            final = results[-1]
            if ok and final.is_integer and final >= 0 and final != gold_rat:
                return Perturbation(
                    old=int(value), new=new_value,
                    gold_old=int(gold_rat), gold_new=int(final),
                )
    return None


def _format_like(value: int, style: str) -> str:
    if style == "comma":
        return f"{value:,}"
    if style == "dot":
        return f"{value:,}".replace(",", ".")
    return str(value)


def substitute_number(text: str, old: int, new: int) -> str | None:
    """Replace standalone occurrences of `old` in text, keeping the grouping
    style found (plain 1000 / en 1,000 / eu 1.000). None if not found."""
    styles = ["plain"] + (["comma", "dot"] if old >= 1000 else [])
    for style in styles:
        token = _format_like(old, style)
        pattern = re.compile(
            r"(?<![\d.,])" + re.escape(token) + r"(?!\d)(?![.,]\d)"
        )
        if pattern.search(text):
            return pattern.sub(_format_like(new, style), text)
    return None


def build_canary_item(index: int, lang: str, lang_question: str,
                      perturbation: Perturbation) -> dict | None:
    """Apply an (EN-chosen) perturbation to one language's parallel question."""
    question = substitute_number(
        lang_question, perturbation.old, perturbation.new
    )
    if question is None:
        return None
    instruction = LANGUAGES[lang].instruction
    return {
        "item_id": f"mgsm-canary-{lang}-{index}",
        "question": question,
        "prompt": f"{question}\n\n{instruction}",
        "gold": perturbation.gold_new,
        "lang": lang,
    }


def load(lang: str, max_items: int | None = None,
         n_items: int = DEFAULT_N_ITEMS) -> list[dict]:
    """Canary items for `lang`: first `n_items` MGSM items (in index order)
    with a verified perturbation that also substitutes cleanly into the
    language's question text."""
    import random

    from datasets import load_dataset

    from mlkv.tasks import mgsm

    en = mgsm._mgsm_split("en")
    gsm8k = load_dataset("openai/gsm8k", "main", split="test")
    if lang == "en":
        lang_questions = {i: row["question"] for i, row in enumerate(en)}
    elif lang == "vi":
        lang_questions = {
            int(item["item_id"].rsplit("-", 1)[-1]): item["question"]
            for item in mgsm.load("vi")
        }
    else:
        lang_questions = {
            i: row["question"] for i, row in enumerate(mgsm._mgsm_split(lang))
        }

    items, dropped_perturb, dropped_subst = [], 0, 0
    for i, en_row in enumerate(en):
        if len(items) >= n_items:
            break
        if en_row["question"] != gsm8k[i]["question"]:
            logger.warning("GSM8K/MGSM question mismatch at index %d — skipped", i)
            continue
        if i not in lang_questions:
            continue
        rng = random.Random(f"{SEED}:{i}")
        perturbation = choose_perturbation(
            en_row["question"], gsm8k[i]["answer"], en_row["answer_number"], rng
        )
        if perturbation is None:
            dropped_perturb += 1
            continue
        item = build_canary_item(i, lang, lang_questions[i], perturbation)
        if item is None:
            dropped_subst += 1
            continue
        items.append(item)
    logger.info(
        "canary[%s]: %d items (%d no valid perturbation, %d substitution failed)",
        lang, len(items), dropped_perturb, dropped_subst,
    )
    return items[:max_items] if max_items else items
