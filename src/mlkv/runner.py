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
        from importlib.metadata import version
        desc["kvpress"] = version("kvpress")
    except Exception:  # not installed (Mac dev box) or metadata missing
        pass
    return desc


def load_model(model_name: str, device: str, dtype: torch.dtype = torch.bfloat16):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        # Llama tokenizers ship without a pad token; batched generation pads
        # on the left, so EOS is safe (attention mask covers the pad columns).
        tokenizer.pad_token = tokenizer.eos_token
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


def effective_batch_size(config: CompressionConfig, batch_size: int) -> int:
    """Press configs always run single-stream: budget presses need a per-item
    compression ratio (impossible with one press object per batch), and the
    kvpress-hook × left-padding interaction is unverified. Correctness over
    speed — quant/baseline cells carry the batching win (long MGSM decodes)."""
    if batch_size > 1 and config.kind == "press":
        return 1
    return max(1, batch_size)


def _plan_batches(entries: list, batch_size: int, length_of) -> list[list]:
    """Chunk work into batches, sorted by prompt length so batch members have
    similar lengths (less padding → less wasted compute, fewer pad artifacts)."""
    ordered = sorted(entries, key=length_of)
    return [ordered[i:i + batch_size] for i in range(0, len(ordered), batch_size)]


def _count_new_tokens(new_ids, pad_id: int) -> int:
    """Token count matching the single-stream path: strip trailing pads but
    count the genuine EOS that ended the sequence (pad==eos for most models)."""
    ids = list(new_ids)
    trailing = 0
    for t in reversed(ids):
        if t == pad_id:
            trailing += 1
        else:
            break
    n = len(ids) - trailing
    if trailing > 0:
        n += 1  # the first token of the trailing run is the real EOS
    return n


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
    press = config.press(prefill_len=n_prompt_tokens,
                         prompt_bytes=len(prompt_text.encode("utf-8")))
    if press is not None:
        with press(model):
            out = model.generate(**inputs, **gen_kwargs)
    else:
        out = model.generate(**inputs, **gen_kwargs)
    new_tokens = out[0][n_prompt_tokens:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return text, len(new_tokens), n_prompt_tokens


@torch.inference_mode()
def generate_batch(model, tokenizer, prompt_texts: list[str],
                   config: CompressionConfig, device: str,
                   max_new_tokens: int) -> list[tuple[str, int, int]]:
    """Batched sibling of generate_one for non-press configs (left padding).

    Numerics differ microscopically from single-stream (padding + batched
    kernels); the batch-equivalence check quantifies this once per stack and
    the batch size is recorded in the stack description."""
    pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id
    enc = tokenizer(prompt_texts, return_tensors="pt", padding=True,
                    padding_side="left").to(device)
    gen_kwargs = dict(
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=pad_id,
        **config.generate_kwargs(),
    )
    out = model.generate(**enc, **gen_kwargs)
    prompt_len = enc["input_ids"].shape[1]
    results = []
    for i in range(len(prompt_texts)):
        new_ids = out[i][prompt_len:]
        text = tokenizer.decode(new_ids, skip_special_tokens=True)
        n_new = _count_new_tokens(new_ids.tolist(), pad_id)
        n_prompt = int(enc["attention_mask"][i].sum())
        results.append((text, n_new, n_prompt))
    return results


def default_score(output: str, item: dict) -> tuple[bool, dict]:
    """Numeric exact-match scoring (MGSM-style)."""
    return is_correct(output, item["gold"]), {}


def run_matrix(model_name: str, task_name: str, items_by_lang: dict[str, list[dict]],
               configs: list[CompressionConfig], db_path: str,
               max_new_tokens: int = 512, enable_thinking: bool = False,
               score_fn=default_score, cooldown_s: float = 0.0,
               batch_size: int = 1) -> dict:
    """cooldown_s: sleep after each generation/batch — thermal duty-cycle control
    for laptop runs; wall-clock only, outputs are unaffected (greedy decoding).
    batch_size: >1 enables batched generation for non-press configs (press
    cells always run single-stream — see effective_batch_size)."""
    device = pick_device()
    conn = store.connect(db_path)
    desc = stack_description(model_name, device, "bfloat16")
    if batch_size > 1:
        desc["batch_size"] = batch_size  # numerics differ from single-stream
    stack_id = store.register_stack(conn, desc)
    logger.info("device=%s stack=%s batch_size=%d", device, stack_id, batch_size)

    model, tokenizer = load_model(model_name, device)
    counts = {"done": 0, "skipped": 0, "failed": 0}

    def score_and_save(key: str, item: dict, lang: str, config, language,
                       output: str, n_tokens: int, n_prompt: int, latency: float) -> None:
        # A failure in the secondary drift metric must never discard a
        # completed (expensive) generation.
        try:
            drift = drift_score(output, language)
        except Exception:
            logger.exception("drift_score failed: %s", item["item_id"])
            drift = None
        correct, meta = score_fn(output, item)
        # Per-generation covariates for the RQ2 fertility×budget regression:
        # content size in tokens (templated prompt, what eviction acts on) and
        # bytes (the fertility-free axis), plus the eviction ratio actually
        # applied (budget configs vary it per item).
        meta.update({
            "n_prompt_tokens": n_prompt,
            "prompt_bytes": len(item["prompt"].encode("utf-8")),
            # Raw item bytes, not templated-prompt bytes: ~0.3% smaller. For
            # bb configs the press used templated bytes; the covariate drift
            # is negligible and documented here.
            "kv_ratio": config.effective_ratio(
                n_prompt, prompt_bytes=len(item["prompt"].encode("utf-8"))),
        })
        store.save(
            conn, key,
            model=model_name, task=task_name, lang=lang, config=config.name,
            item_id=item["item_id"], stack_id=stack_id, output=output,
            n_output_tokens=n_tokens, answer_gold=item["gold"],
            correct=correct, drift=drift, latency_s=latency, meta=meta,
        )
        counts["done"] += 1
        if counts["done"] % 10 == 0:
            logger.info("progress: %s", counts)

    for config in configs:
        ebs = effective_batch_size(config, batch_size)
        if batch_size > 1 and ebs == 1:
            logger.info("config %s: press kind -> single-stream", config.name)
        for lang, items in items_by_lang.items():
            language = expected_language(lang)
            pending = []
            for item in items:
                key = store.run_key(model_name, task_name, lang, config.name, item["item_id"])
                if store.is_done(conn, key):
                    counts["skipped"] += 1
                else:
                    pending.append((key, item))

            if ebs == 1:
                for key, item in pending:
                    prompt_text = build_prompt(tokenizer, item["prompt"], enable_thinking)
                    start = time.perf_counter()
                    try:
                        output, n_tokens, n_prompt = generate_one(
                            model, tokenizer, prompt_text, config, device, max_new_tokens
                        )
                    except Exception:
                        logger.exception("generation failed: %s %s %s",
                                         config.name, lang, item["item_id"])
                        counts["failed"] += 1
                        continue
                    latency = time.perf_counter() - start
                    score_and_save(key, item, lang, config, language,
                                   output, n_tokens, n_prompt, latency)
                    if cooldown_s > 0:
                        time.sleep(cooldown_s)
            else:
                entries = [
                    (key, item, build_prompt(tokenizer, item["prompt"], enable_thinking))
                    for key, item in pending
                ]
                batches = _plan_batches(entries, ebs, length_of=lambda e: len(e[2]))
                for batch in batches:
                    prompts = [e[2] for e in batch]
                    start = time.perf_counter()
                    try:
                        results = generate_batch(
                            model, tokenizer, prompts, config, device, max_new_tokens
                        )
                    except Exception:
                        logger.exception("batch failed: %s %s (%d items)",
                                         config.name, lang, len(batch))
                        counts["failed"] += len(batch)
                        continue
                    latency = (time.perf_counter() - start) / len(batch)
                    for (key, item, _), (output, n_tokens, n_prompt) in zip(batch, results):
                        score_and_save(key, item, lang, config, language,
                                       output, n_tokens, n_prompt, latency)
                    if cooldown_s > 0:
                        time.sleep(cooldown_s)
    return counts
