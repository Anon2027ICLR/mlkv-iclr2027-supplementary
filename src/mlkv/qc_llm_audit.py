"""LLM-assisted direct-comparison audit of MGSM-VI (QC layer 3).

Sends each (EN, VI) question pair to an LLM via OpenRouter and asks for
substantive divergences only (numbers, relations, dropped premises, concrete
nouns). Complements the other two QC layers:
- the 30-item human audit bounds the overall error rate,
- the chrF round-trip screen catches truncation/garbling but is blind to
  single-noun errors (all 4 known noun errors ranked outside its bottom-15),
- this layer catches exactly that class (validated on the 4 known errors:
  gemini-2.5-flash recovered 3/4 incl. the answer-changing one, with grounded
  quotes; see docs/mgsm-vi-llm-audit.md header for the record).

SUSPECT = review candidate for the native-speaker author, never a verdict —
consistent with the design commitment (no LLM judges in headline metrics;
data QC with human confirmation is out of that scope). API decoding is
temperature-0 but not bit-deterministic; the report records model + date.

Requires OPENROUTER_API_KEY in the environment.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"

PROMPT_TEMPLATE = """You are auditing the Vietnamese translation of an English math word problem for a research dataset. Compare VI against EN and report ONLY substantive divergences that change the math or solvability:
1. different/missing/extra numbers
2. flipped or altered mathematical relations (more/less, times, per, percent)
3. missing or added premises/constraints (including truncated text)
4. mistranslated concrete nouns that could change counts or quantities (e.g. unicycle vs bicycle, dozen vs pair)
Ignore style, naturalness, and word order. For every issue you MUST quote the exact EN phrase and the exact VI phrase — re-read the VI text to verify the phrase is really there before reporting. Reply with JSON only:
{"verdict": "OK" | "SUSPECT", "issues": [{"type": "...", "en_quote": "...", "vi_quote": "...", "detail": "one short line"}]}

EN: {en}

VI: {vi}"""


@dataclass
class AuditRecord:
    index: int
    en: str
    vi: str
    verdict: str                 # OK | SUSPECT | ERROR
    issues: list[dict] = field(default_factory=list)
    audited: bool = False        # in the 30-item human audit
    chrf_flagged: bool = False   # in the chrF screen's bottom-15


def audit_pair(en: str, vi: str, model: str = DEFAULT_MODEL,
               timeout: float = 120.0) -> tuple[dict, int, int]:
    """One API call; returns (parsed verdict JSON, prompt tokens, completion tokens)."""
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user",
                      "content": PROMPT_TEMPLATE.replace("{en}", en).replace("{vi}", vi)}],
    }).encode()
    request = urllib.request.Request(
        OPENROUTER_URL, data=body,
        headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"],
                 "Content-Type": "application/json"})
    response = json.load(urllib.request.urlopen(request, timeout=timeout))
    usage = response.get("usage", {})
    verdict = json.loads(response["choices"][0]["message"]["content"])
    return verdict, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def write_report(records: list[AuditRecord], path: str, model: str,
                 total_in: int, total_out: int) -> None:
    from datetime import date

    suspects = [r for r in records if r.verdict == "SUSPECT"]
    errors = [r for r in records if r.verdict == "ERROR"]
    lines = [
        "# MGSM-VI LLM-Assisted Audit — QC layer 3",
        "",
        f"- **Method**: direct EN↔VI comparison, `{model}` via OpenRouter, "
        "temperature 0, grounded quotes required. SUSPECT = review candidate "
        "for the author, not a verdict.",
        f"- **Run**: {date.today().isoformat()}, {len(records)} items, "
        f"{total_in}/{total_out} tokens.",
        "- **Sensitivity record** (pre-run, on the 4 known unpatched errors): "
        "caught xe-đạp-đơn (answer-changing), xanh-lá-cây, bộ-sưu-tập; missed "
        "wheat→lúa; 1 false positive on 1 clean control.",
        f"- **SUSPECT**: {len(suspects)} / {len(records)}"
        + (f"  |  **ERROR (API)**: {len(errors)}" if errors else ""),
        "- **Reviewer**: a native VI speaker. **Date**: __________",
        "",
        "**Verdict after review**: __ new BROKEN found",
        "",
        "---",
        "",
    ]
    for k, r in enumerate(suspects, 1):
        marks = []
        if r.audited:
            marks.append("in 30-item audit")
        if r.chrf_flagged:
            marks.append("chrF-flagged")
        suffix = f"  *({'; '.join(marks)})*" if marks else ""
        lines += [f"## S{k}. mgsm-vi-{r.index}{suffix}", "",
                  f"**VI**: {r.vi}", "", f"**EN**: {r.en}", ""]
        for issue in r.issues:
            lines.append(f"- `{issue.get('type', '?')}`: EN «{issue.get('en_quote', '')}» "
                         f"↔ VI «{issue.get('vi_quote', '')}» — {issue.get('detail', '')}")
        lines += ["", "- [ ] OK  - [ ] BROKEN — note: ", ""]
    if errors:
        lines += ["---", "", "## API errors (re-run these)", ""]
        lines += [f"- mgsm-vi-{r.index}" for r in errors]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def run_audit(out_path: str, model: str = DEFAULT_MODEL, max_workers: int = 8,
              audited_seed: int = 42, audited_n: int = 30,
              chrf_flagged: set[int] | None = None) -> list[AuditRecord]:
    import random

    from mlkv.tasks import mgsm

    if "OPENROUTER_API_KEY" not in os.environ:
        raise SystemExit("OPENROUTER_API_KEY not set")

    vi = {int(i["item_id"].rsplit("-", 1)[-1]): i["question"] for i in mgsm.load("vi")}
    en = {int(i["item_id"].rsplit("-", 1)[-1]): i["question"] for i in mgsm.load("en")}
    audited = set(random.Random(audited_seed).sample(sorted(vi), audited_n))
    chrf_flagged = chrf_flagged or set()
    indices = sorted(vi)

    totals = {"in": 0, "out": 0}

    def one(idx: int) -> AuditRecord:
        try:
            verdict, n_in, n_out = audit_pair(en[idx], vi[idx], model)
            totals["in"] += n_in
            totals["out"] += n_out
            return AuditRecord(idx, en[idx], vi[idx],
                               verdict.get("verdict", "ERROR"),
                               verdict.get("issues", []))
        except Exception as exc:
            logger.warning("audit failed for %d: %s", idx, exc)
            return AuditRecord(idx, en[idx], vi[idx], "ERROR")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        records = list(pool.map(one, indices))
    for r in records:
        r.audited = r.index in audited
        r.chrf_flagged = r.index in chrf_flagged
    write_report(records, out_path, model, totals["in"], totals["out"])
    logger.info("audit report written: %s (%d SUSPECT)", out_path,
                sum(r.verdict == "SUSPECT" for r in records))
    return records
