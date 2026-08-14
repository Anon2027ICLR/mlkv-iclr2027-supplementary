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


def cmd_qc_vi(args: argparse.Namespace) -> None:
    """Print a random sample of MGSM-VI items next to the EN originals for a
    human translation-quality spot-check (design doc §2.2)."""
    import random
    import textwrap

    from mlkv.tasks import mgsm

    vi_items = {
        int(item["item_id"].rsplit("-", 1)[-1]): item for item in mgsm.load("vi")
    }
    en_items = {
        int(item["item_id"].rsplit("-", 1)[-1]): item for item in mgsm.load("en")
    }
    indices = random.Random(args.seed).sample(sorted(vi_items), min(args.n, len(vi_items)))

    def wrap(label: str, text: str) -> str:
        return textwrap.fill(
            text, width=100, initial_indent=f"  {label}: ",
            subsequent_indent=" " * (len(label) + 4),
        )

    print(f"MGSM-VI spot-check: {len(indices)} of {len(vi_items)} aligned items "
          f"(seed={args.seed})\n")
    for k, i in enumerate(indices, 1):
        print(f"[{k}/{len(indices)}] mgsm-vi-{i}  (gold: {en_items[i]['gold']})")
        print(wrap("VI", vi_items[i]["question"]))
        print(wrap("EN", en_items[i]["question"]))
        print()


def cmd_screen_vi(args: argparse.Namespace) -> None:
    """Round-trip-translation screen over all MGSM-VI items (QC layer 2)."""
    from mlkv import qc_screen

    records = qc_screen.run_screen(args.out, n_flag=args.n_flag)
    flagged = [r for r in records if r.flagged]
    print(f"\nscreened {len(records)} items -> {args.out}")
    print(f"review queue ({len(flagged)} flagged, lowest chrF first):")
    for r in flagged:
        note = "  [already audited]" if r.audited else ""
        print(f"  mgsm-vi-{r.index:<5} chrF {r.chrf:5.1f}{note}")


def cmd_audit_vi(args: argparse.Namespace) -> None:
    """LLM-assisted EN<->VI divergence audit over all MGSM-VI items (QC layer 3)."""
    import re
    from pathlib import Path

    from mlkv import qc_llm_audit

    chrf_flagged: set[int] = set()
    screen_report = Path("docs/mgsm-vi-screen.md")
    if screen_report.exists():  # cross-reference the chrF screen's flags
        chrf_flagged = {
            int(m) for m in re.findall(r"## F\d+\. mgsm-vi-(\d+)", screen_report.read_text())
        }
    records = qc_llm_audit.run_audit(args.out, model=args.model, chrf_flagged=chrf_flagged)
    suspects = [r for r in records if r.verdict == "SUSPECT"]
    print(f"\naudited {len(records)} items -> {args.out}")
    print(f"review queue: {len(suspects)} SUSPECT")
    for r in suspects:
        print(f"  mgsm-vi-{r.index}")


def _parse_byte_ctx(spec: str) -> int:
    """'12k' -> 12288 bytes; bare integers are taken as bytes."""
    part = spec.strip().lower()
    return int(part[:-1]) * 1024 if part.endswith("k") else int(part)


def _parse_ctx(spec: str) -> list[int]:
    """'8k,32k' -> [8192, 32768]; bare integers are taken as tokens."""
    budgets = []
    for part in spec.split(","):
        part = part.strip().lower()
        budgets.append(int(part[:-1]) * 1024 if part.endswith("k") else int(part))
    return budgets


def cmd_run(args: argparse.Namespace) -> None:
    from mlkv import compression, runner
    from mlkv.languages import resolve
    from mlkv.tasks import mgsm, mgsm_canary, mrag

    score_fn = runner.default_score
    if args.task == "mgsm":
        items_by_lang = {
            lang.code: mgsm.load(lang.code, max_items=args.max_items)
            for lang in resolve(args.langs)
        }
    elif args.task == "mgsm-canary":
        items_by_lang = {
            lang.code: mgsm_canary.load(lang.code, max_items=args.max_items)
            for lang in resolve(args.langs)
        }
    elif args.task == "mrag":
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(args.model)
        budgets = _parse_ctx(args.ctx)
        items_by_lang = {}
        for lang in resolve(args.langs):
            logging.getLogger("mlkv").info("building mrag items lang=%s", lang.code)
            items_by_lang[lang.code] = mrag.build(
                lang.code, tokenizer, budgets, max_items=args.max_items,
                layout=args.mrag_layout,
                instr_pad_tokens=args.mrag_instr_pad,
                tail=args.mrag_tail,
            )
        score_fn = mrag.score
    elif args.task == "mgsm-stuffed":
        from transformers import AutoTokenizer

        from mlkv.tasks import mgsm_stuffed

        tokenizer = AutoTokenizer.from_pretrained(args.model)
        budgets = _parse_ctx(args.ctx)
        items_by_lang = {
            lang.code: mgsm_stuffed.build(
                lang.code, tokenizer, budgets, max_items=args.max_items
            )
            for lang in resolve(args.langs)
        }
        # numeric exact match — the default scorer
    elif args.task == "mrag-bp":
        from mlkv.tasks import mrag, mrag_bp

        byte_budget = _parse_byte_ctx(args.byte_ctx)
        items_by_lang = {
            lang.code: mrag_bp.build(
                lang.code, byte_budget, max_items=args.max_items
            )
            for lang in resolve(args.langs)
        }
        score_fn = mrag.score
    else:
        raise SystemExit(f"task not implemented yet: {args.task}")

    task_name = args.task
    if args.nfd:
        from mlkv.tasks import nfd_variant

        items_by_lang = {k: nfd_variant(v) for k, v in items_by_lang.items()}
        task_name = f"{args.task}-nfd"

    configs = [compression.parse(c) for c in args.configs.split(",")]
    counts = runner.run_matrix(
        model_name=args.model,
        task_name=task_name,
        items_by_lang=items_by_lang,
        configs=configs,
        db_path=args.db,
        max_new_tokens=args.max_new_tokens,
        enable_thinking=args.thinking,
        score_fn=score_fn,
        cooldown_s=args.cooldown,
        batch_size=args.batch_size,
    )
    print(f"finished: {counts}")


