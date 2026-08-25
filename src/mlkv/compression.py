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
    # PyramidKVPress subclasses SnapKVPress and inherits window_size=64, so the
    # ":w" override applies unchanged — same scorer inputs, different per-layer
    # budget allocation. Second member of the windowed family for the
    # press-generality claim (docs/iclr-pyramidkv-preregister.md).
    "pyramidkv": "PyramidKVPress",
    "h2o": "ObservedAttentionPress",  # H2O-style; requires attn_implementation="eager"
    "streamingllm": "StreamingLLMPress",
    "tova": "TOVAPress",
    "expected": "ExpectedAttentionPress",
    # Constant-free scorers — negative controls for the press-generality sweep:
    # if these show the same per-language ordering as the windowed presses, the
    # ordering is language difficulty, not a token-denominated constant.
    "knorm": "KnormPress",
    "random": "RandomPress",
}

# Optional ":w<int>" overrides the press's observation window (E2, see
# docs/mrag-mechanism-pivot.md): a fixed token window is itself a
# token-denominated constant, so it is exposed as a treatment variable.
# ":wq<c>" is the per-item oracle window w_i = c + |Q_i| (reviewer-5 Q1,
# docs/iclr-oracle-preregister.md): <c> is the measured trailing-block
# constant baked into the config string by the driver after on-pod
# re-derivation, and |Q_i| arrives per item as meta["q_tokens"], computed by
# the task builder on the run tokenizer. Emulated per item, the same shape
# as the @b budget family.
_PRESS_RE = re.compile(
    r"^(?P<name>[a-z0-9]+)@r(?P<ratio>0\.\d+)"
    r"(?::w(?P<window>[1-9]\d*)|:wq(?P<wq_c>[1-9]\d*))?$"
)
_BUDGET_RE = re.compile(r"^(?P<name>[a-z0-9]+)@b(?P<budget>[1-9]\d*)$")
# Byte-denominated cache budget (E3 fix arm): keep the token-equivalent of
# <bytes> of this prompt's text, i.e. ratio = 1 - bytes/prompt_bytes. Content
# kept is language-invariant by construction — the remedy the paper proposes.
_BYTEBUDGET_RE = re.compile(r"^(?P<name>[a-z0-9]+)@bb(?P<bytes>[1-9]\d*)$")


# Presses with an observation window cannot compress prompts shorter than it
# (kvpress asserts). Below the minimum the config runs uncompressed and the
# recorded kv_ratio covariate is 0.0 — same semantics as a satisfied budget.
PRESS_MIN_PREFILL = {
    "snapkv": 65,     # SnapKVPress default window_size=64
    "pyramidkv": 65,  # inherits SnapKVPress window_size=64
}


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

    def resolved_window(self, q_tokens: int | None = None) -> int | None:
        """The observation window this config uses (None: press default).
        Per-item ":wq" configs need the item's question length."""
        if "window" in self.params:
            return self.params["window"]
        if "wq_c" in self.params:
            if q_tokens is None:
                raise ValueError(f"{self.name!r} needs q_tokens per item")
            return self.params["wq_c"] + q_tokens
        return None

    def _min_prefill(self, q_tokens: int | None = None) -> int:
        """Prompts shorter than the observation window cannot be compressed;
        a custom window moves that floor with it."""
        w = self.resolved_window(q_tokens)
        if w is not None:
            return w + 1
        return PRESS_MIN_PREFILL.get(self.params["press"], 0)

    def effective_ratio(self, prefill_len: int,
                        prompt_bytes: int | None = None,
                        q_tokens: int | None = None) -> float | None:
        """Actual eviction ratio applied for this prompt (None if the config
        does not evict). Recorded per generation for the RQ2 regression.
        Byte-budget configs need prompt_bytes; ":wq" configs need q_tokens."""
        if self.kind != "press":
            return None
        if prefill_len < self._min_prefill(q_tokens):
            return 0.0
        if "bytes" in self.params:
            if prompt_bytes is None:
                raise ValueError(f"{self.name!r} needs prompt_bytes")
            if prompt_bytes <= self.params["bytes"]:
                return 0.0
            return 1.0 - self.params["bytes"] / prompt_bytes
        if "budget" in self.params:
            return budget_ratio(self.params["budget"], prefill_len)
        return self.params["ratio"]

    def press(self, prefill_len: int | None = None,
              prompt_bytes: int | None = None,
              q_tokens: int | None = None):
        """Instantiate the kvpress press object, or None.

        Needs prefill_len: prompts under the press's observation window, or
        already within a budget, run uncompressed (None) — decided before the
        kvpress import so no-op paths also work without the CUDA extras.
        Byte-budget configs additionally need prompt_bytes; per-item ":wq"
        configs additionally need q_tokens.
        """
        if self.kind != "press":
            return None
        if prefill_len is None:
            raise ValueError(f"press config {self.name!r} needs prefill_len")
        ratio = self.effective_ratio(prefill_len, prompt_bytes=prompt_bytes,
                                     q_tokens=q_tokens)
        if ratio == 0.0:
            return None
        import kvpress  # CUDA box extra

        cls = getattr(kvpress, PRESS_NAMES[self.params["press"]])
        w = self.resolved_window(q_tokens)
        if w is not None:
            return cls(compression_ratio=ratio, window_size=w)
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
        if m.group("wq_c"):
            params["wq_c"] = int(m.group("wq_c"))
        return CompressionConfig(config, "press", params)
    m = _BYTEBUDGET_RE.match(config)
    if m and m.group("name") in PRESS_NAMES:
        return CompressionConfig(
            config, "press",
            {"press": m.group("name"), "bytes": int(m.group("bytes"))},
        )
    m = _BUDGET_RE.match(config)
    if m and m.group("name") in PRESS_NAMES:
        return CompressionConfig(
            config, "press",
            {"press": m.group("name"), "budget": int(m.group("budget"))},
        )
    raise ValueError(f"unknown compression config: {config!r}")
