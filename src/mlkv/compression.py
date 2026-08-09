"""Compression configuration registry.

Config strings (stable identifiers — they key the result store):
  baseline            full-precision weights, full KV cache
  kv4 | kv2           KV-cache quantization via HF quantized cache (quanto)
  <press>@r<ratio>    KV eviction via kvpress, e.g. snapkv@r0.75
                      (ratio = fraction of the cache REMOVED)
  <press>@b<budget>   KV eviction to an ABSOLUTE cache budget, e.g.
                      snapkv@b2048 (keep at most 2048 prefill KV entries).
                      Emulated via a per-item ratio = 1 - budget/prefill_len;
                      prompts already within budget run uncompressed.
                      This is the serving-realistic knob and the config family
                      that carries the fertility mechanism claim (design §RQ2):
                      a fixed TOKEN budget is a smaller CONTENT budget for
                      high-fertility languages. Ratio configs are the control
                      family (content retained scales proportionally).
                      Caveat: kvpress compresses the prefill cache only;
                      decode-time KV accumulates beyond the budget. Fine for
                      short-answer tasks (mRAG), report honestly elsewhere.

Weight PTQ configs (gptq4/awq4/int8) are separate *checkpoints*, not runtime
configs — handled by pointing --model at the quantized checkpoint and
recording the config name for bookkeeping.

kvpress and quanto are optional imports: the Mac dev box runs baseline only;
the CUDA box installs the extras.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Verified against kvpress 0.5.4 on the CUDA box (2026-08-09).
PRESS_NAMES = {
    "snapkv": "SnapKVPress",
    "h2o": "ObservedAttentionPress",  # H2O-style; requires attn_implementation="eager"
    "streamingllm": "StreamingLLMPress",
    "tova": "TOVAPress",
    "expected": "ExpectedAttentionPress",
}

_PRESS_RE = re.compile(r"^(?P<name>[a-z0-9]+)@r(?P<ratio>0\.\d+)$")
_BUDGET_RE = re.compile(r"^(?P<name>[a-z0-9]+)@b(?P<budget>[1-9]\d*)$")


def budget_ratio(budget: int, prefill_len: int) -> float:
    """Fraction of the prefill cache to remove so <= budget entries survive."""
    if prefill_len <= budget:
        return 0.0
    return 1.0 - budget / prefill_len


@dataclass
class CompressionConfig:
    name: str                       # the config string, verbatim
    kind: str                       # baseline | kvquant | press | weight
    params: dict = field(default_factory=dict)

    def generate_kwargs(self) -> dict:
        """Extra kwargs for model.generate()."""
        if self.kind == "kvquant":
            return {
                "cache_implementation": "quantized",
                "cache_config": {"backend": "quanto", "nbits": self.params["nbits"]},
            }
        return {}

    def effective_ratio(self, prefill_len: int) -> float | None:
        """Actual eviction ratio applied for this prompt length (None if the
        config does not evict). Recorded per generation for the RQ2 regression."""
        if self.kind != "press":
            return None
        if "budget" in self.params:
            return budget_ratio(self.params["budget"], prefill_len)
        return self.params["ratio"]

    def press(self, prefill_len: int | None = None):
        """Instantiate the kvpress press object, or None.

        Budget-mode configs need prefill_len; they return None (no press)
        when the prompt already fits the budget — checked before the kvpress
        import so the no-op path also works without the CUDA extras.
        """
        if self.kind != "press":
            return None
        if "budget" in self.params:
            if prefill_len is None:
                raise ValueError(f"budget config {self.name!r} needs prefill_len")
            ratio = budget_ratio(self.params["budget"], prefill_len)
            if ratio == 0.0:
                return None
        else:
            ratio = self.params["ratio"]
        import kvpress  # CUDA box extra

        cls = getattr(kvpress, PRESS_NAMES[self.params["press"]])
        return cls(compression_ratio=ratio)


def parse(config: str) -> CompressionConfig:
    if config == "baseline":
        return CompressionConfig(config, "baseline")
    if config in ("kv2", "kv4", "kv8"):
        return CompressionConfig(config, "kvquant", {"nbits": int(config[2:])})
    if config in ("gptq4", "awq4", "int8"):
        return CompressionConfig(config, "weight")
    m = _PRESS_RE.match(config)
    if m and m.group("name") in PRESS_NAMES:
        return CompressionConfig(
            config, "press",
            {"press": m.group("name"), "ratio": float(m.group("ratio"))},
        )
    m = _BUDGET_RE.match(config)
    if m and m.group("name") in PRESS_NAMES:
        return CompressionConfig(
            config, "press",
            {"press": m.group("name"), "budget": int(m.group("budget"))},
        )
    raise ValueError(f"unknown compression config: {config!r}")
