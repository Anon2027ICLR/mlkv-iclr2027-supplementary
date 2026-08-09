"""Command-line interface: mlkv <command>."""

from __future__ import annotations

import argparse
import logging


def cmd_fertility(args: argparse.Namespace) -> None:
    from transformers import AutoTokenizer

    from mlkv import fertility
    from mlkv.languages import resolve
    from mlkv.tasks import mgsm

    for model_name in args.models.split(","):
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        stats = []
        for language in resolve(args.langs):
            try:
                texts = mgsm.questions_for_fertility(language.code)
            except Exception as exc:
                print(f"[{language.code}] skipped: {exc}")
                continue
            stats.append(fertility.measure(tokenizer, model_name, language.code, texts))
        rel = fertility.relative_fertility(stats)
        print(f"\n## {model_name} (corpus: MGSM questions, parallel)")
        print(f"{'lang':<6}{'tok/byte':>10}{'tok/char':>10}{'bytes/tok':>11}{'rel. to en':>12}")
        for s in sorted(stats, key=lambda s: rel[s.lang]):
            print(f"{s.lang:<6}{s.tokens_per_byte:>10.4f}{s.tokens_per_char:>10.4f}"
                  f"{s.bytes_per_token:>11.2f}{rel[s.lang]:>12.2f}")


def cmd_run(args: argparse.Namespace) -> None:
    from mlkv import compression, runner
    from mlkv.languages import resolve
    from mlkv.tasks import mgsm

    if args.task != "mgsm":
        raise SystemExit(f"task not implemented yet: {args.task}")
    items_by_lang = {
        lang.code: mgsm.load(lang.code, max_items=args.max_items)
        for lang in resolve(args.langs)
    }
    configs = [compression.parse(c) for c in args.configs.split(",")]
    counts = runner.run_matrix(
        model_name=args.model,
        task_name=args.task,
        items_by_lang=items_by_lang,
        configs=configs,
        db_path=args.db,
        max_new_tokens=args.max_new_tokens,
        enable_thinking=args.thinking,
    )
    print(f"finished: {counts}")


def cmd_summary(args: argparse.Namespace) -> None:
    from mlkv import store

    conn = store.connect(args.db)
    rows = store.summary(conn)
    print(f"{'model':<28}{'task':<7}{'config':<14}{'lang':<6}{'n':>5}"
          f"{'acc':>7}{'tok':>7}{'bytes':>8}{'drift':>7}")
    for r in rows:
        drift = f"{r['avg_drift']:.3f}" if r["avg_drift"] is not None else "-"
        print(f"{r['model'][:27]:<28}{r['task']:<7}{r['config']:<14}{r['lang']:<6}"
              f"{r['n']:>5}{r['accuracy']:>7.3f}{r['avg_tokens']:>7.0f}"
              f"{r['avg_bytes']:>8.0f}{drift:>7}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mlkv")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fert = sub.add_parser("fertility", help="measure tokenizer fertility on MGSM questions")
    p_fert.add_argument("--models", required=True, help="comma-separated HF model names")
    p_fert.add_argument("--langs", default="all")
    p_fert.set_defaults(func=cmd_fertility)

    p_run = sub.add_parser("run", help="run a generation matrix cell")
    p_run.add_argument("--model", required=True)
    p_run.add_argument("--task", default="mgsm")
    p_run.add_argument("--langs", default="en")
    p_run.add_argument("--configs", default="baseline", help="e.g. baseline,kv4,snapkv@r0.75")
    p_run.add_argument("--max-items", type=int, default=None)
    p_run.add_argument("--max-new-tokens", type=int, default=512)
    p_run.add_argument("--thinking", action="store_true", help="enable thinking mode (Qwen3)")
    p_run.add_argument("--db", default="results/mlkv.db")
    p_run.set_defaults(func=cmd_run)

    p_sum = sub.add_parser("summary", help="print per-cell accuracy summary")
    p_sum.add_argument("--db", default="results/mlkv.db")
    p_sum.set_defaults(func=cmd_summary)

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args()
    args.func(args)
