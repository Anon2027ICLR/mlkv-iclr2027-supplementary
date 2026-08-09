"""Compression configuration registry.

Config strings (stable identifiers — they key the result store):
  baseline            full-precision weights, full KV cache
  kv4 | kv2           KV-cache quantization via HF quantized cache (quanto)
  <press>@r<ratio>    KV eviction via kvpress, e.g. snapkv@r0.75
                      (ratio = fraction of the cache REMOVED)

Weight PTQ configs (gptq4/awq4/int8) are separate *checkpoints*, not runtime
configs — handled by pointing --model at the quantized checkpoint and
recording the config name for bookkeeping.

kvpress and quanto are optional imports: the Mac dev box runs baseline only;
the CUDA box installs the extras.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PRESS_NAMES = {
    "snapkv": "SnapKVPress",
    "h2o": "KnormPress",          # placeholder mapping; finalize on CUDA box
    "streamingllm": "StreamingLLMPress",
    "tova": "TOVAPress",
    "expected": "ExpectedAttentionPress",
}

_PRESS_RE = re.compile(r"^(?P<name>[a-z0-9]+)@r(?P<ratio>0\.\d+)$")


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

    def press(self):
        """Instantiate the kvpress press object, or None."""
        if self.kind != "press":
            return None
        import kvpress  # CUDA box extra

        cls = getattr(kvpress, PRESS_NAMES[self.params["press"]])
        return cls(compression_ratio=self.params["ratio"])


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
    raise ValueError(f"unknown compression config: {config!r}")
