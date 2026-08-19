# mlkv — What Does KV-Cache Compression Break Across Languages?

Experiment harness for the ICLR 2027 submission: measuring per-language damage of
KV-cache compression (quantization, eviction) and weight PTQ in LLMs, with
tokenizer fertility as the mechanism covariate.

- **Design doc** (preregistered predictions, matrix, stats plan, gates):
  `../literature_review/notes/topics/experiment-design.md`
- **Pilot runbook** (rent GPU → run → Gate-1 analysis): `docs/pilot-runbook.md`

## Setup

```bash
uv sync                          # Mac/dev: baseline runs, fertility, analysis
# CUDA box extras (main matrix):
uv pip install kvpress optimum-quanto fasttext-wheel
```

## Usage

```bash
uv run mlkv fertility --models Qwen/Qwen3-4B --langs all   # tokens vs EN on parallel MGSM
uv run mlkv run --model Qwen/Qwen3-4B --task mgsm --langs en,vi,th \
    --configs baseline,kv4,snapkv@r0.75 --max-items 250
uv run mlkv summary                                        # per-cell accuracy table
uv run pytest                                              # unit tests
```

Compression config strings: `baseline`, `kv4`/`kv2` (quantized cache),
`snapkv@r0.75` (kvpress eviction, ratio = fraction removed), `gptq4`/`awq4`
(separate checkpoints, bookkeeping only).

## Key invariants

- **Greedy decoding**; serving stack recorded per run (`stacks` table).
- **No LLM judges** — answer scoring is numeric with multilingual number-format
  handling (1.234 ≡ 1,234); drift detection is GlotLID/script-based.
- **Resumable**: completed (model, task, lang, config, item) cells are skipped;
  changing `PROMPT_VERSION` invalidates keys on purpose.

## Measured fertility (Qwen3 tokenizer, parallel MGSM questions, rel. to EN)

en 1.00 · zh 1.07 · es 1.27 · **vi 1.31** · fr 1.32 · ja 1.32 · de 1.34 ·
ru 1.49 · sw 1.74 · **th 2.12** · **bn 4.22** · **te 6.28**

Same content, up to 6× the tokens — a fixed KV budget is a much smaller
*content* budget in high-fertility languages. This is preregistered mechanism P2.
