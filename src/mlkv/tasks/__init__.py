"""Task loaders. Each yields dicts: {item_id, prompt, gold, lang}."""

from __future__ import annotations

import unicodedata


def nfd_variant(items: list[dict]) -> list[dict]:
    """Re-encode prompts in Unicode NFD (decomposed diacritics).

    Within-model fertility probe (design doc §2.6): same model, same language,
    same content — only the byte/token encoding changes. Measured inflation on
    MGSM-VI questions: Llama-3.1 ×2.36, Gemma-2 ×2.08, Qwen3 ×1.00 (its
    tokenizer NFC-normalizes, making Qwen the built-in negative control).
    item_ids are kept — the task name carries the '-nfd' suffix in the store.
    """
    def nfd(text: str) -> str:
        return unicodedata.normalize("NFD", text)

    return [
        {**item, "question": nfd(item["question"]), "prompt": nfd(item["prompt"])}
        if "question" in item else {**item, "prompt": nfd(item["prompt"])}
        for item in items
    ]
