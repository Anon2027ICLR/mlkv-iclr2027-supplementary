"""MGSM with a stuffed context: task-generality check for the window mechanism.

The observation-window finding (docs/mrag-mechanism-pivot.md) comes from one
task with one metric. If the mechanism is real it must appear in ANY task where
eviction has to preserve task-critical text sitting just before a long
instruction tail. This task provides that check with everything different:

- task: grade-school maths (MGSM), not span retrieval;
- metric: numeric exact match (`metrics.is_correct`), immune to the span
  scorer and far less exposed to the decode cap (answers are digits);
- critical text: the PROBLEM itself, placed after distractor passages and
  right before the frozen native instruction.

Prompt = [distractor passages, filled to ctx_tokens] + problem + instruction.
With the default 64-token window, a language whose instruction exceeds the
window (bn: 102 Qwen tokens) leaves eviction blind to the problem; a language
whose instruction fits (en: 20) keeps part of the problem visible. Predicted
signature: same as mRAG — bn damaged at moderate dose, recovering under :w256.

Distractor passages come from the mRAG pools (same-language Wikipedia text),
NOT other maths problems: no second instruction string is needed, so the
frozen instruction set stays untouched.

Item ids are ``mgsmst-<lang>-<ctx//1024>k-<i>``.
"""

from __future__ import annotations

import logging
import random

from mlkv.languages import LANGUAGES
from mlkv.tasks import mgsm as mgsm_task
from mlkv.tasks import mrag as mrag_task

logger = logging.getLogger(__name__)

SEED = "mlkv-mgsm-stuffed-v1"
_JOINER = "\n\n"


def _n_tokens(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def build(lang: str, tokenizer, ctx_tokens_list: list[int],
          max_items: int | None = None,
          problems: list[dict] | None = None,
          passages: list[str] | None = None) -> list[dict]:
    """Items for all context budgets. `problems`/`passages` injectable for tests.

    Problems load via the frozen MGSM loader (gold answers included); the
    distractor pool reuses mrag.load_pool's passage side.
    """
    if problems is None:
        problems = mgsm_task.load(lang)
    if passages is None:
        _, passages = mrag_task.load_pool(lang)
    if max_items:
        problems = problems[:max_items]

    instruction = LANGUAGES[lang].instruction
    items = []
    for ctx_tokens in ctx_tokens_list:
        for i, prob in enumerate(problems):
            fixed = (
                _n_tokens(tokenizer, prob["question"])
                + _n_tokens(tokenizer, instruction)
                + 3 * len(_JOINER)
            )
            pool = list(passages)
            random.Random(f"{SEED}:{lang}:{ctx_tokens}:{i}").shuffle(pool)
            chosen, used = [], fixed
            for p in pool:
                cost = _n_tokens(tokenizer, p) + len(_JOINER)
                if used + cost > ctx_tokens:
                    continue
                chosen.append(p)
                used += cost
            prompt = _JOINER.join([_JOINER.join(chosen), prob["question"], instruction])
            items.append({
                "item_id": f"mgsmst-{lang}-{ctx_tokens // 1024}k-{i}",
                "prompt": prompt,
                "gold": prob["gold"],
                "lang": lang,
                "meta": {
                    "n_passages": len(chosen),
                    "approx_prompt_tokens": used,
                    "ctx_tokens": ctx_tokens,
                },
            })
    return items
