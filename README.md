# mlkv — What Does KV-Cache Compression Break Across Languages?

Supplementary material for the ICLR 2027 submission of the same name: the
experiment harness, the preregistration and readout for every arm, the
32 generation stores the paper's tables are computed from, and the
anonymised version history of all three.

## Verify the paper in one command

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh    # if uv is not installed
uv run python scripts/audit_paper_numbers.py       # 651 checks, 0 mismatches
```

That recomputes every table cell in the paper from the raw generations in
`results/` and exits non-zero on any drift — no number in the paper is
transcribed by hand. `uv run pytest` runs the unit tests, and
`uv run --with matplotlib python scripts/paper_figures.py` redraws both
figures from the same stores.

## What is here

- `src/mlkv/`, `tests/` — the harness: task construction, compression
  configurations, scoring, drift detection.
- `scripts/` — the analysis and the campaign runners.
  `audit_paper_numbers.py` is the one that matters;
  `paper/iclr2027/README.md` explains the rest.
- `docs/iclr-*-preregister.md` / `docs/iclr-*-readout.md` — the predictions and
  kill conditions for each arm, and what came back. Each preregistration was
  committed before its run; `paper/iclr2027/README.md` tabulates which
  timestamps precede their first generation and which do not.
- `docs/commit-map.md` — the anonymised history renumbered every commit, and
  the locked evidence documents cite the old hashes. This is the bridge.
- `results/*.db` — the generation stores: one SQLite row per model output, with
  the serving stack recorded per run. There are 32: the seventeen the
  reproducibility statement names, plus `e3-final` and `e3_384`, which back the
  decode-cap appendix table rather than a main-text cell and so are not in that
  list. The audit needs all 32.
- `paper/iclr2027/` — the LaTeX source, the figures, and the build recipe.

## A word on "the reviewer"

Several preregistrations and readouts answer numbered items from "the second
review", "reviewer-3", and so on. Those were adversarial reviews of our own
draft by large language models, run during preparation and numbered so the
responses could be tracked; the AI use statement in the paper describes the
practice. They are not reports from any venue: this work has not been
submitted or reviewed anywhere.

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
