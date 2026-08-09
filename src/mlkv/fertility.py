"""Tokenizer fertility measurement — the mechanism covariate (RQ2).

Fertility here = tokens per UTF-8 byte (and per char), measured per
model-tokenizer on a parallel corpus, so cross-language comparisons hold
content constant. MGSM questions are parallel across languages and are our
actual task inputs, so they are the primary corpus.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class FertilityStats:
    model: str
    lang: str
    corpus: str
    n_texts: int
    tokens: int
    bytes_: int
    chars: int

    @property
    def tokens_per_byte(self) -> float:
        return self.tokens / self.bytes_

    @property
    def tokens_per_char(self) -> float:
        return self.tokens / self.chars

    @property
    def bytes_per_token(self) -> float:
        return self.bytes_ / self.tokens

    def to_row(self) -> dict:
        row = asdict(self)
        row.update(
            tokens_per_byte=self.tokens_per_byte,
            tokens_per_char=self.tokens_per_char,
            bytes_per_token=self.bytes_per_token,
        )
        return row


def measure(tokenizer, model_name: str, lang: str, texts: list[str],
            corpus: str = "mgsm") -> FertilityStats:
    tokens = 0
    for text in texts:
        tokens += len(tokenizer.encode(text, add_special_tokens=False))
    return FertilityStats(
        model=model_name,
        lang=lang,
        corpus=corpus,
        n_texts=len(texts),
        tokens=tokens,
        bytes_=sum(len(t.encode("utf-8")) for t in texts),
        chars=sum(len(t) for t in texts),
    )


def relative_fertility(stats: list[FertilityStats], anchor_lang: str = "en") -> dict[str, float]:
    """Total tokens per language relative to the anchor.

    Valid because the corpus is PARALLEL: same content, so the token-count
    ratio directly measures how much of a fixed token/KV budget each language
    consumes for equal content. (Per-byte ratios mislead across scripts —
    Thai chars are 3 UTF-8 bytes, Latin 1.)
    """
    anchor = next(s for s in stats if s.lang == anchor_lang)
    return {s.lang: s.tokens / anchor.tokens for s in stats}
