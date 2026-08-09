"""Generation runner: model × language × compression config × task items.

Design notes:
- Greedy decoding (do_sample=False) — determinism by construction; residual
  kernel nondeterminism is quantified separately (3 repeats of one cell).
- One model load per invocation; configs applied per-run via kvpress context
  manager or quantized-cache generate kwargs.
- Resumable: completed (model, task, lang, config, item) cells are skipped.
"""

from __future__ import annotations

import logging
import platform
import time

import torch

from mlkv import store
from mlkv.compression import CompressionConfig
from mlkv.drift import drift_score, expected_language
from mlkv.metrics import is_correct

logger = logging.getLogger(__name__)


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def stack_description(model_name: str, device: str, dtype: str) -> dict:
    import transformers

    desc = {
        "model": model_name,
        "device": device,
        "dtype": dtype,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "platform": platform.platform(),
    }
    if device == "cuda":
        desc["gpu"] = torch.cuda.get_device_name(0)
    try:
        import kvpress
        desc["kvpress"] = kvpress.__version__
    except ImportError:
        pass
    return desc


def load_model(model_name: str, device: str, dtype: torch.dtype = torch.bfloat16):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype)
    model.to(device)
    model.eval()
    return model, tokenizer


def build_prompt(tokenizer, user_text: str, enable_thinking: bool) -> str:
    messages = [{"role": "user", "content": user_text}]
    kwargs = {"tokenize": False, "add_generation_prompt": True}
    try:  # Qwen3 supports enable_thinking; other templates reject it
        return tokenizer.apply_chat_template(
            messages, enable_thinking=enable_thinking, **kwargs
        )
    except (TypeError, ValueError):
        return tokenizer.apply_chat_template(messages, **kwargs)


@torch.inference_mode()
def generate_one(model, tokenizer, prompt_text: str, config: CompressionConfig,
                 device: str, max_new_tokens: int) -> tuple[str, int, int]:
    inputs = tokenizer(prompt_text, return_tensors="pt").to(device)
    n_prompt_tokens = inputs["input_ids"].shape[1]
    gen_kwargs = dict(
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        **config.generate_kwargs(),
    )
    press = config.press(prefill_len=n_prompt_tokens)
    if press is not None:
        with press(model):
            out = model.generate(**inputs, **gen_kwargs)
    else:
        out = model.generate(**inputs, **gen_kwargs)
    new_tokens = out[0][n_prompt_tokens:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return text, len(new_tokens), n_prompt_tokens


def default_score(output: str, item: dict) -> tuple[bool, dict]:
    """Numeric exact-match scoring (MGSM-style)."""
    return is_correct(output, item["gold"]), {}


def run_matrix(model_name: str, task_name: str, items_by_lang: dict[str, list[dict]],
               configs: list[CompressionConfig], db_path: str,
               max_new_tokens: int = 512, enable_thinking: bool = False,
               score_fn=default_score) -> dict:
    device = pick_device()
    conn = store.connect(db_path)
    stack_id = store.register_stack(
        conn, stack_description(model_name, device, "bfloat16")
    )
    logger.info("device=%s stack=%s", device, stack_id)

    model, tokenizer = load_model(model_name, device)
    counts = {"done": 0, "skipped": 0, "failed": 0}

    for config in configs:
        for lang, items in items_by_lang.items():
            language = expected_language(lang)
            for item in items:
                key = store.run_key(model_name, task_name, lang, config.name, item["item_id"])
                if store.is_done(conn, key):
                    counts["skipped"] += 1
                    continue
                prompt_text = build_prompt(tokenizer, item["prompt"], enable_thinking)
                start = time.perf_counter()
                try:
                    output, n_tokens, n_prompt = generate_one(
                        model, tokenizer, prompt_text, config, device, max_new_tokens
                    )
                except Exception:
                    logger.exception("generation failed: %s %s %s", config.name, lang, item["item_id"])
                    counts["failed"] += 1
                    continue
                latency = time.perf_counter() - start
                correct, meta = score_fn(output, item)
                # Per-generation covariates for the RQ2 fertility×budget
                # regression: content size in tokens (templated prompt, what
                # eviction acts on) and bytes (the fertility-free axis), plus
                # the eviction ratio actually applied (budget configs vary it
                # per item).
                meta.update({
                    "n_prompt_tokens": n_prompt,
                    "prompt_bytes": len(item["prompt"].encode("utf-8")),
                    "kv_ratio": config.effective_ratio(n_prompt),
                })
                store.save(
                    conn, key,
                    model=model_name, task=task_name, lang=lang, config=config.name,
                    item_id=item["item_id"], stack_id=stack_id, output=output,
                    n_output_tokens=n_tokens, answer_gold=item["gold"],
                    correct=correct,
                    drift=drift_score(output, language),
                    latency_s=latency,
                    meta=meta,
                )
                counts["done"] += 1
                if counts["done"] % 10 == 0:
                    logger.info("progress: %s", counts)
    return counts