def cmd_summary(args: argparse.Namespace) -> None:
    from mlkv import store

    conn = store.connect(args.db)
    rows = store.summary(conn)
    print(f"{'model':<28}{'task':<13}{'config':<14}{'lang':<6}{'n':>5}"
          f"{'acc':>7}{'tok':>7}{'bytes':>8}{'drift':>7}")
    for r in rows:
        drift = f"{r['avg_drift']:.3f}" if r["avg_drift"] is not None else "-"
        print(f"{r['model'][:27]:<28}{r['task']:<13}{r['config']:<14}{r['lang']:<6}"
              f"{r['n']:>5}{r['accuracy']:>7.3f}{r['avg_tokens']:>7.0f}"
              f"{r['avg_bytes']:>8.0f}{drift:>7}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mlkv")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fert = sub.add_parser("fertility", help="measure tokenizer fertility on MGSM questions")
    p_fert.add_argument("--models", required=True, help="comma-separated HF model names")
    p_fert.add_argument("--langs", default="all")
    p_fert.set_defaults(func=cmd_fertility)

    p_qc = sub.add_parser("qc-vi", help="print random MGSM-VI items next to EN originals")
    p_qc.add_argument("--n", type=int, default=30)
    p_qc.add_argument("--seed", type=int, default=42)
    p_qc.set_defaults(func=cmd_qc_vi)

    p_screen = sub.add_parser("screen-vi",
                              help="round-trip translation screen over all MGSM-VI items")
    p_screen.add_argument("--n-flag", type=int, default=15)
    p_screen.add_argument("--out", default="docs/mgsm-vi-screen.md")
    p_screen.set_defaults(func=cmd_screen_vi)

    p_audit = sub.add_parser("audit-vi",
                             help="LLM-assisted EN<->VI divergence audit (OpenRouter)")
    p_audit.add_argument("--model", default="google/gemini-2.5-flash")
    p_audit.add_argument("--out", default="docs/mgsm-vi-llm-audit.md")
    p_audit.set_defaults(func=cmd_audit_vi)

    p_run = sub.add_parser("run", help="run a generation matrix cell")
    p_run.add_argument("--model", required=True)
    p_run.add_argument("--task", default="mgsm",
                       choices=["mgsm", "mgsm-canary", "mrag", "mrag-bp",
                                "mgsm-stuffed"])
    p_run.add_argument("--byte-ctx", default="12k",
                       help="mrag-bp canonical ENGLISH byte budget per prompt "
                            "(KiB suffix), e.g. 12k = 12288 bytes")
    p_run.add_argument("--mrag-instr-pad", type=int, default=None,
                       help="pad the mrag instruction to N tokens with neutral "
                            "filler (same-language window dose-response)")
    p_run.add_argument("--mrag-tail", default="prose",
                       choices=["prose", "json", "tools"],
                       help="filler family for --mrag-instr-pad "
                            "(prose=G2; json/tools=fate-changer schema tail)")
    p_run.add_argument("--mrag-layout", default="instr-last",
                       choices=["instr-last", "instr-first"],
                       help="mrag prompt order; instr-first is the E1 "
                            "window-visibility intervention")
    p_run.add_argument("--ctx", default="8k,16k,32k",
                       help="mrag context budgets, e.g. 8k,16k,32k")
    p_run.add_argument("--nfd", action="store_true",
                       help="NFD-decompose prompts (within-model fertility probe; "
                            "task stored as <task>-nfd)")
    p_run.add_argument("--batch-size", type=int, default=1,
                       help="batched generation for non-press configs "
                            "(press cells always run single-stream)")
    p_run.add_argument("--cooldown", type=float, default=0.0,
                       help="seconds to sleep after each generation (thermal "
                            "relief on laptops; does not affect outputs)")
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
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = build_parser().parse_args()
    args.func(args)
