"""Round-trip translation screen for MGSM-VI (design doc §2.2, QC layer 2).

Back-translates every VI question to English with NLLB-200 (local, greedy —
deterministic) and scores chrF against the parallel EN original. A LOW chrF is
a *flag for human review*, not a verdict: NLLB's own noise also lowers chrF.
The screen complements the 30-item random audit: the audit bounds the overall
error rate; the screen sweeps the full 250 for the error class the audit
found (concrete-noun mistranslation), which surfaces in the round trip as a
diverging noun.

Triggered by the author's error-class ruling (docs/mgsm-vi-qc.md, 2026-08-09).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NLLB_MODEL = "facebook/nllb-200-distilled-600M"
DEFAULT_N_FLAG = 15


@dataclass
class ScreenRecord:
    index: int              # GSM8K/MGSM item index
    vi: str                 # VI question (patched dataset)
    en: str                 # parallel EN original (reference)
    back: str               # NLLB back-translation VI->EN
    chrf: float
    flagged: bool = False
    audited: bool = False   # was in the 30-item random audit sample


def back_translate(texts: list[str], batch_size: int = 8) -> list[str]:
    """VI -> EN with NLLB, greedy decoding (deterministic by construction)."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    from mlkv.runner import pick_device

    device = pick_device()
    tokenizer = AutoTokenizer.from_pretrained(NLLB_MODEL, src_lang="vie_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL).to(device).eval()
    eng_id = tokenizer.convert_tokens_to_ids("eng_Latn")

    out: list[str] = []
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            enc = tokenizer(batch, return_tensors="pt", padding=True,
                            truncation=True, max_length=512).to(device)
            gen = model.generate(
                **enc, forced_bos_token_id=eng_id,
                do_sample=False, num_beams=1, max_new_tokens=512,
            )
            out.extend(tokenizer.batch_decode(gen, skip_special_tokens=True))
            if (start // batch_size) % 4 == 0:
                logger.info("back-translated %d/%d", len(out), len(texts))
    return out


def chrf_scores(hyps: list[str], refs: list[str]) -> list[float]:
    from sacrebleu.metrics import CHRF

    metric = CHRF()
    return [metric.sentence_score(h, [r]).score for h, r in zip(hyps, refs)]


def rank_and_flag(records: list[ScreenRecord], n_flag: int) -> list[ScreenRecord]:
    """Sort ascending by chrF and flag the bottom n_flag."""
    records = sorted(records, key=lambda r: r.chrf)
    for i, record in enumerate(records):
        record.flagged = i < n_flag
    return records


def write_report(records: list[ScreenRecord], path: str, n_flag: int) -> None:
    scores = [r.chrf for r in records]
    scores_sorted = sorted(scores)
    flagged = [r for r in records if r.flagged]
    n_new = sum(1 for r in flagged if not r.audited)

    lines = [
        "# MGSM-VI Round-Trip Translation Screen — QC layer 2",
        "",
        f"- **Method**: VI question (patched dataset) → `{NLLB_MODEL}` (greedy, "
        "deterministic) → EN; sentence chrF (sacrebleu) vs the parallel EN original.",
        f"- **Scope**: all {len(records)} aligned items. **Flagged**: bottom "
        f"{n_flag} by chrF ({n_new} not already covered by the 30-item audit).",
        "- **Reading a flag**: low chrF = review candidate, NOT a verdict — "
        "NLLB noise also lowers chrF. Check the flagged VI text against EN; "
        "mark BROKEN only if the VI text changes the math.",
        f"- **Score distribution**: min {scores_sorted[0]:.1f} / "
        f"p25 {scores_sorted[len(scores)//4]:.1f} / "
        f"median {scores_sorted[len(scores)//2]:.1f} / "
        f"max {scores_sorted[-1]:.1f}",
        "- **Reviewer**: a native VI speaker. **Date**: __________",
        "",
        "**Verdict after review**: __ new BROKEN found (patch via "
        "`tasks/mgsm.py::VI_PATCHES` + record below)",
        "",
        "---",
        "",
    ]
    for k, r in enumerate(flagged, 1):
        audited = " *(already in 30-item audit)*" if r.audited else ""
        lines += [
            f"## F{k}. mgsm-vi-{r.index}  (chrF {r.chrf:.1f}){audited}",
            "",
            f"**VI**: {r.vi}",
            "",
            f"**EN**: {r.en}",
            "",
            f"**Back-translation**: {r.back}",
            "",
            "- [ ] OK  - [ ] BROKEN — note: ",
            "",
        ]
    lines += ["---", "", "## Full ranking (ascending chrF)", ""]
    lines += [f"| rank | item | chrF | flagged | audited |", "|---|---|---|---|---|"]
    lines += [
        f"| {i+1} | mgsm-vi-{r.index} | {r.chrf:.1f} | "
        f"{'✓' if r.flagged else ''} | {'✓' if r.audited else ''} |"
        for i, r in enumerate(records)
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def run_screen(out_path: str, n_flag: int = DEFAULT_N_FLAG,
               audited_seed: int = 42, audited_n: int = 30) -> list[ScreenRecord]:
    import random

    from mlkv.tasks import mgsm

    vi = {int(i["item_id"].rsplit("-", 1)[-1]): i for i in mgsm.load("vi")}
    en = {int(i["item_id"].rsplit("-", 1)[-1]): i for i in mgsm.load("en")}
    audited = set(random.Random(audited_seed).sample(sorted(vi), audited_n))

    indices = sorted(vi)
    backs = back_translate([vi[i]["question"] for i in indices])
    scores = chrf_scores(backs, [en[i]["question"] for i in indices])
    records = [
        ScreenRecord(index=i, vi=vi[i]["question"], en=en[i]["question"],
                     back=b, chrf=s, audited=i in audited)
        for i, b, s in zip(indices, backs, scores)
    ]
    records = rank_and_flag(records, n_flag)
    write_report(records, out_path, n_flag)
    logger.info("screen report written: %s", out_path)
    return records
