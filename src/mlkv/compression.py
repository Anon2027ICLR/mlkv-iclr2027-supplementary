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

# Optional ":w<int>" overrides the press's observation window (E2, see
# docs/mrag-mechanism-pivot.md): a fixed token window is itself a
# token-denominated constant, so it is exposed as a treatment variable.
_PRESS_RE = re.compile(
    r"^(?P<name>[a-z0-9]+)@r(?P<ratio>0\.\d+)(?::w(?P<window>[1-9]\d*))?$"
)
_BUDGET_RE = re.compile(r"^(?P<name>[a-z0-9]+)@b(?P<budget>[1-9]\d*)$")


# Presses with an observation window cannot compress prompts shorter than it
# (kvpress asserts). Below the minimum the config runs uncompressed and the
# recorded kv_ratio covariate is 0.0 — same semantics as a satisfied budget.
PRESS_MIN_PREFILL = {"snapkv": 65}  # SnapKVPress default window_size=64


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
                "cache_config": {"backend": self.params.get("backend", "quanto"),
                                 "nbits": self.params["nbits"]},
            }
        return {}

    def _min_prefill(self) -> int:
        """Prompts shorter than the observation window cannot be compressed;
        a custom window moves that floor with it."""
        if "window" in self.params:
            return self.params["window"] + 1
        return PRESS_MIN_PREFILL.get(self.params["press"], 0)

    def effective_ratio(self, prefill_len: int) -> float | None:
        """Actual eviction ratio applied for this prompt length (None if the
        config does not evict). Recorded per generation for the RQ2 regression."""
        if self.kind != "press":
            return None
        if prefill_len < self._min_prefill():
            return 0.0
        if "budget" in self.params:
            return budget_ratio(self.params["budget"], prefill_len)
        return self.params["ratio"]

    def press(self, prefill_len: int | None = None):
        """Instantiate the kvpress press object, or None.

        Needs prefill_len: prompts under the press's observation window, or
        already within a budget, run uncompressed (None) — decided before the
        kvpress import so no-op paths also work without the CUDA extras.
        """
        if self.kind != "press":
            return None
        if prefill_len is None:
            raise ValueError(f"press config {self.name!r} needs prefill_len")
        ratio = self.effective_ratio(prefill_len)
        if ratio == 0.0:
            return None
        import kvpress  # CUDA box extra

        cls = getattr(kvpress, PRESS_NAMES[self.params["press"]])
        if "window" in self.params:
            return cls(compression_ratio=ratio, window_size=self.params["window"])
        return cls(compression_ratio=ratio)


def parse(config: str) -> CompressionConfig:
    if config == "baseline":
        return CompressionConfig(config, "baseline")
    if config in ("kv2", "kv4", "kv8"):
        return CompressionConfig(config, "kvquant", {"nbits": int(config[2:])})
    if config in ("kv2h", "kv4h"):  # HQQ backend — naive quanto 2-bit cliffs
        return CompressionConfig(config, "kvquant",
                                 {"nbits": int(config[2]), "backend": "hqq"})
    if config in ("gptq4", "awq4", "int8"):
        return CompressionConfig(config, "weight")
    m = _PRESS_RE.match(config)
    if m and m.group("name") in PRESS_NAMES:
        params = {"press": m.group("name"), "ratio": float(m.group("ratio"))}
        if m.group("window"):
            params["window"] = int(m.group("window"))
        return CompressionConfig(config, "press", params)
    m = _BUDGET_RE.match(config)
    if m and m.group("name") in PRESS_NAMES:
        return CompressionConfig(
            config, "press",
            {"press": m.group("name"), "budget": int(m.group("budget"))},
        )
    raise ValueError(f"unknown compression config: {config!r}")
