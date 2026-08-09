"""MGSM loader (juletxara/mgsm) + Vietnamese extension.

MGSM: 250 human-translated GSM8K test items per language, parallel across
languages — which also makes the questions our fertility corpus.

Vietnamese is not in MGSM. We align `namfam/gsm8k-vietnamese` to the MGSM
item set by matching gold answers against the English split in order; items
that fail alignment are dropped (and counted, so QC is visible).
"""

from __future__ import annotations

import logging

from datasets import load_dataset

from mlkv.languages import LANGUAGES
from mlkv.metrics import parse_gold

logger = logging.getLogger(__name__)

MGSM_DATASET = "juletxara/mgsm"
VI_DATASET = "namfam/gsm8k-vietnamese"


def _mgsm_split(lang: str):
    return load_dataset(MGSM_DATASET, lang, split="test")


def load(lang: str, max_items: int | None = None) -> list[dict]:
    language = LANGUAGES[lang]
    instruction = language.instruction

    if language.in_mgsm:
        ds = _mgsm_split(lang)
        items = [
            {
                "item_id": f"mgsm-{lang}-{i}",
                "question": row["question"],
                "prompt": f"{row['question']}\n\n{instruction}",
                "gold": row["answer_number"],
                "lang": lang,
            }
            for i, row in enumerate(ds)
        ]
    elif lang == "vi":
        items = _load_vietnamese(instruction)
    else:
        raise ValueError(f"no MGSM source for language: {lang}")

    return items[:max_items] if max_items else items


def _load_vietnamese(instruction: str) -> list[dict]:
    """Align the community VI translation of GSM8K test to MGSM's 250 items."""
    en = _mgsm_split("en")
    vi = load_dataset(VI_DATASET, split="test")

    vi_rows = list(vi)
    vi_fields = vi_rows[0].keys()
    q_field = next((f for f in ("question_vi", "question", "vi_question", "problem") if f in vi_fields), None)
    a_field = next((f for f in ("answer", "answer_number", "final_answer") if f in vi_fields), None)
    idx_field = "index" if "index" in vi_fields else None
    if q_field is None or a_field is None:
        raise RuntimeError(f"unexpected schema in {VI_DATASET}: {sorted(vi_fields)}")

    def gold_of(row) -> float | None:
        raw = row[a_field]
        if isinstance(raw, str) and "####" in raw:  # GSM8K rationale format
            raw = raw.split("####")[-1]
        try:
            return parse_gold(raw)
        except (ValueError, TypeError):
            return None

    # Prefer the dataset's own GSM8K index for alignment; fall back to position.
    # MGSM took the first 250 GSM8K test items, so MGSM item i ↔ GSM8K index i.
    by_index = {row[idx_field]: row for row in vi_rows} if idx_field else None

    items, dropped = [], 0
    for i, en_row in enumerate(en):
        vi_row = by_index.get(i) if by_index is not None else (
            vi_rows[i] if i < len(vi_rows) else None
        )
        if vi_row is None:
            dropped += 1
            continue
        vi_gold = gold_of(vi_row)
        en_gold = parse_gold(en_row["answer_number"])
        if vi_gold is None or abs(vi_gold - en_gold) > 1e-6:
            dropped += 1
            continue
        question = vi_row[q_field]
        items.append(
            {
                "item_id": f"mgsm-vi-{i}",
                "question": question,
                "prompt": f"{question}\n\n{instruction}",
                "gold": en_row["answer_number"],
                "lang": "vi",
            }
        )
    if dropped:
        logger.warning("VI alignment: %d/%d items dropped (answer mismatch)", dropped, len(en))
    if len(items) < 200:
        logger.warning(
            "VI alignment yielded only %d items — positional alignment may be "
            "wrong for this dataset revision; inspect before trusting.", len(items)
        )
    return items


def questions_for_fertility(lang: str) -> list[str]:
    """Parallel question texts (no instruction) as the fertility corpus."""
    return [item["question"] for item in load(lang)]
